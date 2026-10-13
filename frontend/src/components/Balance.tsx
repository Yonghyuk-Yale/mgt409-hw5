// Checking balance that rolls like an odometer when cash moves, with a floating delta and coins.
import { useEffect, useRef, useState } from "react";

export const money = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

export function Balance({ value, onClick }: { value: number | null; onClick: () => void }) {
  const [shown, setShown] = useState<number | null>(value);
  const [delta, setDelta] = useState<{ amount: number; key: number } | null>(null);
  const prev = useRef<number | null>(value);
  const frame = useRef<number | null>(null);

  useEffect(() => {
    if (value == null) return;
    const from = prev.current;
    prev.current = value;
    if (from == null || from === value) {
      setShown(value);
      return;
    }
    setDelta({ amount: value - from, key: Date.now() });
    const start = performance.now();
    const dur = 1400;
    const step = (t: number) => {
      const k = Math.min(1, (t - start) / dur);
      const ease = 1 - Math.pow(1 - k, 3);
      setShown(from + (value - from) * ease);
      if (k < 1) frame.current = requestAnimationFrame(step);
    };
    frame.current = requestAnimationFrame(step);
    const clear = window.setTimeout(() => setDelta(null), 2600);
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
      window.clearTimeout(clear);
    };
  }, [value]);

  const falling = delta && delta.amount < 0;
  return (
    <button className={`balance ${falling ? "balance--falling" : ""}`} onClick={onClick} title="Show all transactions">
      <span className="balance__label">Checking balance</span>
      <span className="balance__value">{money(shown)}</span>
      <span className="balance__hint">Transactions ▸</span>
      {delta && (
        <span key={delta.key} className={`balance__delta ${delta.amount < 0 ? "is-out" : "is-in"}`}>
          {delta.amount < 0 ? "−" : "+"}
          {money(Math.abs(delta.amount))}
        </span>
      )}
      {falling && (
        <span key={`coins-${delta.key}`} className="coins" aria-hidden>
          {Array.from({ length: 7 }).map((_, i) => (
            <span key={i} className="coin" style={{ ["--i" as string]: i }}>
              $
            </span>
          ))}
        </span>
      )}
    </button>
  );
}
