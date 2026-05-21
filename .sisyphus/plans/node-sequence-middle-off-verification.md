# Web UI Node Sequence + Middle-Off Verification Plan

## TL;DR
> **Summary**: Add a verification-only browser QA pass for sequential node process bring-up, middle relay pause/kill behavior, SVG link state, and Monitor/inspector information flow. This fills the gap left by the prior Web UI situation PASS matrix.
> **Deliverables**:
> - Playwright/headless Chromium verification driver for the new scenario matrix
> - Evidence under `.sisyphus/evidence/web-ui-situations/task-9-*` through `task-16-*`
> - Additional summary `.sisyphus/evidence/web-ui-situations/node-sequence-middle-off-summary.md` without overwriting prior `final-summary.md`
> - No app/source/selector/routing changes
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 → Tasks 2-7 → Task 8 → Final Verification Wave

## Context
### Original Request
사용자는 기존 검증이 “노드를 순차적으로 키거나 중간 노드를 끄거나 했을 때 기대 결과”를 확인하지 않은 것 같다고 지적했고, 상황별 노드 간 줄 표시와 Monitor에 표시되는 결과/정보 전달 흐름까지 고려한 검증 계획을 요청했다.

### Interview Summary
- 기존 Web UI browser QA는 `.sisyphus/evidence/web-ui-situations/final-summary.md` 기준 PASS였다.
- 기존 범위는 startup smoke, primary route, `pause r1` backup failover, ACK drop/retry, delay controls, lifecycle reset/focus overview 중심이었다.
- 빠진 범위는 full sequential node startup, `r2/r1b/r2b` middle relay off matrix, SVG link DOM state, Monitor/inspector consistency다.

### Metis Review (gaps addressed)
- `pause`, `kill`, `reset/not_started` 의미를 섞지 말고 scenario마다 분리한다.
- screenshot-only PASS를 금지하고 `/api/state`, DOM text, inspector text, SVG `data-*`, console/pageerror absence를 모두 요구한다.
- allowed route links와 forbidden cross-path absence를 함께 assert한다.
- 비동기 timing은 polling timeout으로 처리하되, 실패를 숨기는 retry로 만들지 않는다.
- 검증 중 source code, server API, selector, routing behavior를 수정하지 않는다.

## Work Objectives
### Core Objective
현재 Web UI가 노드 순차 기동과 중간 노드 off 상황에서 topology line, node state, route/fault summary, `route_trace`, inspector detail을 실제 런타임 상태와 일관되게 표시하는지 검증한다.

### Deliverables
- New evidence folders:
  - `.sisyphus/evidence/web-ui-situations/task-9-harness-node-sequence/`
  - `.sisyphus/evidence/web-ui-situations/task-10-sequential-process-startup/`
  - `.sisyphus/evidence/web-ui-situations/task-11-logical-start-pause-reset/`
  - `.sisyphus/evidence/web-ui-situations/task-12-primary-r2-middle-off/`
  - `.sisyphus/evidence/web-ui-situations/task-13-primary-r1-off-backup-flow/`
  - `.sisyphus/evidence/web-ui-situations/task-14-backup-middle-off/`
  - `.sisyphus/evidence/web-ui-situations/task-15-monitor-flow-consistency/`
  - `.sisyphus/evidence/web-ui-situations/task-16-reset-recovery-cleanup/`
- Each folder contains: `screenshot.png`, `dom.txt`, `state.json`, `console.log`, `assertions.json`; inspector scenarios also include `inspector-*.txt`.
- New rollup file: `.sisyphus/evidence/web-ui-situations/node-sequence-middle-off-summary.md`.

### Definition of Done (verifiable conditions with commands)
- `python -m unittest discover -s tests` passes.
- `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py` passes.
- `node --check web_ui/static/app.js` passes.
- Playwright/headless Chromium run produces PASS in `node-sequence-middle-off-summary.md`.
- `assertions.json` in every new task folder has top-level `passed: true`.
- Final port/process cleanup reports no leftover test runtime on the selected web/control/node ports.

### Must Have
- Browser-driven commands via `POST /api/control` and state reads via `GET /api/state`.
- SVG link assertions against `#data-path g[data-link-id][data-hop-state][data-hop-tone]`.
- Link IDs asserted: `host-agent`, `agent-r1`, `r1-r2`, `r2-monitor`, `agent-r1b`, `r1b-r2b`, `r2b-monitor`.
- Forbidden cross-path strings and links absent: `r1 -> r2b`, `r1b -> r2`, `local-agent -> r1 -> r2b`, `local-agent -> r1b -> r2`.
- Actual node IDs only: `host-simulator`, `local-agent`, `r1`, `r2`, `monitor`, `r1b`, `r2b`.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Do not edit `web_ui/`, `nw_demo/`, `tests/`, docs, or selectors.
- Do not overwrite `.sisyphus/evidence/web-ui-situations/final-summary.md` from the prior QA run.
- Do not treat screenshots as pass/fail evidence by themselves.
- Do not add cross-path routing, mesh behavior, load balancing, or new fallback logic.
- Do not claim hard “node failure” in Monitor assertions unless current data explicitly supports it.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + browser QA; use existing stdlib `unittest` and Playwright/headless Chromium.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/web-ui-situations/task-{N}-{slug}/`.
- Runtime isolation:
  - For sequential process startup, run `python -m web_ui.server --web-port 18080 --control-port 19110 --control-token sequence-test --no-supervisor` and launch individual role subprocesses with `NW_CONTROL_TOKEN=sequence-test`.
  - For logical pause/kill matrix, run normal supervised Web UI: `python -m web_ui.server --web-port 18080 --control-port 19110 --control-token sequence-test`.
  - Stop every runtime with `/api/control` line `exit` where possible; then terminate any child subprocesses the QA harness created.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 harness + Task 2 sequential process startup.
Wave 2: Tasks 3-7 situation matrix can run independently if each starts an isolated runtime.
Wave 3: Task 8 reset/recovery cleanup after the matrix.

### Dependency Matrix (full, all tasks)
- Task 1 blocks Tasks 2-8.
- Task 2 is independent after Task 1.
- Tasks 3-7 are independent after Task 1 if they use separate runtime lifecycle.
- Task 8 depends on Tasks 2-7 evidence existing.
- F1-F4 depend on Tasks 1-8 completion.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 2 tasks → `unspecified-high` with `webapp-testing`.
- Wave 2 → 5 tasks → `unspecified-high` with `webapp-testing`.
- Wave 3 → 1 task → `quick` with no extra skill unless browser cleanup is needed.

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Build verification harness and assertion helpers

  **What to do**: Create a temporary Playwright QA driver under `/tmp/opencode/` only. It must start/stop Web UI runtimes, optionally launch individual role subprocesses, call `/api/control`, read `/api/state`, capture browser DOM/screenshot/console/pageerror, and write per-task evidence. Implement reusable assertions for node card state, SVG link state, Monitor inspector text, forbidden route absence, and final summary generation.
  **Must NOT do**: Do not edit project source files. Do not store temporary driver inside repo except evidence outputs.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: browser automation plus runtime lifecycle needs careful cleanup.
  - Skills: `webapp-testing` - Use Playwright/headless Chromium and DOM assertions.
  - Omitted: `api-and-interface-design` - No public API design changes.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2,3,4,5,6,7,8 | Blocked By: none

  **References**:
  - Pattern: `.sisyphus/evidence/web-ui-situations/final-summary.md` - prior rollup convention.
  - Pattern: `.sisyphus/evidence/node_first_preview.spec.py` - Playwright Python pattern with console/pageerror capture.
  - API: `web_ui/server.py:130-157` - `/api/state` and `/api/control` endpoints.
  - UI selector: `web_ui/static/index.html:49-59` - detail inspector and runtime status selectors.
  - UI selector: `web_ui/static/app.js:29-37` - exact link IDs.
  - UI selector: `web_ui/static/app.js:347-396` - link groups expose `data-link-id`, `data-hop-state`, `data-hop-tone`.

  **Acceptance Criteria**:
  - [ ] Temporary driver can launch headless Chromium and load `http://127.0.0.1:18080/`.
  - [ ] Driver writes `screenshot.png`, `dom.txt`, `state.json`, `console.log`, `assertions.json` for a smoke scenario.
  - [ ] Driver records console errors and page errors as failed assertions.
  - [ ] Driver can query `#data-path g[data-link-id='agent-r1']` and read `dataset.hopState` / `dataset.hopTone`.
  - [ ] Driver does not modify repo source files.

  **QA Scenarios**:
  ```
  Scenario: Harness smoke
    Tool: Playwright + Bash
    Steps: Start supervised Web UI on 18080/19110; navigate to `/`; wait for `#diagram-canvas`; fetch `/api/state`; assert seven `button.node-card[data-node-id]`; assert seven SVG link groups under `#data-path`; capture evidence.
    Expected: All selectors exist, `/api/state.nodes` is a list, no console/pageerror, assertions pass.
    Evidence: .sisyphus/evidence/web-ui-situations/task-9-harness-node-sequence/

  Scenario: Harness failure capture
    Tool: Playwright
    Steps: In the harness only, intentionally assert a non-existent selector against a throwaway temp evidence folder under `/tmp/opencode`; verify assertion JSON records failed check without crashing cleanup.
    Expected: Failure is captured as structured JSON and browser/server cleanup still runs.
    Evidence: /tmp/opencode/node-sequence-harness-negative/
  ```

  **Commit**: NO | Message: N/A | Files: [temporary `/tmp/opencode` driver and `.sisyphus/evidence/...`]

- [ ] 2. Verify sequential process startup with `--no-supervisor`

  **What to do**: Start Web UI with `--no-supervisor`, then launch role subprocesses one by one with shared `NW_CONTROL_TOKEN=sequence-test`. Use order: `monitor`, `relay-r2`, `relay-r1`, `relay-r2b`, `relay-r1b`, `agent`, `host`. After each launch, poll `/api/state` and assert node card liveness, link state, and absence of false complete route.
  **Must NOT do**: Do not rely on `start <node>` for process spawn; that command only changes logical running state inside an already-running node.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: multi-process runtime sequencing and browser assertions.
  - Skills: `webapp-testing` - Browser DOM/SVG assertions.
  - Omitted: `debugging-and-error-recovery` - Use only if runtime fails unexpectedly.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 8 | Blocked By: 1

  **References**:
  - Runtime: `README.md:93-116` - role-specific process execution.
  - Runtime: `web_ui/server.py:197-219` - `--no-supervisor` flag and token handling.
  - Startup order baseline: `nw_demo/system.py:17-59` - supervised order for comparison.
  - State: `nw_demo/controller_ui.py:126-155` - normalized node fields.
  - Link states: `web_ui/static/app.js:38-56` - hop state to tone mapping.

  **Acceptance Criteria**:
  - [ ] Before any role starts, all seven cards exist with `reported_state` `UNKNOWN` or no node status, and `observed_liveness` is `unknown` in `/api/state`.
  - [ ] After each role subprocess starts, that node eventually reports `observed_liveness == live` and `reported_state` `실행 중` or `RUNNING`.
  - [ ] Links whose endpoints or peer status are incomplete remain `data-hop-tone='muted'` and `data-hop-state` in `unknown|not_started|not_applicable`.
  - [ ] Full primary success is not asserted until `host`, `agent`, `r1`, `r2`, and `monitor` are all live and a host event has traversed.
  - [ ] Full backup success is not asserted until `agent`, `r1b`, `r2b`, and `monitor` are live and backup is activated by primary failure.
  - [ ] Forbidden cross-path strings are absent from body text and all inspector text.

  **QA Scenarios**:
  ```
  Scenario: One-by-one process bring-up
    Tool: Playwright + Bash
    Steps: Start Web UI `--no-supervisor`; launch roles in order `monitor`, `relay-r2`, `relay-r1`, `relay-r2b`, `relay-r1b`, `agent`, `host`; after each launch poll `/api/state`, DOM node cards, and `#data-path g[data-link-id]`.
    Expected: Newly launched node becomes live; not-yet-launched nodes remain unknown/not started; no active complete route is displayed before prerequisites are live.
    Evidence: .sisyphus/evidence/web-ui-situations/task-10-sequential-process-startup/

  Scenario: Missing downstream during startup
    Tool: Playwright + Bash
    Steps: Stop after launching only `monitor`, `relay-r2`, `relay-r1`; do not launch `agent` or `host`; inspect `agent-r1`, `r1-r2`, `r2-monitor` link groups and node cards.
    Expected: `r1`/`r2`/`monitor` are live; `host-simulator` and `local-agent` remain unknown; no primary route summary claims successful host-to-monitor delivery.
    Evidence: .sisyphus/evidence/web-ui-situations/task-10-sequential-process-startup/missing-downstream-extra.json
  ```

  **Commit**: NO | Message: N/A | Files: [evidence only]

- [ ] 3. Verify logical `start/pause/reset` node controls separately from process lifecycle

  **What to do**: With supervised runtime, use `/api/control` commands `pause <node>`, `start <node>`, and `reset <node>` for each actual node. Assert that `pause` changes `reported_state` to paused/일시정지 while process liveness remains visible, `start` restores running, and `reset` clears stale route/fault displays without killing the process.
  **Must NOT do**: Do not treat `pause` as equivalent to process death.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: matrix assertions over seven nodes.
  - Skills: `webapp-testing` - Browser-driven control and DOM assertions.
  - Omitted: `api-and-interface-design` - No contract changes.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1

  **References**:
  - Commands: `nw_demo/controller_client.py:51-91` - start/pause/reset/kill parsing.
  - Node behavior: `nw_demo/base.py:104-118` - start/pause/reset/shutdown handling.
  - Node card rendering: `web_ui/static/app.js:399-460` - card state and liveness display.

  **Acceptance Criteria**:
  - [ ] `pause r1` returns `{ok: true}` and card/API show paused/일시정지 without `observed_liveness` becoming `unknown` immediately.
  - [ ] `start r1` returns `{ok: true}` and card/API show running/실행 중.
  - [ ] `reset r1` returns `{ok: true}` and clears relay pending/retry details for that node.
  - [ ] Repeat for `host`, `agent`, `r2`, `monitor`, `r1b`, `r2b` using aliases only where supported (`host`, `agent`) and exact IDs elsewhere.
  - [ ] No console/pageerror occurs.

  **QA Scenarios**:
  ```
  Scenario: Pause/start/reset one relay
    Tool: Playwright
    Steps: Start supervised runtime; POST `pause r1`; poll r1 card and `/api/state`; POST `start r1`; poll again; POST `reset r1`; inspect r1 detail.
    Expected: pause/start/reset are accepted; state transitions are visible; reset does not kill the process.
    Evidence: .sisyphus/evidence/web-ui-situations/task-11-logical-start-pause-reset/

  Scenario: Alias and invalid-target guard
    Tool: Playwright
    Steps: POST `pause host`, `start host`, `pause agent`, `start agent`, then POST invalid `pause r3`.
    Expected: host/agent aliases are accepted; invalid target returns non-ok/400 and does not mutate route state.
    Evidence: .sisyphus/evidence/web-ui-situations/task-11-logical-start-pause-reset/alias-invalid.json
  ```

  **Commit**: NO | Message: N/A | Files: [evidence only]

- [ ] 4. Verify primary downstream middle-off: `pause/kill r2`

  **What to do**: In a healthy supervised runtime, first observe primary route. Then test `pause r2` and `kill r2` in separate fresh runs. Assert `r1-r2` and/or `r2-monitor` link state changes to paused/timeout/connection_error/delivery_failed as appropriate, primary complete route is not falsely displayed, and backup may activate only through `local-agent -> r1b -> r2b -> monitor`.
  **Must NOT do**: Do not require Monitor fault localization to claim `r2` if the event never reaches Monitor with enough trace; instead assert that r1/agent inspector exposes the downstream failure and Monitor does not claim false success for the failed primary event.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: nuanced expected behavior across Agent, R1, R2, Monitor.
  - Skills: `webapp-testing` - SVG and inspector assertions.
  - Omitted: `api-and-interface-design` - Verification only.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1

  **References**:
  - Relay paused response: `nw_demo/relay.py:157-182` - paused relay returns ERROR and records `hop_state='paused'`.
  - Relay downstream retry/failure: `nw_demo/relay.py:319-487` - timeout/connection_error/delivery_failed recording.
  - Agent failover boundary: `nw_demo/local_agent.py:295-393` - primary failure can switch to backup.
  - Fault localization: `nw_demo/routing.py:125-163` - trace-based medium confidence only when failed hop exists.

  **Acceptance Criteria**:
  - [ ] Baseline primary route shows active route `primary` and valid trace edges `local-agent->r1`, `r1->r2`, `r2->monitor`.
  - [ ] After `pause r2`, r2 card shows paused/일시정지; `#data-path g[data-link-id='r1-r2']` or r1 inspector shows `paused|timeout|delivery_failed|invalid_response`; no false `r1 -> r2b` path appears.
  - [ ] If backup succeeds after `pause r2`, active route is `backup` and trace uses only `local-agent->r1b`, `r1b->r2b`, `r2b->monitor` for successful delivery.
  - [ ] After `kill r2`, r2 eventually shows `kill_requested|stale|offline` or equivalent unavailable state; `r1-r2` is down/muted with `connection_error|timeout|delivery_failed` evidence.
  - [ ] Monitor detail does not claim a successful primary delivery for a failed primary event.

  **QA Scenarios**:
  ```
  Scenario: Pause primary downstream relay r2
    Tool: Playwright
    Steps: Start supervised runtime; wait for primary route; POST `pause r2`; wait for next event/retry window; inspect `#data-path` link groups, r1 detail, r2 card, monitor detail.
    Expected: r2 visibly paused; primary downstream segment is not shown as acknowledged for the new event; any successful route is constrained backup only; forbidden cross-path absent.
    Evidence: .sisyphus/evidence/web-ui-situations/task-12-primary-r2-middle-off/

  Scenario: Kill primary downstream relay r2
    Tool: Playwright
    Steps: Fresh runtime; wait for primary route; POST `kill r2`; poll until r2 liveness unavailable; wait for route attempt; inspect links and Monitor/Agent/R1 details.
    Expected: r2 unavailable; r1 downstream failure is visible; no false active complete primary route through r2.
    Evidence: .sisyphus/evidence/web-ui-situations/task-12-primary-r2-middle-off/kill-r2/
  ```

  **Commit**: NO | Message: N/A | Files: [evidence only]

- [ ] 5. Verify primary entry off triggers constrained backup: `pause/kill r1`

  **What to do**: Re-run the known `pause r1` failover case with stricter link/Monitor assertions, then run `kill r1`. Assert primary entry failure does not create cross-path and backup route uses only `agent-r1b`, `r1b-r2b`, `r2b-monitor`.
  **Must NOT do**: Do not skip this because previous QA passed; this task adds SVG/link and Monitor consistency checks missing from the earlier run.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: confirms prior behavior with new line/flow criteria.
  - Skills: `webapp-testing` - Browser and SVG assertions.
  - Omitted: `debugging-and-error-recovery` - Use only if unexpected failure occurs.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1

  **References**:
  - Allowed paths: `nw_demo/routing.py:23-33` - primary/backup paths and allowed edges.
  - Agent backup behavior: `nw_demo/local_agent.py:337-368` - BYPASS_ACTIVE backup send.
  - Web links: `web_ui/static/app.js:29-37` - exact allowed link IDs.

  **Acceptance Criteria**:
  - [ ] After `pause r1`, Monitor detail shows `BYPASS_ACTIVE` or active route `backup` for a delivered event.
  - [ ] `#data-path g[data-link-id='agent-r1']` is not `ok` for the failed primary attempt; backup link groups are active/ok according to observed hop state.
  - [ ] Trace contains backup edges only after reroute: `local-agent->r1b`, `r1b->r2b`, `r2b->monitor`.
  - [ ] Fault localization wording is trace/basis-based and does not hard-assert unsupported permanent node failure.
  - [ ] Same constraints hold for `kill r1`, with r1 liveness eventually unavailable.

  **QA Scenarios**:
  ```
  Scenario: Pause r1 constrained backup
    Tool: Playwright
    Steps: Start supervised runtime; wait for primary; POST `pause r1`; poll for backup route; inspect SVG links and Monitor detail.
    Expected: backup route active; only allowed backup links show successful delivery; cross-path absent; fault localization basis shown.
    Evidence: .sisyphus/evidence/web-ui-situations/task-13-primary-r1-off-backup-flow/

  Scenario: Kill r1 constrained backup
    Tool: Playwright
    Steps: Fresh runtime; wait for primary; POST `kill r1`; poll r1 liveness and backup route; inspect Agent and Monitor details.
    Expected: r1 unavailable; backup route succeeds if backup relays live; no `r1 -> r2b` route or text.
    Evidence: .sisyphus/evidence/web-ui-situations/task-13-primary-r1-off-backup-flow/kill-r1/
  ```

  **Commit**: NO | Message: N/A | Files: [evidence only]

- [ ] 6. Verify backup middle-off when backup is needed: `r1b/r2b` pause/kill

  **What to do**: Force primary failure (`pause r1`) and then test backup relay off states in separate fresh runs: `pause r1b`, `kill r1b`, `pause r2b`, `kill r2b`. Assert backup route does not falsely succeed when its middle relay is off and Monitor/Agent/relay details preserve the correct information boundary.
  **Must NOT do**: Do not expect backup off to affect primary healthy traffic; always force primary failure first before asserting backup path behavior.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: multi-fault matrix and expected non-delivery behavior.
  - Skills: `webapp-testing` - Browser assertions.
  - Omitted: `api-and-interface-design` - No new behavior design.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1

  **References**:
  - Backup path contract: `nw_demo/routing.py:24-33` - backup path and allowed backup edges.
  - Relay paused behavior: `nw_demo/relay.py:168-182` - paused relay response.
  - Agent backup failure handling: `nw_demo/local_agent.py:370-393` - active_route backup failed state.
  - Monitor storage: `nw_demo/monitor.py:60-80` - last route summary/trace/fault detail publisher.
  - Monitor observation: `nw_demo/monitor.py:102-107` - records route trace, route summary, and fault localization only for events reaching Monitor.

  **Acceptance Criteria**:
  - [ ] With primary failed and `r1b` paused/killed, `agent-r1b` link or Agent inspector shows `paused|connection_error|timeout|invalid_response|delivery_failed`; no successful backup Monitor delivery is claimed for that event.
  - [ ] With primary failed and `r2b` paused/killed, `r1b-r2b` or `r2b-monitor` segment shows failed/unavailable evidence; backup route is not falsely shown as fully acknowledged.
  - [ ] Monitor may retain last successful event if failed backup event never reaches it; this is PASS only if Agent/R1B inspector clearly records the failed current event and Monitor does not show contradictory success for that event ID.
  - [ ] Forbidden cross-path text and links remain absent.

  **QA Scenarios**:
  ```
  Scenario: Backup entry relay unavailable
    Tool: Playwright
    Steps: Fresh runtime; POST `pause r1`; POST `pause r1b`; wait for route attempt; inspect Agent, r1b card, SVG links, Monitor detail.
    Expected: primary and backup entry are not falsely successful; Agent detail records backup failure boundary; Monitor does not contradict current failed event.
    Evidence: .sisyphus/evidence/web-ui-situations/task-14-backup-middle-off/r1b-pause/

  Scenario: Backup downstream relay unavailable
    Tool: Playwright
    Steps: Fresh runtime; POST `pause r1`; POST `kill r2b`; wait for route attempt; inspect r1b, r2b, Monitor, and SVG links.
    Expected: backup downstream segment failure visible; no complete acknowledged backup route through killed r2b; no cross-path fallback.
    Evidence: .sisyphus/evidence/web-ui-situations/task-14-backup-middle-off/r2b-kill/
  ```

  **Commit**: NO | Message: N/A | Files: [evidence only]

- [ ] 7. Verify Monitor flow consistency across route, fault, and trace fields

  **What to do**: For primary success, primary-to-backup success, primary failed + backup failed, and reset/no-current-route states, compare `/api/state` Monitor detail with `#detail-inspector-inner` text after clicking Monitor. Assert route summary, fault localization, route trace, and event IDs do not contradict node/line state.
  **Must NOT do**: Do not require Monitor to know about an event that never reached it; verify this as an information boundary instead of a failure.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: consistency assertions across API JSON and DOM presentation.
  - Skills: `webapp-testing` - Inspector DOM assertions.
  - Omitted: `api-and-interface-design` - Existing contract only.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1

  **References**:
  - Route summary/fault logic: `nw_demo/routing.py:112-163`.
  - Monitor route fields: `nw_demo/monitor.py:60-80` - `last_route_summary`, `last_route_trace`, `last_fault_localization` publisher.
  - Monitor route observation: `nw_demo/monitor.py:102-107` - event route observation boundary.
  - Monitor renderer: `web_ui/static/app.js:570-591` - route/fault/trace detail sections.

  **Acceptance Criteria**:
  - [ ] Monitor inspector includes sections `Route Summary`, `Fault Localization`, and `Route Trace` when route data exists.
  - [ ] For primary success, `active_route == primary`, no failed hop with medium confidence, and trace uses only primary edges.
  - [ ] For backup success after primary entry failure, `active_route == backup` or `BYPASS_ACTIVE`, failed hop basis is trace/routing-derived, and trace uses allowed primary failure + backup success edges only.
  - [ ] For backup failed before reaching Monitor, Agent/relay inspector records current failure and Monitor does not display a contradictory successful route for the same event ID.
  - [ ] After `reset`, stale `BYPASS_ACTIVE` or failed route wording disappears from Monitor inspector until a new event establishes route data.

  **QA Scenarios**:
  ```
  Scenario: Monitor route consistency matrix
    Tool: Playwright
    Steps: In fresh runtimes, capture Monitor inspector and `/api/state` for primary success, `pause r1` backup success, and `pause r1` + `pause r1b` backup failed.
    Expected: API JSON and inspector text agree on active route/event IDs where Monitor has data; when Monitor lacks a failed event, Agent/relay evidence carries the boundary and Monitor does not falsely claim success for that event.
    Evidence: .sisyphus/evidence/web-ui-situations/task-15-monitor-flow-consistency/

  Scenario: Reset clears route display
    Tool: Playwright
    Steps: Produce backup route; POST `reset`; click Monitor; read inspector and `/api/state`.
    Expected: `BYPASS_ACTIVE` and old fault details are cleared or no longer presented as current route state.
    Evidence: .sisyphus/evidence/web-ui-situations/task-15-monitor-flow-consistency/reset-clear/
  ```

  **Commit**: NO | Message: N/A | Files: [evidence only]

- [ ] 8. Write rollup, run final commands, and cleanup runtimes

  **What to do**: Aggregate Tasks 9-15 evidence into `node-sequence-middle-off-summary.md`, run final validation commands, and verify no leftover runtime/process/port contamination. If any scenario blocks, preserve evidence and mark BLOCK with exact failed assertion.
  **Must NOT do**: Do not rewrite prior `final-summary.md`. Do not hide blocked scenarios by loosening assertions.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: aggregation and final command checks.
  - Skills: [] - No special skill unless browser cleanup requires webapp-testing.
  - Omitted: `webapp-testing` - Only needed if re-opening browser for cleanup verification.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: F1-F4 | Blocked By: 2,3,4,5,6,7

  **References**:
  - Prior summary: `.sisyphus/evidence/web-ui-situations/final-summary.md` - do not overwrite.
  - Validation command pattern: `AI_IMPLEMENTATION_BRIEF.md:136` - prior final checks.
  - Runtime ports: `README.md:118-128`, `README.md:140-151` - node/Web UI ports.

  **Acceptance Criteria**:
  - [ ] Summary lists PASS/BLOCK for every new task and links evidence directories.
  - [ ] `python -m unittest discover -s tests` passes.
  - [ ] `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py` passes.
  - [ ] `node --check web_ui/static/app.js` passes.
  - [ ] Cleanup confirms no leftover QA-owned Web UI/control/node processes.

  **QA Scenarios**:
  ```
  Scenario: Final validation pass
    Tool: Bash
    Steps: Run unittest, py_compile, node --check; inspect all new assertions.json; write rollup summary.
    Expected: Commands pass and every new task has `passed: true`, or summary marks BLOCK with exact assertion names.
    Evidence: .sisyphus/evidence/web-ui-situations/node-sequence-middle-off-summary.md

  Scenario: Runtime cleanup
    Tool: Bash + /api/control if reachable
    Steps: Send `exit` to any QA-owned Web UI runtime; terminate QA child role subprocesses; verify selected ports are clear or processes are not QA-owned.
    Expected: No stale QA runtime remains to contaminate future browser tests.
    Evidence: .sisyphus/evidence/web-ui-situations/task-16-reset-recovery-cleanup/
  ```

  **Commit**: NO | Message: N/A | Files: [evidence only]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- No git commit is required for verification-only evidence unless the user explicitly requests one.
- The temporary Playwright driver remains under `/tmp/opencode/` and is not committed.
- Evidence under `.sisyphus/evidence/` may be created by execution, but this plan does not require source changes.

## Success Criteria
- Sequential process startup behavior is verified with `--no-supervisor` and one-by-one role subprocess launches.
- Logical pause/start/reset behavior is verified separately from process liveness.
- `pause/kill r2`, `pause/kill r1`, `pause/kill r1b`, and `pause/kill r2b` are covered with fresh runtime isolation.
- SVG lines expose correct `data-link-id`, `data-hop-state`, and `data-hop-tone` for active, muted, paused, down, and backup-route states.
- Monitor and node inspector information flow is consistent with `/api/state`, and missing Monitor knowledge for undelivered events is treated as an explicit information boundary, not invented as a false Monitor result.
- No forbidden cross-path route or text appears in body, inspector, route trace, or link groups.
