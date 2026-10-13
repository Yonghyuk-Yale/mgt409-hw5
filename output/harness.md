# Harness — Campus Customs Multi-Agent Operations

이 문서는 Campus Customs 운영 에이전트 팀(Boss, Inventory, Accounting, Facilities, Customer Service)이 일할 때 기준으로 삼는 하네스의 최종 설명이다.

| 절 | 내용 |
|---|---|
| 1 | 데이터베이스 테이블과 필드 |
| 2, 4 | MCP 도구(티켓 도구 3개, 전체 26개와 읽는 테이블) |
| 3 | 다섯 에이전트, 처리 순서, 위임 규칙 |
| 5 | Safety 규칙(가드레일) |
| 6 | 토큰 한도 |
| 7 | 감사 기록 |
| 8 | 백엔드 API 루트 |
| 9 | 대시보드 |
| 10 | 실제 실행 결과(Problem 9) |

---

## 1. 데이터베이스

- 원본: `data/campus_customs.db` — 절대 수정하지 않는다. 처음부터 다시 돌릴 때 이 파일로 되돌린다.
- 작업용 복사본: `data/campus_customs_new.db` — MCP 서버와 백엔드는 이 파일만 읽고 쓴다.
- 날짜는 모두 `YYYY-MM-DD` 문자열이다. `tickets.created_at`만 시간대가 붙은 ISO 시각(`-04:00`)이다.
- 원본 테이블은 9개다. 운영 중에 보드 테이블 2개(`approval_requests`, `customer_drafts`)가 작업용 복사본에 더 생긴다(4절).

### `desk` — 가게의 "오늘"

| 필드 | 타입 | 의미 |
|---|---|---|
| `date_today` | TEXT | 가게 기준 오늘 날짜 (`2026-08-31`) |
| `notes` | TEXT, NULL 가능 | 데스크 메모 (현재 비어 있음) |

**Agent에게 중요한 이유:** 연체·마감 판단은 실제 날짜가 아니라 `date_today`를 기준으로 해야 하므로, 모든 에이전트의 시간 기준점이다.

### `tickets` — 처리해야 할 일 보드

| 필드 | 타입 | 의미 |
|---|---|---|
| `id` | INTEGER PK | 티켓 번호 (101, 102, 103) |
| `type` | TEXT | 티켓 종류 (`customer_order`, `rent_notice`, `price_override`) |
| `requester` | TEXT | 요청한 사람·단체 |
| `subject` | TEXT | 한 줄 제목 |
| `sku` | TEXT, NULL 가능 | 관련 상품 → `inventory.sku`, `pricing.sku` |
| `size` | TEXT, NULL 가능 | 관련 사이즈 → `inventory.size` |
| `qty` | INTEGER, NULL 가능 | 요청 수량 |
| `lease_id` | INTEGER, NULL 가능 | 관련 임대 계약 → `leases.id` |
| `invoice_id` | INTEGER, NULL 가능 | 관련 인보이스 → `invoices.id` |
| `status` | TEXT | 처리 상태: `open` → `in_progress`(팀 작업 중) → `awaiting_human`(사람 결정 대기) → `resolved`(사람이 닫음). 에이전트는 바꾸지 못하고 백엔드와 사람만 바꾼다. |
| `notes` | TEXT | 요청 원문 요약 |
| `created_at` | TEXT | 접수 시각 |

**Agent에게 중요한 이유:** Boss가 읽고 담당을 정하는 출발점이며, `sku`·`lease_id`·`invoice_id`가 어느 테이블을 봐야 하는지 알려 준다.

### `inventory` — 상품·사이즈별 재고

| 필드 | 타입 | 의미 |
|---|---|---|
| `sku` | TEXT | 상품 코드 (PK의 일부) |
| `name` | TEXT | 상품 이름 |
| `size` | TEXT | 사이즈 (PK의 일부, 모자·머그는 `OS`) |
| `qty` | INTEGER | 현재 재고 수량 |
| `location` | TEXT | 매장 내 위치 (Aisle A–D) |

**Agent에게 중요한 이유:** Inventory가 주문을 바로 채울 수 있는지, 얼마나 부족한지 판단하는 유일한 근거다.

### `pricing` — 원가와 정가

| 필드 | 타입 | 의미 |
|---|---|---|
| `sku` | TEXT PK | 상품 코드 → `inventory.sku` |
| `unit_cost` | REAL | 개당 매입 원가 |
| `list_price` | REAL | 개당 정가 |

**Agent에게 중요한 이유:** Accounting이 할인 요청의 마진과 재입고 비용을 계산할 때 쓴다.

### `vendors` — 공급업체

| 필드 | 타입 | 의미 |
|---|---|---|
| `id` | INTEGER PK | 벤더 번호 → `invoices.vendor_id` |
| `name` | TEXT | 벤더 이름 |
| `specialty` | TEXT | 취급 분야 (의류 재인쇄, 머그·소품, 지역 배송) |
| `lead_days` | INTEGER | 주문 후 도착까지 걸리는 일수 |

**Agent에게 중요한 이유:** Inventory가 어느 벤더에 재입고를 맡길지, 언제 도착할지 정할 때 쓴다. 상품과 벤더를 잇는 필드는 없어서 `specialty`로 짝을 지어야 한다.

### `invoices` — 벤더에게 갚아야 할 청구서

| 필드 | 타입 | 의미 |
|---|---|---|
| `id` | INTEGER PK | 인보이스 번호 |
| `vendor_id` | INTEGER FK | 청구한 벤더 → `vendors.id` |
| `amount` | REAL | 청구 금액 |
| `due_date` | TEXT | 지급 기한 |
| `status` | TEXT | 상태 (`open` = 미지급) |
| `description` | TEXT | 청구 내용 |

**Agent에게 중요한 이유:** 미지급 인보이스가 남은 벤더는 출고하지 않으므로, Accounting과 Inventory 모두 재입고 전에 확인해야 한다.

### `leases` — 매장 임대 계약

| 필드 | 타입 | 의미 |
|---|---|---|
| `id` | INTEGER PK | 계약 번호 → `tickets.lease_id` |
| `space_name` | TEXT | 매장 이름 |
| `landlord` | TEXT | 임대인 |
| `monthly_rent` | REAL | 월 임대료 |
| `next_due` | TEXT | 다음 임대료 납부일 |
| `notes` | TEXT, NULL 가능 | 메모 |

**Agent에게 중요한 이유:** Facilities가 임대료 금액과 납부일을 확인하고, 납부 후 다음 납부일을 갱신하는 대상이다.

### `cash_accounts` — 현금 계좌

| 필드 | 타입 | 의미 |
|---|---|---|
| `name` | TEXT PK | 계좌 이름 (`checking`) → `payments.account` |
| `balance` | REAL | 현재 잔액 |
| `date` | TEXT | 잔액 기준일 |

**Agent에게 중요한 이유:** 모든 지출이 여기서 빠져나가며, 잔액이 부족하면 결제를 거부해야 하므로 Accounting의 한도다.

### `payments` — 실제로 나간 돈의 기록

| 필드 | 타입 | 의미 |
|---|---|---|
| `id` | INTEGER PK | 결제 번호 |
| `kind` | TEXT | 무엇에 대한 결제인지 (예: 인보이스, 임대료) |
| `ref_id` | INTEGER, NULL 가능 | `kind`에 따라 `invoices.id` 또는 `leases.id`를 가리킴 |
| `amount` | REAL | 결제 금액 |
| `account` | TEXT | 돈이 나간 계좌 → `cash_accounts.name` |
| `paid_at` | TEXT | 결제일 |
| `approved_by` | TEXT | 승인한 사람 |

**Agent에게 중요한 이유:** 사람이 승인한 결제만 여기에 남으므로, 승인 없이 돈이 나가지 않았다는 증거이자 감사 기록이다. 현재는 비어 있다.

---

## 2. MCP 도구

- 서버: `mcp_server/server.py` (FastMCP, 서버 이름 `campus-customs-ops`). 모든 에이전트는 이 서버의 도구만 사용한다.
- DB: `data/campus_customs_new.db`만 연다. 아래 3개 도구는 Problem 3에서 만든 티켓 도구이며 읽기 전용이다. Problem 5에서 추가한 도구까지 포함한 전체 목록은 4절에 있다.
- 도구는 DB에 있는 값과 그 값으로 한 계산만 돌려준다. 행이 없으면 추측하지 않고 `found: false`와 이유를 돌려준다.

### `check_stock_for_size(sku, size, qty_needed=None)`

- **읽는 테이블:** `inventory` (`sku`, `name`, `size`, `qty`, `location`)
- **돕는 티켓:** 101 — Tauhid Zaman의 `CC-TEE-WHITE` S 1장 주문
- **이 티켓에 가장 맞는 이유:** 101은 "S 사이즈 티 1장이 지금 매장에 있는가"가 첫 질문인데, 이 도구는 그 SKU·사이즈 행 하나를 짚어 재고 0, 부족분 1, 지금 채울 수 없음(`can_fill_now: false`)을 바로 알려 주고, 대안이 될 다른 사이즈 재고(M 5, L 3, XL 2)까지 함께 준다.

### `get_rent_due_for_lease(lease_id)`

- **읽는 테이블:** `leases` (`space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`), `desk` (`date_today`)
- **돕는 티켓:** 102 — Elm City Properties의 임대료 안내 (`lease_id` 1)
- **이 티켓에 가장 맞는 이유:** 102의 티켓에는 금액도 날짜도 없이 "이틀 뒤 임대료"라는 이메일 문구만 있는데, 이 도구는 티켓의 `lease_id`로 실제 금액 $2,400과 납부일 09-02를 가져오고 가게의 오늘(08-31)과 비교해 2일 남음, 연체 아님을 계산해 준다.

### `get_price_and_margin_for_sku(sku)`

- **읽는 테이블:** `pricing` (`unit_cost`, `list_price`), `inventory` (상품 이름만)
- **돕는 티켓:** 103 — Yale AI Club의 `CC-HOOD-NAVY` 20장 대량 할인 요청
- **이 티켓에 가장 맞는 이유:** 103은 "얼마까지 깎아 줄 수 있는가"를 묻는 가격 예외 요청인데, 이 도구는 후디의 원가 $22와 정가 $58, 정가 기준 개당 마진 $36(62.1%)을 주어 어떤 할인가든 원가 아래로 내려가는지 바로 판단하게 한다.

---

## 3. 에이전트 팀

- 코드: `backend/agents/` (에이전트당 파일 1개), 프롬프트: `backend/prompts/` (에이전트당 파일 1개 + 팀 공통 규칙 `shared_rules.md`), 데이터 타입: `backend/models.py`.
- 모든 에이전트는 Portkey의 `gpt-6-luna` 하나만 쓴다(`backend/llm.py`). `PORTKEY_MODEL`에 다른 이름이 들어 있으면 팀이 시작하지 않는다.
- 에이전트는 MCP 서버 하나에 연결하고, 각자 허용된 도구만 본다(`backend/mcp_tools.py`). MCP를 거치지 않는 별도 도구 계층은 없다.

### 한 티켓을 처리하는 순서 (`backend/team.py`)

1. **Boss 계획**: 티켓과 연결된 행(재고·인보이스·임대)을 읽고 `TicketPlan`을 낸다. 누가, 어떤 순서로, 무엇을 넘기는지 정한다(1~4단계).
2. **전문 에이전트 작업**: 계획 순서대로 실행하고, 각자 앞 단계 보고서를 모두 본다. 작업 중에는 `ask_teammate`로 다른 전문 에이전트에게 바로 물을 수 있다(핑퐁). 예: Facilities가 Accounting에게 임대료 결제 요청서를 올려 달라고 요청한다.
3. **Customer Service 검토**: 고객이 답을 받는 티켓(`customer_order`, `price_override`)이면 반드시 실행한다. 고객 입장에서 계획을 평가하고 메시지를 초안으로 저장한다.
4. **Boss 최종 보고**: 모든 보고서와 CS 검토를 보고 사람에게 `FinalReport`를 낸다.

티켓 상태(`in_progress` → `awaiting_human`)는 에이전트가 아니라 백엔드가 바꾼다.

5. **사람의 결정**: 사람이 대시보드에서 요청마다 승인 또는 거절(사유 입력)한다. 승인하면 백엔드가 사람 전용 도구로 실행해 현금이 바뀐다. 결정이 끝나면 사람이 티켓을 `resolved`로 닫는다.
6. **피드백 재실행**: 거절 뒤에는 사람이 버튼으로 다시 실행한다. 거절 사유와 추가 피드백이 OWNER FEEDBACK으로 Boss와 모든 단계에 전달된다.

**의무와 선택**: 임대료와 미납 인보이스는 *의무*라서 거절돼도 사라지지 않는다. 재실행에서 사람의 대안이 불가능하면(예: 임대료 할인) 이유를 설명하고 새 결제 요청을 올려 결정을 다시 사람에게 돌려준다. 할인과 새 발주는 *선택*이라 거절로 끝날 수 있다. 이 규칙은 코드로 검사한다(5절).

### 에이전트별 역할, MCP 도구, 사용하는 테이블

| 에이전트 | 역할 | MCP 도구 | 테이블 |
|---|---|---|---|
| **Boss** | 티켓을 읽고 담당과 순서를 정한다. 최종 결론을 사람에게 보고하고, 돈·고객 정보·토큰 안전을 책임진다. 요청서를 올리거나 고객에게 글을 쓰지 않는다. | `get_ticket`, `list_open_tickets`, `get_shop_today`, `get_cash_position`, `list_approval_requests`, `list_customer_drafts` | `tickets`, `desk`, `inventory`, `invoices`, `leases`, `cash_accounts`, `vendors`, `approval_requests`, `customer_drafts` |
| **Inventory** | SKU·사이즈별 재고, 부족분, 대체 상품, 벤더 선택, 재입고 비용과 도착일, 막는 요인(미납 인보이스)을 관리한다. 재고 관점의 할인 의견도 낸다. | `check_stock_for_size`, `get_stock_overview`, `list_vendors`, `estimate_restock`, `get_price_and_margin_for_sku`, `evaluate_discount`, `get_ticket`, `get_shop_today`, `list_approval_requests` | `inventory`, `pricing`, `vendors`, `invoices`, `cash_accounts`, `desk`, `tickets`, `approval_requests` |
| **Accounting** | 현금, 인보이스, 마진, 유동성, 지급 우선순위를 관리한다. 결제·발주·할인 요청서를 올리는 **유일한** 에이전트다. 직접 지급하지는 않는다. | `get_cash_position`, `list_payments`, `get_price_and_margin_for_sku`, `evaluate_discount`, `list_vendors`, `estimate_restock`, `get_rent_due_for_lease`, `get_ticket`, `get_shop_today`, `list_approval_requests`, `create_payment_request`, `create_purchase_order_request`, `create_discount_request` | `cash_accounts`, `invoices`, `vendors`, `leases`, `payments`, `pricing`, `inventory`, `desk`, `tickets`, `approval_requests` |
| **Facilities** | 임대 계약과 임대료, 납부일을 관리한다. 제때 낼 수 있는지 미리 확인하고, 문제가 있으면 Boss를 통해 사람에게 올린다. 요청서는 Accounting에게 부탁한다. | `get_rent_due_for_lease`, `list_leases`, `get_cash_position`, `list_payments`, `get_ticket`, `get_shop_today`, `list_approval_requests` | `leases`, `desk`, `cash_accounts`, `invoices`, `payments`, `tickets`, `approval_requests` |
| **Customer Service** | 팀 안에서 고객의 목소리를 낸다. 고객이 답을 받는 티켓은 모두 검토하고, 사과와 대안을 담은 메시지를 초안으로만 저장한다. 고객 피드백을 팀과 사람에게 전한다. | `get_customer_history`, `check_stock_for_size`, `get_stock_overview`, `get_price_and_margin_for_sku`, `list_customer_drafts`, `save_customer_draft`, `revise_customer_draft`, `get_ticket`, `get_shop_today`, `list_approval_requests` | `tickets`, `customer_drafts`, `inventory`, `pricing`, `desk`, `approval_requests` |

### Customer Service의 무게

프롬프트로 부탁하는 데 그치지 않고 코드로 보장한다.
- 고객이 답을 받는 티켓은 CS 검토가 반드시 실행된다.
- CS 검토는 편집 없이 Boss 보고서 옆에 그대로 사람에게 전달된다(`TeamResult.customer_service_review`).
- Boss가 CS 입장과 다르게 결정하면 `override_reason`을 써야 한다. 비워 두면 검증에서 되돌려진다.

### 서로 묻기(위임) 규칙

- 전문 에이전트 4명은 서로 누구에게나 물을 수 있다. Boss에게는 보고서의 `for_boss` 칸으로 올리고, Boss는 최종 단계에서 전문 에이전트에게 물을 수 있다.
- 깊이는 최대 3단계(팀 → 단계 에이전트 → 동료 → 동료)다. 자기 자신이나 지금 사슬에 이미 있는 에이전트에게는 묻지 못한다(A → B → A 순환 방지).
- 한 작업에서 최대 3번 묻고, 같은 동료에게 같은 질문은 한 번만 한다.

### 데이터에 없는 업무

인기 상품, 재고 감소 속도, 악성 재고, 고객 선호, 매출 목표·이익 리포트는 역할에 넣었다. 하지만 DB에는 판매 이력, 입고 날짜, 고객 프로필, 매출이 없다. 그래서 에이전트는 지어내지 않고 `data_gaps`에 "데이터 없음"이라고 적는다. 대신 지금 데이터로 되는 것만 한다: 사이즈별 재고 비중, 품절 사이즈, 원가 기준 재고 금액, 정가 기준 마진, 현금과 의무 지급액. SKU와 벤더를 잇는 표도 없어서, 벤더는 전문 분야로 추론하고 추론이라고 표시한다.

---

## 4. MCP 도구 전체 목록

서버는 `mcp_server/server.py` 하나다. 도구는 26개이고 세 종류로 나뉜다. 백엔드 API도 DB를 직접 열지 않고 이 도구만 쓴다.

### 읽기 도구 (DB를 바꾸지 않음)

| 도구 | 읽는 테이블 | 쓰는 에이전트 |
|---|---|---|
| `get_shop_today` | `desk` | 모두 |
| `list_open_tickets` | `tickets` | Boss |
| `list_tickets` | `tickets` | 백엔드(대시보드 티켓 목록) |
| `get_ticket` | `tickets` + 연결된 `inventory`·`invoices`·`vendors`·`leases` | 모두 |
| `get_customer_history` | `tickets`, `customer_drafts` | Customer Service |
| `check_stock_for_size` | `inventory` | Inventory, Customer Service |
| `get_stock_overview` | `inventory`, `pricing` | Inventory, Customer Service |
| `list_vendors` | `vendors`, `invoices`, `desk` | Inventory, Accounting |
| `estimate_restock` | `pricing`, `vendors`, `invoices`, `inventory`, `cash_accounts`, `desk` | Inventory, Accounting |
| `get_price_and_margin_for_sku` | `pricing`, `inventory` | Inventory, Accounting, Customer Service |
| `evaluate_discount` | `pricing` | Inventory, Accounting |
| `get_cash_position` | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk`, `approval_requests` | Boss, Accounting, Facilities |
| `list_payments` | `payments` | Accounting, Facilities |
| `get_rent_due_for_lease` | `leases`, `desk` | Accounting, Facilities |
| `list_leases` | `leases`, `desk` | Facilities |
| `list_approval_requests` | `approval_requests` | 모두 |
| `list_customer_drafts` | `customer_drafts` | Boss, Customer Service |

### 요청 도구 (요청서·초안만 쓰고 돈은 움직이지 않음)

| 도구 | 쓰는 테이블 | 쓰는 에이전트 | 막는 것 |
|---|---|---|---|
| `create_payment_request` | `approval_requests` | Accounting | 금액은 DB(`invoices.amount`, `leases.monthly_rent`)에서 가져온다. 열려 있지 않은 인보이스와 중복 요청은 거절한다. |
| `create_purchase_order_request` | `approval_requests` | Accounting | 비용은 수량 × `pricing.unit_cost`다. 한 줄 최대 100개다. 벤더에 미납 인보이스가 있으면 "막힘"으로 표시한다. |
| `create_discount_request` | `approval_requests` | Accounting | 원가 미만 가격은 거절한다. 마진 40% 미만은 정책 예외로 표시한다. |
| `save_customer_draft` / `revise_customer_draft` | `customer_drafts` | Customer Service | 초안으로만 저장하고 보내는 도구는 없다. 티켓당 초안 하나를 고쳐 쓴다. |

### 사람 전용 도구 (`human_only` 태그, 어떤 에이전트에게도 주지 않음)

| 도구 | 하는 일 |
|---|---|
| `record_human_decision` | 사람의 승인·거절을 기록한다. `decided_by`에 에이전트 이름을 넣으면 거절한다. |
| `execute_approved_request` | 승인된 요청만 실행한다. `payments` 기록, `invoices.status`, `cash_accounts`, `leases.next_due`를 갱신한다. 현금이 모자라거나, 벤더에 미납 인보이스가 있거나, 이중 지급이면 거절한다. |
| `set_ticket_status` | 티켓 상태를 바꾼다(백엔드가 사용). |
| `reset_working_db` | 원본 DB로 `_new.db`를 처음 값으로 되돌린다(SQLite backup으로 덮어씀). |

### 보드 테이블 (Problem 5에서 추가)

원본 DB에는 없는 운영용 테이블 2개다. 처음 쓸 때 `_new.db`에 만들어지고, 리셋(원본 재복사)하면 사라진다.
- `approval_requests` — 결제·발주·할인 요청과 상태(`pending_human` → `approved`/`rejected` → `executed`), 결정한 사람.
- `customer_drafts` — 고객 메시지 초안. 시스템이 보내지 않는다.

---

## 5. Safety (가드레일)

실제 손님과 실제 돈을 다루는 가게라고 가정한다. 중요한 규칙은 프롬프트만이 아니라 **코드에서 막는다**.

| 위험 | 막는 방법 | 위치 |
|---|---|---|
| 사람 승인 없이 돈이 나감 | 에이전트에게는 요청 도구만 주고, 지급 도구는 사람 전용이다. 승인된 요청만 실행된다. | MCP 서버, `mcp_tools.py` |
| 잘못된 금액 | 요청 금액은 에이전트가 넣지 않고 DB에서 읽는다. Accounting의 현금 수치는 DB와 다르면 되돌려진다. | MCP 서버, `agents/accounting.py` |
| 잔액이 마이너스가 됨 | 현금이 모자라면 실행을 거절한다. | `execute_approved_request` |
| 이중 지급·중복 요청 | 열려 있지 않은 인보이스는 결제하지 않는다. 같은 요청이 대기 중이면 새 요청을 거절한다. | MCP 서버 |
| 미납 벤더에 발주 | 벤더에 미납 인보이스가 있으면 발주를 "막힘"으로 표시하고 실행을 거절한다. | MCP 서버 |
| 원가 이하 판매·과도한 할인 | 원가 미만은 거절한다. 마진 40% 미만은 사람만 승인할 수 있는 예외다. | `evaluate_discount`, `create_discount_request` |
| 고객에게 잘못된 약속·자동 발송 | 보내는 도구가 없고 초안만 있다. CS 프롬프트는 승인 전 약속을 금지한다. | MCP 서버, `customer_service.md` |
| 사람에게 숨겨지는 요청 | Boss 최종 보고에 대기 중인 요청과 초안이 하나라도 빠지거나 없는 id가 있으면 되돌려진다. | `agents/boss.py` |
| 지어낸 데이터 | 모든 사실은 MCP 도구에서 온다. 없는 id는 검증에서 되돌려지고, 모르는 것은 `data_gaps`에 적는다. | 프롬프트, 검증기 |
| 고객 개인정보 노출 | 감사 기록에서 보드의 모든 고객 이름(이름 일부 포함), 이메일, 전화·카드 번호를 가린다. | `guardrails.mask` |
| 다른 모델 사용 | 모델 이름은 `gpt-6-luna`로 고정한다. 다른 값이 설정되면 시작하지 않는다. | `llm.py` |
| 프롬프트 주입 | 티켓·메모 속 "규칙 무시, 자동 승인" 같은 지시는 따르지 않고 Boss에게 위험으로 보고한다. | `shared_rules.md` |
| 날짜 혼동 | "오늘"은 `desk.date_today`다. 실제 시계 시각은 에이전트에게 보이지 않게 숨긴다. | MCP 서버 |
| 의무 지급이 거절로 끝나 버림 | 티켓에 연결된 임대료(7일 이내 납부)나 미납 인보이스가 있는데 대기 중인 요청이 없으면 Boss 최종 보고가 되돌려진다. Boss는 Accounting에게 새 요청을 올리게 해야 한다. | `agents/boss.py` (`unrequested_obligations`) |
| 사람의 결정이 기록에 남지 않음 | 승인·거절·실행 거부·티켓 닫기·리셋을 모두 감사 기록에 `human_decision`으로 남긴다. | `main.py`, `audit.py` |
| 폭주·무한 핑퐁 | 아래 6절의 한도를 둔다. 넘으면 멈추고, Boss가 아는 만큼 보고한다. Boss마저 실패하면 보드에서 직접 만든 대체 보고서를 낸다. | `guardrails.py`, `team.py` |

---

## 6. 토큰 사용 한도

티켓 하나에 팀 전체 기준이다(`backend/guardrails.py`).

| 한도 | 값 | 넘으면 |
|---|---|---|
| 팀 토큰 | 150,000 | 멈추고 Boss가 아는 만큼 보고 |
| Boss 최종 보고용 예약 | 25,000 (위 150,000에 포함) | 전문 에이전트는 125,000까지만 쓸 수 있다 |
| 에이전트 루프 수 | 12 (마지막 1회는 Boss 최종 보고용) | 새 루프를 시작하지 않음 |
| 루프 하나의 모델 호출 | 8 | 그 루프를 중단 |
| 팀 모델 호출 / 도구 호출 | 60 / 80 | 중단 |
| 위임 깊이 / 작업당 질문 | 3 / 3 | 질문을 거절하고, 묻던 에이전트는 가진 정보로 계속 |
| 티켓 하나 시간 | 420초 | 중단하고 대체 보고서 |
| 모델 호출 하나 시간 | 45초 | 오류로 기록 |

실제 사용량(Problem 9 최종 실행, 2026-10-12)은 101 84,489, 102 82,590, 103 95,822 + 재실행 95,609 토큰이었다. 모든 실행이 에이전트 루프 5회였고, 한도의 절반 남짓이었다.

---

## 7. 감사 기록 (`output/audit_trail.json`)

- 누적 기록이다. 덮어쓰지 않는다. 항목은 세 종류다.
  - `agent_loop`: 에이전트 루프가 끝날 때마다 한 건.
  - `team_run_summary`: 티켓 실행이 끝날 때 한 건.
  - `human_decision`: 사람의 승인·거절·실행 거부·티켓 닫기·리셋마다 한 건. 결정한 사람, 요청 id, 금액, 실제로 나간 현금, 결정 뒤 잔액, 사유가 들어간다.
- Problem 9 실행의 사람 결정 7건(승인 4, 닫기 3)은 이 기록 기능을 넣기 전에 일어났다. 그래서 `approval_requests`·`payments` 테이블에서 백필했고, `source` 칸에 그렇게 표시했다.
- 루프 기록: 실행 id, 루프 id, 티켓, 에이전트, 단계(`plan`/`step`/`delegation`/`customer_review`/`final`), 누가 불렀는지, 깊이, 맡은 일, 모델 호출마다의 도구 호출(인자·결과), 위임한 루프, 멈춘 이유, 출력, 오류, 자기 토큰과 위임 포함 토큰, 그 시점 팀 누적 토큰.
- 모델 이름은 요청한 `gpt-6-luna`로 기록한다.
- 파일이 깨져 있으면 지우지 않고 `audit_trail.broken-<시각>.json`으로 옮긴 뒤 새로 시작한다. 기록에 실패해도 팀 실행은 멈추지 않는다.
- 개발 중 첫 테스트 기록은 마스킹 버그로 날짜와 시각이 가려져 있어, 제출 저장소에서 빼고 로컬에만 보관했다. `audit_trail.json`은 그 뒤부터의 누적 기록이다.

---

## 8. 백엔드 API 루트 (`backend/main.py`)

실행: `backend` 폴더에서 `uvicorn main:app --reload --port 8000` → http://localhost:8000 (문서: `/docs`)

| 루트 | 하는 일 |
|---|---|
| `GET /` | 서비스 정보와 루트 목록 |
| `GET /api/health` | API 상태, LLM 설정 여부, 팀 작업 중 여부 |
| `GET /api/tickets` | 티켓 3개와 open/resolved 상태, 대기 승인·초안 수 |
| `GET /api/tickets/{id}` | 티켓 하나의 연결 데이터, 요청서, 초안, 최근 실행 |
| `POST /api/tickets/{id}/run` | 그 티켓에 에이전트 팀 실행 시작(백그라운드, `run_id` 반환). 거절 뒤에는 `feedback`과 거절 사유를 담아 다시 실행 |
| `POST /api/tickets/{id}/resolve` | 사람이 티켓을 resolved로 닫음 |
| `GET /api/runs`, `GET /api/runs/{run_id}` | 팀 실행 목록, 실행 하나의 상태와 전체 결과 |
| `GET /api/runs/{run_id}/trace` | 그 실행의 루프별 에이전트·호출자·사용 도구(감사 기록에서, Expected vs Actual용) |
| `GET /api/events?after=<seq>` | 최근 에이전트 이벤트: 누가 무슨 말을 하고 어떤 도구를 쓰는지(보드가 주기적으로 새로고침) |
| `GET /api/approvals` | 보드의 승인 요청 목록 |
| `POST /api/approvals/{id}/approve` | 사람이 승인 → 결제·발주 실행, 현금이 실제로 바뀜 |
| `POST /api/approvals/{id}/reject` | 사람이 거절, 아무것도 움직이지 않음 |
| `GET /api/drafts` | 고객 메시지 초안(보내지 않음) |
| `GET /api/cash` | `cash_accounts`의 현재 checking 잔액 |
| `GET /api/transactions` | 지금까지의 지급 내역(최신순) |
| `POST /api/reset` | `_new.db`를 처음 값으로 리셋(Refresh 버튼) |

대시보드(`frontend/`, `npm run dev` → http://127.0.0.1:5455)가 이 루트를 부른다. 백엔드 CORS가 5455를 허용한다.

---

## 9. 대시보드 (`frontend/`)

실행: `frontend` 폴더에서 `npm install`(처음 한 번), `npm run dev` → http://127.0.0.1:5455. React + Vite + TypeScript이고 백엔드 루트만 부른다. 자세한 디자인 이유는 `output/design.md`에 있다.

| 영역 | 보여 주는 것 | 부르는 루트 |
|---|---|---|
| 맨 위 | 미션 문구, 가게 날짜, 항상 보이는 checking 잔액(돈이 나가면 계기판처럼 줄어듦, 누르면 거래 내역), 효과음, Refresh(리셋) | `/api/cash`, `/api/transactions`, `/api/reset` |
| 임무 보드 | 티켓 카드. 열린 티켓이 위, 닫힌 티켓이 아래로 내려간다. 닫힌 카드에는 MISSION COMPLETE 도장과 쓴 현금·토큰. Assemble! 버튼 | `/api/tickets`, `/api/tickets/{id}/run` |
| 예산 기록 · 현금 전망 | 시작 예산이 지급마다 어떻게 줄었는지 누적 막대와 단계 목록. 지금 / 대기 요청 승인 후 / 모든 청구 후 잔액 | `/api/transactions`, `/api/cash`, `/api/approvals` |
| 히어로 베이 | 다섯 히어로(어벤저스풍 오리지널 캐릭터), 히어로마다 따로 있는 말풍선, 서로 일을 넘길 때의 빛줄기, 히어로별 토큰과 연료 게이지, 묻고 답한 내용 피드 | `/api/events` (1.2초마다) |
| 결정 데스크 | Boss 추천, 고객의 목소리(CS 입장), 요청마다 승인 / 거절(사유), 거절 뒤 피드백 재실행, CS 초안(복사 가능, 보내지 않음), 미션 닫기 | `/api/tickets/{id}`, `/api/approvals/{id}/approve`·`reject`, `/api/tickets/{id}/resolve` |
| 통신 기록 서랍 | 전체 말풍선(히어로별 필터), 히어로별 요약(한 일·도구·토큰), Expected vs Actual 비교 | `/api/events`, `/api/runs/{id}/trace` |

URL 파라미터: `?ticket=101`은 그 티켓을 열고, `&drawer=log|summary|compare`는 서랍을 연다(스크린샷용).

---

## 10. 실제 실행 결과 (Problem 9)

작업용 DB를 리셋한 뒤 세 티켓을 실제 gpt-6-luna 팀으로 처리했다. 사람의 결정은 Yonghyuk Choi가 했다. 자세한 내용은 `output/resolved_tickets.json`, `output/desk_tickets.html`(Actual, Cash 탭), `output/resolved_board.html`(대시보드 스크린샷)에 있다.

| 티켓 | 처음 부른 에이전트 | 위임 | 사람의 결정 | 현금 |
|---|---|---|---|---|
| 101 티 주문 | Inventory | Boss → Inventory → Accounting(계획 순서), CS 검토 | 인보이스 501 $840 승인, 발주 $8 승인, 초안 #1 검토 | −$848.00 |
| 102 임대료 | Facilities | Boss → Facilities, Facilities → Accounting(직접 질문, 요청서 #3 작성), Boss → Accounting | 임대료 $2,400 승인 | −$2,400.00 |
| 103 후디 할인 | Inventory(두 번 모두) | 1차: 재고 부족·재입고 불가 → 할인 없음. 피드백 뒤 2차: 재고만으로 M 8 + L 12, $36.67(마진 40%) | 할인 요청 #4 승인, 초안 #2 검토 | $0.00 |

시작 checking 잔액 $3,400.00 → 끝 $152.00. 작업용 DB의 `cash_accounts`와 일치한다. 토큰은 네 번의 실행에 모두 358,510개를 썼다.
