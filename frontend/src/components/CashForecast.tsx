// Where cash is heading: now → after approving what is waiting → after every known bill.
import type { ApprovalRequest, Cash } from "../types";
import { money } from "./Balance";

export function CashForecast({ cash, approvals }: { cash: Cash | null; approvals: ApprovalRequest[] }) {
  if (!cash) return null;
  const pending = approvals.filter((r) => r.status === "pending_human" && r.amount > 0);
  const pendingOut = pending.reduce((s, r) => s + r.amount, 0);
  // Invoice and rent requests are already part of "obligations"; purchase orders add to them.
  const pendingPOs = pending.filter((r) => r.kind === "purchase_order").reduce((s, r) => s + r.amount, 0);
  const now = cash.balance;
  const afterPending = now - pendingOut;
  const afterAll = cash.cash_after_all_obligations - pendingPOs;
  const max = Math.max(now, 1);
  const pct = (v: number) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`;
  const rows = [
    { label: "Now", value: now, tone: "now" },
    { label: `If you approve what is waiting (${pending.length})`, value: afterPending, tone: afterPending < 0 ? "neg" : "mid" },
    { label: "After every known bill + waiting orders", value: afterAll, tone: afterAll < 0 ? "neg" : afterAll < 300 ? "low" : "ok" },
  ];
  return (
    <section className="panel forecast">
      <h3 className="panel__title">Cash outlook</h3>
      {rows.map((r) => (
        <div key={r.label} className="forecast__row">
          <div className="forecast__meta">
            <span>{r.label}</span>
            <b className={r.value < 0 ? "neg" : ""}>{money(r.value)}</b>
          </div>
          <div className="forecast__track">
            <div className={`forecast__bar forecast__bar--${r.tone}`} style={{ width: pct(r.value) }} />
          </div>
        </div>
      ))}
      <p className="forecast__note">
        Owed now: {money(cash.obligations_total)} (open invoices + rent due within 30 days). The shop records no revenue, so this is the real limit.
      </p>
    </section>
  );
}
