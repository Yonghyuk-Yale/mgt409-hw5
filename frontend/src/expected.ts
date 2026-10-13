// The owner's Expected plans from output/desk_tickets.html (Problem 6), in a form the dashboard
// can compare with what the team actually did.
import type { AgentName } from "./types";

export interface ExpectedPlan {
  firstAgent: AgentName;
  why: string;
  // who hands work to whom ("boss" -> specialist, or specialist <-> specialist)
  handoffs: { from: AgentName; to: AgentName; label: string }[];
  tools: { agent: AgentName; tool: string }[];
}

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
      { agent: "inventory", tool: "check_stock_for_size" },
      { agent: "inventory", tool: "get_stock_overview" },
      { agent: "inventory", tool: "list_vendors" },
      { agent: "inventory", tool: "estimate_restock" },
      { agent: "accounting", tool: "get_cash_position" },
      { agent: "accounting", tool: "list_approval_requests" },
      { agent: "accounting", tool: "create_payment_request" },
      { agent: "customer_service", tool: "get_customer_history" },
      { agent: "customer_service", tool: "save_customer_draft" },
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
      { agent: "facilities", tool: "get_rent_due_for_lease" },
      { agent: "facilities", tool: "list_leases" },
      { agent: "facilities", tool: "list_payments" },
      { agent: "accounting", tool: "get_cash_position" },
      { agent: "accounting", tool: "create_payment_request" },
      { agent: "boss", tool: "list_open_tickets" },
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
      { agent: "inventory", tool: "check_stock_for_size" },
      { agent: "inventory", tool: "get_stock_overview" },
      { agent: "inventory", tool: "estimate_restock" },
      { agent: "accounting", tool: "get_price_and_margin_for_sku" },
      { agent: "accounting", tool: "evaluate_discount" },
      { agent: "accounting", tool: "get_cash_position" },
      { agent: "accounting", tool: "create_discount_request" },
      { agent: "customer_service", tool: "get_customer_history" },
      { agent: "customer_service", tool: "save_customer_draft" },
    ],
  },
};
