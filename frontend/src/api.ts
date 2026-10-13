// Thin client for the FastAPI backend (backend/main.py).
import type { AgentEvent, ApprovalRequest, Cash, Draft, Run, RunSummary, Ticket, TicketDetail, TraceLoop, Transaction } from "./types";

export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, `Cannot reach the backend at ${API_BASE}. Is "uvicorn main:app --reload --port 8000" running?`);
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : detail?.error ?? JSON.stringify(detail ?? body);
    throw new ApiError(res.status, message);
  }
  return body as T;
}

const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });

export const api = {
  health: () => request<{ ok: boolean; model: string; llm_configured: boolean; llm_error: string | null; team_running: boolean }>("/api/health"),
  tickets: () => request<{ count: number; tickets: Ticket[] }>("/api/tickets"),
  ticket: (id: number) => request<TicketDetail>(`/api/tickets/${id}`),
  run: (id: number, feedback?: string) =>
    post<{ run_id: string; ticket_id: number; status: string }>(`/api/tickets/${id}/run`, feedback ? { feedback } : undefined),
  resolve: (id: number) => post<{ ok: boolean }>(`/api/tickets/${id}/resolve`),
  runs: () => request<{ count: number; runs: RunSummary[] }>("/api/runs"),
  runDetail: (runId: string) => request<Run>(`/api/runs/${runId}`),
  trace: (runId: string) => request<{ run_id: string; loops: TraceLoop[] }>(`/api/runs/${runId}/trace`),
  events: (after: number) => request<{ latest_seq: number; count: number; events: AgentEvent[] }>(`/api/events?after=${after}&limit=500`),
  approvals: () => request<{ count: number; requests: ApprovalRequest[] }>("/api/approvals"),
  approve: (id: number, decided_by: string) =>
    post<{ approved: boolean; executed: boolean; result: { cash_moved?: number; balance_after?: number }; cash: Cash }>(
      `/api/approvals/${id}/approve`,
      { decided_by },
    ),
  reject: (id: number, decided_by: string, note: string) => post<{ ok: boolean }>(`/api/approvals/${id}/reject`, { decided_by, note }),
  drafts: () => request<{ count: number; drafts: Draft[] }>("/api/drafts"),
  cash: () => request<Cash>("/api/cash"),
  transactions: () => request<{ count: number; total_paid: number; balance: number; transactions: Transaction[] }>("/api/transactions"),
  reset: () => post<{ ok: boolean; total_cash: number }>("/api/reset"),
};
