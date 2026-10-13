// Campus Customs HQ: the owner's dashboard for the five-agent operations team.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, API_BASE } from "./api";
import { Balance } from "./components/Balance";
import { CashForecast } from "./components/CashForecast";
import { CashLedger } from "./components/CashLedger";
import { CommsDrawer } from "./components/CommsDrawer";
import { DecisionDesk } from "./components/DecisionDesk";
import { HeroBay, type Reaction } from "./components/HeroBay";
import { MissionBoard } from "./components/MissionBoard";
import { TransactionsModal } from "./components/TransactionsModal";
import { deriveBeams, deriveHandoffs, deriveHeroes, tokensFromEvents } from "./heroState";
import { HERO_ORDER } from "./heroes";
import { play, sound } from "./sound";
import type { AgentEvent, AgentName, ApprovalRequest, Cash, Ticket, TicketDetail, TraceLoop } from "./types";

type Toast = { msg: string; tone: "ok" | "warn" | "error" } | null;

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  // ?ticket=101 opens that mission; ?drawer=log|summary|compare opens the comms drawer (handy for screenshots)
  const params = new URLSearchParams(window.location.search);
  const [selectedId, setSelectedId] = useState<number | null>(() => Number(params.get("ticket")) || null);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [cash, setCash] = useState<Cash | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [activeRun, setActiveRun] = useState<{ runId: string; ticketId: number } | null>(null);
  const [trace, setTrace] = useState<TraceLoop[]>([]);
  const [reactions, setReactions] = useState<Partial<Record<AgentName, Reaction>>>({});
  const [stamps, setStamps] = useState<Record<number, "approved" | "denied">>({});
  const [stampedId, setStampedId] = useState<number | null>(null);
  const [busy, setBusy] = useState<number | "resolve" | "rerun" | null>(null);
  const [toast, setToast] = useState<Toast>(null);
  const [drawerOpen, setDrawerOpen] = useState(() => params.has("drawer"));
  const [txnOpen, setTxnOpen] = useState(false);
  const [txnKey, setTxnKey] = useState(0);
  const [soundOn, setSoundOn] = useState(false);
  const [signer, setSigner] = useState(() => localStorage.getItem("hq-signer") || "Owner");
  const [offline, setOffline] = useState<string | null>(null);
  const lastSeq = useRef(0);
  const selectedRef = useRef<number | null>(null);
  selectedRef.current = selectedId;
  const reactionTimer = useRef<number | null>(null);

  const notify = useCallback((msg: string, tone: "ok" | "warn" | "error" = "ok") => {
    setToast({ msg, tone });
    window.setTimeout(() => setToast((t) => (t?.msg === msg ? null : t)), 4500);
  }, []);

  const react = useCallback((r: Partial<Record<AgentName, Reaction>>, ms = 3800) => {
    setReactions(r);
    if (reactionTimer.current) window.clearTimeout(reactionTimer.current);
    reactionTimer.current = window.setTimeout(() => setReactions({}), ms);
  }, []);

  // ---------------------------------------------------------------- loading

  const loadBoard = useCallback(async () => {
    try {
      const [t, c, a] = await Promise.all([api.tickets(), api.cash(), api.approvals()]);
      setTickets(t.tickets);
      setCash(c);
      setApprovals(a.requests);
      setOffline(null);
      setSelectedId((id) => id ?? (t.tickets.find((x) => !x.is_resolved) ?? t.tickets[0])?.id ?? null);
    } catch (e) {
      setOffline((e as Error).message);
    }
  }, []);

  const loadDetail = useCallback(async (id: number | null) => {
    if (id === null) return null;
    try {
      const d = await api.ticket(id);
      if (selectedRef.current === id) setDetail(d); // ignore answers for a ticket no longer selected
      return d;
    } catch {
      return null;
    }
  }, []);

  // first load: board + is the team already working?
  useEffect(() => {
    void loadBoard();
    api
      .runs()
      .then((r) => {
        const running = r.runs.find((x) => x.status === "running");
        if (running) setActiveRun({ runId: running.run_id, ticketId: running.ticket_id });
      })
      .catch(() => undefined);
  }, [loadBoard]);

  // board + cash refresh
  useEffect(() => {
    const t = window.setInterval(loadBoard, activeRun ? 2500 : 5000);
    return () => window.clearInterval(t);
  }, [loadBoard, activeRun]);

  // selected ticket detail
  useEffect(() => {
    void loadDetail(selectedId);
    const t = window.setInterval(() => void loadDetail(selectedId), activeRun?.ticketId === selectedId ? 2500 : 6000);
    return () => window.clearInterval(t);
  }, [selectedId, loadDetail, activeRun]);

  // live events
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const r = await api.events(lastSeq.current);
        if (stop || r.events.length === 0) return;
        lastSeq.current = r.latest_seq;
        setEvents((prev) => [...prev, ...r.events].slice(-4000));
      } catch {
        /* offline is reported by the board poll */
      }
    };
    void tick();
    const t = window.setInterval(tick, 1200);
    return () => {
      stop = true;
      window.clearInterval(t);
    };
  }, []);

  // run finished?
  useEffect(() => {
    if (!activeRun) return;
    const end = events.find((e) => e.team_run_id === activeRun.runId && (e.kind === "run_finished" || e.kind === "run_failed"));
    const check = async () => {
      const run = await api.runDetail(activeRun.runId).catch(() => null);
      if (!end && run?.status === "running") return;
      setActiveRun(null);
      setSelectedId(activeRun.ticketId);
      await Promise.all([loadBoard(), loadDetail(activeRun.ticketId)]);
      if (run?.status === "failed") {
        notify(`The mission failed: ${run.error}`, "error");
        react(Object.fromEntries(HERO_ORDER.map((a) => [a, { mood: "sad", emoji: "😞", line: "" }])) as Partial<Record<AgentName, Reaction>>);
      } else {
        play("done");
        notify("Boss is back with a recommendation. Your call!", "ok");
        react({ boss: { mood: "celebrate", emoji: "📨", line: "Mission report is on your desk." } }, 3000);
      }
    };
    if (end) void check();
    const t = window.setInterval(check, 4000);
    return () => window.clearInterval(t);
  }, [events, activeRun, loadBoard, loadDetail, notify, react]);

  // trace for the selected ticket's latest finished run
  const latestRunId = detail?.latest_run?.status === "completed" ? detail.latest_run.run_id : null;
  useEffect(() => {
    if (!latestRunId) {
      setTrace([]);
      return;
    }
    api
      .trace(latestRunId)
      .then((t) => setTrace(t.loops))
      .catch(() => setTrace([]));
  }, [latestRunId]);

  // ---------------------------------------------------------------- actions

  const assemble = async (ticketId: number, feedback?: string) => {
    setSelectedId(ticketId);
    setBusy(feedback !== undefined ? "rerun" : null);
    try {
      const r = await api.run(ticketId, feedback);
      setActiveRun({ runId: r.run_id, ticketId });
      setStamps({});
      play("assemble");
      react({ boss: { mood: "celebrate", emoji: "🛡️", line: feedback !== undefined ? "Heroes, again, with the owner's feedback!" : "Heroes, assemble!" } }, 2500);
      void loadDetail(ticketId);
    } catch (e) {
      notify((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const resolve = async (ticketId: number) => {
    setBusy("resolve");
    try {
      await api.resolve(ticketId);
      setStampedId(ticketId);
      window.setTimeout(() => play("stamp"), 250);
      window.setTimeout(() => play("done"), 650);
      react(Object.fromEntries(HERO_ORDER.map((a) => [a, { mood: "celebrate", emoji: "🎉", line: "" }])) as Partial<Record<AgentName, Reaction>>, 3000);
      notify(`Ticket #${ticketId} resolved. Mission complete!`, "ok");
      await Promise.all([loadBoard(), loadDetail(ticketId)]);
    } catch (e) {
      notify((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const approve = async (req: ApprovalRequest) => {
    setBusy(req.id);
    try {
      const r = await api.approve(req.id, signer);
      setStamps((s) => ({ ...s, [req.id]: "approved" }));
      play("stamp");
      if (r.result.cash_moved) window.setTimeout(() => play("cash"), 350);
      setCash(r.cash);
      setTxnKey((k) => k + 1);
      react({
        accounting: { mood: "happy", emoji: "💸", line: r.result.cash_moved ? `Paid. Ledger updated, ${r.cash.balance.toLocaleString("en-US", { style: "currency", currency: "USD" })} left.` : "Approved quote logged." },
        boss: { mood: "celebrate", emoji: "👍", line: "Good call, boss." },
        customer_service: req.ticket_id && [101, 103].includes(req.ticket_id) ? { mood: "happy", emoji: "😊", line: "The customer will be glad." } : undefined,
        facilities: req.kind === "rent_payment" ? { mood: "happy", emoji: "🏛️", line: "Rent's handled. The walls stand." } : undefined,
        inventory: req.kind === "purchase_order" ? { mood: "happy", emoji: "📦", line: "Restock on its way." } : undefined,
      });
      const d = await loadDetail(req.ticket_id ?? selectedId);
      await loadBoard();
      // all decided and nothing denied this round → close the mission with a stamp
      if (d && req.ticket_id) {
        const cycle = new Set((d.latest_run?.result?.approval_requests ?? []).filter((x) => x.status === "pending_human").map((x) => x.id));
        const pendingLeft = d.approval_requests.some((x) => x.status === "pending_human");
        const deniedThisRound = d.approval_requests.some((x) => x.status === "rejected" && cycle.has(x.id));
        if (!pendingLeft && !deniedThisRound) window.setTimeout(() => void resolve(req.ticket_id!), 1400);
      }
    } catch (e) {
      const err = e as ApiError;
      notify(err.message, err.status === 409 ? "warn" : "error");
      react({ accounting: { mood: "worried", emoji: "⛔", line: `Can't do it: ${err.message}` } }, 5000);
      void loadDetail(req.ticket_id ?? selectedId);
    } finally {
      setBusy(null);
    }
  };

  const deny = async (req: ApprovalRequest, note: string) => {
    setBusy(req.id);
    try {
      await api.reject(req.id, signer, note);
      setStamps((s) => ({ ...s, [req.id]: "denied" }));
      play("deny");
      react({
        boss: { mood: "worried", emoji: "🫡", line: "Understood. We'll rethink it." },
        accounting: { mood: "worried", emoji: "😬", line: "Request withdrawn." },
        inventory: { mood: "worried", emoji: "🤔", line: "Let me look for other options." },
        customer_service: { mood: "worried", emoji: "💭", line: "I'll keep the customer in mind." },
        facilities: { mood: "worried", emoji: "😐", line: "" },
      }, 4500);
      await Promise.all([loadDetail(req.ticket_id ?? selectedId), loadBoard()]);
    } catch (e) {
      notify((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const reset = async () => {
    if (!window.confirm("Start over? This resets the shop database to its starting values (cash $3,400, all tickets open).")) return;
    try {
      await api.reset();
      setStamps({});
      setStampedId(null);
      setTrace([]);
      play("stamp");
      notify("Fresh start: the database is back to its starting values.", "ok");
      await Promise.all([loadBoard(), loadDetail(selectedId)]);
    } catch (e) {
      notify((e as Error).message, "error");
    }
  };

  // ---------------------------------------------------------------- derived

  const runId = activeRun && activeRun.ticketId === selectedId ? activeRun.runId : detail?.latest_run?.run_id ?? null;
  const result = detail?.latest_run?.result ?? null;
  const heroes = useMemo(() => deriveHeroes(events, runId, result), [events, runId, result]);
  const beams = useMemo(() => deriveBeams(events, runId), [events, runId]);
  const handoffs = useMemo(() => deriveHandoffs(events, runId), [events, runId]);
  // tokens per hero: live from the event feed; after a run, from the audit trail (survives restarts)
  const tokensByAgent = useMemo(() => {
    const live = tokensFromEvents(events, runId);
    if (Object.keys(live).length > 0 || !trace.length || activeRun) return live;
    const fromTrace: Partial<Record<AgentName, number>> = {};
    for (const l of trace) fromTrace[l.agent] = (fromTrace[l.agent] ?? 0) + (l.tokens ?? 0);
    return fromTrace;
  }, [events, runId, trace, activeRun]);
  const running = !!activeRun && activeRun.ticketId === selectedId;
  const lastWithTokens = [...events].reverse().find((e) => e.team_run_id === runId && typeof e.team_tokens === "number");
  const tokens = running ? lastWithTokens?.team_tokens ?? 0 : result?.usage?.total_tokens ?? detail?.latest_run?.tokens ?? 0;
  const loops = running ? lastWithTokens?.loops ?? 0 : result?.usage?.agent_loops ?? 0;
  const selected = tickets.find((t) => t.id === selectedId);
  const bayTitle = selected ? `#${selected.id} · ${selected.subject} — ${selected.requester}` : "Pick a mission";

  return (
    <div className="app">
      <div className="brand">YALE SOM - Yonghyuk Choi</div>
      <header className="topbar">
        <div className="topbar__title">
          <img src="/shield.svg" alt="" width={40} height={40} />
          <div>
            <h1>Campus Customs HQ</h1>
            <p className="topbar__mission">
              <b>Our mission:</b> get every customer the right gear, keep the shop&apos;s doors open, and never spend a dollar the owner hasn&apos;t approved.
            </p>
            <p>
              Shop date <b>{cash?.shop_today ?? "—"}</b> · five heroes, one owner
            </p>
          </div>
        </div>
        <div className="topbar__actions">
          <Balance value={cash?.balance ?? null} onClick={() => setTxnOpen(true)} />
          <button
            className={`icon-btn ${soundOn ? "on" : ""}`}
            title={soundOn ? "Sound on" : "Sound off"}
            onClick={() => {
              sound.set(!soundOn);
              setSoundOn(!soundOn);
              if (!soundOn) window.setTimeout(() => play("cash"), 50);
            }}
          >
            {soundOn ? "🔊" : "🔇"}
          </button>
          <button className="btn btn--ghost" onClick={reset} disabled={!!activeRun} title="Reset the database to its starting values">
            ⟳ Refresh
          </button>
        </div>
      </header>

      {offline && (
        <div className="offline">
          ⚠️ {offline} <span className="muted">({API_BASE})</span>
        </div>
      )}

      <main className="grid">
        <div className="col col--left">
          <MissionBoard
            tickets={tickets}
            selectedId={selectedId}
            runningTicketId={activeRun?.ticketId ?? null}
            stampedId={stampedId}
            onSelect={setSelectedId}
            onAssemble={(id) => void assemble(id)}
          />
          <CashLedger balance={cash?.balance ?? null} refreshKey={txnKey} />
          <CashForecast cash={cash} approvals={approvals} />
        </div>
        <HeroBay
          heroes={heroes}
          beams={beams}
          handoffs={handoffs}
          reactions={reactions}
          title={bayTitle}
          tokens={tokens}
          loops={loops}
          running={running}
          tokensByAgent={tokensByAgent}
        />
        <DecisionDesk
          detail={detail && detail.ticket.id === selectedId ? detail : null}
          running={running}
          busy={busy}
          stamps={stamps}
          signer={signer}
          onSigner={(s) => {
            setSigner(s);
            localStorage.setItem("hq-signer", s);
          }}
          onApprove={(r) => void approve(r)}
          onDeny={(r, note) => void deny(r, note)}
          onRerun={(extra) => selectedId && void assemble(selectedId, extra)}
          onResolve={() => selectedId && void resolve(selectedId)}
        />
      </main>

      <CommsDrawer initialTab={(params.get("drawer") as "log" | "summary" | "compare" | null) ?? undefined} events={events} ticketId={selectedId} result={result} trace={trace} open={drawerOpen} onToggle={() => setDrawerOpen(!drawerOpen)} />
      <div className="brand brand--bottom">YALE SOM - Yonghyuk Choi</div>

      {txnOpen && <TransactionsModal onClose={() => setTxnOpen(false)} refreshKey={txnKey} />}
      {toast && <div className={`toast toast--${toast.tone}`}>{toast.msg}</div>}
    </div>
  );
}
