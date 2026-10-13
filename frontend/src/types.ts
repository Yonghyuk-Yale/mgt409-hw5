export type AgentName = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: string;
  notes: string | null;
  created_at: string;
  is_resolved: boolean;
  state: "open" | "resolved";
  pending_approvals: number;
  drafts: number;
  latest_run: RunSummary | null;
  cash_spent: number;
  tokens_used: number;
  runs: number;
}

export interface RunSummary {
  run_id: string;
  ticket_id: number;
  status: "running" | "completed" | "failed";
  started_at: string;
  finished_at: string | null;
  stop_reason: string | null;
  headline: string | null;
  tokens: number | null;
  token_limit: number;
  error: string | null;
  feedback?: string | null;
}

export interface Run extends RunSummary {
  result: TeamResult | null;
}

export interface ApprovalRequest {
  id: number;
  kind: "invoice_payment" | "rent_payment" | "purchase_order" | "discount";
  ticket_id: number | null;
  ref_id: number | null;
  vendor_id: number | null;
  sku: string | null;
  size: string | null;
  qty: number | null;
  unit_price: number | null;
  amount: number;
  summary: string;
  reason: string;
  details: Record<string, unknown> | null;
  requested_by: string;
  status: "pending_human" | "approved" | "rejected" | "executed";
  shop_date: string;
  decided_by: string | null;
  decision_note: string | null;
  payment_id: number | null;
}

export interface Draft {
  id: number;
  ticket_id: number;
  recipient: string;
  subject: string;
  body: string;
  written_by: string;
  status: string;
  shop_date: string;
}

export interface HumanAction {
  kind: string;
  request_id: number | null;
  draft_id: number | null;
  what: string;
  amount: number | null;
  why: string;
  urgency: "today" | "this_week" | "when_convenient";
}

export interface FinalReport {
  ticket_id: number;
  headline: string;
  recommended_outcome: string;
  human_actions: HumanAction[];
  how_the_team_worked: string[];
  money_summary: string;
  agrees_with_customer_service: boolean | null;
  override_reason: string | null;
  risks: string[];
  data_gaps: string[];
}

export interface PlanStep {
  order: number;
  agent: AgentName;
  task: string;
  deliverable: string;
  hand_off_to: AgentName | null;
}

export interface TicketPlan {
  ticket_id: number;
  understanding: string;
  customer_facing: boolean;
  steps: PlanStep[];
  success_criteria: string[];
  risks_to_watch: string[];
}

export interface Report {
  summary: string;
  recommendations: string[];
  for_boss?: string[];
  data_gaps?: string[];
  confidence?: string;
  [key: string]: unknown;
}

export interface CustomerServiceReview extends Report {
  stance: "support" | "support_with_changes" | "concerns" | "oppose";
  customer_impact: string;
  what_the_customer_needs: string;
  apology_needed: boolean;
  alternatives_for_customer: string[];
  draft_ids: number[];
  feedback_for_team: string[];
  must_tell_human: string[];
}

export interface TeamResult {
  team_run_id: string;
  ticket_id: number;
  plan: TicketPlan | null;
  steps: { order: number; agent: AgentName; task: string; report: Report | null; error: string | null }[];
  customer_service_review: CustomerServiceReview | null;
  final: FinalReport | null;
  usage: { agent_loops: number; total_tokens: number; token_limit: number };
  stop_reason: string;
  errors: string[];
  feedback?: string | null;
  approval_requests: ApprovalRequest[];
  customer_drafts: Draft[];
}

export interface TicketDetail {
  found: boolean;
  shop_today: string;
  ticket: Omit<Ticket, "is_resolved" | "state" | "pending_approvals" | "drafts" | "latest_run" | "cash_spent" | "tokens_used" | "runs">;
  linked: Record<string, unknown>;
  state: "open" | "resolved";
  approval_requests: ApprovalRequest[];
  customer_drafts: Draft[];
  latest_run: Run | null;
}

export interface AgentEvent {
  seq: number;
  at: string;
  kind: string;
  text: string;
  agent?: AgentName;
  phase?: string;
  team_run_id?: string;
  loop_id?: string;
  called_by?: string;
  ticket_id?: number;
  tool?: string;
  to?: AgentName;
  ok?: boolean;
  stance?: string;
  tokens?: number;
  team_tokens?: number;
  loops?: number;
  request_id?: number;
}

export interface Cash {
  account: string;
  balance: number;
  as_of: string;
  shop_today: string;
  total_cash: number;
  obligations_total: number;
  cash_after_all_obligations: number;
}

export interface Transaction {
  id: number;
  kind: string;
  ref_id: number;
  amount: number;
  account: string;
  paid_at: string;
  approved_by: string;
  request_id: number | null;
  ticket_id: number | null;
  description: string;
}

export interface TraceLoop {
  loop_id: string;
  agent: AgentName;
  phase: string;
  called_by: string;
  depth: number;
  tools: string[];
  stop_reason: string;
  tokens: number | null;
}

export type Mood = "idle" | "thinking" | "happy" | "worried" | "celebrate" | "sad";
