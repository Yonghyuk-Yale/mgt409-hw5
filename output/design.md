# Dashboard Design — Campus Customs HQ

The dashboard is where the shop owner watches five AI agents work a ticket and then makes the decisions only a person may make: paying, ordering, discounting, and closing the ticket. It is a React + Vite + TypeScript app (`frontend/`, `npm run dev` → http://127.0.0.1:5455) that talks only to the FastAPI backend (`http://localhost:8000`).

## 1. Concept: an operations room you would want to sit in

The idea is a small "HQ" for a hero team. The agents are drawn as an original, Avengers-inspired squad. Each hero has a role, a costume color, and a face that reacts to what is happening. The heroes do the legwork in the middle of the screen, and the owner sits at the decision desk on the right.

Why this concept:
- **Agents feel like a team, not a log file.** A multi-agent system is hard to follow as text. Giving each agent a face, a color, and a position lets you see at a glance who is working, who is waiting, and who asked whom. That is the point of a multi-agent dashboard.
- **The human stays the boss of the bosses.** The heroes propose; only the owner's clicks move money. The layout makes that hierarchy visible: action happens in the middle, authority sits on the right.
- **It should be fun to use.** Stamps, coins, and reactions turn approvals into moments you notice. That keeps the owner engaged with decisions that matter instead of clicking through them.

## 2. Layout

```
┌──────────────────────── YALE SOM - Yonghyuk Choi ────────────────────────┐
│ 🛡 Campus Customs HQ · OUR MISSION: …   [ Checking $3,400.00 ] 🔇 ⟳ Refresh │
├───────────────┬────────────────────────────────────┬────────────────────┤
│ MISSION BOARD │ HERO BAY  ⛽ fuel, split by hero     │ DECISION DESK      │
│ #101 #102 #103│ Captain Yale ── [his speech box]    │ Boss recommendation│
│ [Assemble!]   │   ╲  beams  ╱                       │ Voice of customer  │
│ BUDGET HISTORY│ Iron · Margin · Fortress · Neighbor │ Approve / Deny     │
│ CASH OUTLOOK  │ [box]  [box]   [box]     [box]      │ Customer draft     │
│               │ 🔁 hand-offs: who asked / answered  │                    │
├───────────────┴────────────────────────────────────┴────────────────────┤
│ ▲ COMMS LOG — all bubbles · hero summary · Expected vs Actual           │
└──────────────────────── YALE SOM - Yonghyuk Choi ────────────────────────┘
```

The screen reads left to right, in the order the owner works:

1. **Mission board (left).** The three tickets are mission dossiers: type icon, requester, the customer's own words, a status chip (Open / On mission / Awaiting your call / Resolved), and badges for items waiting on you. **Assemble!** sends the team.
2. **Hero bay (center).** The team at work. This is the biggest area because it is where things change most often. Captain Yale sits on top with a wide speech box beside him; the four specialists stand in their own columns, each with a fixed speech box under the avatar. Because every hero has a dedicated box, two heroes talking at once can never cover each other. Under them, a **hand-off feed** lists the latest questions, answers, and reports between heroes as chat lines (*The Fortress asks → Doctor Margin: …*, *Doctor Margin answers → The Fortress: …*).
3. **Decision desk (right).** What Boss brought back and the buttons that act on it. It sits on the right, the end of the reading direction, because a decision is the end of every mission.
4. **Comms log (bottom drawer).** The full history. It stays closed so the main screen shows only what is happening now, and opens with one click when you want the details.
5. **Always visible: the checking balance** (top right), because every decision on this screen is about cash.
6. **The mission statement** sits under the title: *get every customer the right gear, keep the shop's doors open, and never spend a dollar the owner hasn't approved.* It states, on every screen, what the team optimizes for and the one rule it never breaks.

On narrower screens the hero bay moves to the top and the side panels stack below it.

## 3. Visual language

- **White + Yale Blue**, the project's house style. Yale Blue (`#00356b`) marks structure and authority: brand bars, titles, Boss, primary buttons. White space keeps a busy, live screen calm enough to read for a long session. The `YALE SOM - Yonghyuk Choi` bar sits at the very top and bottom of the page.
- **One accent color per hero**, used everywhere that hero appears: avatar ring, name, speech-bubble border, log entries, summary card. You learn the colors once and can then follow a hero across the screen without reading names.
- **Status colors mean the same thing everywhere.** Green = approved / paid / resolved, red = denied / money out / problem, amber = waiting on you or a policy warning, blue = in progress.
- **Numbers are tabular and large** for the balance and every amount, so dollar values line up and are easy to compare.

### The hero squad (original characters)

All characters are our own SVG drawings, inspired by the Avengers but using no Marvel names, logos, or artwork. The repository is public, so the design keeps the spirit and avoids the trademarks.

| Agent | Hero | Why this hero |
|---|---|---|
| Boss | **Captain Yale** — navy helmet and a round Yale-blue "Y" shield, placed at the center | The shield-bearing team leader who plans and protects (money, customers, the token budget). |
| Inventory | **Iron Stock** — red-and-gold armor with a box emblem | A suit built to scan: stock, sizes, vendors, arrival dates. |
| Accounting | **Doctor Margin** — cape and a glowing "$" amulet | Sees the cash future: liquidity, margins, which payment comes first. |
| Facilities | **The Fortress** — a green giant in a hard hat with a brick emblem | The strength that holds the building up; never late on rent. |
| Customer Service | **Friendly Neighbor** — web-patterned mask with a heart speech-bubble | The friendly neighbor who knows every customer. Tagged **"Voice of the customer"** on screen. |

Each hero has six expressions drawn into the SVG (idle, thinking, happy, worried, celebrating, sad) through eyes, mouth, and small extras (thought dots, a sweat drop, stars).

## 4. How each requirement is met

| Requirement | Design |
|---|---|
| List the three tickets | Mission cards with status chip, type icon, requester, and the ticket's note. |
| Pick a ticket → team works it | Click the card, press **Assemble!** The card pulses "On mission"; a fanfare plays if sound is on. |
| Show each agent and what it says or does | The hero bay shows all five heroes. Each one's **latest action appears in its own speech box**: "🔧 check_stock_for_size(…)", "❓ asks accounting: …", "📋 report summary". The active hero's ring glows, a red live dot appears, and its face shows *thinking*. Each hero also shows a 🪙 token chip with what it has spent on this mission. |
| History of bubbles and interactions | The **Comms log** drawer keeps every bubble with avatar and time. Filter by hero, show only hand-offs and reports, or include raw tool results. |
| Resolved stamp | When the owner's decisions are done, a **"MISSION COMPLETE" rubber stamp slams onto the card** (scale-and-rotate animation with a thud sound). A small line under it records what the mission used: *💵 $2,400.00 paid · ⛽ 137k tokens (2 runs)*. |
| Short summary per agent | **Hero summary** tab: one card per hero with what it did, the MCP tools it used, whom it asked, and its token cost; heroes not needed show as idle. |
| Approve / Deny payments and purchases | Each approval request is a card with amount, reason, cash after, and blockers. **Approve** stamps *APPROVED* (or *PAID*), executes the payment, and plays a cash-register sound. **Deny** asks for a short reason, stamps *DENIED*, and shakes the card. |
| Re-run with feedback after a Deny | A **"Re-run with feedback"** panel appears. Every deny reason (plus optional extra guidance) is passed to the team; Boss's next report shows which feedback it answered. Backend: `POST /api/tickets/{id}/run` with `feedback`. |
| Agent reactions | Approve → Doctor Margin happy 💸 ("Paid. Ledger updated…"), Captain Yale celebrates 👍, the relevant hero cheers. Deny → heroes look worried; Captain Yale salutes 🫡 "Understood. We'll rethink it." Execution refused (e.g. not enough cash) → Doctor Margin ⛔ explains why. Mission complete → everyone celebrates 🎉. |
| Checking balance, always visible, with animation | Top right. When cash goes out, the number **rolls down like an odometer**, a red **−$2,400.00** floats up, gold coins fly out, and the border flashes red. Click it for the **Transactions** list (date, what, ticket, approver, amount, total paid). |

## 5. Special features

1. **Light beams between heroes.** When Boss assigns a step or a hero asks a teammate, an animated beam in the caller's color connects the two heroes until the answer comes back; finished hand-offs stay as faint lines. The collaboration ("not Boss calls everyone") is visible as a network, not just described.
2. **Mission fuel gauge, split by hero.** The team's token budget (150k per ticket, 12 agent loops, 25k reserved for Boss's final report, hatched at the end of the bar) fills live during a run, **in each hero's color**, with a legend (*Captain Yale 9k · Doctor Margin 21k · …*); loops still running show as a striped segment. The border turns amber, then red, near the limit. It makes Boss's safety duty for token use visible and shows which hero is expensive.
3. **Budget history.** One bar is the starting cash (today's balance + everything paid, since cash only goes out). It is cut into every payment, in the payment's color (rent green, vendor invoice red, purchase order amber), and the remaining balance is shown in Yale Blue. Below it, a step list shows the running balance after each payment: *Starting cash $3,400 → 🧾 Vendor invoice #101 −$840 → $2,560 → 🏛️ Rent #102 −$2,400 → $160*. The owner sees not just what is left but where the budget went.
4. **Cash outlook bars.** Three bars: cash now → if you approve everything waiting → after every known bill (open invoices, rent due within 30 days, waiting purchase orders). The owner sees the consequence *before* clicking Approve. This matters here because the shop records no revenue, so cash only goes down.
5. **Expected vs Actual.** The drawer compares the owner's plan from `output/desk_tickets.html` (first agent, hand-offs, MCP tools) with what the team actually did (from the audit trail), with ✅/❌ and a score. This prepares the Actual sections of the desk tickets.
6. **Voice of the customer.** Customer Service's stance (supports / with changes / concerns / opposes) appears in its own colored box under Boss's recommendation, unedited, and Boss's override reason appears if Boss disagreed. The customer's view gets the visual weight the team rules give it.
7. **Sound effects.** Assemble fanfare, stamp thud, cash register, deny buzz, mission-complete chime. They are synthesized in the browser (no audio files) and **off by default**; the speaker button turns them on.
8. **Customer draft ready to act on.** The Customer Service draft sits next to the decisions with a **Copy message** button. It is clearly labelled "never sent automatically", because agents must never contact customers.

## 6. Safety in the interface

- **Only a person moves money.** Approve/Deny are the only controls that change cash; they send the name in "Signing as" (agent names are refused by the backend). Payments the cash cannot cover, or orders blocked by an unpaid invoice, are refused and explained.
- **Nothing is hidden.** Every waiting request and every draft for the ticket is shown on the desk, matching the backend rule that Boss must list them all.
- **Refresh asks first.** Resetting the database to its starting values needs a confirmation.
- **Honest states.** "Awaiting your call", "On mission", and a red banner when the backend cannot be reached, with the command to start it.

## 7. Accessibility and comfort

- Readable sizes (13–16 px body, 26 px balance), high-contrast text on white, and color always paired with a word or icon (status chips, stamps, ✅/❌).
- Keyboard: mission cards are focusable (Enter selects); the transactions dialog closes with Escape.
- `prefers-reduced-motion` turns the animations off.
- Speech boxes are clipped to five lines (Boss: three); hovering shows the full text, and the comms log keeps everything.

## 8. How it stays live

The dashboard polls the backend: events every 1.2 s (`GET /api/events?after=<seq>`, only new ones), tickets / cash / approvals every 2.5–5 s, and the selected ticket every 2.5–6 s. A finished run is detected from the `run_finished` event (with `GET /api/runs/{id}` as a backup), which triggers the toast, the reactions, and the report refresh. Finished runs are saved by the backend, so a backend restart does not wipe the reports on screen.
