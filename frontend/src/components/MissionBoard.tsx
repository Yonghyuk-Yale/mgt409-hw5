// The three tickets as mission dossiers. Click to select; ASSEMBLE sends the team.
import type { Ticket } from "../types";
import { money } from "./Balance";
import { kTokens } from "./HeroBay";

const TYPE: Record<string, { icon: string; label: string }> = {
  customer_order: { icon: "🛒", label: "Customer order" },
  rent_notice: { icon: "🏠", label: "Rent notice" },
  price_override: { icon: "🏷️", label: "Discount request" },
};

const STATUS: Record<string, { label: string; tone: string }> = {
  open: { label: "Open", tone: "open" },
  in_progress: { label: "On mission", tone: "running" },
  awaiting_human: { label: "Awaiting your call", tone: "awaiting" },
  resolved: { label: "Resolved", tone: "resolved" },
};

export function MissionBoard({ tickets, selectedId, runningTicketId, stampedId, onSelect, onAssemble }: {
  tickets: Ticket[];
  selectedId: number | null;
  runningTicketId: number | null;
  stampedId: number | null;
  onSelect: (id: number) => void;
  onAssemble: (id: number) => void;
}) {
  return (
    <section className="panel missions">
      <h3 className="panel__title">Mission board</h3>
      {tickets.length === 0 && <p className="muted">Loading tickets…</p>}
      {/* open missions first, resolved ones sink to the bottom */}
      {[...tickets].sort((a, b) => Number(a.is_resolved) - Number(b.is_resolved) || a.id - b.id).map((t) => {
        const type = TYPE[t.type] ?? { icon: "📌", label: t.type };
        const running = runningTicketId === t.id;
        const status = STATUS[running ? "in_progress" : t.status] ?? { label: t.status, tone: "open" };
        return (
          <article
            key={t.id}
            className={`mission ${selectedId === t.id ? "is-selected" : ""} ${running ? "is-running" : ""} ${t.is_resolved ? "is-resolved" : ""}`}
            onClick={() => onSelect(t.id)}
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && onSelect(t.id)}
          >
            <header className="mission__head">
              <span className="mission__icon">{type.icon}</span>
              <span className="mission__id">#{t.id}</span>
              <span className={`chip chip--${status.tone}`}>{status.label}</span>
            </header>
            <h4 className="mission__subject">{t.subject}</h4>
            <p className="mission__meta">
              {type.label} · {t.requester}
            </p>
            <p className="mission__notes">“{t.notes}”</p>
            <footer className="mission__foot">
              {t.pending_approvals > 0 && <span className="badge">⚖️ {t.pending_approvals} to decide</span>}
              {t.drafts > 0 && <span className="badge badge--soft">✉️ {t.drafts} draft</span>}
              {!t.is_resolved && (
                <button
                  className="btn btn--assemble"
                  disabled={runningTicketId !== null}
                  onClick={(e) => {
                    e.stopPropagation();
                    onAssemble(t.id);
                  }}
                >
                  {running ? "On mission…" : t.latest_run ? "Assemble again" : "Assemble!"}
                </button>
              )}
            </footer>
            {t.is_resolved && (
              <>
                <div className={`stamp stamp--complete ${stampedId === t.id ? "stamp--slam" : ""}`}>MISSION COMPLETE</div>
                <div className="mission__cost" title="What this mission used">
                  💵 {t.cash_spent > 0 ? `${money(t.cash_spent)} paid` : "no cash spent"} · ⛽ {kTokens(t.tokens_used)} tokens
                  {t.runs > 1 ? ` (${t.runs} runs)` : ""}
                </div>
              </>
            )}
          </article>
        );
      })}
    </section>
  );
}
