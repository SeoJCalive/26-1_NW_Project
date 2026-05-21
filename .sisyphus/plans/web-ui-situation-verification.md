# Web UI Situation Verification Plan

## TL;DR
> **Summary**: 현재 Web UI가 primary/backup routing, route trace, Monitor fault-localization, 제어 버튼 상태를 상황별로 의도대로 표시하는지 Playwright 기반 DOM assertion과 screenshot evidence로 검증한다.
> **Deliverables**:
> - 상황별 browser QA evidence: `.sisyphus/evidence/web-ui-situations/`
> - console error log, DOM/text snapshot, screenshot per scenario
> - 최종 PASS/BLOCK 요약
> **Effort**: Short
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 → Tasks 2-8 → Final Verification Wave

## Context
### Original Request
- 사용자는 현재 수정 사항이 반영된 웹페이지가 각 상황에 따라 의도한 대로 나오는지 확인하려고 한다.
- 먼저 어떤 경우에 어떤 반응이 나와야 하고 어떻게 검증할지 계획을 세우라고 요청했다.

### Interview Summary
- 실행이 아니라 검증 계획 수립 단계다.
- 사용자는 “현재 페이지가 상황별로 의도대로 나오는지”를 확인하려 한다.
- 검증 대상은 recent changes: `r1b/r2b` backup relay, constrained backup route, route trace, Monitor fault-localization, Web UI 표시다.

### Metis Review (gaps addressed)
- 스크린샷은 evidence이며 PASS 기준은 DOM/text assertion이어야 한다.
- scenario마다 reset, console error 수집, screenshot, DOM snapshot을 남긴다.
- valid route만 기대값에 포함한다: `local-agent -> r1 -> r2 -> monitor`, `local-agent -> r1b -> r2b -> monitor`.
- cross-path route는 정상 기대값으로 만들지 않는다. 부재 또는 rejection/불출현을 검증한다.
- source code / selector / routing logic 수정은 금지한다.

## Work Objectives
### Core Objective
현재 Web UI runtime에서 사용자가 볼 페이지가 primary 정상, backup failover, ACK drop/retry, relay delay, lifecycle, focus/overview 상황에서 routing truth와 일치하는지 검증한다.

### Deliverables
- `.sisyphus/evidence/web-ui-situations/task-1-harness/`
- `.sisyphus/evidence/web-ui-situations/task-2-startup-smoke/`
- `.sisyphus/evidence/web-ui-situations/task-3-primary-normal/`
- `.sisyphus/evidence/web-ui-situations/task-4-backup-failover/`
- `.sisyphus/evidence/web-ui-situations/task-5-ackdrop-retry/`
- `.sisyphus/evidence/web-ui-situations/task-6-relay-delay-controls/`
- `.sisyphus/evidence/web-ui-situations/task-7-lifecycle-reset/`
- `.sisyphus/evidence/web-ui-situations/task-8-focus-overview/`
- `.sisyphus/evidence/web-ui-situations/final-summary.md`

### Definition of Done (verifiable conditions with commands)
- `python -m web_ui.server --web-port 18080 --control-port 19110` starts Web UI and supervisor-managed Host / Agent / R1 / R2 / R1B / R2B / Monitor.
- Browser can load `http://127.0.0.1:18080/` and `GET /api/state` returns JSON.
- All scenario evidence directories contain `screenshot.png`, `dom.txt` or `dom.json`, `console.log`, and `assertions.json`.
- No unexpected browser console errors occur in any scenario.
- No scenario shows invalid cross-path route text: `r1 -> r2b`, `r1b -> r2`, `local-agent -> r1 -> r2b`, `local-agent -> r1b -> r2`.
- Final summary states PASS/BLOCK per scenario with exact failing assertion if blocked.

### Must Have
- Use actual browser via Playwright/headless Chromium.
- Use DOM/text assertions as pass/fail.
- Use screenshots only as supporting evidence.
- Use existing selectors only:
  - `#diagram-canvas`
  - `#data-path`
  - `#node-layer`
  - `#detail-inspector`
  - `#detail-inspector-inner`
  - `#runtime-status`
  - `button.node-card[data-node-id]`
  - `[data-command]`
- Reset state before every scenario.
- Fail on uncaught browser errors and unexpected console errors.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Do not modify app code, selectors, routing logic, tests, docs, or CSS.
- Do not do GitHub operations.
- Do not require human visual judgment.
- Do not add permanent browser test files unless separately approved.
- Do not treat Web UI as a new routing source of truth. It only displays controller/node status.
- Do not invent arbitrary mesh/load-balancing behavior.
- Do not expect or normalize cross-path routing.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: browser QA only; no app-code test additions.
- QA policy: Every task has agent-executed scenarios with DOM/text assertion + screenshot evidence.
- Evidence: `.sisyphus/evidence/web-ui-situations/task-{N}-{slug}/`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 harness/setup validation.
Wave 2: Tasks 2-7 browser scenario execution; all depend on Task 1 and use independent reset-before-run.
Wave 3: Task 8 final synthesis and cross-scenario consistency.

### Dependency Matrix (full, all tasks)
- Task 1 blocks Tasks 2-8.
- Tasks 2-7 can run independently after Task 1 if each uses a fresh server or clean reset.
- Task 8 depends on Tasks 2-7 evidence.
- Final Verification Wave depends on Task 8.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 1 task → `unspecified-high` with `webapp-testing`.
- Wave 2 → 6 tasks → `unspecified-high` with `webapp-testing`.
- Wave 3 → 1 task → `writing` / `unspecified-high`.

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Establish Playwright Harness and Baseline Runtime

  **What to do**: Start Web UI with supervisor-managed roles using `python -m web_ui.server --web-port 18080 --control-port 19110`. Open `http://127.0.0.1:18080/` in headless Chromium. Capture console messages, page errors, `GET /api/state`, and baseline DOM. Confirm available buttons and node cards before any scenario testing.
  **Must NOT do**: Do not edit source files. Do not use `--no-supervisor` for scenario runs. Do not continue if Web UI does not start or `/api/state` fails.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Requires browser automation, process lifecycle, and evidence capture.
  - Skills: [`webapp-testing`] - Playwright browser QA procedure.
  - Omitted: [`api-and-interface-design`] - No API design changes.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: Tasks 2-8 | Blocked By: none

  **References** (executor has NO interview context - be exhaustive):
  - Runtime: `web_ui/server.py:197-218` - CLI args and supervisor default.
  - API: `web_ui/server.py:130-157` - `/api/state` and `/api/control`.
  - Commands: `web_ui/static/index.html:55-86` - static command buttons.
  - Command wiring: `web_ui/static/app.js:720-741` - `[data-command]` posts to `/api/control` and refreshes state.
  - Runtime docs: `README.md` section `Web UI runtime` - `python -m web_ui.server --web-port 8080` starts controller and all node roles.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Command starts server and page loads at `http://127.0.0.1:18080/`.
  - [ ] `#diagram-canvas`, `#node-layer`, `#data-path`, `#detail-inspector`, `#runtime-status` exist.
  - [ ] Seven node cards exist: `host-simulator`, `local-agent`, `r1`, `r2`, `monitor`, `r1b`, `r2b`.
  - [ ] Static buttons exist for `start`, `pause`, `reset`, `ackdrop`, `delay r1 1.5`, `delay r2 1.5`, `delay r1b 1.5`, `delay r2b 1.5`.
  - [ ] No uncaught browser page error occurs.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Baseline Web UI loads
    Tool: Playwright
    Steps: Start `python -m web_ui.server --web-port 18080 --control-port 19110`; navigate to `/`; wait for networkidle; query required selectors and node-card counts.
    Expected: Required selectors exist; seven node cards exist; all four delay buttons exist; `/api/state` returns JSON.
    Evidence: .sisyphus/evidence/web-ui-situations/task-1-harness/screenshot.png

  Scenario: Browser error capture
    Tool: Playwright
    Steps: Attach console/pageerror listeners before navigation; wait 5 seconds after first render; write console log and page errors.
    Expected: No pageerror; no unexpected console error.
    Evidence: .sisyphus/evidence/web-ui-situations/task-1-harness/console.log
  ```

  **Commit**: NO | Message: `n/a` | Files: evidence only

- [ ] 2. Verify Startup Smoke and Topology Display

  **What to do**: From clean runtime, click `[data-command="reset"]`, then `[data-command="start"]`. Verify topology elements and node cards remain visible and represent primary + backup topology without opening monitor detail yet.
  **Must NOT do**: Do not infer routing state from CSS alone. Do not accept a screenshot without DOM/text assertions.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Browser QA with live runtime state.
  - Skills: [`webapp-testing`] - DOM and screenshot validation.
  - Omitted: [`debugging-and-error-recovery`] - Use only if server fails unexpectedly.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: Task 8 | Blocked By: Task 1

  **References**:
  - Node order: `web_ui/static/app.js:5` - seven displayed nodes.
  - Backup positions/meta: `web_ui/static/app.js:12-22` - `r1b`, `r2b` display names.
  - Links: `web_ui/static/app.js:34-36` - backup links.
  - Web UI spec: `docs/reference/ui-preview/WEB_UI_SPEC.md:288` - delay controls include r1/r2/r1b/r2b.

  **Acceptance Criteria**:
  - [ ] `#runtime-status` changes to command-completion text after `reset` and `start`.
  - [ ] Node cards for `r1b` and `r2b` are visible with backup relay labels.
  - [ ] Primary and backup link labels are present in DOM or rendered path summary.
  - [ ] No invalid cross-path route text appears anywhere in `document.body.innerText`.

  **QA Scenarios**:
  ```
  Scenario: Startup topology visible
    Tool: Playwright
    Steps: Click reset; click start; wait for state refresh; collect body text and node-card metadata.
    Expected: Seven nodes visible; r1b/r2b visible; runtime-status says command completed; no cross-path text.
    Evidence: .sisyphus/evidence/web-ui-situations/task-2-startup-smoke/screenshot.png

  Scenario: Invalid cross-path absent at startup
    Tool: Playwright
    Steps: Search body text for `r1 -> r2b`, `r1b -> r2`, `local-agent -> r1 -> r2b`, `local-agent -> r1b -> r2`.
    Expected: All invalid strings absent.
    Evidence: .sisyphus/evidence/web-ui-situations/task-2-startup-smoke/assertions.json
  ```

  **Commit**: NO | Message: `n/a` | Files: evidence only

- [ ] 3. Verify Primary Normal Route in Monitor Detail

  **What to do**: Reset, start, wait until Monitor receives a normal event on primary route. Click `button.node-card[data-node-id="monitor"]`. Assert Monitor detail shows `Route Summary`, `Fault Localization`, and `Route Trace` sections, with active route primary and primary path nodes.
  **Must NOT do**: Do not require backup route absence if the app has not emitted an event yet; wait for deterministic Monitor text or `/api/state` detail data.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Browser QA with async runtime observation.
  - Skills: [`webapp-testing`] - Playwright waits and evidence.
  - Omitted: [`api-and-interface-design`] - No interface design.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: Task 8 | Blocked By: Task 1

  **References**:
  - Primary route behavior: `nw_demo/local_agent.py:295-309`.
  - Relay forwarding: `nw_demo/relay.py:277-294`.
  - Monitor receive behavior: `nw_demo/monitor.py:121-230`.
  - Monitor detail rendering: `web_ui/static/app.js:585-587`.
  - Route rows: `web_ui/static/app.js:555-627`.
  - Tests: `tests/test_bypass_routing_contracts.py:54-63`.

  **Acceptance Criteria**:
  - [ ] Monitor inspector opens with `data-detail-state="open"`.
  - [ ] Inspector text includes `Route Summary`, `Fault Localization`, `Route Trace`.
  - [ ] Inspector text includes `primary` or `PRIMARY` as active/route state.
  - [ ] Route trace/detail includes `local-agent`, `r1`, `r2`, `monitor`.
  - [ ] Inspector does not show invalid cross-path route text.

  **QA Scenarios**:
  ```
  Scenario: Primary happy path
    Tool: Playwright
    Steps: Reset; start; poll `/api/state` or DOM until monitor detail has route summary; click monitor card; collect inspector text.
    Expected: Primary route shown through local-agent/r1/r2/monitor; route sections visible; no cross-path text.
    Evidence: .sisyphus/evidence/web-ui-situations/task-3-primary-normal/screenshot.png

  Scenario: Primary route has no false failure claim
    Tool: Playwright
    Steps: Inspect Monitor detail during primary normal state.
    Expected: Fault localization is absent/unavailable or non-failure; it must not claim `r1` failed during healthy primary route.
    Evidence: .sisyphus/evidence/web-ui-situations/task-3-primary-normal/dom.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: evidence only

- [ ] 4. Verify Backup Failover Display After Primary-Hop Failure

  **What to do**: Reset runtime, start nodes, then induce a primary `local-agent -> r1` failure by pausing or killing `r1` through Web UI/generated command or `/api/control` (`pause r1` preferred; if backup state does not appear within 20 seconds, restart an isolated runtime and use `kill r1`). Wait for Agent to attempt backup. Open Monitor detail and verify backup route + fault localization.
  **Must NOT do**: Do not create artificial `/api/state` fixtures. Do not call backend internals directly. Do not accept a backup route unless same UI state also avoids cross-path text.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Multi-step runtime state induction and browser assertion.
  - Skills: [`webapp-testing`, `debugging-and-error-recovery`] - Browser QA and systematic handling if timing/failover is flaky.
  - Omitted: [`api-and-interface-design`] - No API changes.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: Task 8 | Blocked By: Task 1

  **References**:
  - Backup failover: `nw_demo/local_agent.py:311-393`.
  - Valid paths: `nw_demo/routing.py:23-44`.
  - Route mismatch guard: `nw_demo/relay.py:125-130`, `nw_demo/relay.py:200-215`.
  - Fault localization: `nw_demo/routing.py` function `fault_localization_from_event`.
  - Tests: `tests/test_local_agent_event_policy.py:55-97`, `tests/test_bypass_routing_contracts.py:176-194`.

  **Acceptance Criteria**:
  - [ ] Monitor detail shows `BYPASS_ACTIVE` or `backup` after primary hop failure.
  - [ ] Route trace/detail includes `local-agent`, `r1b`, `r2b`, `monitor`.
  - [ ] Fault localization indicates observed failed hop `local-agent -> r1` or equivalent failed-hop text.
  - [ ] Fault localization includes suspected node `r1` and confidence `medium` when available.
  - [ ] No invalid cross-path route text appears.

  **QA Scenarios**:
  ```
  Scenario: Primary failure triggers backup UI
    Tool: Playwright
    Steps: Reset; start; send `pause r1` via `/api/control` or generated node switch; wait up to 20 seconds for monitor route summary to include backup; if absent, restart isolated runtime and repeat with `kill r1`; click monitor card.
    Expected: Monitor inspector shows backup/BYPASS_ACTIVE and route through r1b/r2b/monitor.
    Evidence: .sisyphus/evidence/web-ui-situations/task-4-backup-failover/screenshot.png

  Scenario: Backup UI excludes cross-paths
    Tool: Playwright
    Steps: During backup state, search body and monitor inspector text for invalid cross-path strings.
    Expected: `r1 -> r2b`, `r1b -> r2`, `local-agent -> r1 -> r2b`, `local-agent -> r1b -> r2` absent.
    Evidence: .sisyphus/evidence/web-ui-situations/task-4-backup-failover/assertions.json
  ```

  **Commit**: NO | Message: `n/a` | Files: evidence only

- [ ] 5. Verify ACK Drop and Retry/Dedup Visibility

  **What to do**: Reset, start, click `[data-command="ackdrop"]`, then wait through the next Monitor ACK drop and relay retry window. Inspect relevant relay cards and Monitor detail. Verify the UI exposes dropped ACK/retry/dedup state without losing route validity.
  **Must NOT do**: Do not force ACK drop by editing code. Do not require exact retry count at a single instant unless captured from `/api/state`; use eventual and bounded waits.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Async retry timing and browser state capture.
  - Skills: [`webapp-testing`, `debugging-and-error-recovery`] - Browser QA and flaky timing recovery.
  - Omitted: [`api-and-interface-design`] - No design changes.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: Task 8 | Blocked By: Task 1

  **References**:
  - ACK drop: `nw_demo/monitor.py:114-212`.
  - Relay retry/pending: `nw_demo/relay.py:319-487`.
  - Config timing: `nw_demo/config.py:44-63` - ACK timeout/retry/delay caps.
  - Tests: `tests/test_status_detail_publishers.py:274-287`, `tests/test_node_monitor_mode.py:275-296`.

  **Acceptance Criteria**:
  - [ ] `#runtime-status` reports command completion for `ackdrop`.
  - [ ] At least one relay or Monitor detail/status exposes dropped ACK, pending ACK, retry, timeout, or dedup-related state.
  - [ ] Eventually route returns to a valid primary or backup state, or failure is displayed with explicit route/fault detail.
  - [ ] No cross-path route text appears.

  **QA Scenarios**:
  ```
  Scenario: ACK drop is visible
    Tool: Playwright
    Steps: Reset; start; click ackdrop; poll body text and `/api/state` for ack_dropped/dropped/retry/pending evidence; capture monitor and active relay detail.
    Expected: UI shows ACK drop or retry-related state in text/detail; no console errors.
    Evidence: .sisyphus/evidence/web-ui-situations/task-5-ackdrop-retry/screenshot.png

  Scenario: ACK drop does not create invalid route
    Tool: Playwright
    Steps: During and after retry window, search body and detail text for invalid cross-path strings.
    Expected: Invalid cross-path strings absent.
    Evidence: .sisyphus/evidence/web-ui-situations/task-5-ackdrop-retry/assertions.json
  ```

  **Commit**: NO | Message: `n/a` | Files: evidence only

- [ ] 6. Verify Relay Delay Controls for Primary and Backup Relays

  **What to do**: Confirm delay command buttons exist for `r1`, `r2`, `r1b`, `r2b`; click each in separate reset-start runs or sequentially with reset between groups. Verify command completion and that the UI remains responsive and route display stays valid.
  **Must NOT do**: Do not assert exact visual animation duration. Do not require delay beyond configured cap.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Browser command verification over multiple controls.
  - Skills: [`webapp-testing`] - Button interaction and DOM assertion.
  - Omitted: [`debugging-and-error-recovery`] - Only needed if commands fail.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: Task 8 | Blocked By: Task 1

  **References**:
  - Delay buttons: `web_ui/static/index.html:81-85`.
  - Command POST: `web_ui/static/app.js:720-731`.
  - Relay delay cap: `nw_demo/relay.py:92-108`.
  - Spec: `IMPLEMENTATION_SPEC.md:232-235` - `delay r1|r2|r1b|r2b <sec>`.

  **Acceptance Criteria**:
  - [ ] Four delay buttons exist and are clickable.
  - [ ] Clicking each produces `명령 완료: delay <node> 1.5` or equivalent successful runtime-status.
  - [ ] No console error occurs after each command.
  - [ ] Route display remains primary or backup, never cross-path.

  **QA Scenarios**:
  ```
  Scenario: Delay buttons execute
    Tool: Playwright
    Steps: For each command `delay r1 1.5`, `delay r2 1.5`, `delay r1b 1.5`, `delay r2b 1.5`, click the corresponding `[data-command]`; wait for runtime-status.
    Expected: Each command completes; page stays responsive; no pageerror.
    Evidence: .sisyphus/evidence/web-ui-situations/task-6-relay-delay-controls/screenshot.png

  Scenario: Delay commands preserve route validity
    Tool: Playwright
    Steps: After delay commands, inspect body and monitor detail if available.
    Expected: No invalid cross-path route; route sections still render when monitor selected.
    Evidence: .sisyphus/evidence/web-ui-situations/task-6-relay-delay-controls/assertions.json
  ```

  **Commit**: NO | Message: `n/a` | Files: evidence only

- [ ] 7. Verify Pause, Kill, Reset Lifecycle Visibility

  **What to do**: Use Web UI controls and `/api/control` for lifecycle commands. Verify pause changes node/system state, kill is reflected as unavailable/non-running, and reset clears stale backup/fault/delay indicators.
  **Must NOT do**: Do not leave runtime killed for later scenarios; run this in its own server instance or as the last Wave 2 scenario.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Runtime lifecycle state and cleanup are fragile.
  - Skills: [`webapp-testing`, `debugging-and-error-recovery`] - Browser QA and recovery if killed process affects scenario.
  - Omitted: [`api-and-interface-design`] - No interface changes.

  **Parallelization**: Can Parallel: YES, preferably last or isolated | Wave 2 | Blocks: Task 8 | Blocked By: Task 1

  **References**:
  - Base lifecycle: `nw_demo/base.py:104-124`.
  - Controller commands: `nw_demo/controller_client.py:51-100`.
  - Controller local commands: `nw_demo/controller_ui.py:1176-1193`, `nw_demo/controller_ui.py:1291-1316`.
  - Tests: `tests/test_controller_client_commands.py:10-75`, `tests/test_controller_ui_local_commands.py:12-188`.

  **Acceptance Criteria**:
  - [ ] `pause` command completes and UI reflects paused/non-running state in summary, card, or detail.
  - [ ] `reset` command completes and clears stale backup/fault text from Monitor detail after refresh.
  - [ ] If `kill monitor` is used, Monitor card/status reflects stopped/unavailable and server remains responsive.
  - [ ] No stale backup route remains after reset unless a new runtime event legitimately recreates it.

  **QA Scenarios**:
  ```
  Scenario: Pause and reset are visible
    Tool: Playwright
    Steps: Reset; start; click pause; capture card/detail state; click reset; wait for refresh; capture body text.
    Expected: Pause visible as changed running/reported state; reset clears stale failure/backup indicators.
    Evidence: .sisyphus/evidence/web-ui-situations/task-7-lifecycle-reset/screenshot.png

  Scenario: Kill is reflected without crashing Web UI
    Tool: Playwright
    Steps: In isolated runtime, POST `/api/control` with `kill monitor`; wait for `/api/state`; inspect monitor card.
    Expected: Web UI remains reachable; monitor state reflects stopped/unavailable; no browser pageerror.
    Evidence: .sisyphus/evidence/web-ui-situations/task-7-lifecycle-reset/kill-monitor.png
  ```

  **Commit**: NO | Message: `n/a` | Files: evidence only

- [ ] 8. Verify Focus/Overview and Final Scenario Synthesis

  **What to do**: Click node cards for `host-simulator`, `local-agent`, `r1`, `r2`, `r1b`, `r2b`, `monitor`, then close inspector. Verify focus changes inspector context only and does not mutate route state. Synthesize all evidence into final summary.
  **Must NOT do**: Do not send `focus` as a node CONTROL expectation. It is UI-local/controller-local observation behavior.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Cross-scenario evidence synthesis and UI state verification.
  - Skills: [`webapp-testing`] - Browser interaction and evidence capture.
  - Omitted: [`api-and-interface-design`] - No API design.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: Final Verification Wave | Blocked By: Tasks 2-7

  **References**:
  - Inspector state: `web_ui/static/app.js` detail rendering around role-specific renderers and `#detail-inspector`.
  - Click command handling: `web_ui/static/app.js:734-738`.
  - Focus behavior: `nw_demo/controller_ui.py:402-448`; `tests/test_controller_ui_local_commands.py:12-109`.
  - Web UI guardrail: `docs/reference/ui-preview/WEB_UI_SPEC.md:342` - UI must not invent routing truth.

  **Acceptance Criteria**:
  - [ ] Clicking each node opens inspector with that node's role-specific detail or unavailable state.
  - [ ] Closing inspector sets `#detail-inspector[data-detail-state]` to `closed` or equivalent closed state.
  - [ ] Node selection/focus does not change `route_state`, `active_route`, or route trace in `/api/state`.
  - [ ] `final-summary.md` lists PASS/BLOCK for Tasks 2-7, evidence paths, console error status, and any suspected defects.

  **QA Scenarios**:
  ```
  Scenario: Node inspector focus is UI-local
    Tool: Playwright
    Steps: Capture `/api/state` route fields; click each node card; capture inspector heading/text; re-read `/api/state` route fields.
    Expected: Inspector target changes; route fields do not change solely due to selection.
    Evidence: .sisyphus/evidence/web-ui-situations/task-8-focus-overview/screenshot.png

  Scenario: Final synthesis is complete
    Tool: Bash / Playwright evidence review
    Steps: Verify every scenario directory contains screenshot, DOM/text snapshot, console log, assertions JSON; write final summary.
    Expected: final-summary.md has one PASS/BLOCK row per scenario and exact file references for failures.
    Evidence: .sisyphus/evidence/web-ui-situations/final-summary.md
  ```

  **Commit**: NO | Message: `n/a` | Files: evidence only

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Evidence Completeness Review — unspecified-high
- [ ] F3. Real Manual QA Simulation Review — unspecified-high (+ webapp-testing)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- No commit.
- No GitHub operations.
- Evidence files may be generated under `.sisyphus/evidence/web-ui-situations/` during execution.
- If QA discovers a product defect, stop and report exact failing scenario; do not patch source code inside this verification plan.

## Success Criteria
- All eight tasks complete with evidence.
- Every scenario uses DOM/text assertions plus screenshots.
- No unexpected browser console/page errors.
- Primary route, backup route, ACK drop/retry, relay delay controls, lifecycle, and focus/overview behavior are verified against actual Web UI.
- Cross-path route strings are absent in every scenario.
- Final review agents approve, then user explicitly approves completion.
