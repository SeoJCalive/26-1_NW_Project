# Web UI Stale Link Freshness Overlay

## TL;DR
> **Summary**: Add a frontend-only link-endpoint freshness overlay so currently healthy-looking Web UI SVG paths stop reading as live when endpoint status updates stop, without mutating raw hop-state truth, route-inactivity meaning, or active/warn/down failures.
> **Deliverables**:
> - `web_ui/static/app.js` endpoint freshness helper and `renderPaths` precedence wiring
> - `web_ui/static/app.css` freshness-specific stale/offline overlay styles
> - Canonical docs updated to describe freshness as a separate visual axis
> - Browser/DOM evidence proving raw hop attrs stay unchanged and lifecycle/afterglow precedence holds
> **Effort**: Short
> **Parallel**: YES - 2 waves
> **Critical Path**: Task 1 → Task 2/3/4 → Task 5 → Final Verification Gate

## Context

### Original Request
User asked for a modification plan after evaluating the idea that lines not updated for several seconds should appear gray, because paths can look active after an agent/node is off.

### Interview Summary
- The desired behavior is a visual correction for misleading overview path activity, not a semantic rewrite of data-plane truth.
- Prior implementation context already includes recent-transfer afterglow and lifecycle path override.
- User required strict review for meaning distortion and collateral damage.
- Prior reviews required separate freshness attributes and conservative `unknown` handling.

### Metis Review (gaps addressed)
- **`kill_requested`**: treat as freshness-safe; it does not trigger stale/offline overlay by itself.
- **Unknown/missing endpoint**: classify as `unknown`; no overlay and no afterglow.
- **Overlay tone list**: only `ok` and `idle` may receive freshness label/gray overlay. `inactive` and `muted` already carry their own meaning and only receive freshness attrs.
- **Label precedence**: lifecycle labels first, active/warn/down labels second, existing inactive/muted labels third, freshness labels fourth for `ok`/`idle` only.
- **Verification**: add executable DOM/browser QA because existing unit tests do not cover SVG freshness attrs.

## Work Objectives

### Core Objective
Make Web UI overview SVG paths stop implying current healthy activity when endpoint status updates are stale/offline, while preserving raw `hop_state`, route-state, API payload, detail inspector traffic truth, and active/warn/down visibility.

### Deliverables
- Frontend-only link-endpoint freshness computation in `web_ui/static/app.js`.
- New SVG data attributes:
  - `data-link-freshness="fresh|stale|offline|unknown"`
  - `data-link-freshness-overlay="true|false"`
- Freshness label replacement only when overlay applies:
  - stale: `최근 상태 없음`
  - offline: `엔드포인트 오프라인`
- Freshness CSS keyed only by freshness attributes and limited to overlay-eligible `ok`/`idle` paths.
- Documentation updates in canonical Web UI behavior docs.
- Browser/DOM evidence in `.sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/`.

### Definition of Done (verifiable conditions with commands)
- `node --check web_ui/static/app.js` exits 0.
- `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py` exits 0.
- `python -m unittest discover -s tests` exits 0.
- Browser QA script verifies all required SVG data attrs, labels, and afterglow/lifecycle precedence, writing evidence under `.sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/`.
- `data-hop-state`, `data-raw-hop-tone`, `data-hop-tone`, and `data-display-hop-state` remain raw/hop-display fields, never freshness fields.

### Must Have
- No backend/API/controller changes.
- No changes to `derive_node_liveness()` or thresholds.
- No changes to detail inspector traffic truth.
- `active`, `warn`, `down`, `inactive`, and `muted` visual meanings must remain authoritative even when endpoints are stale/offline.
- Lifecycle stopped/transitioning must continue to override all paths and suppress freshness overlay/afterglow.
- Recent-transfer afterglow must only run when endpoint freshness is `fresh`.
- Unknown/missing endpoint must show `data-link-freshness="unknown"`, overlay false, afterglow false.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- MUST NOT write `stale`, `offline`, or `unknown` into `data-hop-state`, `data-hop-tone`, or `data-display-hop-state`.
- MUST NOT use `traffic.captured_at` to decide endpoint liveness/freshness.
- MUST NOT gray over `request_sent`, `request_received`, `pending`, `retrying`, `timeout`, `connection_error`, `ack_dropped`, `delivery_failed`, `rejected`, `invalid_response`, existing inactive-route, or already-muted visuals.
- MUST NOT alter `routeActive`, `marker-end`, `path-flow`, or existing inactive-route label semantics.
- MUST NOT add new backend fields, route-state semantics, or generalized state machines.
- MUST NOT redesign the SVG layout, node cards, detail inspector, or command palette.
- MUST NOT use color alone; stale/offline overlay must include explicit Korean label text when applied.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after using existing stdlib `unittest`, JS syntax check, Python compile check, and browser DOM QA.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-{N}-{slug}.{ext}`

## Execution Strategy

### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 foundation JS freshness helper and fixture plan.
Wave 2: Tasks 2-5 implementation/documentation/QA, with Task 4 and Task 5 depending on the code/CSS behavior being in place.

### Dependency Matrix (full, all tasks)
| Task | Depends On | Blocks |
| --- | --- | --- |
| 1. Add endpoint freshness helper contract | None | 2, 5 |
| 2. Wire renderPaths freshness attrs and precedence | 1 | 3, 5 |
| 3. Add freshness overlay CSS | 2 | 5 |
| 4. Update canonical docs | 2, 3 | 5 |
| 5. Add browser QA evidence and run verification | 2, 3, 4 | Final Verification Gate |

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 1 task → quick
- Wave 2 → 4 tasks → quick, visual-engineering, writing, unspecified-high
- Final Verification Gate → self-review + completed syntax/unit/browser evidence; Oracle only if implementation deviates, QA exposes ambiguity, state precedence changes, or user requests it

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Add endpoint freshness helper contract

  **What to do**: In `web_ui/static/app.js`, add a small helper near the existing path helpers: `linkEndpointFreshness(link, nodesById)`. It must read `observed_liveness` from `nodesById[link.from]` and `nodesById[link.to]` only. Return exactly `offline`, `stale`, `unknown`, or `fresh` using this precedence: offline if either endpoint is `offline`; stale if neither offline and either endpoint is `stale`; unknown if either endpoint is missing, has missing `observed_liveness`, has `unknown`, or has an unrecognized value; fresh if both endpoints are either `live` or `kill_requested`. Add any local constants needed, e.g. `FRESH_ENDPOINT_STATES`, but keep them frontend-local.
  **Must NOT do**: Do not read `traffic.captured_at`, `traffic.recent`, route summary, `reported_state`, or backend state. Do not change `derive_node_liveness()` or any Python file in this task.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: localized JS helper with deterministic logic.
  - Skills: [] - No external API or special UI design needed.
  - Omitted: [`webapp-testing`] - Browser QA happens in Task 5 after wiring exists.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2, 5] | Blocked By: []

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web_ui/static/app.js:159-180` - existing path helper style and tone lookup functions.
  - Pattern: `web_ui/static/app.js:385-413` - `adaptState()` creates nodes with `observed_liveness`.
  - API/Type: `nw_demo/controller_ui.py:109-123` - canonical `observed_liveness` values and threshold semantics.
  - API/Type: `tests/test_node_view_contracts.py:52-65` - liveness transition contract.
  - External: Oracle verdict in planning session - `unknown` gets no overlay and no afterglow; `kill_requested` counts as freshness-safe.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `linkEndpointFreshness({from:"local-agent",to:"r1"}, nodesById)` returns `fresh` for both endpoints `live`.
  - [ ] It returns `fresh` for `live` + `kill_requested`, and for `kill_requested` + `kill_requested`.
  - [ ] It returns `stale` for `live` + `stale`.
  - [ ] It returns `offline` for any endpoint `offline`, including `offline` + `stale`.
  - [ ] It returns `unknown` for missing endpoint, missing liveness, `unknown`, or unrecognized liveness.
  - [ ] If the helper is not directly executable from Node without browser setup, executor records these helper cases as Task 5 DOM fixture requirements instead of faking unit coverage.
  - [ ] `node --check web_ui/static/app.js` exits 0.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Helper classifies fresh and kill_requested endpoints
    Tool: Bash
    Steps: run `node --check web_ui/static/app.js`; record the fresh/kill_requested fixture requirement for Task 5 if no direct helper test harness exists yet.
    Expected: syntax check passes; no helper result is claimed unless actually executed through the later real browser fixture matrix.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-1-helper-fresh.json

  Scenario: Helper classifies missing/unknown endpoint conservatively
    Tool: Bash
    Steps: record the unknown-endpoint fixture requirement for Task 5 if no direct helper test harness exists yet.
    Expected: no result is claimed in Task 1 unless actually executed; Task 5 must later verify `data-link-freshness="unknown"`, `data-link-freshness-overlay="false"`, and no `data-recent-transfer="true"`.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-1-helper-unknown.json
  ```

  **Commit**: NO | Message: `N/A` | Files: [`web_ui/static/app.js`]

- [ ] 2. Wire freshness attrs, labels, and afterglow precedence in `renderPaths`

  **What to do**: In `web_ui/static/app.js` `renderPaths`, always compute `linkFreshness = linkEndpointFreshness(link, adapted.nodesById)` before recent-transfer calculation. Add `isFreshnessOverlayAllowed(tone, linkFreshness, lifecycleOverride)` or equivalent local logic: overlay only when no lifecycle override, `linkFreshness` is `stale` or `offline`, and current display `tone` is `ok` or `idle`. Set `group.dataset.linkFreshness = linkFreshness` and `group.dataset.linkFreshnessOverlay = overlay ? "true" : "false"`. Replace visible path label only when overlay applies: stale → `최근 상태 없음`; offline → `엔드포인트 오프라인`. Keep `data-hop-state`, `data-raw-hop-tone`, `data-hop-tone`, `data-display-hop-state`, `data-route-active`, `marker-end`, and `path-flow` exactly tied to existing hop/route/lifecycle semantics. Lifecycle override must suppress overlay and afterglow without falsifying `data-link-freshness`. Gate `recentTransfer` so it can be true only when no lifecycle override, `tone === "ok"`, and `linkFreshness === "fresh"`.
  **Must NOT do**: Do not set `data-hop-tone="inactive"` solely because freshness is stale/offline. Do not change labels for active/warn/down/inactive/muted. Do not set afterglow for `unknown`, `stale`, or `offline` freshness.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: localized render path precedence change.
  - Skills: [] - Existing functions and plain JS only.
  - Omitted: [`api-and-interface-design`] - No public API changes.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [3, 5] | Blocked By: [1]

  **References**:
  - Pattern: `web_ui/static/app.js:483-510` - current `renderPaths()` data attr and title creation.
  - Pattern: `web_ui/static/app.js:203-206` - current route-aware inactive projection.
  - Pattern: `web_ui/static/app.js:208-234` - recent-transfer afterglow helper; keep capture timestamp usage limited to afterglow.
  - Pattern: `web_ui/static/app.js:236-259` - lifecycle stopped/transitioning override.
  - Pattern: `web_ui/static/app.js:269-285` - existing hop-state label mapping that active/warn/down must keep.
  - Guardrail: `docs/reference/ui-preview/WEB_UI_SPEC.md:161-223` - state axes separation and data path hop-state contract.

  **Acceptance Criteria**:
  - [ ] For neutral `acknowledged/ok` with stale endpoint, SVG group has `data-hop-state="acknowledged"`, `data-hop-tone="ok"`, `data-link-freshness="stale"`, `data-link-freshness-overlay="true"`, and label `최근 상태 없음`.
  - [ ] For neutral `acknowledged/ok` with offline endpoint, SVG group has raw hop attrs unchanged, `data-link-freshness="offline"`, overlay true, and label `엔드포인트 오프라인`.
  - [ ] For `request_sent`/`active`, `retrying`/`warn`, and `timeout`/`down` with stale/offline endpoint, `data-hop-tone` remains `active`/`warn`/`down`, overlay false, and original label remains.
  - [ ] For inactive-route or muted link with stale/offline endpoint, freshness attr is present but `data-link-freshness-overlay="false"` and existing inactive/muted label remains.
  - [ ] For unknown endpoint, `data-link-freshness="unknown"`, overlay false, no afterglow.
  - [ ] For lifecycle stopped/transitioning, existing `전원 꺼짐` / `전원 전환 중` label and inactive behavior remains; actual endpoint `data-link-freshness` is still reported; freshness overlay false; afterglow false.
  - [ ] `node --check web_ui/static/app.js` exits 0.

  **QA Scenarios**:
  ```
  Scenario: Stale neutral link gets explicit freshness overlay without raw mutation
    Tool: Playwright
    Steps: load controlled `/api/state` fixture with `local-agent -> r1` raw `acknowledged`, both route-active, local-agent live, r1 stale; inspect `g[data-link-id="agent-r1"]` and label text.
    Expected: raw attrs remain `data-hop-state="acknowledged"`, `data-hop-tone="ok"`; freshness attrs are `stale`/`true`; label text is `최근 상태 없음`.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-2-stale-neutral.json

  Scenario: Failure/active tones are not hidden by freshness
    Tool: Playwright
    Steps: load fixtures for `request_sent`, `retrying`, `timeout`, inactive route, and muted link on stale/offline endpoints; inspect corresponding SVG groups and labels.
    Expected: `data-hop-tone` remains `active`, `warn`, `down`, `inactive`, or `muted`; `data-link-freshness-overlay="false"`; labels remain transfer/retry/timeout/inactive/muted labels.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-2-authoritative-tones.json
  ```

  **Commit**: NO | Message: `N/A` | Files: [`web_ui/static/app.js`]

- [ ] 3. Add freshness-specific stale/offline CSS overlay

  **What to do**: In `web_ui/static/app.css`, add styles keyed only by `[data-link-freshness-overlay="true"][data-link-freshness="stale"]` and `[data-link-freshness-overlay="true"][data-link-freshness="offline"]`. Stale should visually read as muted gray but less severe than offline. Offline should use stronger inactive gray. Apply styles to `.path-halo`, `.path-line`, `.path-status-label rect`, and `.path-status-label text`. Do not alter existing `[data-hop-tone="active"]`, `[data-hop-tone="warn"]`, `[data-hop-tone="down"]`, `[data-hop-tone="inactive"]`, `[data-hop-tone="muted"]`, or `[data-recent-transfer="true"]` selectors except if necessary to ensure freshness overlay selectors only apply when overlay true.
  **Must NOT do**: Do not replace existing hop tone selectors. Do not use global selectors that accidentally gray all active/warn/down paths. Do not remove recent-transfer animations.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: CSS state layering and visual contrast.
  - Skills: [] - Plain CSS; no browser interaction skill required in implementation task.
  - Omitted: [`frontend-ui-ux`] - The visual system is already defined; this is constrained styling, not redesign.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [5] | Blocked By: [2]

  **References**:
  - Pattern: `web_ui/static/app.css:279-323` - current path tone CSS.
  - Pattern: `web_ui/static/app.css:325-378` - current path label CSS by tone.
  - Pattern: `web_ui/static/app.css:285-293` - recent-transfer afterglow animation selectors.
  - Visual Contract: `docs/reference/ui-preview/WEB_UI_SPEC.md:161-168` - color plus text/icon, not color alone.

  **Acceptance Criteria**:
  - [ ] Stale overlay has separate selector from hop tone and makes `ok`/`idle` line gray without changing DOM hop attrs.
  - [ ] Offline overlay is visually distinct from stale and reads more inactive/severe.
  - [ ] Existing active/warn/down/inactive/muted CSS remains unchanged in behavior when overlay false.
  - [ ] Recent-transfer CSS still works when `data-recent-transfer="true"` and freshness is fresh.

  **QA Scenarios**:
  ```
  Scenario: Stale and offline neutral links are visually gray and labeled
    Tool: Playwright
    Steps: load controlled stale and offline fixtures; take screenshots; inspect computed stroke colors for `.path-line` and label text.
    Expected: stale/offline fixtures show gray/slate styling and explicit labels; no green/cyan afterglow on stale/offline.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-3-stale-offline-visual.png

  Scenario: Active/warn/down/inactive/muted retain visual authority
    Tool: Playwright
    Steps: load stale endpoint fixtures with active/warn/down/inactive/muted display tones; take screenshots and inspect computed styles.
    Expected: active is blue, warn is orange, down is red, inactive/muted keep existing muted semantics; no stale/offline gray overlay selector applies.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-3-authoritative-tones.png
  ```

  **Commit**: NO | Message: `N/A` | Files: [`web_ui/static/app.css`]

- [ ] 4. Update canonical Web UI behavior docs

  **What to do**: Update `IMPLEMENTATION_SPEC.md` and `AI_IMPLEMENTATION_BRIEF.md` after the implementation is in place. In `IMPLEMENTATION_SPEC.md` Web UI section, add one concise bullet stating that overview SVG paths may add a frontend-only link-endpoint freshness overlay derived from existing endpoint `observed_liveness`, but it never creates a new API field, mutates `data-hop-state`, changes API payload, changes detail inspector traffic truth, or hides active/warn/down/inactive/muted hop/route visuals. In `AI_IMPLEMENTATION_BRIEF.md`, add only a short recent-decision handoff bullet summarizing the freshness overlay behavior and evidence location. If `docs/reference/ui-preview/WEB_UI_SPEC.md` needs a runtime visual contract update, add a small subsection under Traffic/state expression documenting `data-link-freshness` and overlay precedence.
  **Must NOT do**: Do not create new root markdown files. Do not duplicate long implementation details into `AI_IMPLEMENTATION_BRIEF.md`. Do not change unrelated UI scope or historical docs.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: concise canonical documentation updates.
  - Skills: [] - No specialized docs skill available.
  - Omitted: [`api-and-interface-design`] - Documents behavior only; no interface design beyond DOM attrs already planned.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [5] | Blocked By: [2, 3]

  **References**:
  - Pattern: `IMPLEMENTATION_SPEC.md:149-160` - Web UI behavior bullets including lifecycle override and recent-transfer afterglow.
  - Pattern: `AI_IMPLEMENTATION_BRIEF.md:78-79` - recent lifecycle/afterglow decisions.
  - Pattern: `docs/reference/ui-preview/WEB_UI_SPEC.md:161-223` - state axes and traffic rendering contract.
  - Governance: `AGENTS.md` - no new root markdown beyond allowed files; `AI_IMPLEMENTATION_BRIEF.md` is living context.

  **Acceptance Criteria**:
  - [ ] Docs explicitly say freshness overlay is display-only and separate from `hop_state`.
  - [ ] Docs explicitly say active/warn/down/inactive/muted are not hidden by stale/offline freshness.
  - [ ] Docs mention lifecycle stopped/transitioning remains higher priority.
  - [ ] No new root-level `.md` files are created.

  **QA Scenarios**:
  ```
  Scenario: Canonical docs describe the final behavior without scope creep
    Tool: Bash
    Steps: run `GIT_MASTER=1 git diff -- IMPLEMENTATION_SPEC.md AI_IMPLEMENTATION_BRIEF.md docs/reference/ui-preview/WEB_UI_SPEC.md` and inspect only relevant sections.
    Expected: diff contains concise freshness-overlay behavior and no unrelated rewrites.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-4-doc-diff.txt

  Scenario: Root markdown governance is preserved
    Tool: Bash
    Steps: run `GIT_MASTER=1 git status --short` and inspect file paths.
    Expected: no new root markdown files outside allowed list; docs changes limited to existing canonical/reference docs.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-4-root-md-governance.txt
  ```

  **Commit**: NO | Message: `N/A` | Files: [`IMPLEMENTATION_SPEC.md`, `AI_IMPLEMENTATION_BRIEF.md`, `docs/reference/ui-preview/WEB_UI_SPEC.md` if needed]

- [ ] 5. Add browser QA evidence and run full verification

  **What to do**: Create a temporary or evidence-local browser QA harness that loads the real Web UI app bundle and serves or intercepts only controlled `/api/state` payloads. Assert rendered SVG DOM state and computed CSS in a real browser. It must cover fresh, stale, offline, unknown, kill_requested, active/warn/down preservation, inactive/muted preservation, recent-transfer gating, and lifecycle stopped/transitioning. Store a compact matrix JSON, targeted screenshots, and command logs under `.sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/`. Run final commands: `node --check web_ui/static/app.js`, `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py`, and `python -m unittest discover -s tests`.
  **Must NOT do**: Do not rely on manual visual inspection as the only pass condition. Do not use jsdom-only tests, direct helper invocation, or DOM mutation setup that bypasses `renderPaths` as the primary QA. Do not store full DOM/API dumps for every subcase. Do not skip lifecycle or unknown cases. Do not leave long-lived QA servers/ports running.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: hands-on browser QA, fixtures, evidence capture, cleanup.
  - Skills: [`webapp-testing`] - Browser automation and screenshot/DOM verification.
  - Omitted: [] - Browser verification is central to the task.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [Final Verification Gate] | Blocked By: [2, 3, 4]

  **References**:
  - Pattern: `.sisyphus/evidence/web-ui-situations/` - existing evidence location convention.
  - Pattern: `web_ui/static/app.js:483-527` - SVG groups and labels to assert.
  - Pattern: `web_ui/static/app.css:279-378` - path visual selectors to verify.
  - Test: `tests/test_node_view_contracts.py` - existing liveness threshold contracts must continue passing.
  - Test: `tests/test_hop_state_visibility.py` - hop state preservation must continue passing.

  **Acceptance Criteria**:
  - [ ] Evidence directory exists: `.sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/`.
  - [ ] QA asserts stale neutral raw attrs unchanged + overlay true + label `최근 상태 없음`.
  - [ ] QA asserts offline neutral raw attrs unchanged + overlay true + label `엔드포인트 오프라인`.
  - [ ] QA asserts active/warn/down/inactive/muted raw visuals remain authoritative with overlay false.
  - [ ] QA asserts `kill_requested` freshness is fresh and can still allow qualifying afterglow.
  - [ ] QA asserts unknown freshness has overlay false and afterglow false.
  - [ ] QA asserts lifecycle stopped/transitioning suppresses overlay and afterglow.
  - [ ] `node --check web_ui/static/app.js` exits 0.
  - [ ] `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py` exits 0.
  - [ ] `python -m unittest discover -s tests` exits 0.
  - [ ] QA ports/processes are cleaned up and recorded.

  **QA Scenarios**:
  ```
  Scenario: Full DOM fixture matrix passes
    Tool: Playwright
    Steps: run the QA harness against controlled fixtures for fresh, stale, offline, unknown, kill_requested, active, warn, down, inactive route, muted, lifecycle stopped with stale/offline endpoints, and lifecycle transitioning with stale/offline endpoints.
    Expected: all DOM assertions pass and evidence JSON summarizes each fixture with expected attrs/labels.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-5-fixture-matrix.json

  Scenario: Repository verification remains green
    Tool: Bash
    Steps: run `node --check web_ui/static/app.js`; run `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py`; run `python -m unittest discover -s tests`.
    Expected: all commands exit 0; output saved to evidence text file.
    Evidence: .sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/task-5-verification.txt
  ```

  **Commit**: NO | Message: `N/A` | Files: [`.sisyphus/evidence/web-ui-situations/stale-link-freshness-overlay/*`, temporary QA script only if intentionally kept under evidence]

## Final Verification Gate
> This is a narrow frontend-only change. Do not add a mandatory multi-agent review wave unless implementation deviates from this plan, QA exposes ambiguity, or the state precedence rules change.
- [ ] Run final self-review against the user's motive: stop stale successful paths from looking currently active without changing raw truth.
- [ ] Confirm syntax/unit/browser fixture QA evidence is complete.
- [ ] Consult Oracle again only if implementation deviates from the plan, QA exposes ambiguity, state precedence changes, or the user explicitly asks for another review.

## Commit Strategy
- Do not commit automatically. User has not requested a commit.
- Before any user-requested commit, run:
  - `GIT_MASTER=1 git status --short`
  - `GIT_MASTER=1 git diff --stat`
  - `GIT_MASTER=1 git diff`
- Commit only intended files and evidence after user approval.
- Suggested commit message if requested later: `Web UI stale path freshness overlay 추가`

## Success Criteria
- Stale/offline endpoint status no longer leaves neutral successful paths looking freshly healthy.
- Raw hop-state and traffic truth remain intact in API/detail/DOM raw attrs.
- Active/warn/down route problems and existing inactive/muted meanings are never hidden by gray freshness styling.
- Recent-transfer afterglow still works for fresh links but never appears for stale/offline/unknown links.
- Lifecycle stopped/transitioning behavior remains unchanged and highest priority.
- All automated verification passes, and any conditional review required by the final verification gate is complete.
