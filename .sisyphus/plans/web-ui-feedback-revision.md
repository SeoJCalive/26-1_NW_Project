# Web UI Feedback Revision Plan

## TL;DR
> **Summary**: Correct the static Web UI preview after user feedback by removing the separate Controller/UI visual entity, translating TUI-like copied text into fixed dashboard slots, and deduplicating per-node information. This plan supersedes the literal-copy portions of `.sisyphus/plans/web-ui-tui-parity.md` while preserving the goal of carrying TUI observation meaning into the Web UI.
> **Deliverables**:
> - `docs/reference/ui-preview/preview.revised.jsx` revised to show only five graph nodes: Host, Agent, R1, R2, Monitor
> - Page-level control/status chrome instead of a graph/controller hub
> - Fixed node dashboard slot schema with human-readable labels and updatable values
> - Deduplication matrix applied across NodeCard, DetailPanel, traffic board, monitor board, logs, and controls
> - Static and rendered QA evidence under `.sisyphus/evidence/`
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 → Tasks 2/3/4 → Task 5

## Context
### Original Request
- User feedback:
  1. `컨트롤러 노드는 필요없다. webUI 자체가 컨트롤러 노드이다.`
  2. `TUI의 UI 표현 요소(state =, attempt = 등)를 그대로 가져오는 것이 아니다... 계기판과 같이 칸을 픽스하고 해당 칸이 어떤 정보를 갱신할지 명확히 해야한다.`
  3. `각 노드별 중복되는 요소를 검토 후 제거하라... input 표현요소 + TUI요소를 포함해 중복적 요소가 반영된 것 같다.`

### Interview Summary
- No additional user decision is blocking.
- Interpret feedback as a semantic redesign of the static preview, not a runtime Web UI request.
- Keep TUI educational meaning, but do not copy TUI labels/layout/text directly.

### Metis Review (gaps addressed)
- Must explicitly state this plan supersedes prior literal TUI copying.
- Must remove the visual Controller/UI hub/card/entity and any controller-like graph edge.
- Must avoid reintroducing controller under names like `Reporting Hub`, `Control Hub`, `Management Node`, or `UI Hub`.
- Must define an authoritative display location for each repeated fact before deleting duplicates.
- Must verify with static checks and rendered preview QA; no human visual confirmation.

## Work Objectives
### Core Objective
Revise the static Web UI preview so it behaves conceptually like a Web dashboard: the browser page is the controller/viewer surface, each node has fixed dashboard slots for updateable facts, and duplicate TUI-derived text is removed.

### Deliverables
- Controller visual entity removal from graph/canvas.
- Page-level chrome/toolbar/status strip for control and observation affordances.
- Fixed dashboard slot schema for node cards and detail panels.
- Deduplication matrix embedded in comments or evidence and reflected in UI responsibilities.
- Updated `runSanityChecks()` covering controller removal, fixed slots, and forbidden strings.
- Browser QA evidence proving graph and details render correctly.

### Definition of Done (verifiable conditions with commands)
- `python -m py_compile main.py nw_demo/*.py tests/*.py` passes.
- `python -m unittest tests.test_node_monitor_mode tests.test_integrated_monitor_preservation tests.test_hop_state_visibility tests.test_node_view_contracts -q` passes.
- Static inspection confirms `preview.revised.jsx` contains no visible UI strings matching forbidden TUI/controller-copy patterns listed in Task 5.
- Rendered preview confirms Host, Agent, R1, R2, Monitor appear as the only graph nodes and no separate Controller/UI/hub node appears.
- `runSanityChecks()` passes in the browser console path used by the preview.

### Must Have
- Exactly five graph/data-plane node cards: `host`, `agent`, `r1`, `r2`, `monitor`.
- Data path remains `Host -> Agent -> R1 -> R2 -> Monitor`.
- Browser UI itself is treated as the controller/viewer; control/status affordances live in page chrome only.
- Fixed slots use human-readable labels such as Korean equivalents of `처리 상태`, `대기열`, `ACK 대기`, `재시도 정책`, `중복 처리`, `최근 이벤트`, `이전 구간`, `다음 구간`.
- Each repeated fact has one authoritative display location.
- Korean-first visible labels; technical terms like ACK, retry, event_id may remain where useful.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Do not create a production Web UI app, HTTP API, WebSocket, gateway, build setup, or package manifest.
- Do not modify Python runtime/TUI/data-plane behavior.
- Do not show `Controller/UI`, `제어/관찰 표면`, `Reporting Hub`, `Control Hub`, `Management Node`, or equivalent as a graph node/card/hub.
- Do not keep TUI-style visible strings such as `state =`, `attempt =`, `queue=`, `pending=`, `retries=`, `dup=`.
- Do not use raw JSON dumps as primary UI.
- Do not solve duplication by deleting educational facts; move each fact to its authoritative slot.
- Do not rely on user visual confirmation.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after; no JS test framework setup because the preview uses static React/Babel CDN.
- QA policy: Every implementation task includes static or rendered QA.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 fact inventory and authority matrix.
Wave 2: Task 2 controller entity removal, Task 3 fixed slot conversion, Task 4 node deduplication can proceed after Task 1.
Wave 3: Task 5 sanity/QA/documentation update after Tasks 2-4.

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

- [ ] 1. Build Fact Inventory and Deduplication Matrix

  **What to do**: Inspect `docs/reference/ui-preview/preview.revised.jsx` and create a working fact inventory for all repeated node facts before editing UI structure. Use this authority matrix as the implementation rule: node identity/role → `NodeCard` title/subtitle and `DetailPanel` header only; current processing state → one fixed `NodeCard` slot and optional detail explanation; queue/pending → one fixed slot group, not raw repeated lines; retry/duplicate → detail policy slot or monitor health slot, with only a concise badge allowed elsewhere; recent activity → `activityLogs` only; data path → graph only; control/status affordance → page chrome only. The matrix may be captured in `.sisyphus/evidence/task-1-dedup-matrix.md` and optionally as a short source comment near the UI slot schema.
  **Must NOT do**: Do not start deleting UI sections before the matrix is written. Do not make Controller/UI authoritative for any graph fact.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: UI information architecture and static React component responsibilities.
  - Skills: [] - No available skill specifically matches static preview information architecture.
  - Omitted: [`frontend-ui-ux`] - Full visual redesign skill is unnecessary; the task is semantic correction.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2, 3, 4, 5] | Blocked By: []

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:553` - `cardStats()` currently duplicates raw key summaries.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:599` - `NodeCard` currently shows stats plus repeated raw queue/pending/retry/dup lines.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:874` - `CommonNodeSection` repeats common node facts in detail.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:921` - `TrafficBoard` carries structured traffic facts.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:996` - `DetailPanel` composes detail sections.
  - Intent: `INTENT_ALIGNMENT_NOTE.md:53` - node-local activity is important, but it should be structured.
  - Intent: `INTENT_ALIGNMENT_NOTE.md:123` - avoid adding a separate management hub entity.

  **Acceptance Criteria**:
  - [ ] Evidence file lists every fact family: identity, role, liveness, processing state, queue, pending ACK, retry, duplicate, previous hop, next hop, event lineage, recent activity, control/status affordance.
  - [ ] Evidence file assigns exactly one authoritative UI location for each fact family.
  - [ ] Evidence file lists specific duplicate render locations to remove or downgrade.
  - [ ] No source files outside `docs/reference/ui-preview/`, `.sisyphus/evidence/`, and optional `AI_IMPLEMENTATION_BRIEF.md` are changed by this task.

  **QA Scenarios**:
  ```
  Scenario: Dedup matrix completeness
    Tool: Bash
    Steps: Generate `.sisyphus/evidence/task-1-dedup-matrix.md`; verify it contains the headings `Fact`, `Authoritative Location`, `Allowed Secondary Location`, and `Remove From` plus all fact families listed in acceptance criteria.
    Expected: Script exits 0 and prints `dedup matrix complete`.
    Evidence: .sisyphus/evidence/task-1-dedup-matrix.md

  Scenario: Scope remains static-preview only
    Tool: Bash
    Steps: Inspect changed files after task completion.
    Expected: Only `.sisyphus/evidence/task-1-dedup-matrix.md` and optional preview source comments changed.
    Evidence: .sisyphus/evidence/task-1-scope.txt
  ```

  **Commit**: NO | Message: `plan web preview fact ownership` | Files: [`docs/reference/ui-preview/preview.revised.jsx`, `.sisyphus/evidence/task-1-dedup-matrix.md`]

- [ ] 2. Remove Separate Controller/Hub Graph Entity

  **What to do**: In `docs/reference/ui-preview/preview.revised.jsx`, remove `reportingHub`, `reportLinks`, `getHubAnchor()`, `buildReportPath()`, `MonitoringHub()`, and the `<MonitoringHub />` render from `DiagramCanvas`. Remove report-link SVG paths and labels that visually connect data-plane nodes to the hub. Replace this with page-level chrome outside the graph, such as a compact toolbar/status strip above or beside the preview that says the browser page can observe nodes, switch focus, and issue controls. The chrome must not be positioned inside the graph canvas as a node/card/hub and must not use `data-testid="controller-surface"`.
  **Must NOT do**: Do not rename the hub to another controller-like graph object. Do not add a sixth node to `revisedNodes`. Do not show a data-plane arrow to the page chrome.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: Diagram semantics and page-level UI restructuring.
  - Skills: [] - No external library skill required.
  - Omitted: [`playwright`] - QA uses browser automation, but implementation itself is static JSX.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [5] | Blocked By: [1]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:389` - `reportingHub` object to remove.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:413` - `reportLinks` to remove.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:535` - `getHubAnchor()` depends on `reportingHub`.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:546` - `buildReportPath()` depends on report links.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:640` - `MonitoringHub()` currently renders separate controller surface.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:727` - report link SVG paths.
  - Spec: `IMPLEMENTATION_SPEC.md:136` - data path is only Host -> Agent -> R1 -> R2 -> Monitor.
  - Spec: `IMPLEMENTATION_SPEC.md:145` - Web UI is a controller/gateway surface representation, not a data-plane peer.

  **Acceptance Criteria**:
  - [ ] `revisedNodes` still contains exactly five ids: `host`, `agent`, `r1`, `r2`, `monitor`.
  - [ ] No rendered graph/canvas element displays `Controller/UI`, `Reporting Hub`, `Control Hub`, `UI Hub`, `Management Node`, or `제어/관찰 표면`.
  - [ ] `reportingHub`, `reportLinks`, `MonitoringHub`, `getHubAnchor`, and `buildReportPath` are removed from `preview.revised.jsx`.
  - [ ] Page-level control/status chrome exists outside the graph canvas and explains focus/overview/control affordances without looking like a node.
  - [ ] `mainLinks` remains exactly four data-path links.

  **QA Scenarios**:
  ```
  Scenario: Graph has no controller entity
    Tool: Playwright
    Steps: Open `preview.revised.html`; query graph node cards using `[data-testid^="node-card-"]`; collect their visible names.
    Expected: Exactly Host, Agent, R1, R2, Monitor are present; no Controller/UI/hub/management card exists.
    Evidence: .sisyphus/evidence/task-2-no-controller-node.png

  Scenario: Controller strings removed from graph source
    Tool: Bash
    Steps: Run a static text check over `preview.revised.jsx` for `reportingHub|reportLinks|MonitoringHub|controller-surface|제어/관찰 표면|Reporting Hub|Control Hub|Management Node`.
    Expected: Forbidden graph/controller entity strings are absent, except if the evidence script explicitly whitelists non-visible comments explaining removal.
    Evidence: .sisyphus/evidence/task-2-controller-removal.txt
  ```

  **Commit**: NO | Message: `remove controller hub from web preview graph` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 3. Convert TUI-Like Text into Fixed Dashboard Slots

  **What to do**: Replace raw key/value UI copy in `cardStats()`, `NodeCard`, `CommonNodeSection`, `TrafficBoard`, and `MonitorBoard` with a slot schema. Each slot must have a stable semantic key, a human-readable Korean label, a value, and optional helper text. Use labels like `처리 상태`, `대기열`, `ACK 대기`, `재시도`, `중복 처리`, `최근 이벤트`, `이전 구간`, `다음 구간`, `마지막 응답`. Values may still contain technical tokens such as `ACK`, `event_id`, `retry`, or ids, but visible labels must not be copied TUI raw keys. Keep `data-testid` hooks for the slot groups, e.g. `dashboard-slot-processing-state`, `dashboard-slot-queue-depth`, `dashboard-slot-pending-ack`, `dashboard-slot-retry-policy`, `dashboard-slot-duplicate-handling`.
  **Must NOT do**: Do not keep visible UI text containing `state=`, `state =`, `attempt=`, `attempt =`, `queue=`, `pending=`, `retries=`, or `dup=`. Do not replace them with raw JSON or monospaced dumps.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: Component layout and dashboard slot semantics.
  - Skills: [] - Static React/Babel code only.
  - Omitted: [`frontend-ui-ux`] - Visual polish is secondary to semantic clarity.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [5] | Blocked By: [1]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:553` - raw `cardStats()` label source.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:632` - visible `queue=`, `pending=`, `retries=`, `dup=` strings to remove.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:330` - Monitor rows currently use `구간 상태=`, `종류=`, `대상=`, `CPU=`, etc.; translate to slot labels/values instead of equals text.
  - Intent: `INTENT_ALIGNMENT_NOTE.md:82` - screen should feel like an operating/monitoring surface, not a static copied state board.

  **Acceptance Criteria**:
  - [ ] Node cards render fixed dashboard slots with descriptive labels and values.
  - [ ] Selected node details use the same slot vocabulary and do not show TUI-style equals strings as labels.
  - [ ] Monitor board rows are translated into labeled slots, not `key=value` text lines.
  - [ ] Every slot group has stable `data-testid` attributes for QA.
  - [ ] Static check finds no forbidden visible-copy strings: `state=`, `state =`, `attempt=`, `attempt =`, `queue=`, `pending=`, `retries=`, `dup=`.

  **QA Scenarios**:
  ```
  Scenario: Fixed dashboard slots render for relay node
    Tool: Playwright
    Steps: Open preview, click `[data-testid="node-card-r1"]`, assert slot test ids for processing state, queue depth, pending ACK, retry policy, duplicate handling, previous hop, and next hop exist.
    Expected: All slot labels are human-readable Korean labels and contain updateable values.
    Evidence: .sisyphus/evidence/task-3-r1-slots.png

  Scenario: TUI equals-text removed
    Tool: Bash
    Steps: Search `preview.revised.jsx` and rendered DOM dump for `state=|state =|attempt=|attempt =|queue=|pending=|retries=|dup=`.
    Expected: No matches in visible UI strings or rendered DOM.
    Evidence: .sisyphus/evidence/task-3-forbidden-tui-copy.txt
  ```

  **Commit**: NO | Message: `translate tui text into dashboard slots` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 4. Apply Deduplication Across Node Card, Detail, Boards, Logs, and Controls

  **What to do**: Refactor render responsibilities according to Task 1. `NodeCard` should be a compact status card: identity, liveness, 3-5 key slots max. `DetailPanel` should be the authoritative expanded view for selected node details. `TrafficBoard` should own previous/next hop data only. `MonitorBoard` should own final sink interpretation/health only. `activityLogs` should show recent activity lines only, not restate all slot values. `ControlPanel` should be page-level command affordance only and must not duplicate node-specific `controls` unless it is clearly a global command palette. If node-specific controls remain, render them once in detail, not both globally and per node.
  **Must NOT do**: Do not remove node-first observability. Do not hide critical retry/duplicate/ACK teaching facts; relocate them to one authoritative place.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: UI hierarchy, component responsibility, and duplication cleanup.
  - Skills: [] - No specialized skill required.
  - Omitted: [`ai-slop-remover`] - This is multi-component redesign, not single-file smell cleanup.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [5] | Blocked By: [1]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:777` - `ControlPanel` currently includes global commands that may overlap with node `controls`.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:874` - `CommonNodeSection` responsibility to narrow.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:921` - `TrafficBoard` should own hop traffic only.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:963` - `MonitorBoard` should own monitor-specific final situation only.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:996` - `DetailPanel` composes sections and must not repeat NodeCard verbatim.
  - Intent: `INTENT_ALIGNMENT_NOTE.md:43` - node-first monitoring remains core.

  **Acceptance Criteria**:
  - [ ] `NodeCard` no longer repeats detail-only facts in raw text lines.
  - [ ] Queue/pending/retry/duplicate facts each appear only in their authoritative slot plus at most one concise summary badge if Task 1 permits it.
  - [ ] `activityLogs` do not duplicate slot values line-for-line.
  - [ ] Control affordances appear in one page-level or detail-level location, with no competing global/per-node duplicate command sets.
  - [ ] Host and Monitor edge cases remain truthful: Host has no upstream EVENT receive; Monitor has no next forwarding hop.

  **QA Scenarios**:
  ```
  Scenario: Duplicate count check for selected facts
    Tool: Bash
    Steps: Produce a rendered DOM text dump for R1 selected state; count occurrences of approved fact labels for queue depth, pending ACK, retry, duplicate handling using the Task 1 matrix.
    Expected: Each fact appears only in approved authoritative/secondary locations.
    Evidence: .sisyphus/evidence/task-4-dedup-counts.txt

  Scenario: Edge nodes remain truthful
    Tool: Playwright
    Steps: Click host and monitor node cards. For host, assert no text claims Host forwards EVENT to R1/R2/Monitor. For monitor, assert no text claims Monitor forwards to a next hop.
    Expected: Host and Monitor edge cases are explicitly shown without fake upstream/downstream claims.
    Evidence: .sisyphus/evidence/task-4-edge-nodes.png
  ```

  **Commit**: NO | Message: `deduplicate web preview node panels` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 5. Update Sanity Checks, Evidence, and Living Brief

  **What to do**: Extend `runSanityChecks()` in `preview.revised.jsx` to assert: five graph nodes only, no controller/hub graph entity, no forbidden TUI-copy strings, required fixed slot test ids, and no runtime scope creep strings (`WebSocket`, `fetch(`, `runtime server`, `ws://`). Run Python regression/compile commands. Use browser QA to capture DOM/screenshots for graph and selected node details. Update `AI_IMPLEMENTATION_BRIEF.md` briefly: previous TUI parity preview was corrected so browser page itself is the controller surface; no separate controller hub; TUI semantics are translated into fixed dashboard slots; duplication cleanup applied.
  **Must NOT do**: Do not add long implementation history to `AI_IMPLEMENTATION_BRIEF.md`. Do not update root markdown other than the living brief.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: verification, evidence production, and brief update across files.
  - Skills: [] - No matching specialized skill is required; Playwright can be invoked if available by executor.
  - Omitted: [`review-work`] - Final verification wave already covers independent review.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [Final Verification] | Blocked By: [2, 3, 4]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx` - `runSanityChecks()` currently validates previous parity assumptions and must be updated.
  - Brief: `AI_IMPLEMENTATION_BRIEF.md:63` - current preview description still mentions Controller/UI surface separation; revise to match new feedback.
  - Tests: `tests.test_node_monitor_mode`, `tests.test_integrated_monitor_preservation`, `tests.test_hop_state_visibility`, `tests.test_node_view_contracts` - regression suite to keep Python/TUI stable.

  **Acceptance Criteria**:
  - [ ] `runSanityChecks()` fails if a controller/hub graph entity returns.
  - [ ] Static check fails on forbidden strings: `Controller/UI`, `제어/관찰 표면`, `state=`, `state =`, `attempt=`, `attempt =`, `queue=`, `pending=`, `retries=`, `dup=`, except allowed source comments in evidence scripts.
  - [ ] Static check confirms no `WebSocket`, `fetch(`, `runtime server`, or `ws://` was introduced.
  - [ ] Python compile and focused unittest commands pass.
  - [ ] `AI_IMPLEMENTATION_BRIEF.md` records the new interpretation in ≤5 bullets.

  **QA Scenarios**:
  ```
  Scenario: Full static verification
    Tool: Bash
    Steps: Run Python/text inspection script that checks forbidden strings, node ids, main link count, required slot test ids, and absence of runtime networking markers.
    Expected: Script exits 0 and writes all pass markers.
    Evidence: .sisyphus/evidence/task-5-static-check.txt

  Scenario: Rendered preview verification
    Tool: Playwright
    Steps: Open preview; assert five graph nodes only; assert page-level chrome exists outside graph; click R1 and Monitor; assert fixed slots render and no separate controller node appears.
    Expected: All assertions pass; screenshots/DOM dump saved.
    Evidence: .sisyphus/evidence/task-5-rendered-preview.png and .sisyphus/evidence/task-5-rendered-dom.html

  Scenario: Python regression unaffected
    Tool: Bash
    Steps: Run `python -m py_compile main.py nw_demo/*.py tests/*.py` and `python -m unittest tests.test_node_monitor_mode tests.test_integrated_monitor_preservation tests.test_hop_state_visibility tests.test_node_view_contracts -q`.
    Expected: Both commands pass.
    Evidence: .sisyphus/evidence/task-5-python-regression.txt
  ```

  **Commit**: NO | Message: `verify web preview feedback revision` | Files: [`docs/reference/ui-preview/preview.revised.jsx`, `AI_IMPLEMENTATION_BRIEF.md`, `.sisyphus/evidence/*`]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ Playwright if available)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Do not commit unless the user explicitly requests a commit.
- Preferred single commit after user approval: `fix(ui-preview): clarify web dashboard semantics`.
- Include only `docs/reference/ui-preview/preview.revised.jsx`, optional `docs/reference/ui-preview/preview.revised.html`, `AI_IMPLEMENTATION_BRIEF.md`, and relevant `.sisyphus/evidence/*` if the user wants evidence committed.

## Success Criteria
- User feedback item 1 satisfied: no separate controller node/hub exists; Web UI itself is the controller/viewer surface.
- User feedback item 2 satisfied: TUI raw text is translated into fixed dashboard slots with clear labels and updatable values.
- User feedback item 3 satisfied: duplicate node facts are removed according to a documented authority matrix.
- Static preview scope preserved: no runtime Web UI/API/WebSocket/build system added.
- Existing Python/TUI behavior remains unchanged and regression checks pass.
