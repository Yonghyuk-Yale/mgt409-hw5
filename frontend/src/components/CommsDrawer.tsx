// Bottom drawer: every bubble so far, a short summary per hero, and Expected vs Actual.
import { useEffect, useMemo, useRef, useState } from "react";
import { EXPECTED } from "../expected";
import { Avatar, HEROES, HERO_ORDER, heroName } from "../heroes";
import { bubbleFor } from "../heroState";
import type { AgentEvent, AgentName, TeamResult, TraceLoop } from "../types";

type Tab = "log" | "summary" | "compare";

const SYSTEM_KINDS = new Set(["run_started", "run_finished", "run_failed", "approved", "rejected", "executed", "execution_refused", "ticket_resolved", "reset"]);

function LogTab({ events }: { events: AgentEvent[] }) {
  const [hero, setHero] = useState<AgentName | "all">("all");
  const [handoffsOnly, setHandoffsOnly] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const shown = events.filter(
    (e) =>
      (hero === "all" || e.agent === hero || (e.kind === "asks" && e.to === hero)) &&
      (!handoffsOnly || e.kind === "asks" || e.kind === "report" || (e.kind === "loop_started" && e.called_by && e.called_by !== "team") || SYSTEM_KINDS.has(e.kind)) &&
      (showResults || e.kind !== "tool_result"),
  );
  useEffect(() => {
    // Newer browsers return a Promise from scrollIntoView; never hand it back to React as a cleanup.
    void end.current?.scrollIntoView({ block: "end" });
  }, [shown.length]);
  return (
    <div className="log">
      <div className="log__filters">
        <button className={`chip-btn ${hero === "all" ? "on" : ""}`} onClick={() => setHero("all")}>
          Everyone
        </button>
        {HERO_ORDER.map((a) => (
          <button key={a} className={`chip-btn ${hero === a ? "on" : ""}`} onClick={() => setHero(a)} style={{ ["--hero" as string]: HEROES[a].color }}>
            {HEROES[a].emoji} {HEROES[a].name}
          </button>
        ))}
        <label className="toggle">
          <input type="checkbox" checked={handoffsOnly} onChange={(e) => setHandoffsOnly(e.target.checked)} /> Hand-offs & reports only
        </label>
        <label className="toggle">
          <input type="checkbox" checked={showResults} onChange={(e) => setShowResults(e.target.checked)} /> Show tool results
        </label>
      </div>
      <div className="log__list">
        {shown.length === 0 && <p className="muted">Nothing yet. Assemble the team on a mission.</p>}
        {shown.map((e) =>
          e.agent ? (
            <div key={e.seq} className={`log__item log__item--${e.kind}`} style={{ ["--hero" as string]: HEROES[e.agent]?.color }}>
              <Avatar agent={e.agent} mood={e.kind === "report" ? "happy" : e.kind === "loop_failed" ? "worried" : "idle"} size={30} />
              <div>
                <div className="log__who">
                  {heroName(e.agent)}
                  {e.kind === "asks" && e.to && <span> → {heroName(e.to)}</span>}
                  {e.kind === "loop_started" && e.called_by && e.called_by !== "team" && <span> ← {heroName(e.called_by)}</span>}
                  <time>{new Date(e.at).toLocaleTimeString("en-US")}</time>
                </div>
                <div className="log__text">{bubbleFor(e)}</div>
              </div>
            </div>
          ) : (
            <div key={e.seq} className={`log__system log__system--${e.kind}`}>
              <time>{new Date(e.at).toLocaleTimeString("en-US")}</time> {e.text}
            </div>
          ),
        )}
        <div ref={end} />
      </div>
    </div>
  );
}

function SummaryTab({ result, trace }: { result: TeamResult | null; trace: TraceLoop[] }) {
  if (!result) return <p className="muted pad">Run a mission to see what each hero did.</p>;
  const did: Partial<Record<AgentName, string[]>> = {};
  const add = (a: AgentName, s?: string | null) => s && (did[a] = [...(did[a] ?? []), s]);
  add("boss", result.plan ? `Plan: ${result.plan.understanding}` : null);
  for (const s of result.steps) add(s.agent, s.report?.summary ?? (s.error ? `Failed: ${s.error}` : null));
  add("customer_service", result.customer_service_review?.summary);
  add("boss", result.final ? `Final call: ${result.final.headline}` : null);
  const tools = (a: AgentName) => [...new Set(trace.filter((l) => l.agent === a).flatMap((l) => l.tools))];
  const asked = (a: AgentName) => [...new Set(trace.filter((l) => l.called_by === a && l.phase === "delegation").map((l) => heroName(l.agent)))];
  const tokens = (a: AgentName) => trace.filter((l) => l.agent === a).reduce((s, l) => s + (l.tokens ?? 0), 0);
  return (
    <div className="summary">
      {HERO_ORDER.map((a) => {
        const lines = did[a];
        const used = tools(a);
        if (!lines && used.length === 0) {
          return (
            <article key={a} className="summary__card summary__card--idle">
              <Avatar agent={a} mood="idle" size={42} />
              <div>
                <b>{HEROES[a].name}</b>
                <p className="muted">Not needed on this mission.</p>
              </div>
            </article>
          );
        }
        return (
          <article key={a} className="summary__card" style={{ ["--hero" as string]: HEROES[a].color }}>
            <Avatar agent={a} mood="happy" size={42} />
            <div>
              <b>{HEROES[a].name}</b> <span className="muted">· {HEROES[a].role} · {Math.round(tokens(a) / 1000)}k tokens</span>
              {lines?.map((l) => (
                <p key={l}>{l}</p>
              ))}
              {a === "customer_service" && result.customer_service_review && (
                <p className="summary__stance">Stance: {result.customer_service_review.stance.replace(/_/g, " ")}</p>
              )}
              {asked(a).length > 0 && <p className="summary__asked">Asked: {asked(a).join(", ")}</p>}
              {used.length > 0 && (
                <div className="summary__tools">
                  {used.map((t) => (
                    <code key={t}>{t}</code>
                  ))}
                </div>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}

function CompareTab({ ticketId, result, trace }: { ticketId: number | null; result: TeamResult | null; trace: TraceLoop[] }) {
  const exp = ticketId ? EXPECTED[ticketId] : undefined;
  if (!exp) return <p className="muted pad">Pick a mission.</p>;
  const actualFirst = result?.plan?.steps?.[0]?.agent ?? null;
  const pairs = new Set(
    trace
      .filter((l) => l.called_by !== "team" || l.phase === "customer_review")
      .map((l) => `${l.phase === "customer_review" ? "boss" : l.called_by}>${l.agent}`),
  );
  const used = new Set(trace.flatMap((l) => l.tools.map((t) => `${l.agent}:${t}`)));
  const hit = (b: boolean) => (result ? (b ? "✅" : "❌") : "⏳");
  const handoffHits = exp.handoffs.filter((h) => pairs.has(`${h.from}>${h.to}`)).length;
  // a row of the Expected table matches when one of its agents used any of its tools
  const rowHit = (r: (typeof exp.tools)[number]) => r.agents.some((a) => r.tools.some((t) => used.has(`${a}:${t}`)));
  const toolHits = exp.tools.filter(rowHit).length;
  return (
    <div className="compare">
      <div className="compare__col">
        <h4>First call</h4>
        <p>
          Expected: <b>{heroName(exp.firstAgent)}</b> — {exp.why}
        </p>
        <p>
          Actual: <b>{actualFirst ? heroName(actualFirst) : "not run yet"}</b> {hit(actualFirst === exp.firstAgent)}
        </p>
      </div>
      <div className="compare__col">
        <h4>
          Hand-offs {result && <span className="score">{handoffHits}/{exp.handoffs.length}</span>}
        </h4>
        <ul>
          {exp.handoffs.map((h) => (
            <li key={`${h.from}${h.to}${h.label}`}>
              {hit(pairs.has(`${h.from}>${h.to}`))} {heroName(h.from)} → {heroName(h.to)} <span className="muted">· {h.label}</span>
            </li>
          ))}
        </ul>
        {result && (
          <p className="muted">
            Actual: {[...pairs].map((p) => p.split(">").map((x) => heroName(x)).join(" → ")).join(" · ") || "none"}
          </p>
        )}
      </div>
      <div className="compare__col">
        <h4>
          MCP tools {result && <span className="score">{toolHits}/{exp.tools.length}</span>}
        </h4>
        <ul className="compare__tools">
          {exp.tools.map((r) => (
            <li key={`${r.agents.join("+")}${r.tools.join("+")}`}>
              {hit(rowHit(r))}{" "}
              {r.tools.map((t, i) => (
                <span key={t}>
                  {i > 0 && " / "}
                  <code>{t}</code>
                </span>
              ))}{" "}
              <span className="muted">by {r.agents.map((a) => heroName(a)).join(" / ")}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function CommsDrawer({ events, ticketId, result, trace, open, onToggle, initialTab }: {
  initialTab?: Tab;
  events: AgentEvent[];
  ticketId: number | null;
  result: TeamResult | null;
  trace: TraceLoop[];
  open: boolean;
  onToggle: () => void;
}) {
  const [tab, setTab] = useState<Tab>(initialTab && ["log", "summary", "compare"].includes(initialTab) ? initialTab : "log");
  const ticketEvents = useMemo(
    () => events.filter((e) => ticketId === null || e.ticket_id === ticketId || (!e.ticket_id && SYSTEM_KINDS.has(e.kind))),
    [events, ticketId],
  );
  const latest = [...ticketEvents].reverse().find((e) => e.agent);
  return (
    <section className={`drawer ${open ? "is-open" : ""}`}>
      <header className="drawer__bar" onClick={onToggle}>
        <span className="drawer__arrow">{open ? "▼" : "▲"}</span>
        <b>Comms log</b>
        <span className="drawer__latest">{latest ? `${heroName(latest.agent)}: ${bubbleFor(latest)}` : "No transmissions yet"}</span>
        <span className="drawer__count">{ticketEvents.length} events</span>
      </header>
      {open && (
        <div className="drawer__body">
          <nav className="tabs">
            {(
              [
                ["log", "💬 All bubbles"],
                ["summary", "📋 Hero summary"],
                ["compare", "🎯 Expected vs Actual"],
              ] as [Tab, string][]
            ).map(([k, label]) => (
              <button key={k} className={`tab ${tab === k ? "on" : ""}`} onClick={() => setTab(k)}>
                {label}
              </button>
            ))}
          </nav>
          {tab === "log" && <LogTab events={ticketEvents} />}
          {tab === "summary" && <SummaryTab result={result} trace={trace} />}
          {tab === "compare" && <CompareTab ticketId={ticketId} result={result} trace={trace} />}
        </div>
      )}
    </section>
  );
}
