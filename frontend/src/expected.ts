// The owner's Expected plans from output/desk_tickets.html (Problem 6), in a form the dashboard
// can compare with what the team actually did.
// `tools` mirrors the Expected MCP-tool table in desk_tickets.html row by row: a row matches when one
// of its agents used any tool in it. That way the dashboard's score equals the Actual section's.
import type { AgentName } from "./types";

export interface ToolRow {
  agents: AgentName[];
  tools: string[];
}

export interface ExpectedPlan {
  firstAgent: AgentName;
  why: string;
  // who hands work to whom ("boss" -> specialist, or specialist <-> specialist)
  handoffs: { from: AgentName; to: AgentName; label: string }[];
  tools: ToolRow[];
}

const row = (agents: AgentName | AgentName[], ...tools: string[]): ToolRow => ({
  agents: Array.isArray(agents) ? agents : [agents],
  tools,
});

export const EXPECTED: Record<number, ExpectedPlan> = {
  101: {
    firstAgent: "inventory",
    why: "It is a stock question first: is a size-S tee on the shelf?",
    handoffs: [
      { from: "boss", to: "inventory", label: "Can we fill 1 × size S now?" },
      { from: "inventory", to: "accounting", label: "Clear invoice 501 to unblock the reprint" },
      { from: "accounting", to: "inventory", label: "Cash vs. invoice + rent" },
      { from: "boss", to: "customer_service", label: "Customer-side view + draft" },
    ],
    tools: [
      row("boss", "get_ticket"),
      row("inventory", "check_stock_for_size"),
      row("inventory", "get_stock_overview"),
      row("inventory", "list_vendors"),
      row("inventory", "estimate_restock"),
      row("accounting", "get_cash_position"),
      row("accounting", "list_payments", "list_approval_requests"),
      row("accounting", "create_payment_request"),
      row("accounting", "create_purchase_order_request"),
      row("customer_service", "get_customer_history"),
      row("customer_service", "save_customer_draft", "revise_customer_draft"),
      row("boss", "list_approval_requests", "list_customer_drafts"),
    ],
  },
  102: {
    firstAgent: "facilities",
    why: "Check that the landlord's notice matches lease 1 before paying anything.",
    handoffs: [
      { from: "boss", to: "facilities", label: "Does the notice match the lease?" },
      { from: "facilities", to: "accounting", label: "Can we pay $2,400 by 09-02, and when?" },
      { from: "accounting", to: "inventory", label: "Restocks competing for the same cash" },
    ],
    tools: [
      row("boss", "get_ticket"),
      row("facilities", "get_rent_due_for_lease"),
      row("facilities", "list_leases"),
      row("facilities", "list_payments"),
      row(["facilities", "accounting"], "get_cash_position"),
      row("accounting", "list_approval_requests"),
      row("accounting", "create_payment_request"),
      row("inventory", "estimate_restock"),
      row("boss", "list_open_tickets", "get_cash_position"),
    ],
  },
  103: {
    firstAgent: "inventory",
    why: "Can we supply exactly 20 × size M before talking about price?",
    handoffs: [
      { from: "boss", to: "inventory", label: "Can we supply 20 × M?" },
      { from: "inventory", to: "accounting", label: "Options + restock cost → discount" },
      { from: "accounting", to: "inventory", label: "Is a restock affordable?" },
      { from: "boss", to: "customer_service", label: "Customer view at the end + draft" },
    ],
    tools: [
      row("boss", "get_ticket"),
      row("inventory", "check_stock_for_size"),
      row("inventory", "get_stock_overview"),
      row("inventory", "list_vendors", "estimate_restock"),
      row("accounting", "get_price_and_margin_for_sku"),
      row("accounting", "evaluate_discount"),
      row("accounting", "get_cash_position"),
      row("accounting", "create_discount_request"),
      row("accounting", "create_purchase_order_request"),
      row("customer_service", "get_customer_history"),
      row("customer_service", "save_customer_draft", "revise_customer_draft"),
      row("boss", "list_open_tickets", "list_approval_requests", "list_customer_drafts"),
    ],
  },
};
