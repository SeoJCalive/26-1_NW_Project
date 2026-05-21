# Web UI TUI Parity Plan

## TL;DR
> **Summary**: Update the current Web UI preview so it mirrors the TUI's node-first monitoring experience instead of remaining a generic topology dashboard. Keep the work scoped to static preview parity and do not introduce backend/runtime Web UI infrastructure.
> **Deliverables**:
> - TUI-to-Web parity schema in `docs/reference/ui-preview/preview.revised.jsx`
> - Updated node cards/detail panel/controller surface showing all TUI sections
> - Monitor-specific situation board in Web UI preview
> - Expanded static sanity checks and Playwright DOM QA evidence
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 → Task 2/3/4 → Task 5 → Final Verification

## Context
### Original Request
- User confirmed the parity direction and asked: "web UI를 어떻게 수정해야할지 계획을 세워."
- Immediate prior finding: current Web UI preview contains five data-plane nodes but does not yet show all TUI elements per node.

### Interview Summary
- No further user decision is required before planning.
- User's priority is TUI parity: every element the TUI shows should have an equivalent Web UI field/section.
- Web UI must remain an extension of the existing TUI educational observation experience, not a separate generic dashboard.

### Metis Review (gaps addressed)
- Scope creep risk addressed by limiting work to `docs/reference/ui-preview/preview.revised.jsx` and optional `preview.revised.html` title/meta only if needed.
- Controller/UI must be visible as a control/status surface but must not be rendered as a data-plane peer.
- Parity must be validated through explicit schema/sanity checks and Playwright DOM assertions.
- Edge cases must be represented: host no previous peer, monitor no next peer, stale liveness, retry/duplicate non-zero, empty fallback, long payload/truncated preview.

## Work Objectives
### Core Objective
Make `docs/reference/ui-preview/preview.revised.jsx` display the same information categories as the current TUI overview and focused node monitor.

### Deliverables
- Static parity data model for each node.
- Web UI sections for TUI common node fields.
- Web UI sections for non-monitor structured traffic lanes.
- Web UI Monitor situation board with the six TUI sections.
- Controller/UI surface explicitly labeled as control/status plane.
- Automated preview sanity checks and Playwright DOM verification evidence.

### Definition of Done (verifiable conditions with commands)
- `python -m unittest tests.test_node_monitor_mode tests.test_integrated_monitor_preservation tests.test_hop_state_visibility tests.test_node_view_contracts -q` still passes.
- `python -m py_compile main.py nw_demo/*.py tests/*.py` still passes.
- Browser QA against `file:///home/tjwocjf0915/workspace/NW_project/docs/reference/ui-preview/preview.revised.html` verifies required Web UI sections using Playwright.
- `runSanityChecks()` in `preview.revised.jsx` asserts all five data-plane nodes and all parity schema keys exist.

### Must Have
- Data-plane nodes in order: host, agent, r1, r2, monitor.
- Controller/UI shown as control/status surface, outside the data path.
- Per-node common fields equivalent to TUI: state, queue, pending, retries, dup, liveness, reported, last_seen, note, controls, hop summary.
- Non-monitor focused/detail fields equivalent to TUI structured traffic monitor: previous node, received data, response data, next node, sent data, received response, recent traffic lineage.
- Monitor board sections: 처리 경로, 현재 상황, Host 최신 상태, 전달 건강도, 확인 응답 / 재시도, 최근 알림/이벤트.
- Korean-first visible labels; technical tokens such as ACK, retry, queue may be kept when useful.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Do not create a production Web UI app, package setup, HTTP API, WebSocket, or gateway.
- Do not modify Python runtime/TUI/data-plane files.
- Do not place Controller/UI in the data path arrow chain.
- Do not add generic dashboard charts/KPIs that are not rooted in TUI fields.
- Do not use raw full payload dumps as the primary overview display.
- Do not rely on "user visually checks it" as acceptance criteria.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after; no new JS test framework setup because preview uses CDN React/Babel only.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 foundation schema and parity matrix.
Wave 2: Task 2 node card/detail parity, Task 3 controller surface parity, Task 4 monitor board parity can proceed after Task 1.
Wave 3: Task 5 sanity/Playwright verification after all UI rendering tasks.

### Dependency Matrix (full, all tasks)
- Task 1 blocks Tasks 2, 3, 4, 5.
- Task 2 depends on Task 1 and blocks Task 5.
- Task 3 depends on Task 1 and blocks Task 5.
- Task 4 depends on Task 1 and blocks Task 5.
- Task 5 depends on Tasks 1-4.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 1 task → visual-engineering
- Wave 2 → 3 tasks → visual-engineering
- Wave 3 → 1 task → unspecified-high

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Define Web Preview Parity Schema

  **What to do**: In `docs/reference/ui-preview/preview.revised.jsx`, replace/extend each `revisedNodes` entry so it has explicit TUI-parity fields. Add stable keys for `summary`, `observation`, `note`, `controls`, `hopSummary`, `trafficBoard`, `monitorBoard`, and `activityLogs`. Keep existing visual values only when they map cleanly into these fields. Preserve the five data-plane nodes in the order `host`, `agent`, `r1`, `r2`, `monitor`. Represent edge cases explicitly: host previous peer is not applicable/agent polling source, monitor next peer is not applicable, R2 has retry/timeout sample, Monitor has duplicate/ACK sample.
  **Must NOT do**: Do not create runtime fetching, backend gateway, WebSocket, or modify Python files. Do not remove Korean labels. Do not rename `NetworkDemoWebUIRevised`.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: static React preview data model directly drives UI fidelity.
  - Skills: [] - No matching specialized skill is required for static JSX data reshaping.
  - Omitted: [`frontend-ui-ux`] - Not required as a loaded skill unless executor wants design polish; parity is more important than new aesthetics.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2, 3, 4, 5] | Blocked By: []

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:6` - current `revisedNodes` static data source.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:647` - current `runSanityChecks()` location to extend later.
  - TUI Source: `nw_demo/controller_ui.py:923` - `_build_node_section` common TUI fields.
  - TUI Source: `nw_demo/controller_ui.py:481` - `_append_focused_traffic_lines` non-monitor traffic board fields.
  - TUI Source: `nw_demo/controller_ui.py:876` - `_append_focused_monitor_board_lines` Monitor six-section board.
  - Type/Order: `nw_demo/config.py:36` - canonical node order.
  - Intent: `INTENT_ALIGNMENT_NOTE.md:13` - Web UI must extend TUI observation experience.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `docs/reference/ui-preview/preview.revised.jsx` contains five node objects with parity keys for common fields.
  - [ ] Node ids are exactly `host`, `agent`, `r1`, `r2`, `monitor` and render in that data-path order.
  - [ ] Controller/UI is not added to `revisedNodes` as a data-plane node.
  - [ ] R2 sample data includes non-zero retry or timeout state.
  - [ ] Monitor sample data includes duplicate/ACK/host-state information.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Schema coverage check
    Tool: Bash
    Steps: Use a one-off Node or Python text inspection script to assert every revisedNodes object has summary, observation, note, controls, hopSummary, and activityLogs keys, and monitor has monitorBoard.
    Expected: Script exits 0 and writes .sisyphus/evidence/task-1-schema.txt with all node ids and keys found.
    Evidence: .sisyphus/evidence/task-1-schema.txt

  Scenario: No runtime scope creep
    Tool: Bash
    Steps: Search project files for newly added package manifests, HTTP server, WebSocket, or runtime gateway code after the change.
    Expected: No new production Web UI/runtime files exist; only preview artifact changes are reported.
    Evidence: .sisyphus/evidence/task-1-scope.txt
  ```

  **Commit**: NO | Message: `update web preview parity schema` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 2. Render Common Node and Structured Traffic Sections

  **What to do**: Update `NodeCard` and `DetailPanel` in `docs/reference/ui-preview/preview.revised.jsx` so every selected node shows TUI common fields: 요약/state/queue/pending/retries/dup, 관찰/liveness/reported/last_seen, 비고/note, 제어/start/pause/reset/kill, hop summary/prev/next/last. Add a dedicated structured traffic panel for non-monitor nodes with sections equivalent to TUI: 이전 노드, 받은 자료, 응답 자료, 다음 노드, 보낸 자료, 받은 응답, 최근 traffic lineage. Use stable `data-testid` attributes: `node-card-{id}`, `detail-common`, `detail-hop-summary`, `detail-traffic-board`, `traffic-previous-peer`, `traffic-next-peer`, `traffic-lineage`.
  **Must NOT do**: Do not display raw multiline JSON dumps. Use concise preview/summary strings. Do not hide required fields behind hover-only interactions.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: React component layout and visual hierarchy.
  - Skills: [] - Static JSX update; no external library docs needed.
  - Omitted: [`playwright`] - Verification is specified in QA; implementation does not need browser automation skill unless executor chooses.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [5] | Blocked By: [1]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:336` - current `NodeCard` rendering.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:575` - current `DetailPanel` rendering.
  - TUI Source: `nw_demo/controller_ui.py:933` - common node section text.
  - TUI Source: `nw_demo/controller_ui.py:481` - structured traffic monitor fields.
  - Tests: `tests/test_node_monitor_mode.py:27` - focused monitor expects structured lane labels.
  - Tests: `tests/test_hop_state_visibility.py:37` - hop summary state taxonomy examples.

  **Acceptance Criteria**:
  - [ ] Every node card contains visible status and at least state/queue/pending/retry/duplicate indicators.
  - [ ] Detail panel for `host`, `agent`, `r1`, and `r2` includes `detail-traffic-board` with previous and next peer sections.
  - [ ] `r1` and `r2` details show pending/retry/duplicate/ACK-related content.
  - [ ] Host edge case does not invent fake upstream data; it labels non-applicable or polling source clearly.
  - [ ] Long payload/preview values are rendered as bounded text, not raw expanded JSON.

  **QA Scenarios**:
  ```
  Scenario: Non-monitor traffic parity
    Tool: Playwright
    Steps: Open preview.revised.html, click/select R1 node card using [data-testid="node-card-r1"], then assert [data-testid="detail-traffic-board"] contains 이전 노드, 받은 자료, 응답 자료, 다음 노드, 보낸 자료, 받은 응답, 최근 traffic lineage.
    Expected: All required labels are present in the R1 detail panel.
    Evidence: .sisyphus/evidence/task-2-r1-traffic.png

  Scenario: Host edge case remains truthful
    Tool: Playwright
    Steps: Open preview.revised.html, click/select host node card, inspect detail traffic board.
    Expected: Host detail shows host polling/Agent relation and does not claim Host forwards EVENT to R1/R2/Monitor.
    Evidence: .sisyphus/evidence/task-2-host-edge.png
  ```

  **Commit**: NO | Message: `render node traffic parity panels` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 3. Make Controller/UI Surface Explicit Without Data-Path Confusion

  **What to do**: Update `MonitoringHub`, `ControlPanel`, and diagram labels so Controller/UI is visibly the sixth role/control-status surface. Label it `Controller/UI · 제어/관찰 표면` or equivalent. Show status report collection, liveness calculation, local focus/overview state, and control command distribution. Keep report links from all five data-plane nodes to this surface. Ensure the data path remains only `Host -> Agent -> R1 -> R2 -> Monitor`.
  **Must NOT do**: Do not add Controller/UI to `mainLinks` as a data-plane node. Do not imply it forwards EVENT/ACK.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: diagram semantics and control surface presentation.
  - Skills: [] - No external skill required.
  - Omitted: [`frontend-ui-ux`] - This is semantic parity, not redesign.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [5] | Blocked By: [1]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:144` - `reportingHub` current metadata.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:379` - current `MonitoringHub` component.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:510` - current `ControlPanel`.
  - Spec: `IMPLEMENTATION_SPEC.md:145` - controller/gateway surface semantics.
  - Spec: `IMPLEMENTATION_SPEC.md:136` - data path definition.
  - Intent: `INTENT_ALIGNMENT_NOTE.md:87` - Controller/UI must not look like data plane.

  **Acceptance Criteria**:
  - [ ] Web preview contains a visible `Controller/UI` or `Controller / UI` label.
  - [ ] Controller/UI surface includes status collection and control distribution concepts.
  - [ ] Controller/UI surface includes focus/overview as local UI state, not node control.
  - [ ] `mainLinks` remains exactly four data-path links.
  - [ ] `reportLinks` remains one per data-plane node.

  **QA Scenarios**:
  ```
  Scenario: Controller surface visible and separate
    Tool: Playwright
    Steps: Open preview.revised.html and locate [data-testid="controller-surface"]. Assert it contains Controller/UI, 상태 수집, 제어 명령, focus/overview or 관찰 대상 전환.
    Expected: Controller surface exists and is separate from [data-testid="data-path"].
    Evidence: .sisyphus/evidence/task-3-controller-surface.png

  Scenario: Data path remains five-node chain
    Tool: Bash
    Steps: Inspect preview.revised.jsx mainLinks and revisedNodes with a script.
    Expected: mainLinks are host-agent, agent-r1, r1-r2, r2-monitor only; no Controller/UI in mainLinks.
    Evidence: .sisyphus/evidence/task-3-data-path.txt
  ```

  **Commit**: NO | Message: `clarify controller surface in web preview` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 4. Add Monitor Situation Board Parity

  **What to do**: Add a dedicated Monitor board rendering path in `DetailPanel` or a new component such as `MonitorBoard`. When selected node is `monitor`, show the six TUI board sections exactly as named: `처리 경로`, `현재 상황`, `Host 최신 상태`, `전달 건강도`, `확인 응답 / 재시도`, `최근 알림/이벤트`. Use static sample data that demonstrates R2 -> Monitor receipt, ACK returned or dropped/retry observation, host latest state, duplicate suppression, out-of-order counter, and recent event summary.
  **Must NOT do**: Do not show raw EVENT JSON or raw payload dumps as the primary monitor board. Do not include fragile ASCII signal-flow diagrams.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: Monitor board is a UI composition task with exact semantic sections.
  - Skills: [] - No external skill needed.
  - Omitted: [] - None.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [5] | Blocked By: [1]

  **References**:
  - TUI Source: `nw_demo/controller_ui.py:876` - focused Monitor board source.
  - TUI Source: `nw_demo/controller_ui.py:882` - exact Monitor section list.
  - Tests: `tests/test_node_monitor_mode.py:66` - expected Monitor section labels and no raw JSON dump.
  - Guide: `docs/reference/network-project/guide/노드 전달.md:99` - Monitor role and human-readable display.
  - Guide: `docs/reference/network-project/guide/노드 자료형.md:1154` - Monitor status report as focused board source.

  **Acceptance Criteria**:
  - [ ] Selecting Monitor shows all six Monitor board sections by exact Korean labels.
  - [ ] Monitor board shows host latest state with CPU/memory/service/latency/fault mode.
  - [ ] Monitor board shows health counters: stored/logged, duplicate suppressed, out-of-order.
  - [ ] Monitor board shows ACK/retry status including ACK returned or dropped/retry observation.
  - [ ] Monitor board does not contain raw `"msg_type": "EVENT"` or raw `"payload":` dump.

  **QA Scenarios**:
  ```
  Scenario: Monitor board section parity
    Tool: Playwright
    Steps: Open preview.revised.html, click/select [data-testid="node-card-monitor"], assert [data-testid="monitor-board"] contains 처리 경로, 현재 상황, Host 최신 상태, 전달 건강도, 확인 응답 / 재시도, 최근 알림/이벤트.
    Expected: All six sections are visible and grouped under the Monitor detail.
    Evidence: .sisyphus/evidence/task-4-monitor-board.png

  Scenario: Monitor board avoids raw dump
    Tool: Playwright
    Steps: Open preview.revised.html, select Monitor, read page text.
    Expected: Page text does not contain '"msg_type": "EVENT"' or '"payload":'.
    Evidence: .sisyphus/evidence/task-4-monitor-no-raw.txt
  ```

  **Commit**: NO | Message: `add monitor situation board parity` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 5. Expand Sanity Checks and Agent-Executable Browser QA

  **What to do**: Extend `runSanityChecks()` in `preview.revised.jsx` to validate parity data coverage: five data-plane nodes, four main data links, five report links, required common keys, required non-monitor traffic keys, required monitor board sections, Controller/UI surface metadata. Then run browser QA using Playwright against `preview.revised.html`. If no Playwright MCP is available in the execution environment, use a local browser-capable alternative already available; do not add dependencies unless explicitly approved.
  **Must NOT do**: Do not introduce a package manager setup solely for tests. Do not remove `runSanityChecks()`.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: final verification spans static code checks and browser QA.
  - Skills: [`playwright`] - Browser verification of the preview is required if skill/tool is available.
  - Omitted: [`review-work`] - Final plan already has separate verification wave; executor can use review agents later if needed.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [] | Blocked By: [1, 2, 3, 4]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:647` - current `runSanityChecks()`.
  - Pattern: `docs/reference/ui-preview/preview.revised.html:22` - preview loads JSX via Babel.
  - TUI Tests: `tests/test_node_monitor_mode.py:47` - Monitor/Agent/R1 focused expectations.
  - TUI Tests: `tests/test_integrated_monitor_preservation.py:70` - overview preservation expectations.

  **Acceptance Criteria**:
  - [ ] `runSanityChecks()` asserts all required parity schema keys and section names.
  - [ ] Browser console has no failed assertions when loading `preview.revised.html`.
  - [ ] Playwright DOM QA confirms all required node cards and detail sections.
  - [ ] Existing Python TUI tests still pass.
  - [ ] Evidence files are written under `.sisyphus/evidence/`.

  **QA Scenarios**:
  ```
  Scenario: Full Web UI parity DOM check
    Tool: Playwright
    Steps: Open file:///home/tjwocjf0915/workspace/NW_project/docs/reference/ui-preview/preview.revised.html. Assert node cards host/agent/r1/r2/monitor exist. For each non-monitor node, select it and assert common, hop summary, and traffic board sections exist. Select Monitor and assert monitor board sections exist.
    Expected: All assertions pass; screenshot saved.
    Evidence: .sisyphus/evidence/task-5-full-dom-parity.png

  Scenario: Regression check for Python TUI unaffected
    Tool: Bash
    Steps: Run python -m unittest tests.test_node_monitor_mode tests.test_integrated_monitor_preservation tests.test_hop_state_visibility tests.test_node_view_contracts -q and python -m py_compile main.py nw_demo/*.py tests/*.py.
    Expected: Commands exit 0.
    Evidence: .sisyphus/evidence/task-5-python-regression.txt
  ```

  **Commit**: NO | Message: `verify web preview tui parity` | Files: [`docs/reference/ui-preview/preview.revised.jsx`, `.sisyphus/evidence/*`]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright)
- [ ] F4. Scope Fidelity Check — deep
## Commit Strategy
- Do not commit unless the user explicitly requests a git commit.
- Keep changes focused on `docs/reference/ui-preview/preview.revised.jsx` unless a tiny `preview.revised.html` title/meta update is required by implementation.
- Do not commit `.sisyphus/evidence/*` unless the user requests evidence artifacts in commit.

## Success Criteria
- Web UI preview visibly contains all five data-plane nodes and an explicit Controller/UI control/status surface.
- Every selected node exposes TUI common fields.
- Every non-monitor selected node exposes structured traffic fields.
- Monitor selected view exposes all six TUI situation-board sections.
- Static sanity checks and browser DOM assertions pass without manual inspection.
- Existing Python TUI tests remain green.
