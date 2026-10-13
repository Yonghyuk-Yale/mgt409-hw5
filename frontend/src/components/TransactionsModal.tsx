// Every payment the shop has made, newest first.
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Transaction } from "../types";
import { money } from "./Balance";

export function TransactionsModal({ onClose, refreshKey }: { onClose: () => void; refreshKey: number }) {
  const [data, setData] = useState<{ total_paid: number; balance: number; transactions: Transaction[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.transactions().then(setData).catch((e: Error) => setError(e.message));
  }, [refreshKey]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="modal" onClick={onClose}>
      <div className="modal__card" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Transactions">
        <header className="modal__head">
          <h3>🧾 Transactions</h3>
          <button className="btn btn--ghost btn--small" onClick={onClose}>
            Close
          </button>
        </header>
        {error && <p className="error">{error}</p>}
        {data && (
          <>
            <div className="txn__totals">
              <div>
                <span>Paid out</span>
                <b className="neg">{money(data.total_paid)}</b>
              </div>
              <div>
                <span>Checking now</span>
                <b>{money(data.balance)}</b>
              </div>
            </div>
            {data.transactions.length === 0 ? (
              <p className="muted">No payments yet. Money only moves when you approve a request.</p>
            ) : (
              <table className="txn">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Date</th>
                    <th>What</th>
                    <th>Ticket</th>
                    <th>Approved by</th>
                    <th className="num">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {data.transactions.map((t) => (
                    <tr key={t.id}>
                      <td>{t.id}</td>
                      <td>{t.paid_at}</td>
                      <td>{t.description}</td>
                      <td>{t.ticket_id ? `#${t.ticket_id}` : "—"}</td>
                      <td>{t.approved_by}</td>
                      <td className="num neg">−{money(t.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </div>
  );
}
