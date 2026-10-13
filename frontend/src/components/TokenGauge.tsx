// Mission fuel: the team's token budget for this ticket (150,000 tokens, 12 agent loops),
// split by hero so you can see who spent what.
import { HEROES, HERO_ORDER } from "../heroes";
import type { AgentName } from "../types";

const k = (n: number) => `${Math.round(n / 1000)}k`;

export function TokenGauge({ tokens, loops, limit = 150_000, maxLoops = 12, running, byAgent }: {
  tokens: number;
  loops: number;
  limit?: number;
  maxLoops?: number;
  running: boolean;
  byAgent: Partial<Record<AgentName, number>>;
}) {
  const used = Math.min(1, tokens / limit);
  const reserve = 25_000 / limit;
  const tone = used > 0.83 ? "danger" : used > 0.6 ? "warn" : "ok";
  const known = HERO_ORDER.reduce((s, a) => s + (byAgent[a] ?? 0), 0);
  const inFlight = Math.max(0, tokens - known); // loops still running have not reported their share yet
  return (
    <div className={`fuel ${running ? "fuel--running" : ""}`} title="Boss's safety budget: 150k tokens per ticket, 25k reserved for the final report">
      <div className="fuel__head">
        <span>⛽ Mission fuel</span>
        <b>
          {k(tokens)} / {k(limit)} tokens · loop {loops}/{maxLoops}
        </b>
      </div>
      <div className={`fuel__track fuel__track--${tone}`}>
        {HERO_ORDER.map((a) =>
          byAgent[a] ? (
            <div
              key={a}
              className="fuel__seg"
              style={{ width: `${((byAgent[a] ?? 0) / limit) * 100}%`, background: HEROES[a].color }}
              title={`${HEROES[a].name}: ${(byAgent[a] ?? 0).toLocaleString()} tokens`}
            />
          ) : null,
        )}
        {inFlight > 0 && <div className="fuel__seg fuel__seg--flight" style={{ width: `${(inFlight / limit) * 100}%` }} title="In progress" />}
        <div className="fuel__reserve" style={{ width: `${reserve * 100}%` }} title="Reserved for Boss's final report" />
      </div>
      {used > 0 && (
        <div className="fuel__legend">
          {HERO_ORDER.filter((a) => byAgent[a]).map((a) => (
            <span key={a}>
              <i style={{ background: HEROES[a].color }} />
              {HEROES[a].name} {k(byAgent[a] ?? 0)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
