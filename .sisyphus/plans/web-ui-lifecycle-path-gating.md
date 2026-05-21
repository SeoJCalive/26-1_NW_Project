# Web UI Lifecycle Path Gating

## TL;DR
> **Summary**: Make the Web UI overview SVG paths respect explicit node power lifecycle before rendering stale traffic snapshots, without clearing `/api/state` traffic evidence.
> **Deliverables**:
> - Raw `node_power.state`-based lifecycle override in `web_ui/static/app.js`
> - `전원 꺼짐` / `전원 전환 중` overview labels for explicit stopped/transitioning states
> - Preserved traffic snapshots in API/detail inspector
> - Browser DOM/API evidence for stopped, transitioning, running, external, and missing/unknown lifecycle states
> **Effort**: Quick
> **Parallel**: NO
> **Critical Path**: Task 1 → Task 2 → Final Verification Wave

## Context
### Original Request
- User observed that after global node power stop, links after Local Agent still look like signals continue.
- Analysis confirmed actual supervised node processes stop, while `details.detail.traffic` preserves the last node-authored traffic snapshot and overview SVG paths continue rendering that stale snapshot as current-looking path state.
- User requested a modification plan based on the agreed fix and required Oracle review until strong PASS.

### Interview Summary
- The fix must not clear or rewrite `/api/state` `details.detail.traffic`.
- The fix must target the overview SVG path display only.
- Explicit stopped lifecycle must show all links as `전원 꺼짐`, muted visual tone, no animation.
- Explicit transitioning lifecycle must show all links as `전원 전환 중`, muted visual tone, no animation.
- Running / external / unknown / missing lifecycle states must preserve existing traffic-based rendering.
- No hacks: use a centralized helper, not scattered one-off checks.

### Metis Review (gaps addressed)
- Metis required an explicit helper contract and exact missing/unknown lifecycle fallback.
- Metis required asserting absence of `.path-flow`, not just labels.
- Metis required all links to be overridden in explicit stopped/transitioning states.
- Metis required `/api/state` and detail traffic evidence to remain intact.
- Metis warned against backend mutation and CSS/layout scope creep.

### Oracle Review (PASS)
- First Oracle review rejected deriving the path override from `nodePowerState(adapted)` because it can infer `stopped` when raw `node_power.state` is missing.
- Revised plan uses only raw `latestState.node_power.state` for path lifecycle override.
- Oracle returned **STRONG PASS** on the revised plan.
- Oracle approved using existing `data-hop-tone="inactive"` as the muted visual implementation, with semantic lifecycle stored in `data-hop-state="stopped"|"transitioning"` and labels.

## Work Objectives
### Core Objective
Prevent stale traffic snapshots from appearing as current live SVG path flow when the Web UI supervisor explicitly reports node power as stopped or transitioning.

### Deliverables
- `web_ui/static/app.js` helper that reads only raw `latestState.node_power.state` for overview path lifecycle override.
- `renderPaths(adapted)` branch that applies lifecycle override before traffic/route rendering only for raw `stopped` and raw `transitioning`.
- Preserved existing traffic-based rendering for raw `running`, `external`, `partial`, `unknown`, missing, null, and unrecognized lifecycle states.
- Browser/API evidence under `.sisyphus/evidence/web-ui-situations/lifecycle-path-gating/`.

### Definition of Done (verifiable conditions with commands)
- `node --check web_ui/static/app.js` exits 0.
- `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py` exits 0.
- `python -m unittest discover -s tests` exits 0.
- Browser DOM/API QA proves explicit stopped state overrides every overview link while `/api/state` still contains stale `details.detail.traffic` evidence.
- Browser DOM/API QA proves explicit transitioning state overrides every overview link and no link has `.path-flow`.
- Browser DOM/API QA proves running and external/missing/unknown lifecycle states are not forced to lifecycle labels.

### Must Have
- Raw lifecycle override source must be exactly `latestState.node_power.state`, accessed through `getNested(latestState, ["node_power", "state"], null)` or equivalent.
- Override helper must return an override object only for raw `"stopped"` and raw `"transitioning"`; otherwise it returns `null`.
- Override object for stopped:
  - `hopState: "stopped"`
  - `rawTone: "muted"`
  - `routeActive: "lifecycle"`
  - `tone: "inactive"` using existing muted/inactive visual style
  - `label: "전원 꺼짐"`
  - `flow: false`
- Override object for transitioning:
  - `hopState: "transitioning"`
  - `rawTone: "muted"`
  - `routeActive: "lifecycle"`
  - `tone: "inactive"` using existing muted/inactive visual style
  - `label: "전원 전환 중"`
  - `flow: false`
- `renderPaths(adapted)` must compute the override once before `MAIN_LINKS.forEach`.
- If override exists, all seven existing `MAIN_LINKS` must use override values for visible label, SVG title, `data-hop-state`, `data-raw-hop-tone`, `data-route-active`, final `data-hop-tone`, marker, and animation decision.
- If override is `null`, existing traffic/route logic must remain semantically unchanged.
- Detail inspector and `/api/state` must continue to expose original node-authored `details.detail.traffic` snapshots.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Do not use `nodePowerState(adapted)` for path lifecycle override.
- Do not infer lifecycle override from live node count, route summary, traffic details, card state, or selected node state.
- Do not treat `external`, `running`, `partial`, `unknown`, missing, null, or unrecognized raw power states as stopped.
- Do not modify `web_ui/server.py`, `nw_demo/controller_ui.py`, node publishers, route summary generation, process supervisor logic, API shape, or traffic snapshot shape.
- Do not clear, replace, normalize, or rewrite `details.detail.traffic`.
- Do not redesign the topology canvas, node cards, palette, CSS layout, command palette, or detail inspector.
- Do not add new CSS unless implementation proves existing `inactive` tone cannot be reused; Oracle approved reusing `inactive` and adding `muted` CSS would be unnecessary overreach.
- Do not rely on screenshots alone; use DOM/API assertions.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + existing Python unittest + JS syntax check + Playwright/headless Chromium browser QA.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/web-ui-situations/lifecycle-path-gating/`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. This is a narrow fix; use 2 sequential tasks to avoid over-splitting.

Wave 1: Task 1 (frontend lifecycle override + focused verification)
Wave 2: Task 2 (runtime browser/API regression evidence)

### Dependency Matrix (full, all tasks)
- Task 1: blocks Task 2.
- Task 2: blocked by Task 1; blocks final verification.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 1 task → quick
- Wave 2 → 1 task → unspecified-high + webapp-testing

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Add raw lifecycle override to overview SVG path rendering

  **What to do**: In `web_ui/static/app.js`, add small helper(s) near the existing path state helpers. The helper must read only the raw API state, e.g. `const state = getNested(latestState, ["node_power", "state"], null)`. It must return the stopped override object only when `state === "stopped"`, the transitioning override object only when `state === "transitioning"`, and `null` for every other value. Update `renderPaths(adapted)` so it computes this override once before `MAIN_LINKS.forEach`. Inside the loop, preserve `path` and `labelPosition` calculation. If override exists, use its lifecycle values for `hopState`, `rawTone`, `routeActive`, `tone`, and `label`; set SVG `<title>` to include the lifecycle label and lifecycle dataset values; use `markerForTone("inactive")`; never add `.path-flow`. If override is `null`, execute the existing `linkHopState()`, `hopTone()`, `routeActiveForLink()`, `overviewToneForLink()`, and `linkStatusLabel()` flow with no semantic change.

  **Must NOT do**: Do not call `nodePowerState(adapted)` from the path override helper. Do not edit `web_ui/server.py`, controller code, API schema, traffic snapshots, CSS layout, or detail inspector code. Do not use live node count as an override input. Do not add `data-hop-tone="muted"`; use existing `data-hop-tone="inactive"` for the muted visual tone unless implementation proves impossible.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: Single-file frontend projection change with exact helper contract.
  - Skills: [] - No specialized skill needed for focused JavaScript edit.
  - Omitted: [`frontend-ui-ux`] - No broad design or styling work is requested.
  - Omitted: [`api-and-interface-design`] - API contract is intentionally unchanged.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2] | Blocked By: []

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web_ui/static/app.js:157-174` - Existing `peerStateForLink()` and `linkHopState()` derive hop state from node traffic snapshots.
  - Pattern: `web_ui/static/app.js:201-204` - Existing `overviewToneForLink()` must remain the traffic-mode final tone path.
  - Pattern: `web_ui/static/app.js:214-229` - Existing `linkStatusLabel()` must remain the traffic-mode label path.
  - Pattern: `web_ui/static/app.js:285-294` - `nodePowerState(adapted)` exists but MUST NOT be used for path lifecycle override because it can infer stopped from live count.
  - Pattern: `web_ui/static/app.js:428-484` - `renderPaths(adapted)` is the exact place to insert lifecycle-qualified overview display.
  - Pattern: `web_ui/static/app.css:309-368` - Existing `data-hop-tone="inactive"` path/label styling provides the approved muted visual tone.
  - API: `web_ui/server.py:113-122` - Server snapshot preserves `details` while overlaying stopped liveness/note; do not change it.
  - Oracle: Revised plan received STRONG PASS only after using raw `latestState.node_power.state` instead of `nodePowerState(adapted)`.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `node --check web_ui/static/app.js` exits 0.
  - [ ] Static inspection confirms path lifecycle override helper reads raw `latestState.node_power.state` and does not call `nodePowerState(adapted)`.
  - [ ] Static inspection confirms override branch uses `data-hop-state="stopped"` / `"transitioning"`, final `data-hop-tone="inactive"`, label `전원 꺼짐` / `전원 전환 중`, and cannot add `.path-flow`.
  - [ ] Static inspection confirms `external`, `running`, `partial`, `unknown`, missing, null, and unrecognized raw states return `null` and therefore use existing traffic rendering.
  - [ ] No files outside `web_ui/static/app.js` are changed by this task unless the executor stops and records a blocker.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Helper contract rejects inferred lifecycle
    Tool: Bash
    Steps: Run `node --check web_ui/static/app.js`; inspect the helper implementation text or evaluate it in the browser after loading a mocked state where all nodes are offline but `node_power.state` is missing/unknown.
    Expected: The helper returns null for missing/unknown raw power state; it does not force `전원 꺼짐` from liveCount or nodePowerState fallback.
    Evidence: .sisyphus/evidence/web-ui-situations/lifecycle-path-gating/task-1-helper-contract.json

  Scenario: Traffic branch remains reachable
    Tool: Bash
    Steps: Inspect or evaluate a mocked state with raw `node_power.state="running"` and traffic hop states `acknowledged`, `retrying`, and `delivery_failed`.
    Expected: Labels/tone follow existing traffic logic (`완료`, retry label, failure label as applicable); no lifecycle label appears.
    Evidence: .sisyphus/evidence/web-ui-situations/lifecycle-path-gating/task-1-traffic-branch.json
  ```

  **Commit**: NO | Message: `Fix Web UI lifecycle path gating` | Files: [`web_ui/static/app.js`]

- [ ] 2. Verify lifecycle-gated paths against live Web UI runtime

  **What to do**: Run browser/API QA with Playwright/headless Chromium against the Web UI. Use a disposable QA port if needed, or the existing local `28083` runtime if safe. Produce evidence under `.sisyphus/evidence/web-ui-situations/lifecycle-path-gating/`. First create stale traffic by starting node power and waiting for normal traffic snapshots. Then stop node power and verify API says stopped while traffic details remain present. Verify all SVG links show lifecycle-gated stopped state. Also verify transitioning during stop/start lock, running regression after start completes, and external/no-supervisor or mocked missing/unknown lifecycle fallback. Clean up any QA runtime processes and ports.

  **Must NOT do**: Do not rely on screenshot-only proof. Do not leave QA servers/processes running. Do not use `--fixed-node-ports` unless specifically testing fixed-port behavior; it is irrelevant to this fix. Do not clear traffic to make assertions pass.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: Requires runtime orchestration, API assertions, browser DOM assertions, and cleanup.
  - Skills: [`webapp-testing`, `debugging-and-error-recovery`] - Playwright QA plus structured triage if runtime state differs.
  - Omitted: [`frontend-ui-ux`] - No visual redesign; assertions are DOM/API semantics.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [] | Blocked By: [1]

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web_ui/static/index.html:33-52` - SVG root and `#data-path` container for `[data-link-id]` assertions.
  - Pattern: `web_ui/static/app.js:428-484` - Link groups expose `data-link-id`, `data-hop-state`, `data-raw-hop-tone`, `data-route-active`, `data-hop-tone`, visible `<text>`, and SVG `<title>`.
  - Pattern: `web_ui/static/app.js:855-887` - `/api/power` action flow and transition lock refresh behavior.
  - API: `web_ui/server.py:124-140` - `node_power.state` values are `external`, `transitioning`, `running`, or `stopped`.
  - Evidence style: `.sisyphus/evidence/web-ui-situations/task-7-lifecycle-reset/` and `.sisyphus/evidence/web-ui-situations/active-route-link-state/` - Prior DOM/API/screenshot evidence layout.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py` exits 0.
  - [ ] `python -m unittest discover -s tests` exits 0.
  - [ ] `node --check web_ui/static/app.js` exits 0.
  - [ ] Stopped QA: `/api/state.node_power.state == "stopped"`; every node has `observed_liveness == "offline"`; at least one node still has non-empty `details.detail.traffic.recent` or non-null traffic peer capture; every `[data-link-id]` has visible label `전원 꺼짐`, `data-hop-state="stopped"`, `data-hop-tone="inactive"`, and no `.path-flow` descendant.
  - [ ] Transitioning QA: during stop or start lock, `/api/state.node_power.state == "transitioning"`; every `[data-link-id]` has visible label `전원 전환 중`, `data-hop-state="transitioning"`, `data-hop-tone="inactive"`, and no `.path-flow` descendant.
  - [ ] Detail preservation QA: opening a node detail inspector after stopped state still shows `Traffic Snapshot` with the last node-authored traffic values, or API evidence shows the same preserved traffic if detail opening is impractical.
  - [ ] Running regression: after node power start completes, no `[data-link-id]` visible label is `전원 꺼짐` or `전원 전환 중`; at least one link returns to traffic-derived `data-hop-state` such as `acknowledged`, `request_sent`, `request_received`, `retrying`, `delivery_failed`, `invalid_response`, or `unknown` according to runtime state.
  - [ ] External/missing/unknown regression: explicit `node_power.state="external"` and mocked/missing/unknown lifecycle state do not force lifecycle labels; traffic-derived labels remain.
  - [ ] Evidence files include assertions JSON, DOM/text dump, browser console log if available, and screenshot.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Stopped lifecycle overrides stale traffic without erasing it
    Tool: Playwright + Bash
    Steps: Start Web UI supervisor, wait for traffic, POST `/api/power` action `stop`, wait until `/api/state.node_power.state` is `stopped`, then inspect `/api/state` and all `[data-link-id]` DOM groups.
    Expected: API still contains at least one stale traffic snapshot; all overview links show `전원 꺼짐`, `data-hop-state="stopped"`, `data-hop-tone="inactive"`, and no `.path-flow`.
    Evidence: .sisyphus/evidence/web-ui-situations/lifecycle-path-gating/task-2-stopped-override.json

  Scenario: Transitioning lifecycle is procedural and non-animated
    Tool: Playwright + Bash
    Steps: Trigger stop or start and sample DOM while `/api/state.node_power.state` is `transitioning`.
    Expected: All overview links show `전원 전환 중`, `data-hop-state="transitioning"`, `data-hop-tone="inactive"`, and no `.path-flow`.
    Evidence: .sisyphus/evidence/web-ui-situations/lifecycle-path-gating/task-2-transitioning-override.json

  Scenario: Non-explicit lifecycle states preserve traffic rendering
    Tool: Playwright + Bash
    Steps: Verify running runtime after start completion, then verify external/no-supervisor or mocked missing/unknown lifecycle state.
    Expected: No forced lifecycle labels; existing traffic-derived labels/tone/datasets appear; missing/unknown lifecycle does not infer stopped from offline nodes.
    Evidence: .sisyphus/evidence/web-ui-situations/lifecycle-path-gating/task-2-non-lifecycle-regression.json
  ```

  **Commit**: NO | Message: `Fix Web UI lifecycle path gating` | Files: [`web_ui/static/app.js`, `.sisyphus/evidence/web-ui-situations/lifecycle-path-gating/*`]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ webapp-testing)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Do not commit automatically.
- If the user later asks to commit, inspect `GIT_MASTER=1 git status`, `GIT_MASTER=1 git diff`, and recent log first.
- Intended implementation commit message: `Fix Web UI lifecycle path gating`.
- Intended implementation files: `web_ui/static/app.js` plus generated evidence under `.sisyphus/evidence/web-ui-situations/lifecycle-path-gating/` if evidence is tracked by project practice.

## Success Criteria
- Stopped/transitioning overview SVG paths are lifecycle-qualified and cannot look like current active signal flow.
- Historical traffic evidence is preserved in API/detail surfaces.
- Running/external/unknown/missing lifecycle cases retain existing traffic-based rendering.
- No backend, API, controller, node runtime, topology layout, or CSS redesign scope creep occurs.
- Oracle PASS criterion from planning is preserved: explicit raw `node_power.state` only, no inferred stopped state.
