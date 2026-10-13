// What Boss brought back, and the owner's decisions: approve / deny (with a reason), re-run, close.
import { useState } from "react";
import { HEROES } from "../heroes";
import type { ApprovalRequest, Draft, TicketDetail } from "../types";
import { money } from "./Balance";

const KIND_LABEL: Record<string, string> = {
  invoice_payment: "Pay invoice",
  rent_payment: "Pay rent",
  purchase_order: "Purchase order",
  discount: "Discount quote",
};

const STANCE: Record<string, { label: string; tone: string }> = {
  support: { label: "Supports the plan", tone: "ok" },
  support_with_changes: { label: "Supports, with changes", tone: "mid" },
  concerns: { label: "Has concerns", tone: "warn" },
  oppose: { label: "Opposes", tone: "neg" },
};

function RequestCard({ req, busy, stamp, onApprove, onDeny }: {
  req: ApprovalRequest;
  busy: boolean;
  stamp?: "approved" | "denied";
  onApprove: () => void;
  onDeny: (note: string) => void;
}) {
  const [denying, setDenying] = useState(false);
  const [note, setNote] = useState("");
  const d = (req.details ?? {}) as Record<string, unknown>;
  const pending = req.status === "pending_human";
  const shown = stamp ?? (req.status === "executed" || req.status === "approved" ? "approved" : req.status === "rejected" ? "denied" : undefined);
  return (
    <article className={`request ${stamp === "denied" ? "request--shake" : ""} ${!pending ? "request--done" : ""}`}>
      <header className="request__head">
        <span className="request__kind">{KIND_LABEL[req.kind] ?? req.kind}</span>
        <span className="request__amount">{req.kind === "discount" ? `${money(req.unit_price)}/unit` : money(req.amount)}</span>
      </header>
      <p className="request__summary">{req.summary}</p>
      <p className="request__reason">{req.reason}</p>
      <ul className="request__facts">
        {typeof d.cash_after_this_payment === "number" && <li>Cash after: {money(d.cash_after_this_payment as number)}</li>}
        {typeof d.cash_after_this_order_only === "number" && <li>Cash after: {money(d.cash_after_this_order_only as number)}</li>}
        {Array.isArray(d.blocked_by_open_invoices) && (d.blocked_by_open_invoices as number[]).length > 0 && (
          <li className="warn">Blocked until invoice {(d.blocked_by_open_invoices as number[]).join(", ")} is paid</li>
        )}
        {typeof d.margin_pct === "number" && (
          <li className={d.policy_exception ? "warn" : ""}>
            Margin {String(d.margin_pct)}% {d.policy_exception ? "· below the 40% policy (exception)" : "· within policy"}
          </li>
        )}
        <li>Filed by {HEROES.accounting.name} · #{req.id}</li>
      </ul>
      {pending && !denying && (
        <div className="request__actions">
          <button className="btn btn--approve" disabled={busy} onClick={onApprove}>
            ✓ Approve{req.amount > 0 ? ` & pay ${money(req.amount)}` : ""}
          </button>
          <button className="btn btn--deny" disabled={busy} onClick={() => setDenying(true)}>
            ✗ Deny
          </button>
        </div>
      )}
      {pending && denying && (
        <div className="deny-form">
          <label>
            Why not? <span className="muted">(the team reads this on the re-run)</span>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="e.g. Keep cash for rent first; offer the club a size mix instead." autoFocus />
          </label>
          <div className="request__actions">
            <button className="btn btn--deny" disabled={busy || !note.trim()} onClick={() => onDeny(note.trim())}>
              Deny with this reason
            </button>
            <button className="btn btn--ghost" onClick={() => setDenying(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {!pending && req.decision_note && <p className="request__note">Your note: “{req.decision_note}”</p>}
      {shown && <div className={`stamp stamp--${shown} ${stamp ? "stamp--slam" : ""}`}>{shown === "approved" ? (req.status === "executed" && req.amount > 0 ? "PAID" : "APPROVED") : "DENIED"}</div>}
    </article>
  );
}

function DraftCard({ draft }: { draft: Draft }) {
  const [copied, setCopied] = useState(false);
  return (
    <article className="draft">
      <header>
        ✉️ To <b>{draft.recipient}</b> · <span className="muted">draft #{draft.id}, never sent automatically</span>
      </header>
      <h5>{draft.subject}</h5>
      <pre>{draft.body}</pre>
      <button
        className="btn btn--ghost btn--small"
        onClick={() => {
          void navigator.clipboard?.writeText(`${draft.subject}\n\n${draft.body}`);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? "Copied ✓" : "Copy message"}
      </button>
    </article>
  );
}

export function DecisionDesk({ detail, running, busy, stamps, signer, onSigner, onApprove, onDeny, onRerun, onResolve }: {
  detail: TicketDetail | null;
  running: boolean;
  busy: number | "resolve" | "rerun" | null;
  stamps: Record<number, "approved" | "denied">;
  signer: string;
  onSigner: (s: string) => void;
  onApprove: (r: ApprovalRequest) => void;
  onDeny: (r: ApprovalRequest, note: string) => void;
  onRerun: (extra: string) => void;
  onResolve: () => void;
}) {
  const [extra, setExtra] = useState("");
  if (!detail) {
    return (
      <section className="panel desk">
        <h3 className="panel__title">Decision desk</h3>
        <p className="muted">Pick a mission on the left.</p>
      </section>
    );
  }
  const result = detail.latest_run?.result ?? null;
  const final = result?.final ?? null;
  const cs = result?.customer_service_review ?? null;
  const requests = detail.approval_requests;
  const pending = requests.filter((r) => r.status === "pending_human");
  const cycleIds = new Set((result?.approval_requests ?? []).filter((r) => r.status === "pending_human").map((r) => r.id));
  const deniedThisRound = requests.filter((r) => r.status === "rejected" && cycleIds.has(r.id));
  const resolved = detail.ticket.status === "resolved";
  const awaiting = detail.ticket.status === "awaiting_human";

  return (
    <section className="panel desk">
      <div className="desk__head">
        <h3 className="panel__title">Decision desk · #{detail.ticket.id}</h3>
        <label className="signer">
          Signing as <input value={signer} onChange={(e) => onSigner(e.target.value)} maxLength={40} />
        </label>
      </div>

      {running && <div className="desk__running">🚀 The team is on this mission. Watch the hero bay; Boss will bring the recommendation here.</div>}
      {!running && !final && !resolved && <p className="muted">No report yet. Press <b>Assemble!</b> on the mission card.</p>}

      {final && (
        <div className="report">
          <div className="report__who">
            {HEROES.boss.emoji} {HEROES.boss.name} recommends
          </div>
          <h4 className="report__headline">{final.headline}</h4>
          <p>{final.recommended_outcome}</p>
          <p className="report__money">💵 {final.money_summary}</p>
          {detail.latest_run?.feedback && <p className="report__feedback">↩︎ This run answered your feedback: “{detail.latest_run.feedback}”</p>}
          {final.agrees_with_customer_service === false && final.override_reason && (
            <p className="report__override">⚠️ Boss went against Customer Service: {final.override_reason}</p>
          )}
          {final.risks.length > 0 && (
            <details>
              <summary>Risks ({final.risks.length}) · data gaps ({final.data_gaps.length})</summary>
              <ul>
                {final.risks.map((r) => (
                  <li key={r}>{r}</li>
                ))}
                {final.data_gaps.map((r) => (
                  <li key={r} className="muted">
                    Gap: {r}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {cs && (
        <div className={`voice voice--${STANCE[cs.stance]?.tone ?? "mid"}`}>
          <div className="voice__head">
            {HEROES.customer_service.emoji} Voice of the customer · <b>{STANCE[cs.stance]?.label ?? cs.stance}</b>
          </div>
          <p>{cs.customer_impact}</p>
          {cs.must_tell_human.length > 0 && (
            <ul>
              {cs.must_tell_human.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {requests.length > 0 && <h4 className="desk__sub">Your approvals</h4>}
      {requests.map((r) => (
        <RequestCard
          key={r.id}
          req={r}
          busy={busy !== null || running}
          stamp={stamps[r.id]}
          onApprove={() => onApprove(r)}
          onDeny={(note) => onDeny(r, note)}
        />
      ))}

      {detail.customer_drafts.length > 0 && <h4 className="desk__sub">Customer message (from {HEROES.customer_service.name})</h4>}
      {detail.customer_drafts.map((d) => (
        <DraftCard key={d.id} draft={d} />
      ))}

      {!running && !resolved && deniedThisRound.length > 0 && pending.length === 0 && (
        <div className="rerun">
          <h4>↩︎ Send the team back with your feedback</h4>
          <p className="muted">Your deny reasons go to Boss automatically. Add anything else:</p>
          <textarea rows={2} value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="Optional extra guidance" />
          <div className="request__actions">
            <button className="btn btn--assemble" disabled={busy !== null} onClick={() => onRerun(extra.trim())}>
              Re-run with feedback
            </button>
            <button className="btn btn--ghost" disabled={busy !== null} onClick={onResolve}>
              Close anyway
            </button>
          </div>
        </div>
      )}

      {!running && awaiting && pending.length === 0 && deniedThisRound.length === 0 && (
        <button className="btn btn--complete" disabled={busy !== null} onClick={onResolve}>
          ✔ Decisions done: close the mission
        </button>
      )}
      {resolved && <div className="desk__resolved">This mission is resolved. 🏁</div>}
    </section>
  );
}
