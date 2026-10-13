// Turns the live event feed into what each hero is doing right now.
import { HERO_ORDER } from "./heroes";
import type { AgentEvent, AgentName, Mood, TeamResult } from "./types";

export interface HeroState {
  mood: Mood;
  active: boolean;
  bubble: string | null;
  kind: string | null;
}

export interface Beam {
  from: AgentName;
  to: AgentName;
  active: boolean;
  label: string;
}

const PHASE_LABEL: Record<string, string> = {
  plan: "planning the mission",
  step: "working my step",
  delegation: "answering a teammate",
  customer_review: "reviewing for the customer",
  final: "writing the final report",
};

const clip = (s: string, n = 110) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

export function bubbleFor(e: AgentEvent): string {
  switch (e.kind) {
    case "loop_started":
      return `On it: ${PHASE_LABEL[e.phase ?? ""] ?? e.phase}…`;
    case "tool_call":
      return `🔧 ${clip(e.text.replace(/^calls /, ""), 90)}`;
    case "tool_result":
      return `📄 ${e.tool} ${e.ok === false ? "came back empty" : "✓"}`;
    case "asks":
      return `❓ ${clip(e.text, 140)}`;
    case "says":
      return `💬 ${clip(e.text, 140)}`;
    case "report":
      return `📋 ${clip(e.text.replace(/^\S+ reports: /, ""), 150)}`;
    case "retry":
      return "🔁 Fixing my answer…";
    case "loop_failed":
      return `⚠️ ${clip(e.text, 120)}`;
    default:
      return clip(e.text);
  }
}

const isRunEnd = (e: AgentEvent) => e.kind === "run_finished" || e.kind === "run_failed";

export function deriveHeroes(events: AgentEvent[], runId: string | null, result: TeamResult | null): Record<AgentName, HeroState> {
  const out = Object.fromEntries(
    HERO_ORDER.map((a) => [a, { mood: "idle" as Mood, active: false, bubble: null, kind: null }]),
  ) as Record<AgentName, HeroState>;
  const runEvents = runId ? events.filter((e) => e.team_run_id === runId) : [];

  for (const e of runEvents) {
    if (!e.agent || !(e.agent in out)) continue;
    const h = out[e.agent];
    if (e.kind === "tool_result" && h.kind === "asks") continue; // keep the question on screen
    h.bubble = bubbleFor(e);
    h.kind = e.kind;
    h.active = !["report", "loop_failed"].includes(e.kind);
    h.mood = e.kind === "report" ? "happy" : e.kind === "loop_failed" || e.kind === "retry" ? "worried" : "thinking";
  }
  if (runEvents.some(isRunEnd)) for (const a of HERO_ORDER) out[a].active = false;

  // No live events (e.g. after a backend restart): fall back to the saved reports.
  if (runEvents.length === 0 && result) {
    const say = (a: AgentName, text: string | undefined | null) => {
      if (text) out[a] = { mood: "happy", active: false, bubble: `📋 ${clip(text, 150)}`, kind: "report" };
    };
    for (const s of result.steps) say(s.agent, s.report?.summary ?? null);
    say("customer_service", result.customer_service_review?.summary);
    say("boss", result.final?.headline);
  }
  return out;
}

export interface Handoff {
  key: string;
  from: AgentName;
  to: AgentName;
  kind: "ask" | "answer" | "report";
  text: string;
  active: boolean;
}

/** The conversation between heroes: questions, the answers that come back, and reports to Boss. */
export function deriveHandoffs(events: AgentEvent[], runId: string | null): Handoff[] {
  if (!runId) return [];
  const runEvents = events.filter((e) => e.team_run_id === runId);
  const callerOf = new Map<string, string>(); // loop_id -> who called it
  const out: Handoff[] = [];
  for (const e of runEvents) {
    if (e.kind === "loop_started" && e.loop_id && e.called_by) callerOf.set(e.loop_id, e.called_by);
    if (e.kind === "asks" && e.agent && e.to) {
      out.push({ key: `q${e.seq}`, from: e.agent, to: e.to, kind: "ask", text: e.text.replace(/^asks \S+: /, ""), active: true });
    }
    if (e.kind === "report" && e.agent && e.loop_id) {
      const caller = callerOf.get(e.loop_id);
      const text = e.text.replace(/^\S+ reports: /, "");
      if (e.phase === "delegation" && caller && caller !== "team") {
        // the answer closes the matching question
        const q = [...out].reverse().find((h) => h.kind === "ask" && h.from === caller && h.to === e.agent && h.active);
        if (q) q.active = false;
        out.push({ key: `a${e.seq}`, from: e.agent, to: caller as AgentName, kind: "answer", text, active: false });
      } else if (e.agent !== "boss" && (e.phase === "step" || e.phase === "customer_review")) {
        out.push({ key: `r${e.seq}`, from: e.agent, to: "boss", kind: "report", text, active: false });
      }
    }
  }
  if (runEvents.some(isRunEnd)) out.forEach((h) => (h.active = false));
  return out;
}

/** Tokens each hero spent in one run, from the live feed (each finished loop reports its own share). */
export function tokensFromEvents(events: AgentEvent[], runId: string | null): Partial<Record<AgentName, number>> {
  const out: Partial<Record<AgentName, number>> = {};
  if (!runId) return out;
  for (const e of events) {
    if (e.team_run_id === runId && e.agent && (e.kind === "report" || e.kind === "loop_failed") && typeof e.tokens === "number") {
      out[e.agent] = (out[e.agent] ?? 0) + e.tokens;
    }
  }
  return out;
}

/** A beam joins two heroes while one is working for the other (Boss assigning, or a teammate asking). */
export function deriveBeams(events: AgentEvent[], runId: string | null): Beam[] {
  if (!runId) return [];
  const runEvents = events.filter((e) => e.team_run_id === runId);
  const byLoop = new Map<string, Beam>();
  for (const e of runEvents) {
    if (e.kind === "loop_started" && e.agent && e.loop_id && e.called_by && e.called_by !== "team" && e.called_by !== e.agent) {
      byLoop.set(e.loop_id, {
        from: e.called_by as AgentName,
        to: e.agent,
        active: true,
        label: e.phase === "delegation" ? "asks" : "assigns",
      });
    }
    if ((e.kind === "report" || e.kind === "loop_failed") && e.loop_id && byLoop.has(e.loop_id)) {
      byLoop.get(e.loop_id)!.active = false;
    }
  }
  const ended = runEvents.some(isRunEnd);
  const byPair = new Map<string, Beam>();
  for (const b of byLoop.values()) {
    if (ended) b.active = false;
    const key = `${b.from}>${b.to}`;
    if (!byPair.get(key)?.active) byPair.set(key, b);
  }
  return [...byPair.values()];
}
