# Traffic Snapshot Peer Labels

## TL;DR
> **Summary**: Update the Web UI Traffic Snapshot peer block presentation so endpoint nodes do not show meaningless `next_peer` placeholders, while transit nodes keep both traffic directions with role-appropriate Korean labels.
> **Deliverables**:
> - Role-aware peer block titles in `web_ui/static/app.js`
> - Hidden Host/Monitor `next_peer` placeholder blocks in the Web UI only
> - Single-peer layout support in `web_ui/static/app.css`
> - Agent-executed syntax, regression, and browser DOM/layout verification
> **Effort**: Small UI change with browser QA
> **Parallel**: PARTIAL - implementation is sequential because CSS depends on JS DOM shape; verification can run in a final batch
> **Critical Path**: Task 1 JS peer rendering → Task 2 CSS layout → Final verification

## Context
### Original Request
사용자는 정리된 문제 정의를 바탕으로, 코딩 행동 MD 파일을 읽고 안전하게 수정 계획을 수립하라고 요청했다. 현재 저장소에서 발견된 Markdown 파일은 `README.md`뿐이며, 별도 코딩 행동 MD/AGENTS 문서는 존재하지 않는다.

### Interview Summary
- `Traffic Snapshot`의 `previous_peer` / `next_peer`는 모든 노드에서 같은 의미가 아니다.
- Host/Monitor는 endpoint라 `next_peer`가 실제 상대가 아니라 `not_applicable` placeholder다.
- Backend/API shape는 유지해야 한다.
- Raw recent traffic table은 이번 범위에서 변경하지 않는다.
- 알 수 없는/future node type은 데이터를 숨기지 말고 기존처럼 두 peer block을 보여야 한다.

### Metis Review (gaps addressed)
- Stable branching 기준 확인: `adaptState()`가 `node.id`와 `node.role`을 제공한다 (`web_ui/static/app.js:416-433`).
- Endpoint hide는 known node type + placeholder-shaped `next_peer`일 때만 적용한다. Host/Monitor에서 향후 non-placeholder `next_peer`가 생기면 숨기지 않는다.
- Fallback label/visibility를 명시한다: unknown/future nodes render both peers with localized fallback labels `이전 구간` / `다음 구간`.
- CSS single-peer behavior is required so Host/Monitor do not leave an empty second-column feel.

## Work Objectives
### Core Objective
Make Web UI `Traffic Snapshot` peer blocks match node-specific traffic semantics without changing backend traffic data.

### Deliverables
- `web_ui/static/app.js`: local helper/config for peer block presentation based on `node.id` / `node.role`.
- `web_ui/static/app.js`: render Host previous peer only as `상태 조회 요청/응답` when Host `next_peer` is placeholder.
- `web_ui/static/app.js`: render Monitor previous peer only as `이벤트 수신/ACK` when Monitor `next_peer` is placeholder.
- `web_ui/static/app.js`: render Local Agent peers as `Host 상태 조회` / `이벤트 전달`.
- `web_ui/static/app.js`: render Relay peers as `이벤트 수신` / `이벤트 전달`.
- `web_ui/static/app.css`: one-column `.traffic-peers` layout for one rendered peer block.

### Definition of Done (verifiable conditions with commands)
- `node --check web_ui/static/app.js` exits 0.
- `python -m unittest discover -s tests` exits 0.
- Browser QA against local Web UI verifies:
  - Host `.traffic-peers > div` count is 1 and scoped text shows `상태 조회 요청/응답`.
  - Local Agent `.traffic-peers > div` count is 2 and scoped text shows `Host 상태 조회` / `이벤트 전달`.
  - Relay `.traffic-peers > div` count is 2 and scoped text shows `이벤트 수신` / `이벤트 전달`.
  - Monitor `.traffic-peers > div` count is 1 and scoped text shows `이벤트 수신/ACK`.
  - Endpoint peer grid is one-column; Agent/Relay peer grid remains two-column.

### Must Have
- UI-only change for `Traffic Snapshot` peer block titles/visibility.
- Backend schema unchanged: `previous_peer`, `next_peer`, `detail.traffic`, `/api/state` remain intact.
- Conservative fallback: unknown node types render both peers.
- If known Host/Monitor `next_peer` is not placeholder-shaped, render it rather than hiding unexpected data.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Do not edit Python producer semantics in `nw_demo/`.
- Do not remove or rename backend fields.
- Do not change raw recent traffic table columns/labels in this change.
- Do not add a frontend framework or new test stack.
- Do not broaden into a full localization pass.
- Do not hide data for unknown/future node types.

## Safety Review Checklist
- Purpose fit: This plan changes only the Web UI `Traffic Snapshot` peer block presentation so peer labels/visibility match node semantics.
- Over-scope guard: Do not rename non-peer labels, translate the raw recent traffic table, redesign the detail panel, or alter Host/Agent/Relay/Monitor producers.
- Side-effect guard: Do not change `/api/state`, `detail.traffic`, `previous_peer`, `next_peer`, `traffic.recent`, route rendering, node cards, controls, or overview path logic.
- Error-risk guard: Scope DOM checks to `.traffic-peers` so a label in another section/table cannot create a false pass; verify both endpoint and transit node counts.
- No shortcut guard: Do not hide peer rows with CSS-only tricks. The JS must intentionally render the correct peer spec list, and CSS may only adapt the one-peer layout.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after using existing Python `unittest` suite + JS syntax check + Python Playwright browser smoke.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Keep the work intentionally small: two implementation tasks, then verification. Do not split into extra tasks unless a failing check reveals a concrete defect.

Wave 1: Task 1 (JS rendering helper) then Task 2 (CSS one-peer layout). These are sequential because Task 2 depends on Task 1's `data-peer-count` or equivalent DOM state.
Final Wave: Direct syntax/regression/browser verification in parallel where tool dependencies allow. Any review agent used here must be explicitly read-only and must not edit files.

### Dependency Matrix (full, all tasks)
- Task 1: no dependencies; blocks Task 2 browser layout verification.
- Task 2: depends on Task 1 for one-peer DOM state; blocks final verification.
- Final verification: depends on Tasks 1-2 complete and verified.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 2 tasks → `visual-engineering`
- Final Verification Wave → direct tool checks; optional read-only `oracle` only if a verification result is ambiguous

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Add role-aware Traffic Snapshot peer rendering

  **What to do**:
  - Edit `web_ui/static/app.js` only.
  - Add a small local helper near `trafficSection(node)` such as `trafficPeerSpecs(node, traffic)` or `trafficPeerPresentation(node, traffic)`.
  - Helper must return an ordered list of peer specs: `{ peer, title }`.
  - Required behavior:
    - `node.id === "host-simulator"`: normally return only `traffic.previous_peer` titled `상태 조회 요청/응답` if `traffic.next_peer` is endpoint placeholder.
    - `node.id === "monitor"`: normally return only `traffic.previous_peer` titled `이벤트 수신/ACK` if `traffic.next_peer` is endpoint placeholder.
    - `node.id === "local-agent"`: return previous `Host 상태 조회`, next `이벤트 전달`.
    - `node.role === "Relay"`: return previous `이벤트 수신`, next `이벤트 전달`.
    - fallback: return both previous and next peers titled `이전 구간`, `다음 구간`.
  - Define endpoint placeholder check locally, e.g. `isEndpointPlaceholderPeer(peer)`, and treat the API/runtime placeholder as `peer && peer.hop_state === "not_applicable" && !peer.peer_node_id && !peer.peer_role && !peer.last_received && !peer.last_sent`.
  - If Host/Monitor `next_peer` is not placeholder-shaped, render it with fallback `다음 구간` to avoid data loss.
  - Replace current hard-coded peer HTML at `web_ui/static/app.js:846` with mapped peer specs.
  - Add a `data-peer-count` attribute to the `.traffic-peers` wrapper based on rendered peer count.

  **Must NOT do**:
  - Do not change `traffic.recent` table columns or labels.
  - Do not modify `emptyTraffic()` / `emptyPeer()` backend-shape assumptions.
  - Do not branch on Korean display names.
  - Do not remove `next_peer` from runtime/API data.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: user-facing Web UI label/visibility change.
  - Skills: [`frontend-ui-ux`, `webapp-testing`, `api-and-interface-design`] - Reason: UI semantics, browser QA, and preserving the API/rendering boundary.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: Task 2 | Blocked By: none

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web_ui/static/app.js:824-860` - `trafficSection(node)` / `trafficPeer(peer,title)` current rendering path.
  - Pattern: `web_ui/static/app.js:416-433` - adapted node shape includes stable `node.id` and `node.role`.
  - Pattern: `web_ui/static/app.js:384-407` - `trafficOf`, `emptyPeer`, `emptyTraffic` fallback behavior.
  - Producer: `nw_demo/host_simulator.py:28-30` - Host previous peer is local-agent, next peer is `not_applicable`.
  - Producer: `nw_demo/local_agent.py:62-64` - Local Agent previous Host, next Relay.
  - Producer: `nw_demo/relay.py:43-55` - Relay upstream/downstream peer defaults.
  - Producer: `nw_demo/monitor.py:38-40` - Monitor previous Relay, next `not_applicable`.
  - Test: `tests/test_status_detail_publishers.py:22-52` - Host publisher contract includes `next_peer.hop_state == "not_applicable"`.
  - Test: `tests/test_status_detail_publishers.py:270-312` - Monitor publisher contract includes `next_peer.hop_state == "not_applicable"`.
  - Test: `tests/test_traffic_snapshot_contracts.py:15-25` - traffic schema must keep `previous_peer` and `next_peer`.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `node --check web_ui/static/app.js` exits 0.
  - [ ] Browser DOM check against `http://127.0.0.1:28083` or a newly started Web UI confirms Host `.traffic-peers > div` count is 1 and its scoped text contains `상태 조회 요청/응답`.
  - [ ] Browser DOM check confirms Local Agent `.traffic-peers > div` count is 2 and scoped text contains both `Host 상태 조회` and `이벤트 전달`.
  - [ ] Browser DOM check confirms Relay R1 `.traffic-peers > div` count is 2 and scoped text contains both `이벤트 수신` and `이벤트 전달`.
  - [ ] Browser DOM check confirms Monitor `.traffic-peers > div` count is 1 and its scoped text contains `이벤트 수신/ACK`.
  - [ ] `python -m unittest discover -s tests` exits 0, proving backend traffic schema remains unchanged.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Known node labels and visibility
    Tool: Bash + Python Playwright
    Steps: Open `http://127.0.0.1:28083`; click `[data-testid="node-card-host-simulator"]`, `[data-testid="node-card-local-agent"]`, `[data-testid="node-card-r1"]`, `[data-testid="node-card-monitor"]`; read `#detail-inspector-inner` text after each click.
    Expected: Scoped `.traffic-peers` count is Host=1, Local Agent=2, R1=2, Monitor=1; scoped labels match each node; raw recent table text is ignored for peer-count assertions.
    Evidence: .sisyphus/evidence/task-1-peer-label-dom.txt

  Scenario: Backend schema unchanged
    Tool: Bash
    Steps: Run `python -m unittest discover -s tests`.
    Expected: All tests pass; no producer/API schema test fails.
    Evidence: .sisyphus/evidence/task-1-unittest.txt
  ```

  **Commit**: NO | Message: `ui: clarify traffic peer blocks` | Files: `web_ui/static/app.js`

- [ ] 2. Add one-peer layout for endpoint Traffic Snapshot blocks

  **What to do**:
  - Edit `web_ui/static/app.css` only after Task 1 creates `data-peer-count` or equivalent class on `.traffic-peers`.
  - Keep existing `.traffic-peers` two-column rule for Agent/Relay.
  - Add one-column rule near `web_ui/static/app.css:943-948`, e.g. `.traffic-peers[data-peer-count="1"] { grid-template-columns: minmax(0, 1fr); }`.
  - Ensure single rendered Host/Monitor peer block spans the available width without a blank second column.

  **Must NOT do**:
  - Do not change global detail section layout.
  - Do not change table layout.
  - Do not hide rows within a peer block.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: small layout adjustment with visual/browser verification.
  - Skills: [`frontend-ui-ux`, `webapp-testing`] - Reason: layout clarity and browser-executed verification.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: Final Verification | Blocked By: Task 1

  **References**:
  - Pattern: `web_ui/static/app.css:943-948` - current `.traffic-peers` two-column grid.
  - Pattern: `web_ui/static/app.js:844-846` - wrapper around rendered peer blocks should expose peer count.
  - Browser hook: `web_ui/static/index.html:55-56` - detail inspector DOM target.
  - Browser hook: `web_ui/static/app.js:584-588` - node cards expose `data-testid="node-card-${node.id}"`.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Browser computed style check confirms Host `.traffic-peers` has one grid column.
  - [ ] Browser computed style check confirms Monitor `.traffic-peers` has one grid column.
  - [ ] Browser computed style check confirms Local Agent and R1 `.traffic-peers` still have two columns or two rendered peer blocks with no overlap.
  - [ ] Screenshot evidence captures Host, Local Agent, R1, and Monitor detail states.

  **QA Scenarios**:
  ```
  Scenario: Endpoint layout is single-column
    Tool: Bash + Python Playwright
    Steps: Open Web UI; click Host and Monitor cards; evaluate `getComputedStyle(document.querySelector('.traffic-peers')).gridTemplateColumns` and peer title count for each detail state.
    Expected: Host/Monitor each render one peer title and no empty second column; screenshots saved.
    Evidence: .sisyphus/evidence/task-2-endpoint-layout.txt and .sisyphus/evidence/task-2-host-monitor.png

  Scenario: Transit layout remains two-peer
    Tool: Bash + Python Playwright
    Steps: Click Local Agent and R1 cards; count peer titles inside `.traffic-peers`; capture screenshots.
    Expected: Local Agent and R1 each render two peer titles; no layout overlap; screenshots saved.
    Evidence: .sisyphus/evidence/task-2-transit-layout.txt and .sisyphus/evidence/task-2-agent-relay.png
  ```

  **Commit**: NO | Message: `ui: clarify traffic peer block layout` | Files: `web_ui/static/app.css`

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> Verification is direct and read-only unless a failing check identifies a concrete implementation defect.
> Do not use review agents as implementation agents in this wave; this prevents scope creep after the intended two-file UI change.
- [ ] `node --check web_ui/static/app.js`
- [ ] `python -m unittest discover -s tests`
- [ ] Browser DOM/layout QA for Host, Local Agent, R1, and Monitor using scoped `.traffic-peers` assertions
- [ ] `lsp_diagnostics` on `web_ui/static/app.js` and `web_ui/static/app.css` where the local toolchain supports it; if unsupported, record the toolchain error without editing around it
- [ ] Optional read-only Oracle consultation only if verification produces an ambiguous behavior/risk that cannot be resolved from code and browser evidence
## Commit Strategy
- No commit by default. User did not request commit.
- If user later requests commit, inspect `git status`, `git diff`, and recent log first; stage only `web_ui/static/app.js` and `web_ui/static/app.css` if they are the only intended changes.

## Success Criteria
- User-facing Traffic Snapshot peer block labels match node semantics.
- Host and Monitor no longer show meaningless `next_peer` placeholder blocks.
- Agent and Relay nodes still show both meaningful directions.
- Backend/API traffic schema remains unchanged and regression tests pass.
- Unknown/future nodes retain conservative two-peer visibility.
- Browser evidence proves labels and layout without relying on human visual confirmation.
