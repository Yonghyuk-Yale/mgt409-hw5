"""A background event loop for everything that talks to the MCP server.

Why: the MCP server runs as a subprocess (stdio). On Windows, `uvicorn --reload` serves the app
on a SelectorEventLoop, which cannot start subprocesses. So the agent team and every MCP call run
on this dedicated thread, whose loop can (ProactorEventLoop on Windows). The web routes hand work
to it and await the result; nothing about the API changes.

The thread also holds one long-lived MCP connection for the API's own calls (ticket list, cash,
approvals, reset). Each team run opens its own connection.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import sys
import threading
from collections.abc import Coroutine
from typing import Any

import mcp_tools


class OpsLoop:
    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._toolset = None
        self._toolset_lock: asyncio.Lock | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        ready = threading.Event()

        def run() -> None:
            loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.loop = loop
            ready.set()
            loop.run_forever()
            # Not closed on purpose: MCP transports finalized later still schedule callbacks on it,
            # and a closed loop turns those into "Event loop is closed" noise at shutdown.

        self._thread = threading.Thread(target=run, name="ops-loop", daemon=True)
        self._thread.start()
        ready.wait()

    def submit(self, coro: Coroutine) -> concurrent.futures.Future:
        """Start a coroutine on the ops loop without waiting (used for team runs)."""
        assert self.loop is not None, "ops loop not started"
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    async def run(self, coro: Coroutine) -> Any:
        """Run a coroutine on the ops loop and await its result from the web server's loop."""
        return await asyncio.wrap_future(self.submit(coro))

    # -- the API's own MCP connection -------------------------------------------------

    async def _toolset_ready(self):
        if self._toolset_lock is None:
            self._toolset_lock = asyncio.Lock()
        async with self._toolset_lock:
            if self._toolset is None:
                toolset = mcp_tools.build_toolset()
                await toolset.__aenter__()
                self._toolset = toolset
        return self._toolset

    async def _call(self, name: str, args: dict) -> dict:
        toolset = await self._toolset_ready()
        try:
            return await mcp_tools.call(toolset, name, **args)
        except Exception:
            # The server process may have died; reconnect once and retry.
            await self._close_toolset()
            toolset = await self._toolset_ready()
            return await mcp_tools.call(toolset, name, **args)

    async def call(self, name: str, **args) -> dict:
        """Call one MCP tool from the API (backend-side, never an agent)."""
        return await self.run(self._call(name, args))

    async def _close_toolset(self) -> None:
        if self._toolset is not None:
            toolset, self._toolset = self._toolset, None
            try:
                await toolset.__aexit__(None, None, None)
            except Exception:
                pass

    def stop(self) -> None:
        if self.loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._close_toolset(), self.loop).result(timeout=10)
        except Exception:
            pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=10)
        self._thread = None
        self.loop = None


ops = OpsLoop()
