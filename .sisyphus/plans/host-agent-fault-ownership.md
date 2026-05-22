# Host-Agent Fault Ownership Contract Correction

## TL;DR
> **Summary**: Correct the fault ownership boundary so Host exposes raw observations and Local Agent owns fault judgment, while preserving existing `payload.fault_mode` as an Agent-authored compatibility field.
> **Deliverables**:
> - Canonical/reference docs updated for Host-as-observation-source and Agent-as-judgment-owner.
> - Local Agent detects CPU/service/latency faults from raw observations and authors `payload.fault_mode`.
> - Host `host_state` stops exposing semantic `fault_mode` / `latency_state`; Host keeps injection metadata only.
> - TUI/Web UI copy/data-source changes only; no layout, routing, palette, or Monitor route redesign.
> - User-constraint audit gate added: exact intent, minimal scope, no unwanted additions, no shortcut implementation.
> - Unit/compile/browser QA evidence.
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 2 → Task 3 → Tasks 4/5 → Task 6 → Final Verification

## Context
### Original Request
User asked for a correction plan based on this complaint: Host detail currently shows `fault_mode` and `latency_state`, making Host look like it judges faults, but the intended architecture is Host generates measurements and Local Agent interprets them.

### User Constraint Audit Request
Before implementation, this plan must be judged against the user's four explicit constraints, not only against technical correctness:
1. **Intent fidelity**: the correction must directly address the user's dissatisfaction: Host must not appear to create or own `fault_mode` / latency-state judgment; Local Agent must own both judgment and the fault-status message/result exposed downstream.
2. **Minimal scope**: the correction must not be a broad redesign and must not create side effects in routing, backup behavior, Monitor route summary, command syntax, Web UI layout, or unrelated docs.
3. **No unwanted additions**: the work must not introduce new concepts the user did not ask for, such as recovery, new fault taxonomy, critical-fault semantics, new EVENT payload fields, new UI components, or new compatibility mirrors.
4. **No shortcuts**: the result must not be achieved by label-only UI wording, hidden fallbacks, fake compatibility, ignored tests, or Host-derived semantic inference under another name.

### Interview Summary
- Host should be raw observation source: `cpu_usage`, `memory_usage`, `service_state`, `latency_ms`, `last_update_time`.
- Local Agent should own judgment: `CPU_SPIKE`, `SERVICE_DOWN`, `LATENCY_HIGH`, `NORMAL`.
- Keep `fault cpu/service/latency on|off`; interpret as simulation input that makes Host produce abnormal observations.
- Keep `payload.fault_mode` for compatibility, but it must be Agent-authored.
- Do not touch routing, command palette layout, Monitor route summary, Web UI layout/colors/cards/overlay, or unrelated docs.

### Metis Review (gaps addressed)
- Reordered implementation so Local Agent becomes raw-contract compatible before Host removes legacy semantic fields.
- Added negative compatibility test for contradictory legacy Host fields.
- Preserved existing fault precedence: CPU first, service second, latency third.
- Decided `last_update_time` remains observational metadata and must not enter Agent de-dup signature.
- Split simulation input display from semantic fault judgment: Host `detail.fault_type` may drive control switch ON/OFF as injection metadata, but semantic display must use Agent-owned data.
- Fixture updates are integrated into relevant tasks, not left as a final catch-all.

### Oracle Review
- Oracle verdict: **STRONG PASS**.
- Guardrails incorporated: preserve fault precedence, add no new event payload fields, do not remove controller fault commands, treat Host `detail.fault_type` only as injection metadata, update only related docs/tests, UI changes are copy/data-source only.

### Mandatory Oracle Constraint Gate
- This plan must receive Oracle **STRONG PASS** for each user constraint in `User Constraint Audit Request` before implementation starts.
- Oracle must answer condition-by-condition: intent fidelity, minimal scope, no unwanted additions, no shortcuts.
- If any condition is not **STRONG PASS**, revise this plan using Oracle's feedback and repeat Oracle review until every condition is **STRONG PASS**.
- Do not treat the prior Oracle review as sufficient if the new review does not explicitly evaluate all four user constraints.

## Work Objectives
### Core Objective
Make runtime truth and UI/docs agree that Host produces observations and Local Agent produces fault judgment.

### Deliverables
- Updated Host→Agent observation contract.
- Updated Local Agent detection/event payload contract.
- Minimal TUI/Web UI display-source and copy changes.
- Updated tests/fixtures and documentation.
- Evidence files under `.sisyphus/evidence/host-agent-fault-ownership/`.

### Definition of Done (verifiable conditions with commands)
- Pre-implementation Oracle constraint review gives **STRONG PASS** for all four user constraints.
- `python -m unittest discover -s tests` exits `0`.
- `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py` exits `0`.
- `node --check web_ui/static/app.js` exits `0`.
- Browser QA confirms Host detail shows raw observations and Agent detail shows fault judgment for `fault latency on`.
- Grep confirms runtime Host `host_state` no longer exposes `fault_mode` or `latency_state` as semantic state fields.

### Must Have
- `payload.fault_mode` remains present in Agent-emitted EVENT payload.
- `payload.fault_mode` value is derived by Local Agent from detected fault / event type.
- `HOST_STATE_UPDATE` payload uses `fault_mode: "NORMAL"`.
- `LATENCY_HIGH` is derived from `latency_ms >= 200`.
- Fault precedence remains CPU → service → latency, matching existing `_detect_fault()` ordering.
- `last_update_time` does not participate in `_host_state_signature()` / de-dup.
- Web UI fault switches may use Host `detail.fault_type` only as injection metadata; semantic fault display uses Agent `detected_fault` or Agent-authored `payload.fault_mode`.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- MUST NOT add new EVENT payload fields.
- MUST NOT remove or rename `payload.fault_mode`.
- MUST NOT rename controller commands or alter `fault cpu|service|latency on|off|[sec]` syntax.
- MUST NOT keep Host-owned compatibility mirrors for `host_state.fault_mode` or `host_state.latency_state`.
- MUST NOT replace Host-owned `fault_mode` with an equivalent Host-owned semantic field under a different name.
- MUST NOT infer Agent `NORMAL` / fault judgment from Host injection metadata when Agent data is missing or stale.
- MUST NOT change routing, backup behavior, Monitor route summary, or fault taxonomy.
- MUST NOT change Web UI layout, palette, typography, node positions, cards, overlay mechanics, or command palette structure.
- MUST NOT add recovery, critical-fault semantics, multi-host semantics, or new monitoring surfaces.
- MUST NOT create new root-level markdown files.
- MUST NOT hide contradictory runtime truth only through UI labels.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + existing stdlib `unittest` framework.
- QA policy: Every task has agent-executed scenarios.
- Evidence root: `.sisyphus/evidence/host-agent-fault-ownership/`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 docs contract, Task 2 Local Agent contract/tests.
Wave 2: Task 3 Host raw observation contract, Task 4 TUI display contract, Task 5 Web UI display contract.
Wave 3: Task 6 reference/data-shape cleanup and full verification.

### Dependency Matrix (full, all tasks)
- Task 1: no blockers; informs all tasks.
- Task 2: no blockers; blocks Task 3, Task 4, Task 5, Task 6.
- Task 3: blocked by Task 2; blocks Task 4/5 final assertions.
- Task 4: blocked by Task 2; should run after Task 3 for final expected data shape.
- Task 5: blocked by Task 2; should run after Task 3 for final expected data shape.
- Task 6: blocked by Tasks 1-5.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 2 tasks → writing, unspecified-high.
- Wave 2 → 3 tasks → unspecified-high, unspecified-high, visual-engineering.
- Wave 3 → 1 task → unspecified-high.

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Update canonical contract docs for Host observations and Agent judgment

  **What to do**: Update only existing docs that define or repeat this contract. In `IMPLEMENTATION_SPEC.md`, change Host minimum state from semantic state to raw observations: `cpu_usage`, `memory_usage`, `service_state`, `latency_ms`, `last_update_time`. State that `Local Agent` detects faults from raw observations and writes `payload.fault_mode` for compatibility. In `README.md`, keep the quick overview short but avoid wording that implies Host creates semantic events; describe the flow as Host observation → Agent event generation if touched. In `docs/reference/network-project/guide/노드 전달.md`, change Host polling/control wording so Host produces raw observation changes while Local Agent judges fault. In `docs/reference/network-project/guide/노드 자료형.md`, update all Host / Agent / STATUS_REPORT sample blocks that contain `host_state.fault_mode` or `host_state.latency_state`; remove those Host-owned semantic fields from Host state examples and keep `payload.fault_mode` only in Agent-authored EVENT payload examples. Keep Host `detail.fault_type` only as simulation input metadata. Update `AI_IMPLEMENTATION_BRIEF.md` with a short recent-decision entry. If `WEB_UI_SPEC.md` mentions Host fault ownership, update wording only.
  **Must NOT do**: Do not create new root markdown. Do not rewrite unrelated guide sections. Do not change command names or fault taxonomy. Do not add new user-guide concepts beyond clarifying Host observation vs Agent judgment.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: documentation contract changes with exact wording constraints.
  - Skills: [`api-and-interface-design`] - Reason: this is an internal interface contract.
  - Omitted: [`webapp-testing`] - Not needed for docs.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [6] | Blocked By: []

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `IMPLEMENTATION_SPEC.md:106-115` - role responsibilities already say Host generates state and Agent detects faults.
  - Pattern: `IMPLEMENTATION_SPEC.md:371-400` - Host minimum state and Agent event rules need contract correction.
  - Pattern: `README.md:40` - quick overview should not imply Host creates semantic events if wording is updated.
  - Pattern: `docs/reference/network-project/guide/노드 전달.md:41-60` - Host/Agent delivery wording currently says Host returns fault state.
  - Pattern: `docs/reference/network-project/guide/노드 자료형.md:37-52` - Host→Agent example currently includes legacy semantic fields.
  - Pattern: `docs/reference/network-project/guide/노드 자료형.md:270-288` - Agent EVENT example keeps `payload.fault_mode` compatibility field.
  - Pattern: `AI_IMPLEMENTATION_BRIEF.md:53-80` - recent decisions section for short durable update.
  - Oracle: STRONG PASS guardrails in planning summary; do not add new event payload fields.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -R "latency_state\|host_state.*fault_mode" README.md IMPLEMENTATION_SPEC.md docs/reference/network-project/guide AI_IMPLEMENTATION_BRIEF.md` shows no canonical/reference statement that Host owns semantic fault judgment.
  - [ ] `grep -R "payload.fault_mode" IMPLEMENTATION_SPEC.md docs/reference/network-project/guide/노드\ 자료형.md` still finds Agent EVENT compatibility documentation.
  - [ ] No new root-level `.md` files exist beyond repository allowlist.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Documentation states correct ownership
    Tool: Bash
    Steps: Run targeted grep for "Host Simulator", "Local Agent", "payload.fault_mode", "latency_state", "fault_mode" in updated docs and guide files.
    Expected: Host described as observation source; Local Agent as judgment owner; `payload.fault_mode` retained as Agent EVENT compatibility field.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-1-doc-contract.txt

  Scenario: No root markdown scope creep
    Tool: Bash
    Steps: Run `python - <<'PY'` script listing root `*.md` and compare against README.md, AGENTS.md, IMPLEMENTATION_SPEC.md, INTENT_ALIGNMENT_NOTE.md, AI_IMPLEMENTATION_BRIEF.md.
    Expected: No extra root markdown files.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-1-root-md-check.txt
  ```

  **Commit**: NO | Message: `문서 계약은 실행자 판단에 따라 묶기` | Files: [README.md, IMPLEMENTATION_SPEC.md, docs/reference/network-project/guide/노드 전달.md, docs/reference/network-project/guide/노드 자료형.md, AI_IMPLEMENTATION_BRIEF.md, optional docs/reference/ui-preview/WEB_UI_SPEC.md]

- [ ] 2. Make Local Agent raw-observation compatible and Agent-author `payload.fault_mode`

  **What to do**: Update `nw_demo/local_agent.py` and its tests together. Add `LATENCY_HIGH_THRESHOLD_MS = 200` near Local Agent detection logic unless a better existing constant is found. Change `_detect_fault()` to use `cpu_usage`, `service_state`, and `latency_ms`; preserve precedence CPU → service → latency. Change `_host_state_signature()` to use only raw observations needed for semantic de-dup: `cpu_usage`, `memory_usage`, `service_state`, `latency_ms`; do not include `last_update_time`, `fault_mode`, or `latency_state`. Change `_build_event()` so `payload.fault_mode` is `event_type` for fault events and `NORMAL` for `HOST_STATE_UPDATE`. Add/adjust tests in `tests/test_local_agent_event_policy.py` immediately with fixture changes.
  **Must NOT do**: Do not read Host legacy `fault_mode` or `latency_state` for judgment. Do not add a new payload field. Do not change routing or backup delivery.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: runtime contract change with tests.
  - Skills: [`api-and-interface-design`] - Reason: producer/consumer contract must remain stable.
  - Omitted: [`webapp-testing`] - Browser not needed for Local Agent unit contract.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [3, 4, 5, 6] | Blocked By: []

  **References**:
  - API/Type: `nw_demo/local_agent.py:106-123` - current `_detect_fault()` and signature dependencies.
  - API/Type: `nw_demo/local_agent.py:135-158` - current `_build_event()` copies Host `fault_mode`.
  - API/Type: `nw_demo/local_agent.py:470-498` - run loop records detected fault and emits event.
  - Test: `tests/test_local_agent_event_policy.py:13-55` - local host fixture and detection/event selection tests.
  - Test: `tests/test_local_agent_event_policy.py:57-113` - routing tests must keep event payload compatibility.
  - Research: Host normal latency range is `24 + phase*6` and injected latency is `260`; threshold `200` cleanly separates normal and injected values.

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_local_agent_event_policy` exits `0`.
  - [ ] New test proves incoming host state without `fault_mode` and without `latency_state` still emits correct CPU/SERVICE/LATENCY/NORMAL results.
  - [ ] New negative test proves contradictory legacy `host_state.fault_mode="CPU_SPIKE"` with normal raw observations results in `payload.fault_mode == "NORMAL"`.
  - [ ] Multi-fault test proves CPU wins over service and latency, service wins over latency.

  **QA Scenarios**:
  ```
  Scenario: Agent detects latency from raw latency_ms
    Tool: Bash
    Steps: Run `python -m unittest tests.test_local_agent_event_policy`.
    Expected: Test covering `latency_ms >= 200` passes and emitted EVENT uses `event_type=LATENCY_HIGH`, `payload.fault_mode=LATENCY_HIGH`.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-2-local-agent-tests.txt

  Scenario: Agent ignores contradictory Host semantic labels
    Tool: Bash
    Steps: Run the same unittest module with a test fixture containing normal raw observations plus legacy `fault_mode=CPU_SPIKE`.
    Expected: Agent emits/derives `NORMAL`, proving no Host-authored semantic shortcut remains.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-2-legacy-ignore.txt
  ```

  **Commit**: NO | Message: `로컬 에이전트 장애 판단 소유권 정리` | Files: [nw_demo/local_agent.py, tests/test_local_agent_event_policy.py]

- [ ] 3. Make HostSimulator expose raw observations, with injection metadata only

  **What to do**: Update `nw_demo/host_simulator.py` and related publisher tests. `_apply_normal_state()` should set only raw observation keys: `host_id`, `cpu_usage`, `memory_usage`, `service_state`, `latency_ms`, `last_update_time`. `_apply_fault_state("CPU_SPIKE")` should mutate `cpu_usage` only; `SERVICE_DOWN` should mutate `service_state`; `LATENCY_HIGH` should mutate `latency_ms` only. `publish_status()` should compute `detail.fault_active` from internal `_fault_type is not None` and expose `detail.fault_type` as injection metadata; `host_state` and `detail.host_state` must not include `fault_mode` or `latency_state`. Update `tests/test_status_detail_publishers.py` Host publisher assertions immediately.
  **Must NOT do**: Do not remove `_fault_type`; it is still needed for simulation control. Do not change control command behavior. Do not remove Host traffic snapshot.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: producer contract update with regression risk.
  - Skills: [`api-and-interface-design`] - Reason: changes Host status and Host→Agent interface.
  - Omitted: [`webapp-testing`] - Browser is covered later.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [4, 5, 6] | Blocked By: [2]

  **References**:
  - API/Type: `nw_demo/host_simulator.py:78-89` - Host status payload and detail fields.
  - API/Type: `nw_demo/host_simulator.py:121-142` - current normal/fault state construction.
  - Test: `tests/test_status_detail_publishers.py:18-63` - Host publisher and fault toggle assertions.
  - Guide: `docs/reference/network-project/guide/노드 자료형.md:37-52` - Host→Agent example to align with docs.

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_status_detail_publishers` exits `0`.
  - [ ] Host `snapshot()` after CPU/SERVICE/LATENCY simulation contains no `fault_mode` and no `latency_state`.
  - [ ] Host status detail still contains `fault_active` and `fault_type` as injection metadata.
  - [ ] Local Agent tests from Task 2 still pass after Host fields are removed.

  **QA Scenarios**:
  ```
  Scenario: Host CPU injection is raw-only
    Tool: Bash
    Steps: Run Host publisher unittest that applies CPU fault and inspects `host.snapshot()` / status detail.
    Expected: `cpu_usage=96`; no `fault_mode`; no `latency_state`; `detail.fault_type=CPU_SPIKE`.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-3-host-cpu-raw.txt

  Scenario: Host latency injection is raw-only
    Tool: Bash
    Steps: Run Host publisher unittest that applies LATENCY_HIGH and inspects `host.snapshot()` / status detail.
    Expected: `latency_ms=260`; no `latency_state`; no `fault_mode`; `detail.fault_type=LATENCY_HIGH`.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-3-host-latency-raw.txt
  ```

  **Commit**: NO | Message: `호스트 상태를 관측값 중심으로 정리` | Files: [nw_demo/host_simulator.py, tests/test_status_detail_publishers.py]

- [ ] 4. Update TUI/controller display to separate injection metadata from Agent judgment

  **What to do**: Update `nw_demo/controller_ui.py` and TUI tests/fixtures. Host lines should show raw observations only (`cpu`, `mem`, `service`, `latency_ms`) plus clearly labeled injection metadata if displayed (`주입` / `simulation input` wording), never `mode=` as semantic state. Agent lines should show `detected_fault` and Agent-authored `payload.fault_mode` as judgment/result. Monitor host-state lines should not expect `payload.fault_mode` from Host state; Monitor event/host table may still show Agent event payload compatibility field. Update `tests/status_builders.py`, `tests/test_node_monitor_mode.py`, `tests/test_integrated_monitor_preservation.py`, and relevant assertions immediately.
  **Must NOT do**: Do not change frame layout, focused mode behavior, route summary, sanitization behavior, or prompt rendering.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: terminal display contract and tests.
  - Skills: [] - No loaded skill needed beyond repo patterns.
  - Omitted: [`webapp-testing`] - TUI tests are Python/unit level.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [6] | Blocked By: [2, 3]

  **References**:
  - Pattern: `nw_demo/controller_ui.py:563-586` - Host focused lines currently show latency_state/mode.
  - Pattern: `nw_demo/controller_ui.py:588-616` - Agent lines show payload mode and detected fault.
  - Pattern: `nw_demo/controller_ui.py:685-708` - Monitor host-state lines show payload fault mode.
  - Pattern: `nw_demo/controller_ui.py:882-904` - Monitor host rows show service/latency/fault wording.
  - Test: `tests/status_builders.py:72-206` - Host and Agent fixtures.
  - Test: `tests/test_node_monitor_mode.py:111-149` - payload/sanitization fixture.
  - Test: `tests/test_integrated_monitor_preservation.py:41-58` - integrated frame text expectations.

  **Acceptance Criteria**:
  - [ ] `python -m unittest tests.test_node_monitor_mode tests.test_integrated_monitor_preservation tests.test_hop_state_visibility` exits `0`.
  - [ ] Host focused lines do not contain `mode=` sourced from Host `host_state.fault_mode`.
  - [ ] Agent focused lines still contain `detected_fault` and emitted `payload.fault_mode` value.
  - [ ] Existing malicious payload sanitization test still passes.

  **QA Scenarios**:
  ```
  Scenario: Host TUI display is raw observation first
    Tool: Bash
    Steps: Run node monitor mode tests that render Host focused frame from updated fixtures.
    Expected: Host frame shows CPU/memory/service/latency ms and no Host-owned fault mode label.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-4-tui-host.txt

  Scenario: Agent TUI display owns judgment
    Tool: Bash
    Steps: Run node monitor mode tests that render Agent focused frame after a CPU fault event.
    Expected: Agent frame shows detected fault and Agent-authored event payload compatibility field.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-4-tui-agent.txt
  ```

  **Commit**: NO | Message: `터미널 표시의 장애 판단 출처 정리` | Files: [nw_demo/controller_ui.py, tests/status_builders.py, tests/test_node_monitor_mode.py, tests/test_integrated_monitor_preservation.py, tests/test_hop_state_visibility.py]

- [ ] 5. Update Web UI display source/copy without layout changes

  **What to do**: Update `web_ui/static/app.js` only for data source/copy. Rename or replace `currentFaultType()` concept so fault switch active state is based on Host `detail.fault_type` as simulation input metadata, not Host `host_state.fault_mode`. Host card/detail should show raw observations; if injection metadata is shown, label it as simulation/input, not judgment. Agent card/detail remains the semantic fault judgment surface via `detected_fault` and Agent-authored `payload.fault_mode`. If Agent data is missing/stale, display existing missing value `—` / unavailable behavior; do not infer `NORMAL` or fault from Host metadata. Do not change CSS or HTML unless absolutely necessary for copy-only text.
  **Must NOT do**: Do not change `index.html`, `app.css`, node positions, overlay structure, cards, command palette groups, colors, animations, or SVG route behavior.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: browser-facing UI semantics must be verified visually without redesign.
  - Skills: [`webapp-testing`] - Reason: Playwright/browser QA required.
  - Omitted: [`frontend-ui-ux`] - No redesign requested.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [6] | Blocked By: [2, 3]

  **References**:
  - Pattern: `web_ui/static/app.js:355-358` - current fault type reads Host `host_state.fault_mode`.
  - Pattern: `web_ui/static/app.js:440-456` - Host/Agent card activity chips.
  - Pattern: `web_ui/static/app.js:711-733` - Host/Agent detail sections and Agent `payload.fault_mode` row.
  - Pattern: `web_ui/static/app.js:814-820` - Monitor host summary uses event payload fault mode.
  - Spec: `docs/reference/ui-preview/WEB_UI_SPEC.md:116-132` - detail overlay order, no layout redesign.
  - Guardrail: `INTENT_ALIGNMENT_NOTE.md:100-112` - no viewport drawer/raw JSON/layout change.

  **Acceptance Criteria**:
  - [ ] `node --check web_ui/static/app.js` exits `0`.
  - [ ] No changes to `web_ui/static/app.css` or `web_ui/static/index.html` unless final diff proves copy-only necessity.
  - [ ] Browser QA after `fault latency on` shows Host raw observations and Agent `LATENCY_HIGH` judgment.
  - [ ] Browser QA confirms Host detail text does not include Host-owned `fault_mode` or `latency_state` rows.

  **QA Scenarios**:
  ```
  Scenario: Web Host detail remains raw-observation-only
    Tool: Playwright
    Steps: Start `python -m web_ui.server --web-port 28090 --control-port 29190 --duration 90`; open `http://127.0.0.1:28090`; click `[data-testid="node-card-host-simulator"]`; inspect `#detail-inspector`.
    Expected: Host detail contains CPU/memory/service/latency ms/last_update_time; does not contain `fault_mode` or `latency_state` as Host rows.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-5-web-host.png

  Scenario: Web Agent detail owns latency judgment
    Tool: Playwright
    Steps: POST `/api/control` with `{ "line": "fault latency on" }`; wait for polling; click `[data-testid="node-card-local-agent"]`; inspect `#detail-inspector`.
    Expected: Agent detail contains `detected_fault` = `LATENCY_HIGH` and emitted payload `fault_mode` = `LATENCY_HIGH`; Host detail still shows raw latency observation only.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-5-web-agent-latency.png
  ```

  **Commit**: NO | Message: `Web UI 장애 판단 표시 출처 정리` | Files: [web_ui/static/app.js]

- [ ] 6. Clean reference fixtures, run full regression, and prove no scope creep

  **What to do**: Update remaining docs/reference examples and test fixtures that still encode old ownership after Tasks 1-5. Target `tests/status_builders.py`, `tests/test_node_view_contracts.py`, `tests/test_controller_client_commands.py`, and `docs/reference/ui-preview/preview.revised.jsx` where they represent Host/Agent/Monitor data shape. For `preview.revised.jsx`, update every Host / Agent / Monitor sample, renderer row, preview text, and assertion that still treats Host `host_state.fault_mode` or `latency_state` as Host-owned semantic truth; keep Agent EVENT `payload.fault_mode` assertions as Agent-authored compatibility only. Do not change visual structure. Add command-parser tests for `fault latency on/off` and `fault latency 6`. Run full verification and capture grep evidence that runtime code no longer treats Host `host_state.fault_mode` / `latency_state` as semantic truth.
  **Must NOT do**: Do not broaden to unrelated reference rewrites. Do not update archived docs. Do not change preview layout/style/component hierarchy. Do not commit evidence unless repository convention says to keep it; runtime evidence may stay under `.sisyphus/evidence/` if already tracked by workflow.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: final regression sweep across tests/docs.
  - Skills: [`api-and-interface-design`] - Reason: contract consistency verification.
  - Omitted: [`webapp-testing`] - Browser QA already performed in Task 5; full final QA may reuse its evidence.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [Final Verification] | Blocked By: [1, 2, 3, 4, 5]

  **References**:
  - Test: `tests/status_builders.py:72-206` - shared fixtures.
  - Test: `tests/test_node_view_contracts.py:95-114` - Agent payload and detected fault projection.
  - Test: `tests/test_controller_client_commands.py:98-111` - fault parser coverage; add latency cases.
  - Reference: `docs/reference/ui-preview/preview.revised.jsx:901-919` - Host/Agent detail reference rows.
  - Command: `python -m unittest discover -s tests` - repository-wide stdlib test command.

  **Acceptance Criteria**:
  - [ ] `python -m unittest discover -s tests` exits `0`.
  - [ ] `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py` exits `0`.
  - [ ] `node --check web_ui/static/app.js` exits `0`.
  - [ ] `grep -R "host_state.*fault_mode\|latency_state" nw_demo web_ui/static tests docs/reference/network-project/guide docs/reference/ui-preview/WEB_UI_SPEC.md docs/reference/ui-preview/preview.revised.jsx` only returns Agent EVENT compatibility references, explicitly labeled historical notes, or no runtime/reference semantic dependencies.
  - [ ] `git diff --stat` shows only intended contract/runtime/UI/test/doc files.

  **QA Scenarios**:
  ```
  Scenario: Full regression suite passes
    Tool: Bash
    Steps: Run unit, py_compile, and node syntax checks exactly as listed in acceptance criteria.
    Expected: All exit code 0.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-6-full-regression.txt

  Scenario: Scope creep grep is clean
    Tool: Bash
    Steps: Run grep for old Host semantic fields and inspect matches.
    Expected: No runtime code path treats Host `host_state.fault_mode` or `latency_state` as semantic fault truth.
    Evidence: .sisyphus/evidence/host-agent-fault-ownership/task-6-grep-scope.txt
  ```

  **Commit**: NO | Message: `장애 판단 소유권 회귀 검증 정리` | Files: [tests/status_builders.py, tests/test_node_view_contracts.py, tests/test_controller_client_commands.py, docs/reference/ui-preview/preview.revised.jsx, any remaining docs touched by explicit grep]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle must give condition-by-condition **STRONG PASS** for intent fidelity, minimal scope, no unwanted additions, and no shortcuts. If not, revise and rerun before implementation/acceptance proceeds.
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ webapp-testing / Playwright)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Do not commit unless user explicitly requests commit/push.
- If later requested, use Korean plain messages matching repo style and split runtime, UI/docs, and tests if diff is large.

## Success Criteria
- Host no longer appears to be the semantic fault judge in runtime data, TUI, Web UI, or docs.
- Local Agent is the only semantic fault judgment owner.
- Existing control commands and EVENT compatibility field remain stable.
- No unrelated UI/routing/Monitor behavior changes occur.
- Oracle/QA final verification passes and user explicitly approves final verification summary.
