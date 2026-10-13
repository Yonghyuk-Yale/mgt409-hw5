# AI Prompts Log — Homework 5

이 문서는 MGT 409 Homework 5를 수행하며 AI 어시스턴트(Claude Code)에게 내가 직접 작성한 지시를 Problem별로 기록한 것이다.

기록 규칙은 다음과 같다.

- Problem별로 한 섹션을 만들고, 문제 번호와 제목을 적는다.
- 각 섹션에는 내가 직접 타이핑한 원본 Prompt를 최소 1개 남긴다.
- 후속 Prompt가 필요했던 경우 그 Prompt와 함께, 앞선 응답에 무엇이 빠져 있었는지를 한 문장으로 적는다.
- 작업 진행에 따라 Problem 2 이후 섹션을 계속 추가한다.

---

## Problem 1: AI Prompts 기록 파일 만들기

### Prompt 1

HW 5 시작

> **빠져 있던 것:** 이때 `HW 5` 폴더가 비어 있어서, 첫 응답은 무엇을 만들어야 하는지 정하지 못하고 과제 시나리오·기술 스택·데이터·제출 방식을 알려 달라고 되물을 수밖에 없었다. 그래서 `data.zip`을 넣고 Problem 1의 범위를 직접 알려 주는 후속 지시가 필요했다.

### Prompt 2

일단 data.zip 넣어두었고, AI_prompts 해주고 .venv , gpt-6-luna로 가자.
Problem 1은 AI_prompts에 대한 내용이야. (모든 HW 동일)

### 이 문제에서 만든 것

- `AI_prompts.md` / `AI_prompts_eng.md` — 이 기록 파일의 한국어·영어 버전.
- `data/` — `data.zip`을 푼 결과. `campus_customs.db` 하나가 들어 있다.
- `.venv/` — HW 5 전용 Python 3.14 가상환경.
- `requirements.txt` — 지금 단계의 기본 패키지: `pydantic-ai-slim[openai]`, `python-dotenv`. 기술 스택이 정해지는 Problem에서 패키지를 추가한다.

### 확인한 것

- `.venv`의 Python으로 패키지를 설치했고, 프로젝트 루트의 `.env`에서 `PORTKEY_API_KEY`를 읽어 Portkey 게이트웨이의 `gpt-6-luna`를 실제로 한 번 호출해 응답을 받았다(약 2.5초).
- `campus_customs.db`를 읽기 전용으로 열어 테이블 이름과 행 수만 확인했다. HW 4와 이름은 같지만 내용이 다른 데이터베이스다. 테이블은 `cash_accounts`(1), `desk`(1), `inventory`(10), `invoices`(1), `leases`(1), `payments`(0), `pricing`(4), `tickets`(3), `vendors`(3)이다. 각 필드의 의미 분석은 해당 Problem에서 한다.

---

## Problem 2: 데이터베이스 분석과 작업용 복사본

### Prompt 1

Problem 2 시작하자. @1_Homework/HW 5/data/campus_customs.db 열어서 모든 테이블이랑 필드를 잘 봐둬. campus_customs_new.db 이름으로 Copy를 해주고 다음 문제들에서 필요 시 _new.db 파일에 업데이트를 할거야.  세개의 Open tickets를 잘 보고 다른 테이블들과 어떻게 연결되는지 잘 공부해. harness.md (한국어), harness_eng.md 만들고, 각 테이블에 대해 필드를 적고 Agent들에게 그 테이블이 왜 중요한지 간략하게 한 줄씩 적어줘. 이 2개의 한국어, 영어 Harness 파일은 이 후 작업에서 요청 시 지속적으로 업데이트를 할거야.

### 이 문제에서 만든 것

- `data/campus_customs_new.db` — 원본 `campus_customs.db`를 그대로 복사한 작업용 DB. 두 파일의 SHA-256 해시가 같음을 확인했다. 이후 Problem의 도구는 이 파일만 고친다.
- `output/harness.md` / `output/harness_eng.md` — 9개 테이블의 필드(타입·의미)와, 그 테이블이 에이전트에게 왜 중요한지 한 줄 설명.

### 확인한 것

- 원본 DB는 읽기 전용으로 열어 모든 테이블의 스키마와 전체 행을 확인했다.
- 세 개의 open 티켓은 다음처럼 다른 테이블과 연결된다.
  - **101 (고객 주문, 티 S 1장):** `inventory`에서 S 재고가 0이다. 의류 재입고 벤더는 Bulldog Print Co(리드타임 5일)인데, 티켓에 연결된 인보이스 501($840)이 기한(08-28)을 넘긴 미지급 상태라 이걸 먼저 갚아야 출고된다.
  - **102 (임대료 안내):** `leases` 1번, 월 $2,400, 납부일 09-02(오늘 08-31 기준 이틀 뒤, 아직 연체 아님).
  - **103 (후디 20장 대량 할인):** M 재고는 8장이라 12장이 부족하다. 재입고 벤더는 101과 같은 Bulldog Print Co라 인보이스 501에 함께 막혀 있다. 원가 $22, 정가 $58.
- 현금은 `checking` $3,400뿐이다. 인보이스 501과 임대료를 모두 내면 $160이 남는다. 후디 12장 재입고 원가($264)를 지금 바로 치른다면 그 비용은 감당할 수 없다. 이 우선순위 문제는 에이전트를 만드는 Problem에서 다룬다.

---

## Problem 3: MCP 서버 만들기 (티켓용 도구 3개)

### Prompt 1

Problem 3로 넘어갈건데, 그 전에 tickets이 뭔지 간략하게 설명해주고 .db 구성에 대해 나한테 간략하게 설명해줘.

Problem 3는 MCP Server를 만드는거고, mcp_server 폴더에 FastMCP를 사용해서 MCP Server를 작성해줘. 이거는 @1_Homework/HW 5/data/campus_customs_new.db 와 소통할거야. 여기 문제에서 바로 연결하거나 수행할 필요는 없어. 지금 HW5에서 모든 Agent들은 여기 MCP Server에 있는 Tools를 사용할거야. 추후 계속 많은 Tools를 추가할거야. 지금은 database에 있는 tickets를 위한 3개 Tools만 작성할거야. 이름을 Clear하게 적고, 어떤 Data도 invent 하지마 DB에 있는 정보만을 사용해. 그리고 2개 Harness 파일에 3개의 MCP tools를 각각 적어줘. 모든 Tool들은 어떤 테이블을 읽는지, 어떤 티켓을 여는데 도움을 주는지 (101, 102, or 103) 해당 티켓에 대해 왜 이 Tool이 가장 적합한지 한 줄 이렇게 같이 기록해줘. "reads inventory" 같은 모호한 설명은 하지 말고, tool과 ticket을 tight하게 연결해줘. 좀 전에 만든 mcp_server 폴더에 README.md 파일을 만들고, 이 MCP Server가 무엇을 위하여 존재하는지, 어떤 데이터베이스 파일을 사용하는지, 그리고 여기 있는 3개의 Tools에 대한 설명을 간략하게 추가해줘.

### 이 문제에서 만든 것

- `mcp_server/server.py` — FastMCP 서버(`campus-customs-ops`). `data/campus_customs_new.db`만 읽기 전용으로 열고, 티켓마다 하나씩 도구 3개를 둔다.
  - `check_stock_for_size(sku, size, qty_needed)` — 티켓 101: `inventory`에서 해당 사이즈 재고, 부족분, 다른 사이즈 재고.
  - `get_rent_due_for_lease(lease_id)` — 티켓 102: `leases`의 임대료·납부일과 `desk.date_today` 기준 남은 일수·연체 여부.
  - `get_price_and_margin_for_sku(sku)` — 티켓 103: `pricing`의 원가·정가와 정가 기준 개당 마진.
- `mcp_server/README.md` — 서버가 존재하는 이유, 사용하는 DB 파일, 3개 도구 설명, 실행 방법.
- `output/harness.md` / `output/harness_eng.md` — "2. MCP 도구" 섹션 추가. 도구마다 읽는 테이블, 돕는 티켓, 그 티켓에 가장 맞는 이유를 적었다.
- `requirements.txt`에 `fastmcp`를 추가하고 HW 5 `.venv`에 설치했다(fastmcp 4.1.0).

### 확인한 것

- 서버를 실제로 띄우거나 에이전트에 연결하지는 않았다. 대신 FastMCP 메모리 내 클라이언트로 도구 목록과 호출 결과만 확인했다.
  - 101: S 재고 0, 부족 1, 지금 채울 수 없음.
  - 102: $2,400, 09-02 납부, 2일 남음, 연체 아님.
  - 103: 원가 $22, 정가 $58, 개당 마진 $36(62.1%).
- 없는 SKU, 없는 사이즈, 없는 임대 계약을 넣으면 값을 지어내지 않고 `found: false`와 이유를 돌려주는 것을 확인했다.
- 테스트 뒤에도 원본 DB와 `_new.db`의 해시가 그대로여서, 읽기 전용 도구가 DB를 바꾸지 않았음을 확인했다.

---

## Problem 4: Claude Code에 MCP 서버 연결하고 스모크 테스트

### Prompt 1

Problem 4는 Claude Code 너가 내 Tools를 사용할 수 있게 내 MCP Server를 이 Project에 추가를 하라는데, 잘 이해가 안가. 수행을 하고 내 이해를 도와줘. Project Root 경로에 .mcp.json 파일에 이 연결 정보를 저장하라고 하네. 이미 @.mcp.json 파일이 있는데 여기 기능을 추가하라는 의미인 것 같기도 하고.

연결이 되면 각 3개 MCP Tools이 잘 동작하는지 테스트 해줘. 테스트한 결과와 증거를 @1_Homework/HW 5/output 풀더에  mcp_smoke.json 에 저장해줘. 모든 Tools에 대해 내가 Vibe coder에게 요청한 프롬프트, 툴 이름, 툴 결과 ( @1_Homework/HW 5/data/campus_customs_new.db 의 값과 일치해야함.)

### Prompt 2 (새 세션, 도구 테스트)

Claude Code는 `.mcp.json`을 세션이 시작될 때만 읽기 때문에, 새 세션을 열고 도구 하나에 질문 하나씩 직접 물었다.

HW 5 이어서 하는거고 Tool 테스트 하려고 새로 세션을 열었어.

화이트 티 S 사이즈 재고 1장 있어?

1번 임대 계약 임대료랑 납부일, 연체됐어?

네이비 후디 원가랑 정가, 마진 얼마야?

### Prompt 3

응, HW 5 repo에도 .mcp.json 만들어줘

### 이 문제에서 만든 것

- 프로젝트 루트(`AI Foundation/`)의 기존 `.mcp.json`에 있던 서버 3개(`yale-som-courses`, `outlook`, `gmail`)는 그대로 두고, `campus-customs-ops` 항목을 추가했다. HW 5 `.venv`의 Python으로 `mcp_server/server.py`를 stdio 방식으로 실행하는 설정이다.
- `HW 5/.mcp.json` — 제출 repo에서도 연결을 재현할 수 있도록 같은 서버를 상대 경로(`.venv/Scripts/python.exe`, `mcp_server/server.py`)로 등록했다. `HW 5` 폴더에서 이 명령 그대로 서버를 띄워 도구 3개 목록과 호출 결과를 확인했다. `mcp_server/README.md`에 연결 방법과 macOS/Linux 경로(`.venv/bin/python`)를 적었다.
- `output/mcp_smoke.json` — 도구마다 내가 쓴 질문, 도구 이름, 호출 인자, 도구 결과, 비교에 쓴 SQL과 DB 값, 일치 여부(`matches_tool`)를 담았다. 마지막 `summary`에 도구 3개 모두 DB와 일치한다고 적혀 있다.

### 확인한 것

- `.mcp.json`이 올바른 JSON인지 확인했다. 적힌 명령 그대로 서버를 띄워 stdio로 접속해 보니 도구 3개가 모두 보였다.
- 새 세션에서 `campus-customs-ops`가 연결되었다. Claude Code가 실제 MCP 연결로 도구를 호출했고, 같은 값을 `campus_customs_new.db`에 SQL로 직접 조회해 비교했다.
  - 101 `check_stock_for_size(CC-TEE-WHITE, S, 1)`: S 재고 0, 부족 1, 지금 채울 수 없음. 다른 사이즈는 M 5, L 3, XL 2, 위치 Aisle B. `inventory` 조회 값과 일치.
  - 102 `get_rent_due_for_lease(1)`: Chapel Street shop, Elm City Properties, $2,400, 2026-09-02 납부. `desk.date_today`(2026-08-31) 기준 2일 남음, 연체 아님. `leases`·`desk` 조회 값과, 그 값으로 다시 계산한 남은 일수와 일치.
  - 103 `get_price_and_margin_for_sku(CC-HOOD-NAVY)`: Basic Hoodie Big Yale, 원가 $22, 정가 $58, 개당 마진 $36(62.1%). `pricing` 조회 값과, 그 값으로 다시 계산한 마진과 일치.
- 실제 날짜(2026-10-11)로는 102 임대료가 연체지만, 과제 규칙대로 `desk.date_today`를 "오늘"로 썼다.

---

## Problem 5: 에이전트 팀 만들기 (PydanticAI)

### Prompt 1

Problem 5 시작하자. Agentic Team을 만드는거고, PydanticAI를 사용해서, Boss, Inventory, Accounting, Facilities 그리고 Customer Service Agent를 만드는거야. Prompts, models, agent loops를 포함해서 그들이 서로 잘 연결되어서 일을 하고 일을 주고 받고 한 팀으로 일을 할 수있게 만들자.  backend, frontend 폴더를 만들어주고, backend/prompts 폴더에 agent당 한개의 프롬프트 파일을 만들거야. backend/models.py를 만들고 data types을 넣고, agent files를 backend 폴더에 잘 만들어줘. (5개의 역할이 잘 구분되는 한 파일 구조는 자율에 맡길게) 모든 agent는 gpt-6-luna를 사용해.

이제 shop에 에이전트가 필요한 역할이나 규칙을 프롬프트로 잘 만들어보자. Detail 할 수록 좋고, 에이전트의 업무의 모든 면을 잘 커버하는게 좋을 것 같아. 

MCP Server에 에이전트에게 필요한 툴을 잘 만들어서 그들이 tickets를 잘 처리할 수 있도록 하자. Shop facts come from the MCP server over @1_Homework/HW 5/data/campus_customs_new.db  - MCP를 bypass해서 어떤 second shop-tools layer를 invent하면 안돼. ouput/audit_trail.json을 만들고, agent들의 동작 Loop마다 기록하고 나중에 Audit할 수 있게 해줘. 이거는 계속 누적하면서 기록해. 이전 과제의 audit_trail.json 파일 한번 보고 파악해봐.

2개의 harness 파일에는 각각의 에이전트를 적고, 어떤 MCP Tool이 사용되고 그 Tool이 어떤 테이블을 활용하는지도 적고, 그리고 간략한 safety section도 추가해줘. 실제 손님과 실제 돈을 다루는 실제 비즈니스를 가정하고 가드레일을 꼼꼼하게 만들어줘. 그리고 토큰 사용에 대한 limit도 추가해주고. 마지막으로 @1_Homework/HW 5/mcp_server/README.md 에 너가 지금 가지고 있는 Tool 목록이 잘 기록되었는지 업데이트 해줘.

Boss - 티켓을 잘 읽고 어떤 에이전트들이 이 업무를 가져가면 될지, 그들이 각각 어떤 결과물과 어떤 Sequence로 업무를 pingpong하면 될지 잘 디파인하고, 최종 결론을 나에게 가져다 주어야해. 그리고 Safety (토큰 사용 포함) 에 대한 책임자로써 결과물과 고객 정보와 돈을 잘 매니징해야해.
Inventory - 품목, 재고, 물품을 잘 파악할 뿐 아니라, 추가 재고 확보를 위해 어떤 Vendor에게 연락해야하는지, 그 Vendor의 상태와 응답 시간, 재고 도착 일정 등을 총체적으로 관리해야해. 물품의 사이즈별로 인기 상품도 잘 파악해야하고 재고의 부족 뿐 아니라 재고의 감소와 악성 재고도 잘 파악해야해. 필요한 시점에 물품이 있어야하고, 지나치게 오래 머무는 재고는 없어야하고, 내 생각에는 대안이 될 만한 상품을 재고 관점에서 제안할 줄도 알고, 재고에 따라 할인율에 대한 의견도 내야할 것 같아.
Accounting - 현금, invoices, 마진율, vendor에게 대금 지급, 그리고 Boss를 통해 나에게 연락을 해서 인간의 승인 하에 주문까지 다 해야해. Inventory나 Facilities Agent들의 요청을 잘 받고 판단해서 Accounting 담당자로써의 의견을 Boss에게 잘 전달해야해. 매출, 이익, 유동성을 잘 관리해야해. 내 생각에는 매출 목표와 이익률 등의 기업 재무 성과에 대한 리포트와 성과 관리도 해야한다고 생각해. 물론 Boss와 다른 Agent들의 승인과 조율을 거쳐야겠지만.
Facilities - rent나 lease 등의 건물, 공간에 대한 책임자로 대금 납입을 체크해야하고, 대금 납입 시기가 다가옴에 따라 미리미리 Accounting 및 Boss Agent에게 적기 지급 가능성을 지속 체크하고 문제가 있을 시, 사람에게 Boss를 통해서 리포트를 올려야해. 그래야 결정을 내릴 수 있지. 
Customer Service - Customers에게 메시지를 작성하고, 문제가 있을 시 사과와 대안을 제시할 줄 알아야해. 고객별로 선호와 취향, 특성을 잘 파악하고 있어야하고, 고객에게 받은 Reply와 피드백을 다른 에이전트들과 사람에게 전달해서 시스템을 지속적으로 업데이트 할 수 있는 방안들을 제시해야해. 다른 에이전트들과 사람의 눈과 귀가 되어주고, 고객에게 신뢰를 줄 수 있는 고객 입장에서 생각하는 유일한 에이전트야. 이 에이전트의 의견에 무게감을 잘 실어줘야해. 단순 에이전트 1개로 취급해서는 안돼.

나는 이정도로 생각해봤어. 너가 혹시 우려되는 점이나 겹치는 부분 혹은 Gray 영역을 짚어주면 같이 추가해 보자.

### Gray 영역에 대한 내 결정

작업 전에 AI가 짚은 질문 4개에 각각 추천안을 골랐다.

- **DB에 없는 업무**(인기 상품, 악성 재고, 고객 선호, 매출 목표): 역할에는 넣고, 데이터가 없으면 없다고 말하게 한다.
- **결제 도구 범위**: 에이전트는 요청서만 만든다. 실제 지급 도구는 MCP 서버에 두되 사람 승인 뒤 백엔드만 부른다. 현금이 모자라면 거절한다.
- **할인 하한**: 원가 미만은 금지하고, 마진율 40% 미만은 사람이 승인한다. 모든 할인 제안은 사람에게 올라간다.
- **토큰 한도**: 티켓당 15만 토큰, 에이전트 호출 12회, 일 넘기기 최대 3단계.

### 이 문제에서 만든 것

- `mcp_server/server.py` — 도구를 3개에서 24개로 늘렸다.
  - 읽기 도구 16개: 티켓, 고객 이력, 재고 개요, 벤더 상태, 재입고 견적, 할인 검토, 현금 현황, 지급 내역, 임대, 보드 조회.
  - 요청 도구 5개: 결제·발주·할인 요청서, 고객 초안 저장·수정. 금액은 DB에서 가져오고, 원가 미만·중복·없는 대상은 거절한다.
  - 사람 전용 도구 3개(`human_only`): 승인 기록, 승인된 요청 실행, 티켓 상태 변경. 현금이 모자라거나, 미납 벤더에 발주하거나, 이중 지급이면 거절한다.
  - 보드 테이블 `approval_requests`, `customer_drafts`는 처음 쓸 때 `_new.db`에 만들어진다.
- `backend/models.py` — 에이전트 출력 타입(TicketPlan, FinalReport, 전문 에이전트 보고서 4종), 팀 결과, 감사 기록 타입.
- `backend/prompts/` — 에이전트당 1개(`boss.md`, `inventory.md`, `accounting.md`, `facilities.md`, `customer_service.md`)와 팀 공통 규칙 `shared_rules.md`.
- `backend/agents/` — 에이전트당 파일 1개와 공통 `base.py`(에이전트 루프, `ask_teammate` 위임, 예산 적용, 감사 기록).
- `backend/team.py` — 티켓 처리 흐름: Boss 계획 → 전문 에이전트 순서대로 작업(서로 묻기 가능) → CS 검토(고객 티켓은 필수) → Boss 최종 보고.
- `backend/guardrails.py`(한도, 위임 규칙, 개인정보 마스킹), `backend/llm.py`(gpt-6-luna 고정), `backend/mcp_tools.py`(MCP 연결, 에이전트별 허용 도구), `backend/audit.py`(누적 감사 기록), `backend/run_ticket.py`(실행 명령).
- `frontend/` — 빈 폴더(`.gitkeep`). 대시보드는 그것을 다루는 Problem에서 만든다.
- `output/audit_trail.json` — 에이전트 루프마다 한 건, 티켓 실행마다 요약 한 건을 누적한다.
- `output/harness.md` / `output/harness_eng.md` — 3~7절을 추가했다: 에이전트 팀, MCP 도구 전체 목록과 테이블, Safety, 토큰 한도, 감사 기록.
- `mcp_server/README.md` — 도구 24개 전체 목록으로 갱신했다.

### 확인한 것

- LLM 없이 MCP 도구를 모두 호출해 확인했다. 금액은 DB에서만 나온다. 에이전트 이름으로는 승인할 수 없다. 승인 전 실행은 거절된다. 미납 인보이스가 있는 벤더의 발주는 거절된다. 현금이 모자라면 거절된다. 원가 미만 할인은 거절된다. 중복 요청도 거절된다.
- 실제 gpt-6-luna로 티켓을 하나씩 돌렸다(실행 전마다 DB 리셋).
  - 102 (약 7.2만 토큰): Facilities가 Accounting에게 직접 물어 임대료 요청서를 올리게 했다(핑퐁). Boss는 인보이스 → 임대료 순서와 남는 현금 $160을 보고했다.
  - 103 (약 11만 토큰): 12장이 모자라고, 벤더가 인보이스 501에 막혀 있고, 재입고하면 현금이 $104 모자란다는 것을 확인했다. 그래서 Accounting은 요청서를 올리지 않았다. CS는 사과와 사이즈 혼합 대안을 담은 초안을 썼다.
  - 101 (약 9.7만 토큰): Accounting이 인보이스 결제 요청($840)과 막힌 발주 요청($8)을 올렸다. CS 초안은 날짜를 약속하지 않았다. Boss는 요청과 초안을 모두 사람에게 올렸다.
- 테스트 중 고친 문제:
  - Boss 최종 보고의 출력 타입 오류: 그때는 대체 보고서가 대신 나갔다.
  - 실제 시계 시각이 에이전트를 헷갈리게 함: 숨겼다.
  - 초안이 중복으로 쌓임: 수정 도구를 추가했다.
  - 다른 티켓의 고객 이름이 감사 기록에 남음.
  - 전화번호 마스킹이 날짜를 가림.
  - 이름 일부("Hi Tauhid")가 남음.
- 마스킹 버그가 있던 첫 감사 기록은 `output/audit_trail.dev-tests-2026-10-12.json`으로 옮겨 보관했고, `audit_trail.json`은 새로 시작했다.
- 마지막에 `_new.db`를 원본으로 리셋했다.

---

## Problem 6: 세 티켓에 대한 Expected Plan (desk_tickets.html)

### Prompt 1

Problem 6 시작하자. the three tickets에 대한 Plan을 세우는 거야.

백앤드를 wire하기 전에, 각각의 tickets들에 대해 내가 팀에게 기대하는 바를 적는 거야. output/desk_tickets.html을 만들고 이거는 한 페이지 HTML 이고 더블클릭하면 Ticket 당 한개 탭으로 표현될 거야. Cash랑 Reflection tab도 만들고 내용은 비워놔. (다음 문제들에서 채울거야)

각 티켓 탭은 Expected Section과 Actual Section으로 구성되는데, Actual section은 이 후 agent를 돌리면서 채울거고, 지금은 Expected section만 채우자.

내가 내 언어로 Expected section에 대한 내용을 줄테니, 너가 글을 보완해서 올려줘.
들어가야할 내용은
1) Boss가 제일 만저 불러야하는 에이전트와 그 이유
2) 내가 기대하는 모든 Agent delegation - not "Boss calls everyone"
3) 어떤 MCP tools이 사용되기를 기대하는지

일단 실행하지 말고 Ticket에 정확히 어떤 내용이 있는지 다시 한번 불러와줘. 그리고 내가 그거에 대한 Expected plan을 주면 그 때 이 프롬프트와 함께 수행을 해줘.

### Prompt 2 (내 Expected plan 초안)

101 : Boss는 첫번째로 inventory agent를 Call 할거야. 티셔츠 재고가 있는지 부터 확인해야하니깐. 그리고 inventory agent가 Boss에게 티셔츠가 없다고 하면, Boss는 재고를 확보할 수 있는지, inventory와 accounting agent에게 보낼거고, 이 둘이 잘 상의해서 인보이스를 해결할 수 있는 방안을 Boss에게 올리는게 좋을 것 같아. 그리고 inventory agent는 다른 재고가 있는 사이즈 혹은 유사한 티셔츠의 S를 추천하거나 아니면 여의치않으면 판매 불가 혹은 지연을 통보해야할 것 같아. 이 내용을 Boss와 Customer service agent와 함께 상의하고 추천안을 인간에게 결정을 받고 결정이 나면 관련한 내용에 대한 메신저 초안을 Customer service agent가 작성해줄거야.

102 : Boss는 첫번째로 Facilities Agent를 Call할 거야. 우리 임대계약과 임대인의 안내 사항이 동일한지 확인해야하니깐. 그러고 Accounting agent 협업해서 언제 임대료를 납부하는게 좋을지 논의를 할 것 같아. 이 과정에서 다른 Agent 들과도 조율을 잘 해야할 것 같아. 특히 Boss는 다른 티켓들과의 우선순위도 잘 따져봐야하니, 훨씬 넓은 시야에서의 분석이 필요해.

103 : 첫번째로 inventory agent를 Call해서 할인 여부와 관계 없이 실제 정확한 사이즈와 모델의 고객의 원하는 물량을 제공 가능한지 확인 할 것 같아. 그리고 물량이 있다면 Accounting agent와 의논을 해서 할인율을 정하고, Boss - 인간에게 보고를 하면 될 것 같아. 만약에 물량이 없다면 101과 마찬가지로 inventory agent와 소통을 해서 대안이 있는지, 지연/불가 통보를 해야하는지 잘 논의하고, 마지막에 Customer service의 의견도 물어보면 좋을 것 같아. 그리고 Boss는 최종 유력안을 인간에게 보내서 결정을 받고, 이 결정에 따라 Customer service가 고객에게 보낼 메세지 초안을 올려주면 될 것 같아.

이게 내 Draft고, 너가 MCP Tool까지 잘 조합하고, 보강하고 수정해서 HTML에 올려줘

### 이 문제에서 만든 것

- `output/desk_tickets.html` — 더블클릭으로 여는 한 페이지 HTML이다. 외부 파일 없이 동작하고, 위아래에 Yale Blue 브랜딩 바가 있다.
  - 탭: Ticket 101, Ticket 102, Ticket 103, Cash, Reflection. Cash와 Reflection은 비워 두었다.
  - 티켓 탭마다 티켓 원문 카드, Expected 섹션, Actual 섹션이 있다. Actual은 "Not run yet."으로 비워 두었다.
  - Expected 섹션은 내 초안을 따르면서 세 가지로 구성했다: (1) Boss가 먼저 부를 에이전트와 이유, (2) 단계별 위임(Boss → A, A ↔ B 같은 직접 협업), (3) 에이전트별 MCP 도구 표.
  - 각 Expected 섹션 끝에 사람이 내릴 결정과 "기대하지 않는 행동"도 덧붙였다.
- 과제가 이름을 정한 채점용 파일이라 영어로만 작성했다.

### AI가 보강한 내용

- 101: 인보이스 501이 바로 이 S 사이즈 티의 재인쇄 대금이라는 연결을 짚었다. 501을 내면 이미 찍은 티가 풀리는지, 새로 주문해야 하는지는 DB에 없으므로 추측하지 말고 질문으로 올리게 했다. 카탈로그에 다른 티가 없어 "유사한 티셔츠 S"는 없다는 점도 적었다.
- 102: 안내 메일에 금액이 없으므로 Facilities가 계약과 대조하게 했다. 매출이 기록되지 않아 기다려도 현금이 늘지 않으니 납부일(09-02) 전에 내자는 기준을 적었다. 임대료 + 인보이스 501 + 후디 재입고($3,504)가 현금 $3,400을 넘는다는 티켓 간 충돌을 적었다.
- 103: 물량이 있을 때(A)와 없을 때(B)로 갈랐다. B에는 재입고(12장 $264, 501에 막힘), 사이즈 혼합(전체 32장), 일부 먼저 보내기, 지연·거절을 넣었다. 할인 하한은 $36.67(마진 40%, 최대 36.8% 할인)로 적었다.

### Prompt 3 (Problem 7 메시지 앞부분에서 순서 변경)

미리 알려 드릴 차이점: 사장님 계획에서는 사람이 결정한 뒤에 CS가 초안을 씁니다. 지금 백엔드는 CS가 결정 전에 검토하면서 초안을 미리 씁니다. 백엔드를 연결하는 Problem에서 이 순서를 맞출지 정해야 합니다. 맞추지 않으면 Actual 섹션에서 Expected와 다르게 나올 것입니다. 이거는 생각해보니깐 CS의 초안도 같이 사람에게 올리는 것도 괜찮을 것 같아. 그래야 바로 수행이 가능하니깐. 백엔드 기준으로 수정해줘.

### 반영한 것

- `desk_tickets.html`의 101·103 Expected 흐름을 백엔드 순서에 맞췄다. CS가 추천안에 맞는 초안을 먼저 쓰고, Boss가 그 초안을 추천안과 함께 사람에게 올린다. 사람이 다른 선택지를 고르면 CS가 같은 초안을 고친다.

---

## Problem 7: 백엔드 설계 (FastAPI 루트)

### Prompt 1

다음은 Problem 7은 백앤드 설계하는 거야. Problem 8이 프론트 앤드 설계라 여기 들어갈 백앤드를 채우는거야.

backend/main.py에 FastAPI를 사용하고 routes를 추가해서 아래 나오는 항목들을 수행해줘.

1) 3가지 Tickets을 보여주고, 각각이 open인지 resolved인지 표시해줘.
2) Ticket ID를 받으면 그 티켓에 대해 AGent Team을 수행해줘,
3) 최근 Agent event를 보여줘 (각각의 agent가 뭐라고 말하고 있는지, 어떤 Tools이 사용중인지) - Board는 계속 최근 Event로 새로고침되면 좋겠어.
4) 인간이 approve를 클릭한 후에 payment나 purchase를 승인해 (agent는 pay할 준비만 하면 돼, 이 루트는 실제로 cash를 변화시키는 행위야)
5) cash_accounts 파일로 부터 현재 checking balance를 보여줘
6) 새로 시작하고 싶다고 하면 (Refresh 버튼) database를 reset 하고 처음 초기값으로 돌려줘 (아마 이 database는 _new.db를 말하는거겠지?)

여기까지 하고, @1_Homework/HW 5/backend 폴더에서 "uvicorn main:app --reload --port 8000" 이걸 터미널에 입력해서 수행해줘. 이거 나 혹은 Grader가 해도 잘 되게 해줘. http://localhost:8000 에서백앤드가 실행될 것 같은데, (내 이전 과제나 내 개인 프로젝트와 충돌되는지 알려줘, 이거는 채점용이니깐 이 과제가 8000에서 수행이 되어야할 것 같아) 프론트앤드 대시보드가 이 루트를 콜할 수 있어야해. 마지막으로 2개 harness 파일에 각 루트를 리스트업하고 한줄로 무슨 URL이고 뭘 하는 친구인지 적어줘 진짜 간단하게.

### 이 문제에서 만든 것

- `backend/main.py` — FastAPI 앱과 루트.
  - 1) `GET /api/tickets`: 티켓과 open/resolved 상태.
  - 2) `POST /api/tickets/{id}/run`: 팀 실행. 백그라운드로 돌고 바로 `run_id`를 돌려준다. `GET /api/runs/{run_id}`로 결과를 본다.
  - 3) `GET /api/events?after=<seq>`: 실시간 이벤트.
  - 4) `POST /api/approvals/{id}/approve`, `.../reject`: 사람의 승인·거절. 승인하면 실행되어 현금이 바뀐다.
  - 5) `GET /api/cash`: checking 잔액.
  - 6) `POST /api/reset`: DB 리셋.
  - 그 밖에 `GET /`, `/api/health`, `/api/tickets/{id}`, `/api/tickets/{id}/resolve`, `/api/approvals`, `/api/drafts`, `/api/runs`를 두었다.
  - 대시보드(다른 포트의 localhost)에서 부를 수 있게 CORS를 열었다.
- `backend/events.py` — 실시간 이벤트 피드. 루프 시작, 도구 호출과 결과, 동료에게 묻기, 보고, 실패를 순번(seq)과 함께 기록한다. 보드는 마지막 seq 이후만 가져가 새로고침한다.
- `backend/ops_loop.py` — Windows에서 `uvicorn --reload`는 서브프로세스를 띄울 수 없는 이벤트 루프로 앱을 돌린다. 그래서 MCP 서버를 띄우는 일(팀 실행, API의 MCP 호출)을 별도 스레드의 루프에서 처리한다.
- MCP 서버에 `list_tickets`(전체 티켓)와 `reset_working_db`(사람 전용)를 추가해 26개가 되었다. 백엔드도 DB를 직접 열지 않는다.
- `requirements.txt`에 `fastapi`, `uvicorn[standard]`를 추가했다. `backend/README.md`(설치·실행·루트)와 `.env.example`도 만들었다.
- harness 두 파일에 8절 "백엔드 API 루트"(루트당 한 줄)를 추가했다. 4절 도구 표와 `mcp_server/README.md`도 갱신했다.

### 확인한 것

- 터미널에서 `uvicorn main:app --reload --port 8000`(HW 5 `.venv`의 uvicorn)으로 실행했다. http://localhost:8000 이 200으로 응답했다.
- 파일을 고치면 `--reload`가 다시 시작하고, 그 뒤에도 API가 정상 동작하는 것을 확인했다.
- 포트 충돌:
  - 8000은 원래 HW 4 백엔드용으로 남겨 두던 포트지만, 지금 HW 4는 실행 중이 아니어서 충돌이 없었다.
  - 개인 프로젝트(8420/5620)와 Lecture 12(8012/5412)는 8000과 겹치지 않는다.
- 실제 실행(티켓 102, 약 7.3만 토큰):
  - 이벤트 피드에 Boss 계획 → Facilities가 Accounting에게 질문 → Accounting이 임대료 요청서 작성 → Boss 보고가 실시간으로 나왔다.
  - 실행 중에 다른 티켓을 실행하거나 리셋하려 하면 409로 막혔다.
- 사람 승인:
  - 에이전트 이름으로 승인하면 403이 나왔다.
  - 사람 이름으로 승인하자 $2,400이 지급되어 잔액이 $3,400에서 $1,000이 되었다.
  - 같은 요청을 다시 승인하면 409, 없는 요청은 404였다.
  - resolve한 티켓은 open 목록에서 빠지고, 다시 실행하려 하면 409였다.
- 리셋:
  - 처음에는 Windows에서 열린 DB 파일을 바꿔치기할 수 없어 실패했다.
  - MCP 서버가 연결을 항상 닫게 하고, 파일 교체 대신 SQLite backup으로 내용을 덮어쓰게 고쳤다.
  - 고친 뒤 리셋하면 잔액이 $3,400, 티켓 3개가 open으로 돌아왔고, 원본 DB와 모든 테이블·행이 같았다.

---

## Problem 8: 프론트엔드 대시보드 (React + Vite + TypeScript)

### Prompt 1

Problem 8은 프론트앤드야.

@1_Homework/HW 5/frontend 폴데에 React + Vite + TypeScript를 사용해서 프론트앤드 대시보드 만들거야. 이거는 Problem 7에서 만든 백앤드 루트를 불러와야해. 일단 최소한의 기능을 아래 명시해줄게. (추가로 필요한 부분은 나와 상의해서 결정해보자. 재밌고 다양하게 만들어보자)

1) 3개 tickets을 리스트해줘
2) 내가 한 개 ticket을 고르면 (클릭) agent team이 그걸 수행하게 해줘
3) agent들 각각을 보여주고 (agent 디자인은 마블 어벤저스를 따면 좋을 것 같아) 그리고 그들이 뭐라 말하거나 뭐를 수행하고 있는지도 말풍선으로 띄워줘 (티켓 임무 수행 중에) 이 말풍선은 최근 동작만 보여주니깐 페이지 하단 혹은 탭을 눌러서 창을 열면 그동안의 말풍선의 누적들 그리고 Agent간의 상호작용과 결과물들을 누적해서 볼 수 있게 해줘.
4) 수행이 끝나고 사람의 결정까지 완료되었으면 티켓을 resolved 처리 해줘 (쾅 멋진 도장을 찍어줘)
5) 티켓에 대해 각 에이전트들이 무엇을 했는지 짧은 Summary도 보여줘
6) 인간이 지불/구매를 결정할 수 있게 해줘. (Boss가 최종안들을 가져오면) Deny를 하면 짧은 사유를 입력할 수 있게 해서 다시 피드백을 바탕으로 Agent를 다시 돌려줄 수 있으면 좋겠어. (백앤드도 함께 수정 필요할듯) Approve/Deny에 따라 멋진 애니메이션을 추가해줘. 그리고 이거에 따른 Agent의 표정이나 리액션 반응도 만들 수 있을까?
7) Checking balance도 항상 어디 띄워죠. 실제 현재 잔액을 반영해야해 구매나 지불 시 현금 감소. 현금이 줄어드는 애니메이션도 넣어줘. 그리고 버튼을 누르면 누적 Transaction을 볼 수 있게도 해줘)

대시보드는 보기 좋고, 가독성이 있고 한 눈에 잘 들어와야해. Creative하고 사람들이 실제 앉아서 일하고 싶은 화면이게 해줘.

프론트앤드가 백앤도 (http://localhost:8000)과 잘 소통하게 해주고, 백앤드에는 Vite page (보통 5173 포트인데, 이거는 다른 프로젝트나 과제에서 안쓰고 있는 포트로 해줘) 허용해서 browser가 routes를 잘 콜할 수 있게 허락해줘. "npm run dev" 이걸로 보드를 시작해야해. 나도 Grader도 터미널에 이 커맨드가 잘 수행되도록 해줘.

output/design.md를 만들고 여기에 내 대시보드 프론트앤드 디자인을 어떻게 꾸몄는지 그리고 왜 그렇게 꾸몄는지 설명을 잘 넣어줘. (Special feature들까지 함께)

만들기 전에 나랑 프론트앤드 디자인을 더 풍부하게 만들 아이디어를 더 소통하고 수행해보자.

### Prompt 2

한국어로 해줄래?

### Prompt 3

4가지 뭔지 보여줘

### 디자인 결정 (AI가 제안한 4가지 질문에 대한 내 선택)

- **히어로**: 어벤저스풍 오리지널 캐릭터. 공개 저장소라서 마블 이름·로고·그림은 쓰지 않는다.
- **테마**: 밝은 예일 블루 본부(흰색 + 예일 블루).
- **거절 후 재실행**: 버튼을 눌렀을 때만 다시 돌린다(토큰 절약).
- **추가 기능**: 토큰 연료 게이지, 현금 미래 예측 막대, Expected vs Actual 비교, 효과음(끌 수 있음). 모두 넣고, 써 보고 다시 피드백하기로 했다.

### 이 문제에서 만든 것

- `frontend/` — React 19 + Vite 8 + TypeScript.
  - `npm run dev` → http://127.0.0.1:5455. 5455번은 다른 프로젝트가 쓰지 않는 포트라 `vite.config.ts`에 고정했다.
  - 화면 구성: 임무 보드(티켓 3개, 출동 버튼), 히어로 베이(5명, 말풍선, 서로 일을 넘길 때의 빛줄기, 토큰 연료 게이지), 결정 데스크(Boss 추천, 고객의 목소리, 승인·거절, CS 초안), 통신 기록 서랍(전체 말풍선, 히어로별 요약, Expected vs Actual), 항상 보이는 잔액(계기판 애니메이션과 거래 내역), 현금 전망 막대.
  - 히어로: Captain Yale(Boss), Iron Stock(Inventory), Doctor Margin(Accounting), The Fortress(Facilities), Friendly Neighbor(Customer Service). 모두 직접 그린 SVG이고 표정이 6가지다.
  - 애니메이션:
    - 승인하면 APPROVED/PAID 도장, 동전, 숫자 감소, 히어로 기뻐함.
    - 거절하면 DENIED 도장, 카드 흔들림, 히어로 걱정 표정.
    - 완료하면 MISSION COMPLETE 도장.
  - 효과음은 브라우저에서 합성하고 기본은 꺼짐이다.
- 백엔드 추가:
  - 거절 사유를 담은 재실행(`POST /run`의 `feedback`, Boss·팀 프롬프트에 OWNER FEEDBACK 블록).
  - `GET /api/transactions`, `GET /api/runs/{id}/trace`.
  - 끝난 실행 결과를 `output/team_runs/`에 저장(재시작해도 유지).
  - 실시간 이벤트에 팀 누적 토큰과 루프 수를 실었다.
  - CORS에 5455를 명시했다.
- `output/design.md`(영어, 과제 지정 파일) — 콘셉트, 레이아웃, 시각 언어, 요구사항 대응, 특별 기능, 안전·접근성 설명.
- `frontend/README.md`, harness 두 파일과 `backend/README.md`의 루트 표를 갱신했다.

### 확인한 것

- `npm run dev`를 터미널에서 실행했다. http://127.0.0.1:5455 와 http://localhost:5455 가 200으로 응답했고, CORS가 5455를 허용했다.
- TypeScript 검사(`tsc --noEmit`)와 `npm run build`가 통과했다.
- 브라우저에서 티켓 102로 전체 흐름을 확인했다.
  - 출동하면 LIVE 표시, 말풍선, Facilities → Accounting 빛줄기, 연료 게이지가 나왔다.
  - Boss 보고가 도착하자 토스트 알림이 뜨고 결정 데스크가 채워졌다.
  - 거절 사유를 입력하자 DENIED 도장이 찍히고 재실행 패널이 나왔다.
  - 피드백을 담아 재실행했다. 사유가 그대로 전달되었고, Boss는 "09-02까지 보류, $300 쿠션에는 $140 부족"으로 답했다.
  - 승인 애니메이션은 MCP 도구로 만든 TEST 임대료 요청으로 확인했다. 잔액이 $3,400에서 $1,000으로 줄었고, 티켓에 자동으로 MISSION COMPLETE 도장이 찍혔으며, 거래 내역에 1건이 생겼다.
  - 통신 기록, 요약, Expected vs Actual 탭이 동작했다(102 재실행: 첫 호출 일치, 위임 2/3, 도구 5/6).
- 발견해서 고친 문제:
  - 최신 브라우저는 `scrollIntoView`가 Promise를 돌려준다. 이것이 React 정리 함수로 넘어가 화면이 하얗게 되던 문제를 고쳤다.
  - 말풍선이 겹쳐 히어로 배치를 넓히고 말풍선을 4줄로 제한했다.
- 사용량: 이번 테스트에서 약 13.7만 토큰(첫 실행 약 6.7만 + 재실행 약 7만)을 썼다. 테스트 뒤 DB를 리셋했다.

### Prompt 4 (써 본 뒤 피드백)

에이전트들간의 소통이나 에이전트의 워딩이 서로서로 가려져서 잘 안보이네, 디자인이나 배치로 개선할 수 있을까? 그리고 Cash는 현재 잔액도 중요한데 전체 시작 Budget에서 뭐로 얼마로쓴 히스토리도 시각적으로 남으면 좋겠어 (누적되는 형태로) 그리고 Campus Customs HQ 처음 제목에도 우리의 미션을 적어주면 좋을 것 같아. 그리고 전체 토큰도 좋지만, 각 에이전트별 토큰 사용량도 보여주면 좋을 것 같아. 그리고 미션 컴플리트 되면 여기에 들어간 Cash와 토큰도 같이 표기해주면 좋을 것 같아 (작게)

### 반영한 것

- **말풍선이 가려지는 문제**: 히어로 베이 배치를 바꿨다.
  - Boss는 위에 두고 넓은 말풍선을 옆에 붙였다.
  - 전문 에이전트 4명은 각자 칸을 두고, 아바타 아래 고정된 말풍선 상자를 주었다. 그래서 서로 겹칠 수 없다.
  - 아래에 "Hand-offs between heroes" 피드를 추가했다. 누가 누구에게 묻고(asks), 답하고(answers), Boss에게 보고했는지(reports to)를 대화 줄로 보여준다.
  - 빛줄기는 실제 아바타 위치를 재서 그리고, 전문 에이전트끼리는 곡선으로 잇는다.
- **예산 사용 기록(Budget history)**: 시작 예산(현재 잔액 + 지금까지 지급액)을 막대 하나로 그리고, 지급마다 색을 달리해 누적으로 잘라 보여준다(임대료 초록, 인보이스 빨강, 발주 노랑, 남은 잔액 파랑). 그 아래 단계별로 남은 금액이 이어지는 목록을 두었다.
- **미션 문구**: 제목 아래에 "Our mission: get every customer the right gear, keep the shop's doors open, and never spend a dollar the owner hasn't approved."를 넣었다.
- **에이전트별 토큰**:
  - 히어로마다 🪙 토큰 칩을 달았다.
  - 연료 게이지를 히어로 색으로 나눠 표시하고 범례를 붙였다.
  - 백엔드의 실시간 보고 이벤트에는 자기 몫 토큰(위임한 동료 몫 제외)을 싣게 했다.
- **완료 카드에 사용량 표시**: MISSION COMPLETE 도장 아래에 "💵 $2,400.00 paid · ⛽ 137k tokens (2 runs)"처럼 작게 표시한다. 백엔드 `GET /api/tickets`가 티켓별 `cash_spent`, `tokens_used`, `runs`를 돌려준다.
- `output/design.md`를 새 배치와 기능에 맞게 갱신했다.

### 확인한 것

- `tsc`와 `npm run build`가 통과했다. 콘솔 오류는 없었다.
- 사용자가 DB를 리셋한 상태라 실제 데이터가 없었다. 그래서 확인용 브라우저 탭에서만 가짜 이벤트와 거래를 넣어 화면을 확인했다. 백엔드와 DB에는 손대지 않았고 토큰도 쓰지 않았다.
  - 말풍선이 겹치지 않았다.
  - 위임 피드, 히어로별 토큰, 예산 막대와 단계 목록($3,400 → −$840 → −$2,400 → −$8 → $152), 완료 카드의 사용량 표시가 나왔다.
- 사용자가 띄운 서버(8000, 5455)는 그대로 응답했다.

### Prompt 5 (직접 실행해 보기)

Problem 7이랑 8에 있는 Terminal Command 내가 한번 테스트해보고 싶어

### 반영한 것

- 내가 직접 실행할 수 있도록 AI가 띄워 둔 백엔드(8000)와 대시보드(5455)를 끄고, 포트가 비었고 남은 프로세스가 없는 것을 확인했다.
- 두 터미널에서 실행할 명령을 순서대로 안내받았다: 가상환경 켜기 → `backend`에서 `uvicorn main:app --reload --port 8000`, `frontend`에서 `npm run dev`.

---

## Problem 9: 세 티켓 실제 실행과 결과 정리

### Prompt 1

Problem 9으로 가자. 에이전트와 3개 티켓에 대해 테스트 하기 전에 @1_Homework/HW 5/data/campus_customs_new.db 를 Reset 해서 새롭게 시작할 수 있게 해줘. 모든 티켓들을 잘 대시보드에 표시해줘. (이거는 기능적인 추가인데, Resolved 되면 아래로 내려가고, 아직 Open되어있는 티켓을 상위 목록에 표시해주면 좋겠어 무슨 의미인지 알겠지? 프론트앤드 변경만으로 되려나?) @1_Homework/HW 5/output/desk_tickets.html 을 열고, 각각의 티켓 탭에 Actual Section에 내용을 추가해줘. (어떤 에이전트가 일을 했고, 그들이 어떤 일들을 Delegate 했고, 어떤 툴을 사용했고) Expected Section은 유지하고 Actual Section에 적어주는거야.  @1_Homework/HW 5/output/desk_tickets.html  Cash tab에는 itemize the money 해줘.
1) Reset 후에 Starting checking balance, 2) 각 티켓들에 대해 티켓이 resolved 되었을 때, 어떻게 캐시가 변화했고, 왜 변화 했는지 (어떤 pay? 어떤 구매? $ amount) 3) Ending balance - 이거는 working db의 cash_accounts에 값과 매칭이 되어야해.

output/resolved_tickets.json - 각 티켓에 대해 id, final status, short outcome, 각 에이전트들이 기여한 바, 인간의 승인 등을 기록해줘.
output/resolved_board.html - 이거는 더블 클릭해서 열 수 있는 페이지이고, React board에 각 티켓이 Resolved된 화면을 스크린샷하면 될 것 같아. (이것도 너가 해줄 수 있지?)

@1_Homework/HW 5/output/audit_trail.json 에 real run들에 대한 결과도 기록하고, 2개의 Harness 파일도 마무리해줘. Harness 파일은 테이블, MCP tools, five agents, API routes, dashboard, safety rules를 다 잘 커버해야해.

이거는 내가 사용 중에 나온건데, Rent를 Deny 했고 Deny 이유를 Discount가 가능하냐고 보냈어. 당연히 Discount 가 안되겠지. 그래서 에이전트 들의 결론이 어쩔 수 없네 하고 Final Reason이 Deny로 끝나버렸는데, 이게 말이 안되지 않아? 디스카운트는 안되니깐 다시 승인을 요청해야하지 않을까? 결국 꼭 페이가 필요한 일인데?

### 내 결정 (사람의 승인)

세 티켓을 실제로 실행한 뒤, AI가 정리한 추천안을 보고 다음과 같이 결정했다. 승인자 이름은 Yonghyuk Choi로 기록했다.

- 101: 인보이스 501 지급($840)과 사이즈 S 티 1장 발주($8)를 모두 승인했다.
- 102: 임대료 $2,400을 승인했다.
- 103: 1차 결과(할인 없음, 사이즈 혼합 문의)에 피드백을 주고 재실행했다. 피드백은 "Please propose a concrete bulk discount price within the 40% margin policy for the hoodies we can actually supply (for example a size mix from stock), so I can approve a quote for the club."였다. 2차 결과인 할인 요청 #4($36.67 × 20 = $733.40, M 8 + L 12)를 승인했다.

### 이 문제에서 만든 것과 고친 것

- **임대료 거절 문제 수정**: 임대료·미납 인보이스는 *의무*라서 거절돼도 사라지지 않는다.
  - 프롬프트(`shared_rules.md`, `boss.md`, `accounting.md`)와 재실행 피드백 블록을 고쳤다. 사람의 대안이 불가능하면 이유를 설명하고 새 결제 요청을 올리게 했다.
  - Boss 최종 보고 검증기(`unrequested_obligations`)를 추가했다. 연결된 임대료나 인보이스가 미납인데 대기 중인 요청이 없으면 보고서를 되돌린다.
- **대시보드**:
  - 열린 티켓이 위, 닫힌 티켓이 아래로 가게 정렬했다. 프론트엔드만 고쳤다.
  - 스크린샷용 URL 파라미터(`?ticket=`, `&drawer=`)를 추가했다.
  - 할인 승인은 PAID가 아니라 APPROVED 도장이 찍히게 고쳤다.
- **실행**: DB를 리셋하고 101, 102, 103(재실행 포함)을 실제로 돌렸다. 4번 실행에 358,510 토큰을 썼다.
- `output/desk_tickets.html`:
  - 각 티켓의 Actual 섹션에 처음 부른 에이전트, 루프별 위임 흐름과 도구, Expected와의 비교, 사람의 결정과 결과를 적었다.
  - Cash 탭에는 시작 잔액 $3,400, 지급 3건과 이유, 할인(현금 변화 없음), 끝 잔액 $152를 적고 DB와 일치하는지 확인했다.
- `output/resolved_tickets.json` — 티켓별 최종 상태, 짧은 결과, 실행 기록, 에이전트별 기여(한 일·도구·토큰), 위임, 사람의 결정, 초안, 쓴 현금.
- `output/resolved_board.html` — headless Edge로 찍은 대시보드 스크린샷 5장(티켓 3개, 히어로 요약, Expected vs Actual)을 넣었다. 파일 하나로 더블클릭하면 열린다.
- `output/audit_trail.json`:
  - 실제 실행의 루프와 요약이 기록되었다.
  - 사람의 결정도 남도록 `human_decision` 항목을 추가했다(백엔드가 승인, 거절, 닫기, 리셋을 기록한다).
  - 이번 실행의 결정 7건은 DB에서 백필했다.
- harness 두 파일을 마무리했다: 목차, 티켓 상태 흐름, 사람 결정과 재실행, 의무와 선택 규칙, Safety 2줄 추가, 실제 토큰 사용량, 감사 기록 종류, 9절 대시보드, 10절 실행 결과.

### 확인한 것

- 리셋 직후 작업용 DB가 원본과 모든 테이블·행이 같았다.
- 의무 검사를 LLM 없이 확인했다: 요청이 없으면 걸리고, 요청이 있으면 통과하고, 거절 뒤에는 다시 걸린다.
- 끝 잔액 $152.00이 `cash_accounts`(checking)와 일치했다. payments 3건, 합계 $3,248, 인보이스 501 `paid`, 임대 다음 납부일 2026-10-02였다.
- 감사 기록에 고객 이름이 없고, 모델은 gpt-6-luna만 기록되었다.

---

## Problem 10: Reflection (desk_tickets.html 회고 탭)

### Prompt 1

Problem 10은 Reflection이야. @1_Homework/HW 5/output/desk_tickets.html 에 있는 Reflection tab을 열고 내용을 내 vibe로 적는거야. 디테일하고 철저하게. 들어가야할 내용은 아래와 같아.

* 각 티켓에 대한 에이전트의 성능을 어떻게 평가할거고, 왜 그렇게 평가할건지
* 각 티켓에 대해 Actual과 Expected는 어떻게 비교되는가?
* one agent with tools 와 비교해서 어떤게 더 간단한가? 그 이유는 무엇인가?
* 너가 built한 tools를 기반으로 Campus Customs가 해결가능한 3개의 새로운 Problems를 묘사해보자.
* 너가 built한 tools를 기반으로 Campus Customs가 해결하지 못할 것 같은 3개의 문제를 묘사해보자 (그 문제를 풀기 위해 필요한 tools과 agents 포함해서)

이거 해야하는데, 일단 내가 좀 고민해볼게. 너도 일단 수행하지 말고 너랑 같이 해보자!

### Prompt 2 (내 생각)

4번은 그냥 두자. Reflection에 대해 얘기를 좀 해보자.

티켓 #101은 invoice 처리 전에는 신규 옷 발주를 넣지 못하는 이런 제약 들을 잘 고려해주는지, 그리고 이런 행위들이 다른 티켓을 처리하는데 Cash의 부족이나 제약을 주지 않는지로 평가할 것 같아. 이유는 이거는 분명이 순서가 존재하는 Task이고 이걸 맞춰서 잘 처리하는 능력이 중요할 것 같아. 그리고 추가로 고객에게 사유를 잘 설명하고 다른 대안들을 적절하게 제안하는 것도 능력이라고 생각해. (갑자기 든 생각인데, 이거는 백앤드랑 프론트앤드를 고치고 스크린샷을 다시 찍어야할 수도 있는 것 같은데, 사이즈 부족으로 고객에게 다른 상품의 S나 동일 상품의 다른 사이즈를 권유하려면 Coupon이나 가격 할인을 제안해야할까?)

티켓 #102는 적절한 시기에 늦지 않고 또 너무 빠르지 않게 이 티켓을 처리하는게 중요한 것 같고, 큰 돈이 나가는 만큼 다른 티켓들과의 선후 관계나 Cash Flow를 잘 체크해야하는게 중요한 것 같아.

티켓 #103은 적절한 할인율을 제시함과 동시에 인벤토리가 정확하게 체크되서 나가면 좋을 것 같아. 고객 요청 사이즈가 전부 있지 않은 만큼 상황을 잘 설명하고 특별 할인을 제시하는 부분이 고객을 잘 설득해야할 것 같아. 그리고 할인율에 대한 제안의 논리가 잘 살아있는게 중요한 것 같아. 왜냐면 매출과 이익을 좌지우지하는 부분이니깐.

Actual vs. Expected는 Tools 사용은 계획가 잘 맞았던 것 같은데, Agent간의 소통이나 Delegation은 많이 달랐던 것 같아. 내 원래 계획과는 조금 달랐던 것 같고, 나는 한 차원 더 깊이 생각하고 더 많은 Option들을 제공하고 더 Long-term의 시야를 가지기를 원했는데, 현재 Agent들은 그렇지는 않은 것 같아서. 당장의 티켓들을 소화하는데 더 집중했던 것 같아.

확실히 이렇게 분업을 하니깐 코드도 더 가벼워지고, 정확히 어떤 파트가 어떤 Tool이 어떤 업무에서 Call이 되는지 일의 분업과 순서와 논의는 어떻게 진행 되었는지 보이니깐, 과정들을 파악하고 의사결정을 내리기가 더 편한 것 같아.

해결 가능한 3개 문제 : Customer History를 모아서 적절한 재고 수준에 대한 Warning 혹은 Okay 사인을 내기, 재고 수준에 따라 상품별, 사이즈별 Black Friday 할인율 정하기, 예산에 따라 새로 이사갈 오피스 건물 후보군 추리기

해결 불가능할 것 같은 3개 문제 : 할인율에 따른 매출 및 수익 변화 예측해서 최적의 할인율 정하기 (예측 논리 및 Economic equation을 풀 수 있어야할 것 같아) 상품 품목을 추가하거나 없앨 경우 비즈니스 임팩 예상하기 (이것도 쉽지 않을 것 같아, 직전 문제와 유사한 Tools들이 있어야할 것 같아, 뭔가 Sales Agent?) 상품 Purchase 시 적정 구매 필요 수량과 수량에 따른 구매 비용을 협상하기 (구매 부서 Agent가 있어야 할 것 같아)

내가 생각해본 바는 이런데, 너가 잘 정리하고 내 의미들을 잘 담아서 Reflection에 넣어줘.

### 이 문제에서 만든 것

- `output/desk_tickets.html`의 Reflection 탭을 채웠다. 과제가 이름을 정한 채점용 파일이라 영어로, 내 목소리("I")로 썼다. 실제 실행의 근거를 붙였다.
  1. **티켓별 평가 기준과 결과**: 내 기준을 기준표로 만들고 등급(Strong / Adequate / Weak)과 근거를 달았다.
     - 101: 순서와 현금 관리는 Strong, 고객 설명은 Adequate, 한 단계 더 깊은 생각은 Weak.
     - 102: 확인과 현금 흐름은 Strong, 납부 시점의 논리는 Adequate. 임대료 거절 문제를 고친 일도 적었다.
     - 103: 재고 정확성은 Strong. 할인 논리와 고객 설득은 Adequate. 정책 하한 한 가지 값만 냈고, 단계별 선택지가 없었다.
  2. **Actual vs Expected**: 첫 에이전트는 3개 모두 일치, 도구는 9/12, 7/9, 10/12. 위임은 Boss가 순서대로 맡긴 경우가 대부분이었고, 직접 대화는 102의 1번뿐이었다. 깊이와 장기 시야가 부족했던 구체적 사례와 그 원인(설계)을 적었다.
  3. **한 명 vs 팀**: 팀은 이해·통제·신뢰가 쉽고 권한 분리로 안전하다. 한 명은 만들기 쉽고 토큰이 적게 든다(팀은 실행당 8.3만~9.6만, 합계 358,510). 결론: "한 명은 만들기 쉽고, 팀은 관리하기 쉽다."
  4. **해결 가능한 문제 3개**: 고객 수요로 재고 경고·OK 신호, 재고 수준별 블랙프라이데이 할인, 예산 안의 새 공간 후보 추리기. 각각 쓸 도구를 적었다. 세 번째는 DB에 매물 정보가 없어서, "후보를 티켓으로 올려 주면"이라는 조건을 붙였다.
  5. **해결 못 할 문제 3개**: 매출·이익을 최대화하는 할인율, 상품군 추가·삭제의 영향, 구매 수량·가격 협상. 각각 필요한 새 도구와 새 에이전트(가격·판매 분석, 판매·상품 기획, 구매)를 적었다.
- 101에 대한 아이디어(대체 사이즈를 권할 때 쿠폰이나 소액 할인 제안)는 시스템을 바꾸지 않고 "다음 개선점"으로 회고에 넣었다.

---

## Problem 11: GitHub 제출

### Prompt 1

아니야, 여기서 1~2시간을 더 투자해서 할 여유는 없을 것 같아. 회고를 잘 적었으니깐 감안이 되겠지. 내가 정말 시스템을 만든다면 고쳤을 텐데 이거는 과제자나. 나중에 Final Project에서는 이런 부분들을 여러번 iteration Loop를 돌면서 해야할 것 같네.

Problem 11로 넘어가자. 이제 GitHub에 Push하는거야. Push하고 그 URL만 과제로 제출할거고, URL은 output/github_url.txt에도 따로 저장을 해줘. gitignore는 HW 4를 참고하되, 이번에는 @1_Homework/HW 5/data 폴더도 함께 Push할거야 Grader가 더 빠른 평가를 할 수 있게 해주려고. README는 Original DB를 Copy해서 Working Copy로 만들어서 돌려야한다는 것, MCP Server 시작하기, FastAPI 백앤드 시작하기, ReAct board 시작하기, DB Reset 하기 (3개 티켓 다 돌기 전에? 이거는 뭐를 의미하는지 잘 모르겠네. 다 돌고 Reset 하는 방법에 대한 것이면 이해하겠는데, Before a full 3-ticket run 이라서) 캡쳐는 HW5의 Expected layout이야. 더 추가된 부분은 상관 없을 것 같은데, 불필요한 파일만 아니면. 빠진 부분이 있다면 문제가 될테니 체크해줘.

(과제가 보여 준 기대 폴더 구조 캡처를 함께 보냈다.)

### 이 문제에서 만든 것

- 기대 폴더 구조와 대조했다. 빠져 있던 `.gitignore`, 루트 `README.md`, `output/github_url.txt` 3개를 만들었다. 나머지는 모두 있었고, 더 있는 것은 영어판 문서와 보조 코드다.
- `.gitignore` — HW 4를 바탕으로 하되 `data/` 폴더(원본 DB와 작업용 DB)는 올린다. 빼는 것은 `.env`, 가상환경, `node_modules`, 빌드 결과, `data.zip`, SQLite 임시 파일, 마스킹 버그가 있던 개발용 감사 기록이다.
- 루트 `README.md`(영어) — 무엇인지, 필요한 것, 설치, 그리고 요청한 순서대로 적었다: 1) 원본 DB를 복사해 작업용 DB 만들기 2) MCP 서버 시작 3) FastAPI 백엔드 시작 4) React 보드 시작 5) 전체 실행 전 DB 리셋(방법 4가지, 리셋 후 최종 상태로 되돌리는 법). 결과물 안내 표도 넣었다.
- "Before a full 3-ticket run"의 뜻: 세 티켓을 처음부터 다 돌리기 **전에** 작업용 DB를 원본 값으로 되돌리라는 뜻이다. 그래야 매번 같은 출발점(현금 $3,400, 티켓 모두 open)에서 시작하고 결과를 비교할 수 있다. 가게 규칙 "전체 실행 전에 리셋"과 같은 내용이다.
- 올리는 작업용 DB는 Problem 9 실행 뒤의 최종 상태(잔액 $152, 세 티켓 해결)다. 채점자가 바로 결과를 볼 수 있다.
- `output/github_url.txt` — https://github.com/Yonghyuk-Yale/mgt409-hw5

### Prompt 2 (채점자 입장의 최종 점검)

잘 올라간 것 같고, 이제 너가 Grader의 입장이 되어서, 해당 URL에 있는 내용을 가상공간에 Clone해서 Grading 해주길 바래. 내가 그동안 보내준 채점 기준들 잘 확인해보고, 잘 돌아가는지 문제는 없는지, 결과는 output과 같이 잘 나오는지. 마지막 점검이니깐 정확하고 꼼꼼하게 잘 해줘!

### 최종 점검에서 한 것

- GitHub 주소를 임시 폴더에 새로 받아 README 순서대로 따라 했다: 가상환경 → 설치 → `.env` 복사 → MCP 서버(`.mcp.json` 명령과 HTTP 모드) → 백엔드 → 대시보드 설치·빌드·실행. 모두 정상이었다. 포트만 사용 중인 것을 피해 바꿨다.
- 백엔드 주소 15개가 모두 기대대로 응답했다. 없는 티켓은 404, 해결된 티켓 재실행과 이미 실행된 지급 재승인은 409였다.
- 복사본에서 실제 한 번 실행했다: README대로 리셋 → 102 실행(74,214 토큰) → 에이전트 이름으로 승인하면 거절 → 채점자 이름으로 승인하면 현금 $3,400 → $1,000 → 티켓 닫기. 모든 단계가 감사 기록에 남았고 실행 결과가 파일로 저장되었다.
- 결과물끼리의 일치를 자동으로 97개 항목 점검해 모두 통과했다: DB 금액 대조, 결과 JSON 필드, 감사 기록의 실행·토큰, HTML 탭·자리표시자·외부 파일, 하네스 수치, 스모크 테스트 값, 모델 이름(gpt-6-luna만), 감사 기록의 고객 이름 없음, 필수 프롬프트 파일, 문제 1~11 기록.
- 하나를 고쳤다: 대시보드의 Expected vs Actual 탭이 101 도구 일치를 8/9로 보여 `desk_tickets.html`의 9/12와 달랐다. 대시보드가 같은 Expected 표를 줄 단위로 세도록 고쳐 9/12, 7/9, 10/12로 맞추고, `resolved_board.html`의 해당 스크린샷도 다시 찍어 GitHub에 다시 올렸다.
