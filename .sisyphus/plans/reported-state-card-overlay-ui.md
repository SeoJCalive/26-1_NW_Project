# Reported State Card Overlay UI

## TL;DR
> **Summary**: Update the existing static node-first Web UI preview so `reported_state` is visibly treated as a status axis, node-card visible values use consistent key/value boxes, and the detail inspector overlays the structure diagram without resizing it.
> **Deliverables**:
> - `reported_state` status badge/row UI, separate from `observed_liveness`
> - boxed left-label/right-value node-card rows
> - non-resizing animated detail overlay above the diagram
> - updated static/browser evidence checks
> **Effort**: Short
> **Parallel**: YES - 2 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 4 → Final Verification Wave

## Context

### Original Request
- User asked for an implementation plan after feedback:
  - Make `reported_state` a recognizable status UI element.
  - Change node-card visible values to a clean, consistent boxed layout with labels on the left and values on the right.
  - Move the detail section above the structure diagram as an overlay that does not shrink or push the diagram.
  - Animate detail open and close smoothly.

### Interview Summary
- The user asked for metaphors to be removed from the explanation and the requirements restated in clean implementation language.
- No additional user decision is required; defaults below are applied to make the plan executable.

### Metis Review (gaps addressed)
- Overlay placement defaulted to top-right inside the diagram host on desktop, with responsive inset overlay on smaller viewports.
- Interaction defaulted to explicit close button only; no outside-click or ESC behavior is added.
- Animation defaulted to a deterministic mounted/open/closing state with data attributes and transition duration so QA can verify it without subjective visual judgment.
- Static QA is mandatory. Browser QA must first try existing URL `http://10.192.20.70:8088/preview.revised.html`; if unreachable, launch a temporary local static server from `docs/reference/ui-preview/` and use its `preview.revised.html` URL. The URL must never be hardcoded into source UI code.

## Work Objectives

### Core Objective
Improve the static preview UI clarity without changing runtime behavior, node data, graph topology, or state-axis semantics.

### Deliverables
- `docs/reference/ui-preview/preview.revised.jsx` updated only for static preview UI and embedded sanity checks.
- `.sisyphus/evidence/node_first_preview.spec.py` and/or `.sisyphus/evidence/node_first_preview.spec.js` updated only if required to verify the new DOM/layout contract.
- Evidence files written under `.sisyphus/evidence/`.

### Definition of Done (verifiable conditions with commands)
- `python .sisyphus/evidence/node_first_preview.spec.py` exits `0` and reports PASS for static/DOM contract checks.
- Browser QA exits `0` and captures DOM/screenshot evidence by using the existing preview URL or a temporary local static server launched from `docs/reference/ui-preview/`.
- Source contains no new graph nodes beyond `host-simulator`, `local-agent`, `r1`, `r2`, `monitor`.
- Source contains no synthetic narrative fields/sections: `note`, `reason`, `activityLogs`, `비고`, `설명`.

### Must Have
- `reported_state` remains a separate axis from `observed_liveness`.
- `observed_liveness` continues to control liveness lamp color only.
- `reported_state` gets its own component/test ids/data attributes, e.g. `reported-state-{node.id}` and `data-reported-state-tone`.
- Node-card visible values use boxed rows with label left and value right.
- Detail inspector overlays the diagram and does not change top-level grid columns or diagram dimensions on node selection.
- Open and close transitions expose deterministic DOM signals, e.g. `data-detail-state="open|closing|closed"` or equivalent class/data attribute.

### Must NOT Have
- No production Web UI/API/WebSocket/gateway/package setup.
- No Python runtime, TUI, message contract, or data-plane behavior changes.
- No Controller/UI, Reporting Hub, Control Hub, or Management Node graph node.
- No merging of `observed_liveness`, `reported_state`, `activity`, or `traffic` into a generic health/status field.
- No human-only acceptance criteria such as “visually confirm smooth animation.”
- Do not rename existing `data-testid` hooks unless QA scripts are updated in the same task.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + existing static/browser preview scripts in `.sisyphus/evidence/`
- QA policy: Every task has agent-executed scenarios
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`
- LSP note: current environment’s `typescript-language-server` exits with `Unexpected token '?'`; do not block implementation on LSP diagnostics unless the environment is fixed.

## Execution Strategy

### Parallel Execution Waves
> Target: 5-8 tasks per wave. This plan is intentionally small; Wave 1 creates shared UI foundations, Wave 2 verifies them.

Wave 1: Task 1, Task 2, Task 3 sequential within one file because they touch overlapping React layout.
Wave 2: Task 4 QA/evidence update after UI changes.

### Dependency Matrix (full, all tasks)
- Task 1 blocks Task 2 because node-card rows should reuse the status/value components.
- Task 2 blocks Task 3 only where overlay header/card semantics need consistent test ids.
- Task 3 blocks Task 4 because QA must validate final layout/animation behavior.
- Task 4 blocks Final Verification Wave.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 3 tasks → `visual-engineering`
- Wave 2 → 1 task → `quick`
- Final → 4 review tasks → `oracle`, `unspecified-high`, `deep`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Add reported-state status component and boxed value-row foundation

  **What to do**:
  - In `docs/reference/ui-preview/preview.revised.jsx`, add a dedicated `reportedStateTone(reportedState)` helper near `livenessLampTone`.
  - Add a `ReportedStateBadge({ value, nodeId, compact = false })` component separate from `LivenessLamp`.
  - Map current sample value `"실행 중"` to a distinct reported-state tone such as `running` with blue/cyan styling. Unknown/unmapped values must fall back to `unknown` neutral styling.
  - Do not make `ReportedStateBadge` call `livenessLampTone`; the two axes must remain independent.
  - Add a reusable `NodeInfoRow({ label, value, testId, children })` or equivalent that renders one boxed row with label left and value right.
  - Preserve `reported-state-{node.id}` as the test id for the reported-state UI.
  - Add data attributes that QA can check, e.g. `data-reported-state-tone="running"`.

  **Must NOT do**:
  - Do not rename or remove `LivenessLamp` semantics.
  - Do not add a generic `health`/`status` axis that combines liveness and reported state.
  - Do not add new reported state values to `revisedNodes` unless they already exist in the static sample.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: UI component refactor with visual semantics.
  - Skills: [`frontend-ui-ux`] - Useful for clean status/value presentation.
  - Omitted: [`playwright`] - Browser automation is not needed until QA scenarios execute.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2, 4] | Blocked By: []

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:531` - `livenessLampTone` must remain observed-liveness only.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:535` - `LivenessLamp` component style/test-id pattern.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:613` - `KeyValueRows` left/right detail row pattern to adapt for compact node-card rows.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:775` - current `reported-state-{node.id}` test id to preserve.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Static source check confirms `ReportedStateBadge` or equivalent exists and does not call `livenessLampTone`.
  - [ ] Static source check confirms `reported-state-host-simulator` can render with `data-reported-state-tone="running"` or equivalent deterministic reported-state tone.
  - [ ] `runSanityChecks()` asserts `observed_liveness` and `reported_state` remain separate fields on every node.

  **QA Scenarios**:
  ```
  Scenario: reported_state renders as separate status UI
    Tool: Bash
    Steps: Run `python .sisyphus/evidence/node_first_preview.spec.py` after updating the script to assert reported-state component/test-id/data-tone presence.
    Expected: Command exits 0 and writes PASS output proving reported_state is separate from liveness.
    Evidence: .sisyphus/evidence/task-1-reported-state-static-check.txt

  Scenario: reported_state does not control liveness lamp
    Tool: Bash
    Steps: Static script checks the r2 sample where `observed_liveness` is non-live while `reported_state` is `실행 중`.
    Expected: r2 liveness remains gray/non-live, and reported-state tone remains running/status-like.
    Evidence: .sisyphus/evidence/task-1-reported-state-axis-check.txt
  ```

  **Commit**: NO | Message: `ui(preview): separate reported state status styling` | Files: [`docs/reference/ui-preview/preview.revised.jsx`, `.sisyphus/evidence/*`]

- [ ] 2. Normalize node-card visible values into boxed key/value rows

  **What to do**:
  - Refactor `NodeCard` so visible values after the title use consistent boxed rows.
  - Required rows: `node_id`, `role`, `observed_liveness`, `reported_state`, and up to four existing activity chip values converted into row form.
  - Left side must be the label; right side must be the value or embedded status component.
  - Preserve existing test ids where possible:
    - `node-card-{node.id}`
    - `node-role-{node.id}`
    - `liveness-lamp-{node.id}`
    - `reported-state-{node.id}`
    - `activity-chip-{node.id}-{key}` may remain as compatibility aliases on the activity rows, or update QA scripts in the same task if renamed.
  - Keep cards within the existing absolute node positions and do not change `nodeOrder`, `position`, or `mainLinks`.

  **Must NOT do**:
  - Do not remove the liveness lamp.
  - Do not move role/reported state only into the detail panel; they must remain visible on the card.
  - Do not add narrative text or explanatory prose fields.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: node-card layout and interaction clarity.
  - Skills: [`frontend-ui-ux`] - Helpful for consistent card hierarchy.
  - Omitted: [`ai-slop-remover`] - Single small refactor can be reviewed after implementation.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [3, 4] | Blocked By: [1]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:568` - `activityChips(node)` data source for card activity rows.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:758` - current `NodeCard` implementation.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:764` - existing `node-card-{node.id}` test id.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:774` - existing `node-role-{node.id}` test id.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Static/DOM check confirms every node card contains boxed rows for node id, role, observed liveness, reported state, and activity summary.
  - [ ] DOM check confirms row labels are in left-side elements and row values are in right-side elements using deterministic selectors/classes/data attributes.
  - [ ] No forbidden narrative fields or TUI literal fragments are introduced.

  **QA Scenarios**:
  ```
  Scenario: node cards use consistent key/value row layout
    Tool: Bash
    Steps: Run `python .sisyphus/evidence/node_first_preview.spec.py` and inspect generated DOM assertions for `node-info-row-*` or equivalent selectors.
    Expected: All five `node-card-*` elements contain the required row set with left label/right value selectors.
    Evidence: .sisyphus/evidence/task-2-node-card-static-check.txt

  Scenario: card refactor preserves graph contract
    Tool: Bash
    Steps: Static script checks `nodeOrder`, `mainLinks`, and absence of forbidden graph node labels.
    Expected: Exactly five data-plane nodes and four data path links remain.
    Evidence: .sisyphus/evidence/task-2-node-card-graph-guard.txt
  ```

  **Commit**: NO | Message: `ui(preview): normalize node card visible values` | Files: [`docs/reference/ui-preview/preview.revised.jsx`, `.sisyphus/evidence/*`]

- [ ] 3. Convert detail inspector into non-resizing animated diagram overlay

  **What to do**:
  - Remove the selected-node top-level grid reflow in `NetworkDemoWebUIRevised`; selection must not switch the layout to a two-column grid.
  - Make the diagram area the overlay host, either by passing `selectedNode` and `onClose` into `DiagramCanvas` or by wrapping `DiagramCanvas` and `DetailInspector` in a `relative` container that preserves diagram size.
  - Render `DetailInspector` with absolute/fixed overlay positioning above the diagram:
    - Desktop default: top-right overlay, width approximately `33vw`, min `360px`, max `520px`, max-height within viewport/diagram area.
    - Small viewport default: inset overlay (`left/right/top` spacing) over the diagram; do not push diagram down.
  - Add deterministic test ids/data attributes:
    - Keep `node-detail-inspector`.
    - Add `detail-inspector-overlay` or `data-overlay="diagram"`.
    - Add `data-detail-state="open|closing"` for animation verification.
  - Implement close animation by keeping the selected node mounted during a short closing state, then clearing selection after transition duration, e.g. 200-250ms.
  - Keep explicit `X` close button with `detail-close-button`; do not add outside-click/ESC unless already trivial and fully tested.

  **Must NOT do**:
  - Do not reduce `diagramWidth`, `diagramHeight`, node positions, or path geometry to make room for the overlay.
  - Do not introduce a general modal framework, routing, portal dependency, package setup, or production UI scaffold.
  - Do not make the detail panel open by default.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: overlay positioning and animation behavior.
  - Skills: [`frontend-ui-ux`] - Helpful for smooth motion and non-invasive overlay layout.
  - Omitted: [`git-master`] - No commit requested.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [4] | Blocked By: [2]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:789` - current `DiagramCanvas` and fixed-size diagram host.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:848` - `DetailHeader` close button and header test ids.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:930` - current `DetailInspector` separate-column width.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:971` - current selected-node grid reflow to remove.

  **Acceptance Criteria** (agent-executable only):
  - [ ] DOM/source check confirms selected-node state no longer changes the top-level grid column template.
  - [ ] Browser check records diagram bounding box before node selection and after node selection; width/height remain unchanged within 2px tolerance.
  - [ ] Browser check clicks a node, sees `node-detail-inspector` as overlay, clicks `detail-close-button`, observes `data-detail-state="closing"` or equivalent before unmount/closed state.
  - [ ] Detail inspector is closed on initial page load.

  **QA Scenarios**:
  ```
  Scenario: detail overlay opens without resizing diagram
    Tool: Playwright
    Steps: Navigate to preview URL; record structure diagram container bounding box; click `[data-testid="node-card-r1"]`; record bounding box again.
    Expected: Width and height differ by no more than 2px; `[data-testid="node-detail-inspector"]` is visible with overlay marker.
    Evidence: .sisyphus/evidence/task-3-detail-overlay-browser-check.txt

  Scenario: close animation is detectable
    Tool: Playwright
    Steps: Click `[data-testid="node-card-r1"]`; click `[data-testid="detail-close-button"]`; immediately check detail state attribute/class; wait transition duration; check inspector is hidden/unmounted.
    Expected: Intermediate closing state is present, then panel closes without diagram resize.
    Evidence: .sisyphus/evidence/task-3-detail-overlay-close-check.txt
  ```

  **Commit**: NO | Message: `ui(preview): overlay animated node detail inspector` | Files: [`docs/reference/ui-preview/preview.revised.jsx`, `.sisyphus/evidence/*`]

- [ ] 4. Update preview QA scripts and evidence for the new DOM/layout contract

  **What to do**:
  - Update `.sisyphus/evidence/node_first_preview.spec.py` and/or `.sisyphus/evidence/node_first_preview.spec.js` only as needed to validate the new preview contract.
  - Required static assertions:
    - five allowed node ids only
    - no forbidden graph nodes
    - no forbidden narrative fields/strings
    - `reported_state` and `observed_liveness` rendered through separate test ids/components/data attributes
    - boxed node-card row selectors exist for all five nodes
    - detail inspector overlay selector/data attribute exists
    - selected-node grid reflow has been removed
  - Required browser setup:
    - Try `http://10.192.20.70:8088/preview.revised.html` first because it appears in existing evidence.
    - If it is unreachable, launch a temporary local Python static server from `docs/reference/ui-preview/` and use `http://127.0.0.1:<chosen-port>/preview.revised.html`.
    - Record the actual URL used in `.sisyphus/evidence/task-4-reported-card-overlay-browser-check.txt`.
  - Required browser assertions:
    - initial detail inspector closed
    - click node opens overlay
    - diagram bounding box does not shrink/reflow
    - close button triggers closing state and final closed state
  - Write fresh evidence files:
    - `.sisyphus/evidence/task-4-reported-card-overlay-static-check.txt`
    - `.sisyphus/evidence/task-4-reported-card-overlay-browser-check.txt`
    - `.sisyphus/evidence/task-4-reported-card-overlay-dom.html`
    - `.sisyphus/evidence/task-4-reported-card-overlay-preview.png`

  **Must NOT do**:
  - Do not hardcode the environment URL into source UI code.
  - Do not treat Tailwind/Babel dev warnings or favicon 404 as failures unless they break the preview contract.
  - Do not require manual visual inspection as acceptance.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: targeted QA/evidence update after UI changes.
  - Skills: [`playwright`] - Required if browser QA is executed.
  - Omitted: [`frontend-ui-ux`] - Visual design work should already be complete.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [Final Verification Wave] | Blocked By: [1, 2, 3]

  **References**:
  - Test: `.sisyphus/evidence/node_first_preview.spec.py` - existing Python preview QA script.
  - Test: `.sisyphus/evidence/node_first_preview.spec.js` - existing JS/browser preview QA script.
  - Evidence: `.sisyphus/evidence/task-6-node-first-static-check.txt` - prior static PASS pattern.
  - Evidence: `.sisyphus/evidence/task-6-node-first-browser-check.txt` - prior browser PASS pattern.
  - External/runtime: `http://10.192.20.70:8088/preview.revised.html` - observed existing preview URL, use as environment precondition only.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python .sisyphus/evidence/node_first_preview.spec.py` exits `0`.
  - [ ] Browser QA exits `0` using either the existing preview URL or a temporary local static server; the evidence records the actual URL used.
  - [ ] New evidence files exist under `.sisyphus/evidence/` with PASS status; if browser automation tooling itself is unavailable, record that as a tooling failure note while keeping the static contract PASS evidence separate.

  **QA Scenarios**:
  ```
  Scenario: static preview contract passes
    Tool: Bash
    Steps: Run `python .sisyphus/evidence/node_first_preview.spec.py` from repository root.
    Expected: Exit 0; output includes PASS for reported-state status UI, boxed rows, overlay selector, and forbidden string guard.
    Evidence: .sisyphus/evidence/task-4-reported-card-overlay-static-check.txt

  Scenario: browser preview contract passes with deterministic server fallback
    Tool: Playwright
    Steps: Try `http://10.192.20.70:8088/preview.revised.html`; if unreachable, start a temporary local static server from `docs/reference/ui-preview/`; execute node click/open/close/bounding-box checks; capture DOM and screenshot.
    Expected: Exit 0; detail overlay opens/closes with deterministic state and diagram size stays stable.
    Evidence: .sisyphus/evidence/task-4-reported-card-overlay-browser-check.txt
  ```

  **Commit**: NO | Message: `test(preview): verify reported state overlay card contract` | Files: [`.sisyphus/evidence/node_first_preview.spec.py`, `.sisyphus/evidence/node_first_preview.spec.js`, `.sisyphus/evidence/task-4-*`]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright if UI)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Do not commit unless the user explicitly requests it.
- If a commit is later requested, include only:
  - `docs/reference/ui-preview/preview.revised.jsx`
  - updated `.sisyphus/evidence/node_first_preview.spec.*` if changed
  - generated `.sisyphus/evidence/task-4-*` evidence if user wants evidence committed

## Success Criteria
- `reported_state` is visually status-like but not semantically merged with `observed_liveness`.
- Node-card immediate values are clean boxed key/value rows across all five nodes.
- The detail inspector overlays the diagram with deterministic open/close animation.
- Selecting a node does not change diagram dimensions or top-level grid columns.
- Static and browser QA evidence verifies the behavior without human inspection.
