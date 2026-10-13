// The five heroes, what each is doing right now, who is talking to whom, and what each has spent.
//
// Layout (no overlapping speech): Boss on top with a wide bubble beside him; the four specialists
// in their own columns, each with a fixed speech box under the avatar; a hand-off feed at the bottom
// shows every question and answer between heroes. Beams are drawn between the real avatar positions.
import { useLayoutEffect, useRef, useState } from "react";
import { Avatar, HEROES } from "../heroes";
import type { Beam, Handoff, HeroState } from "../heroState";
import type { AgentName, Mood } from "../types";
import { TokenGauge } from "./TokenGauge";

export interface Reaction {
  mood: Mood;
  emoji: string;
  line: string;
}

const SPECIALISTS: AgentName[] = ["inventory", "accounting", "facilities", "customer_service"];

export const kTokens = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 100_000 ? 0 : 1)}k` : `${n}`);

function HeroFigure({ agent, state, reaction, size, ringRef, tokens }: {
  agent: AgentName;
  state: HeroState;
  reaction?: Reaction;
  size: number;
  ringRef: (el: HTMLDivElement | null) => void;
  tokens: number;
}) {
  const hero = HEROES[agent];
  const mood = reaction?.mood ?? state.mood;
  return (
    <div className={`hero ${state.active ? "is-active" : ""} hero--${mood}`} style={{ ["--hero" as string]: hero.color, ["--glow" as string]: hero.accent }}>
      <div className="hero__ring" ref={ringRef}>
        <Avatar agent={agent} mood={mood} size={size} />
        {reaction && <span className="hero__emoji">{reaction.emoji}</span>}
        {state.active && <span className="hero__live" title="Working now" />}
      </div>
      <div className="hero__name">{hero.name}</div>
      <div className="hero__role">
        {hero.emoji} {hero.role}
      </div>
      <div className="hero__tags">
        {agent === "customer_service" && <span className="voice-tag">Voice of the customer</span>}
        <span className={`token-chip ${tokens ? "" : "token-chip--zero"}`} title="Tokens this hero used on this mission">
          🪙 {kTokens(tokens)}
        </span>
      </div>
    </div>
  );
}

function Speech({ agent, state, reaction, wide = false }: { agent: AgentName; state: HeroState; reaction?: Reaction; wide?: boolean }) {
  const text = reaction?.line || state.bubble;
  const hero = HEROES[agent];
  return (
    <div
      className={`speech ${wide ? "speech--wide" : ""} ${state.kind === "asks" ? "speech--ask" : ""} ${state.active ? "speech--live" : ""} ${text ? "" : "speech--empty"}`}
      style={{ ["--hero" as string]: hero.color }}
      title={text ?? undefined}
    >
      <span className="speech__text" key={text ?? "none"}>
        {text ?? (wide ? "Waiting for a mission." : "Standing by.")}
      </span>
    </div>
  );
}

function HandoffFeed({ items }: { items: Handoff[] }) {
  return (
    <div className="handoffs">
      <div className="handoffs__title">🔁 Hand-offs between heroes</div>
      {items.length === 0 && <div className="handoffs__empty">When heroes ask each other or report back, the conversation shows here.</div>}
      {items.slice(-4).map((h) => (
        <div key={h.key} className={`handoff ${h.active ? "handoff--active" : ""} handoff--${h.kind}`}>
          <span className="handoff__who" style={{ color: HEROES[h.from].color }}>
            <Avatar agent={h.from} mood="idle" size={22} /> {HEROES[h.from].name}
          </span>
          <span className="handoff__arrow">{h.kind === "ask" ? "asks" : h.kind === "answer" ? "answers" : "reports to"} →</span>
          <span className="handoff__who" style={{ color: HEROES[h.to].color }}>
            <Avatar agent={h.to} mood="idle" size={22} /> {HEROES[h.to].name}
          </span>
          <span className="handoff__text" title={h.text}>
            {h.text}
          </span>
        </div>
      ))}
    </div>
  );
}

export function HeroBay({ heroes, beams, handoffs, reactions, title, tokens, loops, running, tokensByAgent }: {
  heroes: Record<AgentName, HeroState>;
  beams: Beam[];
  handoffs: Handoff[];
  reactions: Partial<Record<AgentName, Reaction>>;
  title: string;
  tokens: number;
  loops: number;
  running: boolean;
  tokensByAgent: Partial<Record<AgentName, number>>;
}) {
  const stage = useRef<HTMLDivElement>(null);
  const rings = useRef<Partial<Record<AgentName, HTMLDivElement | null>>>({});
  const [centers, setCenters] = useState<Partial<Record<AgentName, { x: number; y: number; r: number }>>>({});
  const [box, setBox] = useState({ w: 100, h: 100 });

  // Measure where each avatar really is, so beams join the actual heroes at any window size.
  useLayoutEffect(() => {
    const measure = () => {
      const s = stage.current?.getBoundingClientRect();
      if (!s) return;
      const next: Partial<Record<AgentName, { x: number; y: number; r: number }>> = {};
      for (const [agent, el] of Object.entries(rings.current)) {
        if (!el) continue;
        const r = el.getBoundingClientRect();
        next[agent as AgentName] = { x: r.left - s.left + r.width / 2, y: r.top - s.top + r.height / 2, r: r.width / 2 };
      }
      setCenters(next);
      setBox({ w: s.width, h: s.height });
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (stage.current) ro.observe(stage.current);
    return () => ro.disconnect();
  }, []);

  const path = (b: Beam) => {
    const a = centers[b.from];
    const c = centers[b.to];
    if (!a || !c) return "";
    if (b.from === "boss" || b.to === "boss") return `M${a.x} ${a.y} L${c.x} ${c.y}`;
    const lift = 70 + Math.abs(a.x - c.x) * 0.12; // specialist to specialist: arc over the row
    return `M${a.x} ${a.y - a.r} Q${(a.x + c.x) / 2} ${Math.min(a.y, c.y) - lift} ${c.x} ${c.y - c.r}`;
  };

  const ref = (agent: AgentName) => (el: HTMLDivElement | null) => {
    rings.current[agent] = el;
  };

  return (
    <section className={`panel bay ${running ? "bay--running" : ""}`}>
      <div className="bay__head">
        <h3 className="panel__title">Hero bay {running && <span className="live-dot">LIVE</span>}</h3>
        <span className="bay__mission">{title}</span>
      </div>
      <TokenGauge tokens={tokens} loops={loops} running={running} byAgent={tokensByAgent} />
      <div className="bay__stage" ref={stage}>
        <svg className="beams" viewBox={`0 0 ${box.w} ${box.h}`} aria-hidden>
          {beams.map((b) => (
            <path
              key={`${b.from}-${b.to}`}
              d={path(b)}
              className={`beam ${b.active ? "beam--active" : ""}`}
              stroke={HEROES[b.from].accent}
              fill="none"
            />
          ))}
        </svg>
        <div className="bay__boss">
          <HeroFigure agent="boss" state={heroes.boss} reaction={reactions.boss} size={108} ringRef={ref("boss")} tokens={tokensByAgent.boss ?? 0} />
          <Speech agent="boss" state={heroes.boss} reaction={reactions.boss} wide />
        </div>
        <div className="bay__squad">
          {SPECIALISTS.map((agent) => (
            <div key={agent} className="squad__col">
              <HeroFigure agent={agent} state={heroes[agent]} reaction={reactions[agent]} size={84} ringRef={ref(agent)} tokens={tokensByAgent[agent] ?? 0} />
              <Speech agent={agent} state={heroes[agent]} reaction={reactions[agent]} />
            </div>
          ))}
        </div>
      </div>
      <HandoffFeed items={handoffs} />
    </section>
  );
}
