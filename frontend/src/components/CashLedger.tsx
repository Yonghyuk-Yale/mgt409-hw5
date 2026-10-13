// Where the starting budget went: one bar from the starting cash, cut into every payment (cumulative),
// with what is left at the end, plus a step-by-step list. Cash only goes out in this shop, so the
// starting budget is today's balance plus everything paid.
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Transaction } from "../types";
import { money } from "./Balance";

const KIND: Record<string, { label: string; color: string; icon: string }> = {
  rent: { label: "Rent", color: "#3f7d3a", icon: "🏛️" },
  invoice: { label: "Vendor invoice", color: "#b3261e", icon: "🧾" },
  purchase_order: { label: "Purchase order", color: "#e0a92a", icon: "📦" },
};

export function CashLedger({ balance, refreshKey }: { balance: number | null; refreshKey: number }) {
  const [txns, setTxns] = useState<Transaction[]>([]);
  useEffect(() => {
    api
      .transactions()
      .then((d) => setTxns([...d.transactions].reverse())) // oldest first
      .catch(() => setTxns([]));
  }, [refreshKey, balance]);

  if (balance == null) return null;
  const spent = txns.reduce((s, t) => s + t.amount, 0);
  const start = balance + spent;
  const pct = (n: number) => `${start > 0 ? (n / start) * 100 : 0}%`;
  let running = start;

  return (
    <section className="panel ledger">
      <h3 className="panel__title">Budget history</h3>
      <div className="ledger__top">
        <span>
          Start <b>{money(start)}</b>
        </span>
        <span>
          Spent <b className="neg">{money(spent)}</b>
        </span>
        <span>
          Left <b>{money(balance)}</b>
        </span>
      </div>
      <div className="ledger__bar" role="img" aria-label={`Spent ${money(spent)} of ${money(start)}`}>
        {txns.map((t) => (
          <div
            key={t.id}
            className="ledger__seg"
            style={{ width: pct(t.amount), background: KIND[t.kind]?.color ?? "#8a96a8" }}
            title={`${t.description}: ${money(t.amount)}`}
          >
            {t.amount / start > 0.12 && <span>{KIND[t.kind]?.icon}</span>}
          </div>
        ))}
        <div className="ledger__seg ledger__seg--left" style={{ width: pct(balance) }} title={`Left: ${money(balance)}`} />
      </div>
      <ol className="ledger__steps">
        <li className="ledger__step ledger__step--start">
          <span>💼 Starting cash</span>
          <b>{money(start)}</b>
        </li>
        {txns.map((t) => {
          running -= t.amount;
          const kind = KIND[t.kind] ?? { label: t.kind, color: "#8a96a8", icon: "💸" };
          return (
            <li key={t.id} className="ledger__step" style={{ ["--kind" as string]: kind.color }}>
              <span title={t.description}>
                {kind.icon} {kind.label}
                {t.ticket_id ? ` · #${t.ticket_id}` : ""} <em>−{money(t.amount)}</em>
              </span>
              <b>{money(running)}</b>
            </li>
          );
        })}
        {txns.length === 0 && <li className="ledger__step muted">No money has left the shop yet.</li>}
      </ol>
    </section>
  );
}
