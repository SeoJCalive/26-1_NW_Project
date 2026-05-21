# Node-first UI State Revision

## TL;DR
> **Summary**: Revise the static Web UI preview so it becomes a node-first dashboard with separated liveness, reported runtime state, and node-specific processing/communication activity. Remove fabricated narrative UI and replace the fixed detail area with a click-open, X-close inspector around one third of the desktop viewport.
> **Deliverables**:
> - Updated `docs/reference/ui-preview/preview.revised.jsx` with contract-backed node data, shared liveness lamps, node cards with pre-selection activity, and role-specific detail renderers.
> - Updated `runSanityChecks()` and browser/DOM evidence proving state separation, no fabricated prose, and click-open detail behavior.
> - Optional context update in `AI_IMPLEMENTATION_BRIEF.md` only if implementation state changes need handoff documentation.
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 → Task 2 → Task 4 → Task 6

## Context
### Original Request
- User requested a modification plan after confirming: `처리 상태` and node/process activation state are different and must be separated.
- User emphasized the remaining feedback is equally important: pre-selection card activity, shared liveness lamp, per-node details, removal of unsupported prose, and click-open 1/3 detail panel.

### Interview Summary
- `observed_liveness` is the only source for the common lamp: green = recently seen/live, gray = off/unobserved.
- `reported_state` comes from `STATUS.state` and must stay separate from the liveness lamp.
- Processing/communication activity comes from node-specific fields such as `hop_state`, `pending_ack_state`, `latest_input_result`, `downstream_result`, `last_sink_result`, and `last_ack_result`.
- Host, Agent, R1, R2, and Monitor details must not be forced into a generic common template.
- Common detail fields are limited to liveness lamp, node id, and role.
- `비고`, `설명`, synthetic `note`, synthetic `reason`, and AI-created narrative logs must be removed unless directly backed by a documented runtime field.

### Metis Review (gaps addressed)
- Added explicit file allowlist and runtime/API/package mutation ban.
- Added guardrails for contradictory states, missing optional runtime fields, and renamed narrative filler.
- Added browser acceptance criteria for opening, closing, width, role-specific details, and no always-visible fixed detail area.
- Added sanity-check requirements for source/rendered assertions covering state separation and fabricated prose bans.

## Work Objectives
### Core Objective
Make `preview.revised.jsx` a contract-backed node-first static reference preview where users can understand each node before selection, inspect real role-specific details after selection, and never confuse liveness, reported state, and processing/communication activity.

### Deliverables
- Contract-backed preview data shape replacing narrative fields with explicit liveness/state/activity fields.
- Reusable liveness lamp component used in node cards, detail header, and legend.
- Node card layout showing node id/role/lamp plus at least one role-specific activity summary before selection.
- Click-open detail inspector that is closed by default, opens only after node click, closes with X, and uses desktop width approximately `33vw` or equivalent one-third column.
- Role-specific detail renderers for Host, Agent, Relay, and Monitor. R1 and R2 may share the Relay renderer because they share the relay contract.
- Updated static sanity checks and QA evidence.

### Per-node Display Contract (code/doc-backed only)
Use these exact content groups when building node cards and detail inspectors. The executor must not add explanatory prose outside these groups.

#### Common content for every node
- Card and detail header:
  - `node_id`
  - `role`
  - `observed_liveness` shown as the shared lamp only: green for `live`, gray for every non-`live` value.
  - `reported_state` shown as node-reported runtime state, separate from the lamp.
  - `last_seen` / freshness only if the data object already carries it; otherwise omit or show `—` with no explanation.
- Traffic section, when present:
  - `traffic.capture_seq`
  - `traffic.captured_at`
  - `traffic.previous_peer.peer_node_id`, `peer_role`, `hop_state`, `failure_reason`, `last_received`, `last_sent`
  - `traffic.next_peer.peer_node_id`, `peer_role`, `hop_state`, `failure_reason`, `last_received`, `last_sent`
  - `traffic.recent[]` rows: `direction`, `flow`, `peer_node_id`, `peer_role`, `hop_state`, `failure_reason`, `capture.logical_id`, `capture.attempt_no`, `capture.phase`, `capture.captured_at`, `capture.truncated`, `capture.original_size`, `capture.preview`
  - For capture payload, show a compact JSON preview only when already present in the static data; do not synthesize a natural-language interpretation.

#### Host Simulator detail content
- Card activity chips:
  - `host_state.service_state`
  - `host_state.latency_state` + `host_state.latency_ms`
  - `host_state.fault_mode`
- Detail inspector sections:
  - Host metrics: `host_state.host_id`, `cpu_usage`, `memory_usage`, `service_state`, `latency_state`, `latency_ms`, `fault_mode`, `last_update_time`.
  - Runtime tick/fault: `detail.tick`, `detail.fault_active`, `detail.fault_type`.
  - Host-agent communication: `detail.traffic.previous_peer` showing Local Agent request/response facts, including `hop_state` values such as `request_received` and `acknowledged` when represented by the static sample.
- Source references: `nw_demo/host_simulator.py:61`, `nw_demo/host_simulator.py:104`, `nw_demo/host_simulator.py:78`.

#### Local Agent detail content
- Card activity chips:
  - `latest_input_result.status`
  - `detected_fault`
  - `downstream_result.status`
  - emitted event summary from `emitted_event.event_type` + `emitted_event.severity` when present.
- Detail inspector sections:
  - Host input: `latest_input_state` and `latest_input_result` as structured key/value data.
  - Fault detection: `detected_fault`.
  - Emitted event: `emitted_event.msg_type`, `event_id`, `seq_no`, `host_id`, `agent_id`, `event_type`, `severity`, `timestamp`, and payload fields `cpu`, `memory`, `service_state`, `latency_ms`, `fault_mode`.
  - Downstream delivery: `downstream_result` as structured key/value data.
  - Last event: top-level `last_event` if present.
  - Traffic: previous Host peer and next R1 peer lanes.
- Source references: `nw_demo/local_agent.py:66`, `nw_demo/local_agent.py:110`, `nw_demo/local_agent.py:136`.

#### Relay R1/R2 detail content
- Card activity chips:
  - `pending_ack_count`
  - `retry_total`
  - `duplicate_dropped`
  - first/current `pending_ack_state[].state` and `pending_ack_state[].attempt` when present.
  - `last_downstream_result.status` or `last_forwarded_result.status` when present.
- Detail inspector sections:
  - Received event: `last_received_event.event_id`, `event_type`, `seq_no`, `host_id`, `timestamp`.
  - Pending ACK table: each `pending_ack_state[]` row with `event_id`, `event_type`, `seq_no`, `downstream_target`, `attempt`, `state`, `last_outcome`, and optional `ack_from`.
  - Retry/dedup counters: `pending_ack_count`, `retry_total`, `duplicate_dropped`, `recent_received_event_ids`.
  - Downstream/forwarding result: `last_downstream_result` and `last_forwarded_result` as structured key/value data.
  - Traffic: previous upstream peer and next downstream peer lanes. R1 next target is R2; R2 next target is Monitor.
- Source references: `nw_demo/relay.py:66`, `nw_demo/relay.py:109`, `nw_demo/relay.py:263`.

#### Monitor detail content
- Card activity chips:
  - `total_logged`
  - `duplicate_count`
  - `out_of_order_count`
  - `last_sink_result.status`
  - `last_ack_result.status`
- Detail inspector sections:
  - Event sink summary: `recent_event_summaries[]` rows with `event_id`, `event_type`, `severity`, `host_id`, `seq_no`, `timestamp`.
  - Last processed event: `last_processed_event` using the same event summary fields.
  - Sink result: `last_sink_result.status`, `event_id`, `host_id`, `seq_no`.
  - ACK result: `last_ack_result.status`, `event_id`, `duplicate`.
  - Host state table: `host_state_table[host_id].event_type`, `severity`, `payload`, `timestamp`.
  - Counters: `out_of_order_count`, `total_logged`, `duplicate_count`.
  - Traffic: previous R2 peer lane; next peer should be omitted or explicitly `not_applicable` if already represented by the traffic snapshot.
- Source references: `nw_demo/monitor.py:53`, `nw_demo/monitor.py:76`, `nw_demo/monitor.py:160`, `nw_demo/monitor.py:166`, `nw_demo/monitor.py:175`.

### Definition of Done (verifiable conditions with commands)
- `python -m py_compile main.py nw_demo/*.py tests/*.py` passes without modifying Python runtime files.
- `python -m unittest tests.test_node_monitor_mode tests.test_integrated_monitor_preservation tests.test_hop_state_visibility tests.test_node_view_contracts tests.test_traffic_snapshot_contracts tests.test_controller_renderer -q` passes.
- Loading `docs/reference/ui-preview/preview.revised.html` in Chromium produces no console assertion failures from `runSanityChecks()`.
- Browser DOM verification records `.sisyphus/evidence/task-6-node-first-browser-dom.html` and `.sisyphus/evidence/task-6-node-first-preview.png`.
- Static source check records `.sisyphus/evidence/task-6-node-first-static-check.txt` proving forbidden fields/text do not appear.

### Must Have
- Allowed implementation files:
  - `docs/reference/ui-preview/preview.revised.jsx`
  - `docs/reference/ui-preview/preview.revised.html` only if title or loading shell needs matching static-preview wording
  - `AI_IMPLEMENTATION_BRIEF.md` only for final handoff/context update required by repository governance
- Displayed activity fields must map to documented contracts from `IMPLEMENTATION_SPEC.md` and `nw_demo/*.py`.
- `observed_liveness`, `reported_state`, and activity/hop state must be represented as distinct data keys and distinct UI sections.
- A gray liveness lamp with `reported_state = 실행 중` must be allowed as a stale/offline-observation example, not auto-normalized away.
- Missing optional fields must display `—` or omit that row according to the per-role renderer rule below; do not invent explanatory text.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Do not modify Python runtime, TUI, data-plane protocol, process manager, production API, WebSocket, gateway, package setup, or dependency files.
- Do not add graph nodes/hubs such as Controller/UI, Reporting Hub, Control Hub, or Management Node.
- Do not add production Web UI infrastructure.
- Do not show literal TUI copied strings: `state=`, `state =`, `attempt=`, `attempt =`, `queue=`, `pending=`, `retries=`, `dup=`.
- Do not use fabricated fields or labels: `비고`, `설명`, `description`, synthetic `note`, synthetic `reason`, synthetic `activityLogs`, AI interpretation paragraphs.
- Do not collapse `observed_liveness`, `reported_state`, and `hop_state` into a single “processing state”.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + existing stdlib `unittest`, static `runSanityChecks()`, and Chromium/DOM evidence.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 data contract refactor, Task 2 shared lamp/card foundation, Task 3 inspector layout foundation.
Wave 2: Task 4 role-specific detail renderers, Task 5 narrative removal and sanity checks.
Wave 3: Task 6 verification evidence and context update.

### Dependency Matrix (full, all tasks)
- Task 1 blocks Tasks 2, 4, 5, 6.
- Task 2 blocks Tasks 4, 5, 6.
- Task 3 blocks Tasks 4, 6.
- Task 4 blocks Tasks 5, 6.
- Task 5 blocks Task 6.
- Task 6 blocks final verification wave.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 3 tasks → `visual-engineering`, `quick`, `visual-engineering`
- Wave 2 → 2 tasks → `visual-engineering`, `quick`
- Wave 3 → 1 task → `unspecified-high`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Refactor Preview Data Into Contract-backed State Axes

  **What to do**: In `docs/reference/ui-preview/preview.revised.jsx`, refactor `revisedNodes` so every node explicitly separates:
  - `observed_liveness`: use values backed by controller normalization: `live`, `stale`, `offline`, `unknown`, `kill_requested`. For the user lamp rule, map `live` to green; map all other values to gray unless an existing design token explicitly needs a non-green warning state for text only.
  - `reported_state`: a separate value representing `STATUS.state`, e.g. `실행 중`, `일시정지`, `중지`.
  - `activity`: role-specific object containing only documented fields.
  - `traffic`: `previous_peer`, `next_peer`, `recent` summaries using peer fields `peer_node_id`, `peer_role`, `hop_state`, `failure_reason`, `last_received`, `last_sent`.
  Use `—` for missing optional scalar values. Omit optional object sections only when the role truly does not produce them. Include one deliberate contradictory sample where `observed_liveness` is gray-mapped but `reported_state` remains `실행 중` to prove no state conflation.

  Role-specific activity fields to include:
  - Host: exactly the Host Simulator detail content listed in **Per-node Display Contract**.
  - Agent: exactly the Local Agent detail content listed in **Per-node Display Contract**.
  - Relay R1/R2: exactly the Relay detail content listed in **Per-node Display Contract**.
  - Monitor: exactly the Monitor detail content listed in **Per-node Display Contract**.

  **Must NOT do**: Do not keep or rename synthetic `note`, `reason`, or `activityLogs`. Do not add fields not present in the listed contracts. Do not change `nw_demo/*.py`.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: data-shape refactor in a single static preview file.
  - Skills: [] - no specialized skill required.
  - Omitted: [`frontend-ui-ux`] - this task is data contract work, not visual design.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [2, 4, 5, 6] | Blocked By: []

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:22` - current `revisedNodes` data model to refactor.
  - API/Type: `nw_demo/messages.py:51` - `make_status` base STATUS fields.
  - API/Type: `nw_demo/controller_ui.py:114` - normalized node view keys including `reported_state`, `observed_liveness`, `details`.
  - API/Type: `nw_demo/base.py:139` - traffic peer snapshot fields.
  - API/Type: `nw_demo/base.py:247` - traffic recent entry fields.
  - API/Type: `nw_demo/host_simulator.py:61` - Host detail fields.
  - API/Type: `nw_demo/local_agent.py:66` - Agent detail fields.
  - API/Type: `nw_demo/relay.py:66` - Relay detail fields.
  - API/Type: `nw_demo/monitor.py:53` - Monitor detail fields.
  - Spec: `IMPLEMENTATION_SPEC.md:482` - state axis separation rule.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Static source search confirms `revisedNodes` contains separate `observed_liveness`, `reported_state`, and `activity` keys for all 5 nodes.
  - [ ] Static source search confirms no `activityLogs`, synthetic `note`, synthetic `reason`, `비고`, or `설명` remain in preview data.
  - [ ] `runSanityChecks()` includes assertions that all 5 nodes have distinct liveness/state/activity fields.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Contract-backed node data exists
    Tool: Bash
    Steps: Run a read-only static check script that loads docs/reference/ui-preview/preview.revised.jsx as text and verifies all node ids have observed_liveness, reported_state, and activity keys.
    Expected: Script exits 0 and writes .sisyphus/evidence/task-1-contract-data.txt with PASS.
    Evidence: .sisyphus/evidence/task-1-contract-data.txt

  Scenario: Fabricated narrative fields are absent
    Tool: Bash
    Steps: Run a read-only static check for forbidden tokens: activityLogs, 비고, 설명, synthetic note labels, synthetic reason labels, description.
    Expected: Script exits 0 and writes no forbidden token findings.
    Evidence: .sisyphus/evidence/task-1-forbidden-data.txt
  ```

  **Commit**: NO | Message: `N/A` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 2. Create Shared Liveness Lamp and Node-first Cards

  **What to do**: Replace ad hoc liveness badge/dot rendering with a reusable `LivenessLamp` component. Use it in each `NodeCard`, in the detail inspector header, and in a small legend. Lamp mapping is strict: `observed_liveness === "live"` → green; all non-live values → gray lamp. Text may still show exact liveness value beside the lamp, but lamp color must not derive from `reported_state` or activity. Update `NodeCard` so before any detail selection each card shows:
  - node id and role,
  - common liveness lamp,
  - separate reported state row,
  - one or more role-specific activity chips derived from `activity`/`traffic`.

  **Must NOT do**: Do not label the lamp as 처리상태. Do not show `[처리상태: 실행 중]`. Do not compute lamp color from `reported_state`, `hop_state`, retry, or ACK status.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: UI component and card hierarchy change.
  - Skills: [`frontend-ui-ux`] - useful for clear dashboard semantics and visual hierarchy.
  - Omitted: [`playwright`] - browser execution belongs to verification tasks.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [4, 5, 6] | Blocked By: [1]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:473` - current tone/liveness classes.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:609` - current `NodeCard` implementation.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:518` - current compact slot rendering to replace with role-specific activity.
  - Spec: `IMPLEMENTATION_SPEC.md:278` - `STATUS.state` preserved as node-reported state.
  - Spec: `IMPLEMENTATION_SPEC.md:482` - `reported_state`, `observed_liveness`, `hop_state` do not replace one another.

  **Acceptance Criteria**:
  - [ ] Every rendered card has `data-testid="liveness-lamp-{node.id}"`.
  - [ ] Every rendered card has separate `data-testid="reported-state-{node.id}"`.
  - [ ] Every rendered card has at least one `data-testid="activity-chip-{node.id}-..."` before clicking a node.
  - [ ] Static source contains no UI label `처리상태` for the liveness lamp.

  **QA Scenarios**:
  ```
  Scenario: Liveness lamps render before selection
    Tool: Playwright / Chromium
    Steps: Open docs/reference/ui-preview/preview.revised.html; query node-card-host-simulator, node-card-local-agent, node-card-r1, node-card-r2, node-card-monitor; assert each contains liveness-lamp-* and reported-state-*.
    Expected: All 5 cards have lamp and reported-state elements simultaneously.
    Evidence: .sisyphus/evidence/task-2-lamps-cards.html

  Scenario: Lamp color ignores reported_state
    Tool: Bash + Chromium
    Steps: Verify the deliberate sample with non-live observed_liveness and reported_state=실행 중 renders a gray lamp while preserving the reported state text.
    Expected: Gray lamp class/data-state is present; reported-state text remains 실행 중.
    Evidence: .sisyphus/evidence/task-2-lamp-state-separation.txt
  ```

  **Commit**: NO | Message: `N/A` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 3. Replace Fixed Detail Column With Click-open One-third Inspector

  **What to do**: Change the detail panel behavior from a fixed always-present sticky column to an inspector that opens when a node card is clicked and closes via an explicit `X` button. On desktop, use approximately one third of viewport width: acceptable implementations include `w-[33vw]`, `max-w-[520px] min-w-[360px]`, or an `xl:grid-cols-[2fr_1fr]` column that is absent when closed. On narrow screens, stack or full-width drawer is acceptable if the X-close remains visible. Default state must have no detail inspector open; after X-close there must be no detail inspector until a node is clicked again. Add `Esc` close if simple; X-close is mandatory.

  **Must NOT do**: Do not keep an always-visible left or right detail area. Do not shrink information by removing required role fields. Do not add modal overlay that hides the graph/cards completely on desktop.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: layout, interaction, and responsive behavior.
  - Skills: [`frontend-ui-ux`] - useful for drawer/inspector ergonomics.
  - Omitted: []

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [4, 6] | Blocked By: []

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:951` - current `DetailPanel`.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:956` - current sticky panel styling.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:1079` - current `selectedNodeId` state.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:1099` - current `xl:grid-cols-[1fr_400px]` layout to replace.

  **Acceptance Criteria**:
  - [ ] Initial page load has no `data-testid="node-detail-inspector"` visible until a node card is clicked.
  - [ ] Detail inspector has `data-testid="node-detail-inspector"` only when open.
  - [ ] Close button has `data-testid="detail-close-button"` and hides/removes the inspector.
  - [ ] Desktop inspector width is between 28% and 38% of viewport width in browser measurement.
  - [ ] Graph/cards remain visible when inspector is open on desktop.

  **QA Scenarios**:
  ```
  Scenario: Click opens and X closes inspector
    Tool: Playwright / Chromium
    Steps: Open preview; click [data-testid="node-card-r1"]; assert [data-testid="node-detail-inspector"] appears; click [data-testid="detail-close-button"]; assert inspector is absent/hidden.
    Expected: Inspector opens and closes without page reload.
    Evidence: .sisyphus/evidence/task-3-inspector-open-close.html

  Scenario: Inspector occupies around one third
    Tool: Playwright / Chromium
    Steps: Set viewport 1440x900; click node-card-monitor; measure inspector bounding box width / viewport width.
    Expected: Ratio is >=0.28 and <=0.38; node cards still visible.
    Evidence: .sisyphus/evidence/task-3-inspector-width.txt
  ```

  **Commit**: NO | Message: `N/A` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 4. Implement Role-specific Detail Renderers

  **What to do**: Replace the generic detail body with a role-specific renderer registry or equivalent explicit switch. Each renderer must implement the exact field groups from **Per-node Display Contract** above:
  - `HostDetail`: common header, Host metrics, runtime tick/fault, host-agent communication, traffic.
  - `AgentDetail`: common header, host input, fault detection, emitted event, downstream delivery, last event, traffic.
  - `RelayDetail`: common header, received event, pending ACK table, retry/dedup counters, downstream/forwarding result, traffic. Use this for both R1 and R2 with node-specific data.
  - `MonitorDetail`: common header, event sink summary, last processed event, sink result, ACK result, host state table, counters, traffic.
  Common header may contain only lamp, node id, role, reported state, and last-seen/freshness if already present in node contract. For missing optional values, show `—`; for missing optional sections, omit the section with no prose explanation.

  **Must NOT do**: Do not keep `CommonNodeSection` as the primary body for every node. Do not put Host-only fields in Relay/Monitor or Monitor-only fields in Host/Agent. Do not add explanatory paragraphs.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: role-specific UI composition.
  - Skills: [`frontend-ui-ux`] - useful for dense inspector layout.
  - Omitted: []

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [5, 6] | Blocked By: [1, 2, 3]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:733` - current common detail section to reduce/replace.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:796` - current traffic board.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:858` - current monitor board.
  - API/Type: `nw_demo/host_simulator.py:104` - Host state fields.
  - API/Type: `nw_demo/local_agent.py:110` - emitted EVENT fields and payload fields.
  - API/Type: `nw_demo/relay.py:263` - Relay pending ACK state item fields.
  - API/Type: `nw_demo/monitor.py:160` - Monitor host state table values.

  **Acceptance Criteria**:
  - [ ] Source has distinct detail renderers or explicit role-switch sections for Host, Agent, Relay, and Monitor.
  - [ ] R1 and R2 use Relay detail renderer and still render their own node ids/data.
  - [ ] Host detail renders host metrics, runtime tick/fault, and host-agent traffic sections using only Host contract fields.
  - [ ] Agent detail renders host input, detected fault, emitted event, downstream result, last event, and traffic sections using only Agent contract fields.
  - [ ] Relay detail renders received event, pending ACK table, retry/dedup counters, downstream/forwarding result, and traffic sections using only Relay contract fields.
  - [ ] Monitor detail renders event summaries, sink result, ACK result, host state table, counters, and traffic sections using only Monitor contract fields.
  - [ ] Browser DOM for each clicked node exposes role-specific `data-testid` sections: `host-detail`, `agent-detail`, `relay-detail-r1`, `relay-detail-r2`, `monitor-detail`.
  - [ ] No detail body contains generic prose labels `비고`, `설명`, `description`, `reason`.

  **QA Scenarios**:
  ```
  Scenario: Each node opens correct role-specific detail
    Tool: Playwright / Chromium
    Steps: Click host-simulator, local-agent, r1, r2, monitor cards sequentially and record the visible role-specific detail test id for each.
    Expected: Host shows host-detail; Agent shows agent-detail; r1/r2 show relay-detail-r1/r2; Monitor shows monitor-detail.
    Evidence: .sisyphus/evidence/task-4-role-details.html

  Scenario: Missing optional values do not create prose
    Tool: Bash + Chromium
    Steps: Inspect rendered DOM text for 비고, 설명, description, reason, "not available because", "AI"; inspect rows with missing optional values.
    Expected: Forbidden prose absent; missing scalar values show — or absent optional sections.
    Evidence: .sisyphus/evidence/task-4-no-prose-details.txt
  ```

  **Commit**: NO | Message: `N/A` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 5. Strengthen Sanity Checks and Forbidden-regression Guards

  **What to do**: Update `runSanityChecks()` in `preview.revised.jsx` so it fails fast for the user's core requirements. Add assertions for:
  - exactly 5 graph nodes: `host-simulator`, `local-agent`, `r1`, `r2`, `monitor`;
  - no extra controller/reporting/control/management graph node;
  - every node has `observed_liveness`, `reported_state`, `activity`;
  - liveness lamp mapping function depends only on `observed_liveness`;
  - all cards have at least one activity chip;
  - no source data keys or rendered labels include `activityLogs`, synthetic `note`, synthetic `reason`, `비고`, `설명`, `description`;
  - TUI literal strings remain forbidden: `state=`, `state =`, `attempt=`, `attempt =`, `queue=`, `pending=`, `retries=`, `dup=`.

  **Must NOT do**: Do not remove existing useful assertions for topology, monitor sections, retry/dedup examples, or static forbidden fragments unless replacing with stricter equivalent assertions.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: single-file assertion update.
  - Skills: []
  - Omitted: [`frontend-ui-ux`] - not a visual design task.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [6] | Blocked By: [1, 2, 4]

  **References**:
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:989` - current `runSanityChecks()`.
  - Pattern: `docs/reference/ui-preview/preview.revised.jsx:1074` - sanity check invocation.
  - Spec: `IMPLEMENTATION_SPEC.md:488` - hop taxonomy and `not_started` caveat.
  - Guardrail: `INTENT_ALIGNMENT_NOTE.md:207` - state axes must not be merged.

  **Acceptance Criteria**:
  - [ ] Chromium load of `preview.revised.html` produces no console assertion failures.
  - [ ] Deliberately searching source for forbidden strings returns no violations except the forbidden-token list inside `runSanityChecks()` itself.
  - [ ] Assertions cover state separation and node count/topology.

  **QA Scenarios**:
  ```
  Scenario: Sanity checks pass in browser
    Tool: Playwright / Chromium
    Steps: Open preview.revised.html and collect console messages.
    Expected: No console.assert failures; evidence contains PASS.
    Evidence: .sisyphus/evidence/task-5-sanity-browser.txt

  Scenario: Static forbidden strings are guarded
    Tool: Bash
    Steps: Run a script that scans preview.revised.jsx and rendered DOM for forbidden user-facing strings, excluding the assertion allowlist itself.
    Expected: No forbidden user-facing strings found.
    Evidence: .sisyphus/evidence/task-5-forbidden-static.txt
  ```

  **Commit**: NO | Message: `N/A` | Files: [`docs/reference/ui-preview/preview.revised.jsx`]

- [ ] 6. Execute Verification Evidence and Update Context

  **What to do**: Run the full verification sequence and save evidence. If implementation changed the static preview meaning or next-session context, update `AI_IMPLEMENTATION_BRIEF.md` with a concise current-state entry; do not create new root markdown. Verification sequence:
  1. `python -m py_compile main.py nw_demo/*.py tests/*.py`
  2. `python -m unittest tests.test_node_monitor_mode tests.test_integrated_monitor_preservation tests.test_hop_state_visibility tests.test_node_view_contracts tests.test_traffic_snapshot_contracts tests.test_controller_renderer -q`
  3. Serve or open `docs/reference/ui-preview/preview.revised.html` with Chromium using existing file/local-server pattern.
  4. Capture DOM and screenshot evidence.
  5. Run static forbidden-token/source-scope check.

  **Must NOT do**: Do not start a new long-lived server if the existing preview server is still valid unless needed for browser automation. Do not update `README.md`, `IMPLEMENTATION_SPEC.md`, or `INTENT_ALIGNMENT_NOTE.md` unless the implementation contract or intent guardrails actually changed.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: hands-on QA and evidence collection across commands/browser.
  - Skills: [`playwright`] - browser verification is required.
  - Omitted: [`git-master`] - no commit requested.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [Final Verification Wave] | Blocked By: [1, 2, 3, 4, 5]

  **References**:
  - Test: `tests/test_node_monitor_mode.py:27` - node monitor behavior tests.
  - Test: `tests/test_hop_state_visibility.py:11` - hop state visibility tests.
  - Test: `tests/test_node_view_contracts.py:25` - node view contract tests.
  - Test: `tests/test_traffic_snapshot_contracts.py:15` - traffic snapshot tests.
  - Test: `tests/test_controller_renderer.py:25` - controller renderer tests.
  - Pattern: `.sisyphus/evidence/task-5-rendered-check.txt` - prior rendered DOM evidence convention.
  - Pattern: `.sisyphus/evidence/task-5-server-listen.txt` - prior preview server evidence convention.
  - Pattern: `.sisyphus/plans/web-ui-feedback-revision.md:70` - evidence naming convention.

  **Acceptance Criteria**:
  - [ ] Py compile evidence saved to `.sisyphus/evidence/task-6-pycompile.txt`.
  - [ ] Unittest evidence saved to `.sisyphus/evidence/task-6-unittest.txt`.
  - [ ] Browser DOM evidence saved to `.sisyphus/evidence/task-6-node-first-browser-dom.html`.
  - [ ] Screenshot saved to `.sisyphus/evidence/task-6-node-first-preview.png`.
  - [ ] Source-scope evidence proves only allowed files changed.
  - [ ] If `AI_IMPLEMENTATION_BRIEF.md` is changed, it records current state and next steps only, not a session log.

  **QA Scenarios**:
  ```
  Scenario: Full verification passes
    Tool: Bash + Playwright / Chromium
    Steps: Run py_compile, focused unittest command, browser console assertion collection, DOM capture, screenshot capture, and static forbidden-token check.
    Expected: All commands exit 0; evidence files exist and contain PASS or captured output.
    Evidence: .sisyphus/evidence/task-6-verification-summary.txt

  Scenario: Scope guard holds
    Tool: Bash
    Steps: Compare changed files against allowlist: docs/reference/ui-preview/preview.revised.jsx, docs/reference/ui-preview/preview.revised.html, AI_IMPLEMENTATION_BRIEF.md.
    Expected: No Python runtime, TUI, package, API, WebSocket, gateway, or root-new markdown files changed.
    Evidence: .sisyphus/evidence/task-6-scope-guard.txt
  ```

  **Commit**: NO | Message: `N/A` | Files: [`docs/reference/ui-preview/preview.revised.jsx`, `docs/reference/ui-preview/preview.revised.html`, `AI_IMPLEMENTATION_BRIEF.md`]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Do not commit unless the user explicitly requests a git commit after implementation and review.
- If a commit is later requested, include only allowed files and evidence/context files requested by the user; never include secrets or unrelated artifacts.

## Success Criteria
- UI semantics match the user’s full feedback, not only the state-separation subset.
- Users can see each node’s liveness and basic activity before selection.
- Users can click a node, inspect role-specific contract-backed details, close the inspector, and reopen another node.
- No fabricated prose/narrative fields remain.
- Existing Python runtime/tests still pass without runtime changes.
- Static/browser evidence proves the preview behavior and scope guard.
