# Web UI Active Route Link State Fix

## TL;DR
> **Summary**: Fix the Web UI SVG path semantics so green/active overview links mean "currently active route", not "this hop was acknowledged sometime in the past". Preserve last-hop traffic snapshots in detail views for forensic inspection.
> **Deliverables**:
> - Active-route-aware link rendering in `web_ui/static/app.js`
> - Explicit CSS/label support for stale/inactive overview tone in `web_ui/static/app.css` whenever inactive overview states are rendered
> - DOM semantics that keep raw hop state, route-active verdict, and final overview tone separate
> - Exact fallback semantics for missing/malformed/`FAILED`/`DEGRADED` route summaries
> - Regression tests/evidence for primary → backup and backup → primary transitions
> - Brief/spec documentation updates only where behavior contract changes
> **Effort**: Short
> **Parallel**: YES - 2 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 → Final Verification Wave

## Context
### Original Request
- User observed that when `R1` is turned off and traffic enters the backup route, `R2 -> Monitor` remains green even though primary-side `R2` and `Monitor` are no longer exchanging current data.
- User asked whether the same problem happens when returning from backup to primary; reproduction confirmed backup links can remain green after primary recovery.
- User requested: "수정 계획 세워봐".

### Interview Summary
- The desired behavior is educational clarity: overview lines should show the route currently carrying data.
- Old successful hop records are still useful, but they belong in detail/forensic context, not green overview lines.
- No routing algorithm change is requested.

### Metis Review (gaps addressed)
- Metis identified the main risk as semantic mixing between current overview state and forensic last-hop detail.
- Guardrail added: do not erase/downgrade backend `detail.traffic`; derive overview presentation separately.
- Required QA added for both directions:
  - primary → backup failover
  - backup → primary recovery
- Edge handling added for missing/unknown route summary.

## Work Objectives
### Core Objective
Make Web UI data-path lines distinguish the **current active route** from **last observed hop success**, so stale acknowledged links do not appear as current green/active connections.

### Deliverables
- Active route extraction from Monitor detail route summary in `web_ui/static/app.js`.
- Link-state derivation that combines:
  - endpoint hop snapshots for current hop condition, and
  - Monitor route summary for active/inactive route membership.
- Inactive route overview tone/label such as muted/stale/inactive, without deleting last acknowledged hop detail.
- DOM attributes that make the three state axes explicit: raw hop snapshot, route-active verdict, and final overview tone.
- Browser-level regression evidence under `.sisyphus/evidence/web-ui-situations/` or a new subdirectory under it.
- Updated brief/spec/reference docs only if new UI semantics need durable documentation.

### Definition of Done (verifiable conditions with commands)
- `python -m unittest discover -s tests` passes.
- `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py` passes.
- `node --check web_ui/static/app.js` passes.
- Playwright/headless Chromium scenario proves:
  - when `active_route=backup`, primary route links after failed entry are not `ok`/green in overview;
  - when `active_route=primary`, backup route links are not `ok`/green in overview;
  - raw hop snapshots remain visible in DOM attributes and detail inspector even when overview tone is stale/inactive;
  - inactive-route handling never hides current `down`, `warn`, `active`, `paused`, or failure-like hop states;
  - missing/malformed/invalid/`FAILED`/`DEGRADED` route summaries produce `data-route-active="unknown"` and final `data-hop-tone === data-raw-hop-tone`;
  - inactive acknowledged links have no `완료` in visible label text or SVG `<title>` text;
  - detail inspector still exposes last acknowledged hop snapshot for inactive route links/nodes.

### Must Have
- Overview link state must be current-route-aware.
- `Monitor.last_route_summary.active_route` / `route_state` must be used as the active route source for overview rendering, with this caveat: it represents the last route that reached Monitor, not continuous wire-level liveness.
- Route-aware overlay is valid only when `active_route` is `primary` or `backup` and `route_state` is `PRIMARY` or `BYPASS_ACTIVE`; otherwise the Web UI must preserve exact existing hop-state fallback behavior.
- `route_state === "DEGRADED"` is not a valid route-aware overlay source in this fix. Treat `DEGRADED` the same as missing/malformed/unknown/`FAILED` route summaries: `data-route-active="unknown"`, final `data-hop-tone` equals `data-raw-hop-tone`, and no stale/inactive projection is applied from route summary alone.
- Raw hop snapshot state, route-active verdict, and final overview tone must be represented separately in DOM and tests.
- Existing SVG link ids must remain stable:
  - `host-agent`
  - `agent-r1`
  - `r1-r2`
  - `r2-monitor`
  - `agent-r1b`
  - `r1b-r2b`
  - `r2b-monitor`
- Existing topology layout must remain intact.
- Detail inspector must continue to show node-authored `detail.traffic` last-hop data.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Do not modify routing behavior in `nw_demo/local_agent.py`, `nw_demo/relay.py`, or `nw_demo/monitor.py` unless tests prove a data bug separate from UI semantics.
- Do not erase, reset, or downgrade runtime traffic snapshots to make the overview look correct.
- Do not let inactive-route projection mask raw `down`, `warn`, `active`, `paused`, `timeout`, `connection_error`, `delivery_failed`, `rejected`, or other failure/current-progress hop states.
- Do not label inactive acknowledged links as `완료`; reserve `완료` for current active-route success.
- Do not animate stale/inactive acknowledged links with `path-flow`; reserve flow animation for current active/progress route evidence.
- Do not introduce arbitrary mesh/cross routing such as `R1 -> R2B` or `R1B -> R2`.
- Do not redesign the topology canvas, node cards, palette, or detail inspector layout.
- Do not rely on screenshots alone; DOM/text/API assertions are required.
- Do not require human visual confirmation.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + existing stdlib unittest + Playwright/headless Chromium browser QA
- QA policy: Every task has agent-executed scenarios
- Evidence: `.sisyphus/evidence/web-ui-situations/active-route-link-state/`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = acceptable here because this is a narrow bug fix.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 (UI semantic model) and Task 4 (test harness preparation) may run in parallel after reading the same references.
Wave 2: Task 2 (render implementation) and Task 3 (browser regression) depend on Task 1; Task 5 (docs/brief) depends on final behavior from Task 2/3.

### Dependency Matrix (full, all tasks)
- Task 1: blocks Task 2 and Task 3.
- Task 2: blocked by Task 1; blocks Task 3 and Task 5.
- Task 3: blocked by Task 1 and Task 2.
- Task 4: can run in parallel with Task 1; supports Task 3.
- Task 5: blocked by Task 2 and Task 3.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 2 tasks → quick, unspecified-high
- Wave 2 → 3 tasks → quick, unspecified-high, writing

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Define active-route overview semantics in the frontend model

  **What to do**: In `web_ui/static/app.js`, add small pure helper functions that extract Monitor route summary from `adapted.nodesById.monitor.runtime.details.detail.last_route_summary`, classify each `MAIN_LINKS` id as `primary`, `backup`, or shared, and return whether the link belongs to the current active route. Suggested helper split: `monitorRouteSummary(adapted)`, `routeGroupForLink(link)`, `isKnownRouteSummary(summary)`, and `routeActiveForLink(link, summary)`. Use `active_route === "primary"` for `agent-r1`, `r1-r2`, `r2-monitor`; use `active_route === "backup"` for `agent-r1b`, `r1b-r2b`, `r2b-monitor`; treat `host-agent` as shared and never inactive solely due to route. A known route summary requires `active_route` in `{primary, backup}` and `route_state` in `{PRIMARY, BYPASS_ACTIVE}`. If route summary is missing, malformed, unknown, invalid, has unrecognized `active_route`, or has `route_state` in `{FAILED, DEGRADED}`, keep exact existing hop-state behavior to avoid hiding startup diagnostics or inventing live-route certainty; the DOM verdict must be `data-route-active="unknown"`, and final `data-hop-tone` must equal `data-raw-hop-tone`.
  **Must NOT do**: Do not change backend routing, node traffic snapshot lifecycle, SVG layout coordinates, or node card rendering.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: Small focused frontend helper extraction in one file.
  - Skills: [] - No specialized skill required for pure JS helper work.
  - Omitted: [`api-and-interface-design`] - This does not introduce a public API; it refines existing UI projection.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [2, 3] | Blocked By: []

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web_ui/static/app.js:29-37` - Existing `MAIN_LINKS` ids and route segments to classify.
  - Pattern: `web_ui/static/app.js:145-156` - Current `linkHopState()` only reads endpoint hop snapshots and causes stale green links.
  - Pattern: `web_ui/static/app.js:570-591` - Monitor detail already reads `last_route_summary`; use the same data source for overview route awareness.
  - API/Type: `IMPLEMENTATION_SPEC.md:158-174` - Canonical primary/backup route edge definitions and forbidden cross paths.
  - Intent: `INTENT_ALIGNMENT_NOTE.md:212-221` - `reported_state`, `observed_liveness`, and `hop_state` must remain separate; traffic truth comes from nodes.
  - Finding: This plan's `Context` and `Work Objectives` sections - Reproduction summary and scope boundary from the planning session.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `node --check web_ui/static/app.js` exits 0.
  - [ ] A temporary browser/devtools or Node-level inspection can show that helper classification returns `primary` for `r1-r2`, `backup` for `r1b-r2b`, and `shared` for `host-agent`.
  - [ ] Missing, malformed, invalid, unrecognized, `FAILED`, or `DEGRADED` route summary falls back to existing hop-state behavior instead of forcing all links muted or active.
  - [ ] Fallback route summaries produce `data-route-active="unknown"` and final `data-hop-tone === data-raw-hop-tone` for representative acknowledged, failure, and progress raw hop states.
  - [ ] `Monitor.last_route_summary` is treated as last delivered route summary, not continuous liveness proof.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Link ids classify into canonical route groups
    Tool: Bash
    Steps: Run a small non-mutating JS syntax/inspection command or Playwright page evaluation after loading the Web UI; evaluate the route classification for host-agent, r1-r2, r2-monitor, agent-r1b, r1b-r2b, r2b-monitor.
    Expected: host-agent=shared; agent-r1/r1-r2/r2-monitor=primary; agent-r1b/r1b-r2b/r2b-monitor=backup.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-1-route-classification.json

  Scenario: Unknown route summary does not hide diagnostics
    Tool: Bash
    Steps: Evaluate helper behavior with monitor route summary omitted/null, malformed object shapes, `active_route="-"`, `active_route="mesh"`, `route_state="FAILED"`, and `route_state="DEGRADED"` using sample acknowledged, failure, and progress hop_state inputs.
    Expected: Link state remains based on hop_state fallback; `data-route-active="unknown"`; final `data-hop-tone` equals `data-raw-hop-tone`; no forced inactive/muted/active state is applied solely because route summary is absent or invalid.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-1-missing-route-summary.json
  ```

  **Commit**: NO | Message: `Fix Web UI active route link state` | Files: [`web_ui/static/app.js`]

- [ ] 2. Render inactive route links as inactive/stale in overview while preserving detail data

  **What to do**: Update `renderPaths()` / link derivation in `web_ui/static/app.js` so each SVG link group has separate data attributes for raw hop state, raw tone, route-active verdict, and final overview tone: `data-hop-state` remains the raw/effective hop state from endpoint `detail.traffic`; `data-raw-hop-tone` is `hopTone(data-hop-state)`; `data-route-active="true|false|shared|unknown"` is the route-membership verdict; `data-hop-tone` is the final route-aware overview tone used by existing CSS selectors. Precedence rule: inactive-route projection may only downgrade raw `acknowledged` / raw tone `ok` to a distinct stale/inactive tone; it must never downgrade or hide raw `down`, `warn`, `active`, `paused`, `timeout`, `connection_error`, `delivery_failed`, `rejected`, or current-progress/failure-like states. When `active_route=backup`, primary route links except the failed entry indicator must not render as overview `ok`; when `active_route=primary`, backup route links must not render as overview `ok`. Make both the visible label path and SVG `<title>` route-aware: `linkStatusLabel()` may return `완료` only for current active-route success; for acknowledged-but-inactive links it must return `최근 성공 기록` or `비활성 경로`, and neither visible label text nor title text may contain `완료`. Use explicit slate/gray stale/inactive CSS that is visually distinct from green success and cyan idle; do not rely on unstylized fallback gray. Do not delete the original hop state. Keep `host-agent` independent of primary/backup route selection. If a primary entry link such as `agent-r1` has a current failure/paused state, preserve the failure/muted state rather than masking it as inactive success. For fallback route summaries from Task 1, do not apply inactive projection; set `data-route-active="unknown"` and keep final `data-hop-tone` equal to `data-raw-hop-tone`.
  **Must NOT do**: Do not remove `data-link-id`, do not change the seven-link topology, do not make screenshots the only verification, and do not rewrite `detail.traffic` values.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: Focused frontend rendering change with clear references.
  - Skills: [] - No extra skill required unless browser verification is performed in same task.
  - Omitted: [`frontend-ui-ux`] - No broad redesign; this is semantic correction.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [3, 5] | Blocked By: [1]

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web_ui/static/app.js:347-397` - `renderPaths()` sets `data-link-id`, `data-hop-state`, `data-hop-tone`, path classes, marker, and label.
  - Pattern: `web_ui/static/app.js:170-185` - `linkStatusLabel()` currently maps `acknowledged` to "완료" even when stale; add or adjust an overview-aware label path so inactive acknowledged links say `최근 성공 기록` / `비활성 경로` instead.
  - Pattern: `web_ui/static/app.css:185-213` - Existing tone styles for ok/active/warn/down/idle.
  - Pattern: `web_ui/static/app.css:215-261` - Existing label tone styling; extend minimally with a slate/gray stale/inactive tone that cannot be confused with green success or cyan idle.
  - Evidence: Previous reproduction found `active_route=backup` while `r1-r2` and `r2-monitor` rendered `acknowledged / ok`.
  - Evidence: Previous reproduction found `active_route=primary` while backup links rendered `acknowledged / ok`.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `node --check web_ui/static/app.js` exits 0.
  - [ ] If inactive/stale overview tone is used, `web_ui/static/app.css` defines explicit stale/inactive path and label styling distinct from green success and cyan idle; browser loads without console errors and existing path tones still render for active/warn/down/idle cases.
  - [ ] Inactive route links expose machine-readable DOM attributes showing raw hop state, raw hop tone, route-active verdict, and final overview tone separately.
  - [ ] Inactive-route projection only downgrades raw `acknowledged` / raw `ok`; non-acknowledged raw states such as `down`, `warn`, `active`, `paused`, `timeout`, and `connection_error` keep their severity/progress tone.
  - [ ] Inactive acknowledged links never display a visible `완료` label and never expose `완료` in their SVG `<title>`; they display `최근 성공 기록` or `비활성 경로`, and their stale/inactive tone is visibly distinct from both green success and cyan idle.
  - [ ] `path-flow` animation is applied only to current active/progress overview links, never to stale/inactive acknowledged links.
  - [ ] Existing `data-link-id` values are unchanged.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Backup active mutes stale primary successes
    Tool: Playwright
    Steps: Start/reset Web UI runtime, run start, pause r1, trigger fault cpu on, wait until Monitor detail reports active_route=backup, then inspect g[data-link-id="r1-r2"] and g[data-link-id="r2-monitor"].
    Expected: r1-r2 and r2-monitor keep data-hop-state="acknowledged" and data-raw-hop-tone="ok" if that is the raw snapshot, but final data-hop-tone is stale/inactive rather than "ok" and data-route-active="false"; their visible labels and SVG titles do not contain `완료` and instead use `최근 성공 기록` or `비활성 경로`; backup links are active/ok according to their current hop states; any current failure/progress state is not overwritten by inactive projection.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-2-backup-active-links.json

  Scenario: Primary recovery mutes stale backup successes
    Tool: Playwright
    Steps: From backup-active state, run start r1, fault cpu off, fault cpu on to create a new primary event, wait until Monitor detail reports active_route=primary, then inspect backup link groups.
    Expected: agent-r1b, r1b-r2b, and r2b-monitor preserve raw hop attributes but do not have final data-hop-tone="ok" as current overview state when inactive; their visible labels and SVG titles do not contain `완료` and instead use `최근 성공 기록` or `비활성 경로`; primary links show the current route state; inactive logic does not hide any raw down/warn/active/paused state.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-2-primary-recovered-links.json
  ```

  **Commit**: NO | Message: `Fix Web UI active route link state` | Files: [`web_ui/static/app.js`, `web_ui/static/app.css` if needed]

- [ ] 3. Add browser regression verification for both route transitions

  **What to do**: Create or update a Playwright/headless Chromium QA driver under `/tmp/opencode/` or an existing evidence runner pattern that starts or uses the local Web UI runtime and records DOM/API assertions. It must cover both primary → backup and backup → primary. Assertions must inspect `/api/state` Monitor route summary and `g[data-link-id]` DOM attributes in the same scenario, including `data-hop-state`, `data-raw-hop-tone`, `data-route-active`, final `data-hop-tone`, visible SVG label text, and SVG `<title>` text. Store JSON assertions, DOM text, and screenshot evidence under `.sisyphus/evidence/web-ui-situations/active-route-link-state/`. If a temporary script is created under `/tmp/opencode/`, do not commit it unless project practice already commits that script class.
  **Must NOT do**: Do not rely on visual inspection only; do not leave test servers/processes running on QA ports after completion; do not overwrite existing `.sisyphus/evidence/web-ui-situations/final-summary.md`.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Browser/runtime QA with process cleanup and precise assertions.
  - Skills: [`webapp-testing`] - Required for Playwright-driven local Web UI verification.
  - Omitted: [`debugging-and-error-recovery`] - Use only if verification fails unexpectedly; the planned scenario is already diagnosed.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [5] | Blocked By: [1, 2, 4]

  **References** (executor has NO interview context - be exhaustive):
  - Existing evidence: `.sisyphus/evidence/web-ui-situations/task-12-primary-r2-middle-off/` - Browser assertions for primary middle-off conditions.
  - Existing evidence: `.sisyphus/evidence/web-ui-situations/task-14-backup-middle-off/` - Browser assertions for backup middle-off conditions.
  - Existing summary: `.sisyphus/evidence/web-ui-situations/node-sequence-middle-off-summary.md` - Prior PASS rollup and route-state evidence pattern.
  - Runtime entry: `README.md:130-151` - Web UI server command and API endpoints.
  - UI contract: `web_ui/static/app.js:356-360` - Link groups currently expose `data-link-id`, `data-hop-state`, and `data-hop-tone`; this fix must extend that contract with `data-raw-hop-tone` and `data-route-active`.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Browser QA writes a JSON assertion file with zero failed assertions.
  - [ ] Scenario 1 proves `active_route=backup` and primary stale success links are not overview `ok`.
  - [ ] Scenario 2 proves `active_route=primary` and backup stale success links are not overview `ok`.
  - [ ] Browser QA proves raw hop state/tone remains inspectable separately from final overview tone.
  - [ ] Browser QA proves inactive-route logic does not overwrite current `down`, `warn`, `active`, `paused`, or failure-like entry states.
  - [ ] Browser QA proves inactive acknowledged links have no `완료` in visible label text or SVG `<title>` text.
  - [ ] Browser QA proves missing/malformed/invalid/`FAILED`/`DEGRADED` route summaries use `data-route-active="unknown"` and final `data-hop-tone === data-raw-hop-tone`.
  - [ ] Screenshots are saved as evidence, but pass/fail is determined by DOM/API assertions.
  - [ ] QA runtime ports are cleaned up after the script exits.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: R1 pause activates backup without stale primary green links
    Tool: Playwright
    Steps: Open Web UI, reset/start, ensure faults off, pause r1, enable CPU fault, wait for Monitor route summary active_route=backup, inspect DOM link attributes for agent-r1/r1-r2/r2-monitor/agent-r1b/r1b-r2b/r2b-monitor.
    Expected: active_route=backup; r1-r2 and r2-monitor are not current ok/green in final data-hop-tone while preserving raw hop attributes; their visible labels and SVG titles do not contain `완료`; backup path links indicate current route activity/success; agent-r1 reflects paused/failure entry state rather than green success or harmless inactive gray.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-3-primary-to-backup.json

  Scenario: R1 restart returns to primary without stale backup green links
    Tool: Playwright
    Steps: Continue from backup scenario, start r1, turn CPU fault off, turn CPU fault on again, wait for Monitor route summary active_route=primary, inspect all backup SVG link attributes.
    Expected: active_route=primary; agent-r1b/r1b-r2b/r2b-monitor are not current ok/green in final data-hop-tone while preserving raw hop attributes; their visible labels and SVG titles do not contain `완료`; primary route links indicate current route activity/success; inactive logic does not overwrite any raw down/warn/active/paused state.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-3-backup-to-primary.json

  Scenario: Malformed failed or degraded route summary keeps diagnostic fallback
    Tool: Playwright
    Steps: Evaluate or simulate route summary values with missing/malformed `active_route`, invalid `active_route`, `route_state=FAILED`, and `route_state=DEGRADED`, then inspect representative SVG link attributes with acknowledged, failure, and progress raw hop states.
    Expected: final overview tone follows existing raw hop-state behavior; `data-route-active="unknown"`; final `data-hop-tone` equals `data-raw-hop-tone`; no stale/inactive overlay is applied from invalid route summary alone.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-3-invalid-route-summary.json
  ```

  **Commit**: NO | Message: `Fix Web UI active route link state` | Files: [`.sisyphus/evidence/web-ui-situations/active-route-link-state/` if evidence is intended for commit]

- [ ] 4. Add focused unit/contract tests for link-state derivation if practical

  **What to do**: If the frontend helper functions can be made testable without introducing build tooling, add a minimal stdlib/Python or Node-based static test that validates route classification, valid route summary projection, exact fallback for missing/malformed/invalid/`FAILED`/`DEGRADED` route summaries, raw-tone preservation, and inactive overview tone derivation from sample route summaries. Prefer testing pure logic by evaluating `web_ui/static/app.js` in a controlled DOM/page context rather than adding a new frontend framework. If this becomes too invasive, skip new unit files and rely on Task 3 browser assertions, recording the reason in evidence.
  **Must NOT do**: Do not add npm dependencies, bundlers, Jest, or a new build system.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: Small optional regression guard around pure link-state logic.
  - Skills: [] - Existing Python/Node command checks are enough.
  - Omitted: [`api-and-interface-design`] - No new interface design.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [3] | Blocked By: []

  **References** (executor has NO interview context - be exhaustive):
  - Test pattern: `tests/test_hop_state_visibility.py` - Existing hop-state visibility contract style.
  - Test pattern: `tests/status_builders.py` - Existing status fixtures with `detail.traffic` shape.
  - Static check: `node --check web_ui/static/app.js` - Existing JS syntax verification command.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Either a lightweight regression test exists and passes, or evidence explicitly records why browser DOM assertions are the correct regression layer.
  - [ ] No new package/dependency files are introduced.
  - [ ] Test/evidence covers raw acknowledged + inactive route, raw failure/progress + inactive route, shared `host-agent`, invalid route summary fallback, and `DEGRADED` fallback.
  - [ ] `python -m unittest discover -s tests` still passes if tests are changed.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Pure route classification regression guard
    Tool: Bash
    Steps: Run the added unit/static test, or run the documented no-new-test justification command that proves browser QA covers the same assertions.
    Expected: Route classification, valid route summary projection, missing/malformed/invalid/`FAILED`/`DEGRADED` fallback with `data-route-active="unknown"` and final `data-hop-tone === data-raw-hop-tone`, raw tone preservation, and inactive tone behavior are verified without adding dependencies.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-4-contract-test.txt

  Scenario: No frontend dependency creep
    Tool: Bash
    Steps: Inspect git diff for package.json/package-lock/yarn/pnpm additions and run existing Python/Node checks.
    Expected: No new frontend tooling files; existing checks pass.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-4-no-dependency-creep.txt
  ```

  **Commit**: NO | Message: `Fix Web UI active route link state` | Files: [`tests/*` only if a lightweight test is added]

- [ ] 5. Update durable documentation/brief for the corrected UI semantics

  **What to do**: Update `AI_IMPLEMENTATION_BRIEF.md` with a concise session note that Web UI overview links now distinguish current active route from last-hop forensic traffic. If the behavior contract needs canonical wording, update `IMPLEMENTATION_SPEC.md` or `docs/reference/ui-preview/WEB_UI_SPEC.md` minimally: overview SVG path tone is active-route-aware; `detail.traffic` remains node-authored last observed hop truth; `Monitor.last_route_summary` is last-delivered-route evidence, not continuous liveness proof; raw hop state, route-active verdict, and final overview tone are separate UI axes. Keep Korean as the default documentation language.
  **Must NOT do**: Do not create new root markdown files; do not write a long session log; do not duplicate the whole plan into docs.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: Small canonical documentation update in Korean.
  - Skills: [] - No specialized skill needed.
  - Omitted: [`context-budget`] - This is not a context overhead audit.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [] | Blocked By: [2, 3]

  **References** (executor has NO interview context - be exhaustive):
  - Governance: `AGENTS.md` - Root markdown allowed list and brief/spec update rules.
  - Current brief: `AI_IMPLEMENTATION_BRIEF.md:139-147` - Open issues and Web UI verification notes.
  - Canonical spec: `IMPLEMENTATION_SPEC.md:519-541` - State-axis and hop taxonomy separation.
  - Intent: `INTENT_ALIGNMENT_NOTE.md:212-221` - Monitoring surface guardrails and state-axis separation.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Documentation changes, if any, are limited to existing allowed markdown files.
  - [ ] Updated text states that overview route tone and forensic traffic detail are separate concepts.
  - [ ] Updated text states that stale/inactive overview tone must not hide raw failure/progress hop states.
  - [ ] No new root `.md` files are created.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Documentation records corrected route semantics
    Tool: Bash
    Steps: Inspect diff for AI_IMPLEMENTATION_BRIEF.md and any spec/reference doc touched.
    Expected: Concise Korean note explains active-route-aware overview links, preserved detail traffic snapshots, last-delivered-route wording, and raw/route/overview state-axis separation.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-5-doc-diff.txt

  Scenario: Markdown governance preserved
    Tool: Bash
    Steps: Check root markdown file list after changes.
    Expected: Only README.md, AGENTS.md, IMPLEMENTATION_SPEC.md, INTENT_ALIGNMENT_NOTE.md, AI_IMPLEMENTATION_BRIEF.md exist at root; no new root markdown was added.
    Evidence: .sisyphus/evidence/web-ui-situations/active-route-link-state/task-5-root-md-check.txt
  ```

  **Commit**: YES | Message: `Fix Web UI active route link state` | Files: [`web_ui/static/app.js`, `web_ui/static/app.css` if changed, optional tests, docs/brief updates, relevant evidence]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Commit after all implementation and verification pass.
- Suggested message: `Fix Web UI active route link state`
- Include only files directly changed for this fix and generated QA evidence requested by the user.

## Success Criteria
- In backup route mode, primary stale acknowledged links no longer render as current green/ok links.
- After primary recovery, backup stale acknowledged links no longer render as current green/ok links.
- Raw `data-hop-state` / `data-raw-hop-tone` still expose last-hop facts even when final overview tone is stale/inactive.
- Inactive-route projection never masks current failure/progress states such as `down`, `warn`, `active`, `paused`, `timeout`, or `connection_error`.
- Invalid, malformed, missing, unknown, `FAILED`, or `DEGRADED` route summaries do not invent active-route certainty; they preserve existing hop-state fallback behavior with `data-route-active="unknown"` and final `data-hop-tone === data-raw-hop-tone`.
- Inactive acknowledged links do not show `완료` in visible label text or SVG `<title>`; they show `최근 성공 기록` or `비활성 경로`.
- Detail views still preserve and expose last-hop acknowledged records for inactive paths.
- Existing routing tests and Web UI static syntax checks pass.
