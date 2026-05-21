# 우회 Relay Routing 구현 계획

## TL;DR
> **Summary**: `r1b`, `r2b` backup relay node를 추가하되, full mesh가 아니라 primary path / backup path 두 경로만 허용하는 deterministic bypass routing을 구현한다. 기존 hop-by-hop ACK, `event_id` continuity, node-authored traffic snapshot 원칙을 보존한다.
> **Deliverables**:
> - `r1b`, `r2b` role/config/bootstrap 추가
> - constrained route policy와 `detail.routing` 상태 모델 추가
> - `EVENT.route_trace`와 Monitor 장애 위치 요약 추가
> - Agent/Relay delivery logic의 route-aware 확장
> - Controller/TUI/Web UI의 primary/backup route 및 Monitor fault-localization projection
> - unit/integration/browser QA
> **Effort**: Large
> **Parallel**: YES - 4 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 4/5 → Task 6/7 → Final Verification

## Context

### Original Request
- 사용자는 노드 장애에 대비해 우회 노드를 추가한다면 어떤 구조가 맞는지 물었다.
- 이후 “일단 하나만 구현하자는거야? 2개 동시에 구현하면 문제되는 점 있을까?”라고 물었고, 구조적으로 두 backup relay node 추가는 가능하되 full mesh는 피하는 방향으로 정리했다.
- 최종 요청: “구현 계획 작성해”.

### Interview Summary
- Current data path: `Host Simulator -> Local Agent -> Relay R1 -> Relay R2 -> Monitor`.
- Controller/UI는 data plane 밖에서 control/status surface만 담당한다.
- Monitor는 data plane의 최종 sink이므로, 우회가 발생한 이벤트를 받았을 때 “어디가 이상해서 어떤 경로로 우회됐는지”를 EVENT 자체에서 판단할 수 있어야 한다.
- 추천 구조: `r1b`, `r2b` 두 backup relay node를 추가하지만, 허용 경로는 아래 두 개로 제한한다.
  - Primary: `Host -> Agent -> R1 -> R2 -> Monitor`
  - Backup: `Host -> Agent -> R1B -> R2B -> Monitor`
- 금지 경로:
  - `R1 -> R2B`
  - `R1B -> R2`
  - arbitrary mesh / load balancing / duplicate fan-out

### Metis Review (gaps addressed)
- `PRIMARY`, `BYPASS_ACTIVE`, `DEGRADED`, `FAILED` 상태 전이표를 계획에 포함한다.
- Failback 정책을 default로 고정한다: 자동 primary 복귀 없음.
- Reroute trigger를 default로 고정한다: primary retry exhaustion 후 backup route 시도.
- Controller route override command는 이번 범위에서 제외한다.
- Late ACK / duplicate / backup failure edge case를 테스트에 포함한다.
- UI는 route decision에 관여하지 않고 snapshots만 projection한다.

## Work Objectives

### Core Objective
현재 교육용 relay chain에 deterministic backup route를 추가해, primary relay path 장애 시 같은 `event_id`가 backup path를 통해 Monitor까지 전달되고 hop-by-hop ACK가 정상 반환되는 과정을 관찰 가능하게 만든다.

### Deliverables
- `config.NODE_ENDPOINTS`, `ROLE_TO_NODE_ID`, `NODE_ORDER`, supervisor start order, role builder에 `r1b`, `r2b` 추가.
- Route policy contract: `PRIMARY_PATH`, `BACKUP_PATH`, no cross-path.
- `detail.routing` schema 추가.
- `EVENT.route_trace` schema 추가.
- Monitor의 `last_route_trace`, `last_fault_localization`, route-aware event summaries 추가.
- Agent와 Relay의 route-aware delivery implementation.
- Controller/TUI focused monitor와 Web UI route/fault localization visualization.
- Tests and QA evidence.

### Definition of Done (verifiable conditions with commands)
- `python -m unittest discover -s tests` passes.
- `node --check web_ui/static/app.js` passes.
- `python -m web_ui.server --web-port 28083` can start and expose `/api/state` with `r1b`, `r2b` nodes.
- Browser QA captures primary path and backup path rendering evidence under `.sisyphus/evidence/`.
- No source includes a data-plane route decision in Controller/UI or Web UI.
- Monitor status includes the failed hop / suspected node / active route for a rerouted event.

### Must Have
- Preserve `event_id` across retry and reroute.
- Preserve hop-by-hop ACK: upstream ACK only after selected downstream route succeeds.
- Keep `detail.traffic` as actual node-authored hop evidence.
- Add `detail.routing` as route decision/status metadata.
- Add `EVENT.route_trace` as the end-to-end route evidence carried to Monitor.
- Add Monitor fault-localization summary derived only from received `EVENT.route_trace`, not from Controller reconstruction.
- Route state enum: `PRIMARY`, `BYPASS_ACTIVE`, `DEGRADED`, `FAILED`.
- Only two logical paths are allowed: primary and backup.

### Must NOT Have
- No arbitrary mesh routing.
- No `R1 -> R2B` or `R1B -> R2` in this phase.
- No Controller/UI participation in data-plane routing.
- No Web UI direct EVENT/ACK traffic.
- No duplicate fan-out to primary and backup at the same time.
- No automatic failback to primary in this phase.
- No production-grade discovery, health scoring, scheduler, or persistent route DB.
- No Monitor-side guessing from global UI state when route trace is missing; fallback must say trace unavailable.

### Existing Structure Changes Required
- `EVENT` payload must become route-aware by adding optional `route_trace` and `routing` summary fields. This is backward-compatible because existing required EVENT fields remain unchanged.
- `LocalAgent._build_event()` must initialize route metadata on every emitted EVENT.
- `RelayNode._deliver_with_retry()` must append route trace entries for attempted downstream hops, including failed primary attempts and successful backup attempts.
- `Monitor.handle_network_message()` must persist route trace and derive a fault-localization summary before publishing status.
- `Monitor._event_summary()` and `recent_event_summaries` must include route summary fields so UI can show route/failure context without raw JSON dumping.
- `tests/status_builders.py` fixtures must be extended with route-aware EVENT/status examples.
- Web UI and TUI must show Monitor-derived fault localization separately from per-node `detail.routing`.

### EVENT Route Trace Contract
Each EVENT may include:

```json
{
  "route_trace": [
    {
      "from_node": "r1",
      "to_node": "r2",
      "route_id": "primary",
      "attempt_no": 3,
      "phase": "downstream_retry",
      "result": "timeout",
      "failure_reason": "timeout",
      "timestamp": "2026-05-21T00:00:00+00:00"
    },
    {
      "from_node": "r1b",
      "to_node": "r2b",
      "route_id": "backup",
      "attempt_no": 1,
      "phase": "downstream_event",
      "result": "acknowledged",
      "failure_reason": null,
      "timestamp": "2026-05-21T00:00:04+00:00"
    }
  ],
  "routing": {
    "route_state": "DEGRADED",
    "active_route": "backup",
    "failed_hop": "r1->r2",
    "suspected_node": "r2",
    "reroute_reason": "timeout"
  }
}
```

Rules:
- Trace entries are append-only per EVENT as the EVENT moves through Agent/Relay nodes.
- Failed attempts and successful attempts both get trace entries.
- `suspected_node` is a best-effort suspicion, not a hard assertion. UI wording must use “의심 노드” or “관찰된 실패 구간”.
- If `route_trace` is missing, Monitor must not fabricate a failure location.

### Monitor Fault Localization Model
Monitor derives and publishes:
- `last_route_trace`: latest received event's route trace.
- `last_route_summary`: active route, route state, failed hop, reroute reason.
- `last_fault_localization`:
  - `failure_scope`: `hop | node | unknown`
  - `failed_hop`: e.g. `r1->r2`
  - `suspected_node`: e.g. `r2`
  - `failure_reason`: e.g. `timeout`, `connection_error`, `delivery_failed`
  - `confidence`: `low | medium | high`
  - `basis`: short machine-readable reason such as `route_trace_failed_hop`.

Confidence rules:
- `high`: failed hop points to a node and that node's observed liveness/status also indicates offline/stale/unreachable in available status projection.
- `medium`: route trace shows a failed hop but peer liveness is live/unknown.
- `low`: route trace missing or ambiguous.

### Route State Transition Table
| Current | Trigger | Action | Next State | Upstream ACK? |
|---|---|---|---|---|
| `PRIMARY` | primary downstream ACK received | keep primary route | `PRIMARY` | YES |
| `PRIMARY` | primary attempt timeout before retry exhaustion | retry primary with same `event_id` | `PRIMARY` | NO |
| `PRIMARY` | primary retry exhausted, backup available | send same `event_id` on backup path | `BYPASS_ACTIVE` | NO |
| `BYPASS_ACTIVE` | backup downstream ACK received | keep backup route active; record failed primary | `DEGRADED` | YES |
| `BYPASS_ACTIVE` | backup retry exhausted | return existing `ERROR delivery_failed` upstream | `FAILED` | NO |
| `DEGRADED` | primary later appears live again | do not automatically fail back in this phase | `DEGRADED` | N/A |
| `FAILED` | reset command | clear route state and retry counters | `PRIMARY` | N/A |

Rules:
- `DEGRADED` means delivery succeeded through backup but the primary path remains the failed/default-disabled route for this run.
- Automatic failback is forbidden in this plan; only reset may clear route state.
- Reroute always preserves the original `event_id`.
- The current request/response transport may make true late ACK hard to observe; tests must still cover stale/delayed response handling with mocks.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after using existing Python stdlib `unittest` plus JS syntax check and browser QA.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy

### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 route contract/schema, Task 2 config/bootstrap registry.
Wave 2: Task 3 delivery/routing engine.
Wave 3: Task 4 controller/TUI projection, Task 5 Web UI projection, Task 6 docs/guides.
Wave 4: Task 7 end-to-end tests/QA hardening.

### Dependency Matrix (full, all tasks)
- Task 1: blocks Tasks 3, 4, 5, 6, 7.
- Task 2: blocks Tasks 3, 4, 5, 7.
- Task 3: blocks Tasks 4, 5, 7.
- Task 4: blocked by Tasks 1-3; blocks Task 7.
- Task 5: blocked by Tasks 1-3; blocks Task 7.
- Task 6: blocked by Task 1; can run after implementation details stabilize.
- Task 7: blocked by Tasks 1-6.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 2 tasks → quick, unspecified-high.
- Wave 2 → 1 task → deep.
- Wave 3 → 3 tasks → unspecified-high, visual-engineering, writing.
- Wave 4 → 1 task → unspecified-high.

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Route Contract and State Schema 고정

  **What to do**: Define a small route contract before changing delivery logic. Add constants/types/helpers in the most appropriate existing module or new internal module under `nw_demo/` for:
  - route ids: `primary`, `backup`
  - route states: `PRIMARY`, `BYPASS_ACTIVE`, `DEGRADED`, `FAILED`
  - node route membership:
    - primary path: `local-agent -> r1 -> r2 -> monitor`
    - backup path: `local-agent -> r1b -> r2b -> monitor`
  - forbidden cross-path edges: `r1 -> r2b`, `r1b -> r2`
  - `detail.routing` fields:
    - `route_state`
    - `active_route`
    - `primary_downstream`
    - `backup_downstream`
    - `active_downstream`
    - `failed_downstream`
    - `reroute_reason`
    - `event_id`
    - `route_generation`
  - `EVENT.route_trace` entry fields and `EVENT.routing` summary fields.
  - Monitor fault-localization output fields.
  Add contract tests proving default route state, invalid cross-path config behavior, backward-compatible EVENT parsing when `route_trace` is absent, and safe Monitor fallback when route trace is unavailable.

  **Must NOT do**: Do not implement dynamic discovery, scoring, load balancing, controller route override, or automatic failback.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: bounded contract and tests.
  - Skills: [`api-and-interface-design`] - schema/interface boundaries.
  - Omitted: [`webapp-testing`] - no browser behavior yet.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: Tasks 3, 4, 5, 6, 7 | Blocked By: none

  **References**:
  - Pattern: `IMPLEMENTATION_SPEC.md:594-617` - route abstraction, reroute reason, `event_id` continuity.
  - Pattern: `nw_demo/base.py:196-270` - traffic snapshot source-of-truth model to keep separate from route metadata.
  - Test: `tests/test_traffic_snapshot_contracts.py` - schema contract style.
  - Test: `tests/status_builders.py` - status fixture style.

  **Acceptance Criteria**:
  - [ ] `python -m unittest discover -s tests` passes.
  - [ ] Tests assert route state enum values and no cross-path route policy.
  - [ ] Tests assert `detail.routing` is additive and does not remove `detail.traffic`.
  - [ ] Tests assert `EVENT.route_trace` is optional for backward compatibility but required in reroute scenarios.
  - [ ] Tests assert Monitor fallback uses `failure_scope=unknown` when trace is missing.

  **QA Scenarios**:
  ```
  Scenario: Route contract rejects cross-path mesh
    Tool: Bash
    Steps: Run `python -m unittest tests.test_bypass_routing_contracts`.
    Expected: Test shows `r1 -> r2b` and `r1b -> r2` are rejected or ignored deterministically.
    Evidence: .sisyphus/evidence/task-1-route-contract.txt

  Scenario: Unknown route state is safe
    Tool: Bash
    Steps: Run a unit test that normalizes a status payload with unknown `detail.routing.route_state`.
    Expected: Consumer falls back to safe muted/unknown route display without exception.
    Evidence: .sisyphus/evidence/task-1-route-contract-error.txt

  Scenario: Monitor route trace fallback
    Tool: Bash
    Steps: Run a unit test with a legacy EVENT that has no `route_trace`.
    Expected: Monitor records the event and publishes `last_fault_localization.failure_scope=unknown` without guessing a node.
    Evidence: .sisyphus/evidence/task-1-route-trace-fallback.txt
  ```

  **Commit**: YES | Message: `feat(routing): define constrained bypass route contract` | Files: `nw_demo/*`, `tests/*`

- [ ] 2. Backup Relay Nodes 등록과 Bootstrap 확장

  **What to do**: Add `r1b` and `r2b` as concrete relay nodes in runtime configuration and process startup:
  - assign non-conflicting ports after current `9105`, e.g. `9106`, `9107` unless existing config has better reserved values.
  - update `NODE_ENDPOINTS`, `ROLE_TO_NODE_ID`, `NODE_ORDER`.
  - add roles such as `relay-r1b`, `relay-r2b`.
  - update `ROLE_START_ORDER` so monitor starts before relay sinks and agent starts last.
  - update `system.build_role()` to instantiate `RelayNode("r1b", ...)` and `RelayNode("r2b", ...)` with correct primary/backup path constraints.
  - update command target aliases and valid node targets if node-scoped start/pause/reset/kill should work for `r1b`, `r2b`.
  - add tests for command parsing and role registry.

  **Must NOT do**: Do not add new top-level service type; `r1b` and `r2b` are relay nodes, not new roles with different semantics.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: touches config, startup, command parsing, tests.
  - Skills: [] - no specialized skill beyond repo patterns.
  - Omitted: [`api-and-interface-design`] - contract is handled in Task 1.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: Tasks 3, 4, 5, 7 | Blocked By: none

  **References**:
  - Pattern: `nw_demo/config.py:20-36` - node endpoint/order/role mapping.
  - Pattern: `nw_demo/system.py:17-99` - supervisor startup and role builder.
  - Pattern: `nw_demo/controller_client.py:16-30` - valid node targets and aliases.
  - Test: `tests/test_controller_client_commands.py` - command parser contract.

  **Acceptance Criteria**:
  - [ ] `python -m unittest discover -s tests` passes.
  - [ ] `build_role("relay-r1b", ...)` returns a relay with `node_id == "r1b"`.
  - [ ] `build_role("relay-r2b", ...)` returns a relay with `node_id == "r2b"`.
  - [ ] `pause r1b`, `start r2b`, `reset r1b`, `kill r2b` parse to valid CONTROL messages.

  **QA Scenarios**:
  ```
  Scenario: Backup roles bootstrap
    Tool: Bash
    Steps: Run `python -m unittest tests.test_system_roles tests.test_controller_client_commands`.
    Expected: Backup relay roles and node-scoped commands are accepted.
    Evidence: .sisyphus/evidence/task-2-backup-bootstrap.txt

  Scenario: Invalid backup target rejected
    Tool: Bash
    Steps: Run parser test for `pause r3` and `kill all`.
    Expected: Invalid target returns user-facing error and no control message.
    Evidence: .sisyphus/evidence/task-2-backup-bootstrap-error.txt
  ```

  **Commit**: YES | Message: `feat(runtime): register backup relay nodes` | Files: `nw_demo/config.py`, `nw_demo/system.py`, `nw_demo/controller_client.py`, `tests/*`

- [ ] 3. Route-Aware Delivery Logic 구현

  **What to do**: Generalize delivery while preserving hop-by-hop ACK:
  - Local Agent sends to primary `r1` first; after primary route failure, sends to backup `r1b` with the same `event_id`.
  - `r1` sends to `r2`; `r1b` sends to `r2b`.
  - No cross-path edges.
  - Reroute happens only after primary retry exhaustion, not after a single transient timeout.
  - Upstream ACK is returned only after selected downstream path succeeds.
  - If primary and backup both fail, record `FAILED` and return existing `ERROR delivery_failed` semantics upstream.
  - Initialize `EVENT.route_trace` in Local Agent and append entries at every downstream attempt.
  - Add failed primary trace entries before backup attempt.
  - Add successful backup trace entries before returning upstream ACK.
  - Update `EVENT.routing` summary when route switches or fails.
  - Add stale/late ACK handling tests. If current request/response model cannot receive late ACK after timeout, test the equivalent stale response path with mocked delayed `send_request` results.
  - Update `pending_ack_detail` to include `route_id`, `active_downstream`, `failed_downstream`, and route attempt info.
  - Add `detail.routing` to Agent/Relay publish status.

  **Must NOT do**: Do not ACK upstream before downstream selected path success. Do not send to primary and backup simultaneously.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: critical protocol logic and edge cases.
  - Skills: [`debugging-and-error-recovery`, `api-and-interface-design`] - failure path and interface semantics.
  - Omitted: [`webapp-testing`] - backend protocol task.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: Tasks 4, 5, 7 | Blocked By: Tasks 1, 2

  **References**:
  - Pattern: `nw_demo/local_agent.py:136-329` - host polling, event creation, downstream ACK handling.
  - Pattern: `nw_demo/relay.py:118-430` - relay receive, retry, ACK, delivery failure logic.
  - Pattern: `nw_demo/messages.py` - ACK/EVENT helpers.
  - Test: `tests/test_status_detail_publishers.py:98-188` - relay status and delivery reset tests.

  **Acceptance Criteria**:
  - [ ] `python -m unittest discover -s tests` passes.
  - [ ] Test proves primary success keeps `route_state == PRIMARY`.
  - [ ] Test proves primary retry exhaustion then backup success yields `route_state == BYPASS_ACTIVE` or `DEGRADED` with same `event_id`.
  - [ ] Test proves rerouted EVENT delivered to Monitor includes `route_trace` with failed primary hop and successful backup hop.
  - [ ] Test proves primary and backup failure yields `FAILED` and no upstream ACK.
  - [ ] Test proves duplicate same `event_id` is not logged twice by Monitor.

  **QA Scenarios**:
  ```
  Scenario: Primary failure reroutes to backup
    Tool: Bash
    Steps: Run route-aware delivery unit/integration test with primary `send_request` mocked to timeout and backup mocked to ACK.
    Expected: Same `event_id` is sent to backup; `route_trace` contains primary failure and backup success; upstream receives ACK only after backup ACK.
    Evidence: .sisyphus/evidence/task-3-route-aware-delivery.txt

  Scenario: Both paths fail
    Tool: Bash
    Steps: Run test with primary and backup mocked as timeout/connection_error.
    Expected: Relay returns `ERROR delivery_failed`, `detail.routing.route_state == FAILED`, no upstream ACK record.
    Evidence: .sisyphus/evidence/task-3-route-aware-delivery-error.txt
  ```

  **Commit**: YES | Message: `feat(routing): reroute events through backup path` | Files: `nw_demo/local_agent.py`, `nw_demo/relay.py`, `nw_demo/*routing*`, `tests/*`

- [ ] 4. Controller/TUI Route Projection 추가

  **What to do**: Update controller normalization and terminal surfaces to include route and Monitor fault-localization information without turning controller into route owner:
  - Preserve `reported_state`, `observed_liveness`, `hop_state` separation.
  - `normalize_node_view()` carries `detail.routing` through unchanged.
  - Integrated overview shows concise route summary only, e.g. `route=PRIMARY active=r2` or `route=BYPASS_ACTIVE active=r2b reason=timeout`.
  - Focused node monitor shows structured route rows: primary downstream, backup downstream, active downstream, failed downstream, reroute reason, event id.
  - Monitor view shows final route and fault-localization summary from Monitor status:
    - `failed_hop`
    - `suspected_node`
    - `failure_reason`
    - `confidence`
    - `active_route`
  - If Monitor has no route trace, render `우회 근거 없음` / `판단 불가` rather than guessing.
  - Add tests for summary and focused rendering.

  **Must NOT do**: Do not reconstruct route decisions in controller from raw logs. Controller only projects node-authored `detail.routing` and Monitor-authored `last_fault_localization`.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: terminal rendering and normalized API contracts.
  - Skills: [] - follows existing controller patterns.
  - Omitted: [`webapp-testing`] - terminal/controller tests only.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: Task 7 | Blocked By: Tasks 1, 2, 3

  **References**:
  - Pattern: `nw_demo/controller_ui.py` - `normalize_node_view`, overview, focused monitor rendering.
  - Test: `tests/test_hop_state_visibility.py` - state axis separation.
  - Test: `tests/test_node_monitor_mode.py` - focused monitor behavior.

  **Acceptance Criteria**:
  - [ ] `python -m unittest discover -s tests` passes.
  - [ ] Integrated overview includes route summary for relays with `detail.routing`.
  - [ ] Focused relay monitor includes route rows.
  - [ ] Focused Monitor view includes failed hop, suspected node, reason, confidence, and active route when trace exists.
  - [ ] Focused Monitor view renders safe “판단 불가” fallback when trace is missing.
  - [ ] Existing hop summary tests still pass.

  **QA Scenarios**:
  ```
  Scenario: TUI overview shows bypass route
    Tool: Bash
    Steps: Run controller UI rendering tests with relay status fixture containing `BYPASS_ACTIVE`.
    Expected: Frame includes route summary without raw JSON payload dump.
    Evidence: .sisyphus/evidence/task-4-controller-route-projection.txt

  Scenario: Unknown routing does not crash focused monitor
    Tool: Bash
    Steps: Run focused monitor test with missing/unknown `detail.routing`.
    Expected: Focused monitor renders safe fallback and preserves traffic snapshot.
    Evidence: .sisyphus/evidence/task-4-controller-route-projection-error.txt

  Scenario: Monitor explains reroute cause
    Tool: Bash
    Steps: Run focused monitor rendering test with `last_fault_localization={failed_hop:"r1->r2", suspected_node:"r2", failure_reason:"timeout", confidence:"medium"}`.
    Expected: Frame shows observed failed hop and suspected node without raw EVENT JSON dump.
    Evidence: .sisyphus/evidence/task-4-monitor-fault-localization.txt
  ```

  **Commit**: YES | Message: `feat(controller): show route state in node monitors` | Files: `nw_demo/controller_ui.py`, `tests/*`

- [ ] 5. Web UI Primary/Backup Path Visualization 추가

  **What to do**: Extend Web UI runtime to render seven nodes and two constrained path lanes:
  - Add `r1b`, `r2b` to frontend node metadata/order/positions.
  - Add primary and backup path links:
    - `host-agent`
    - `agent-r1`, `r1-r2`, `r2-monitor`
    - `agent-r1b`, `r1b-r2b`, `r2b-monitor`
  - Do not add cross-path links.
  - Link tone still derives from node-authored `detail.traffic` for each actual link.
  - Route label/badge derives from `detail.routing` projection only.
  - Monitor detail inspector includes route diagnosis rows derived from Monitor status:
    - 관찰된 실패 구간
    - 의심 노드
    - 우회 이유
    - 활성 경로
    - 신뢰도
  - Node switches include `r1b`, `r2b` and use `pause/start`, not `kill`.
  - Ensure `runtime-status` layout remains fixed.
  - Add graceful behavior when backend lacks `r1b/r2b` statuses: backup nodes render as not started/unknown, not crash.

  **Must NOT do**: Do not make Web UI choose routes or send EVENT/ACK. Do not replace preview visual structure with a new dashboard.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: diagram geometry, SVG paths, browser QA.
  - Skills: [`webapp-testing`] - browser verification required.
  - Omitted: [`api-and-interface-design`] - schema already defined.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: Task 7 | Blocked By: Tasks 1, 2, 3

  **References**:
  - Pattern: `web_ui/static/app.js:1-30` - current fixed nodes and links.
  - Pattern: `web_ui/static/app.js:138-178` - hop_state link projection and label mapping.
  - Pattern: `docs/reference/ui-preview/WEB_UI_SPEC.md:183-212` - hop_state visual rules.
  - Pattern: `web_ui/static/app.css` - diagram and palette styling.

  **Acceptance Criteria**:
  - [ ] `node --check web_ui/static/app.js` passes.
  - [ ] `python -m unittest discover -s tests` passes.
  - [ ] Browser screenshot shows `r1b` and `r2b` backup lane.
  - [ ] Browser QA confirms no cross-path SVG links exist.
  - [ ] Browser QA confirms Monitor detail shows failed hop and suspected node for a rerouted event.
  - [ ] Node switches for `r1b`, `r2b` send `pause/start` commands.

  **QA Scenarios**:
  ```
  Scenario: Backup lane renders from runtime snapshot
    Tool: Playwright
    Steps: Start `python -m web_ui.server --web-port 28083`; open `http://127.0.0.1:28083`; wait for `/api/state`; capture screenshot.
    Expected: Primary and backup lanes are visible; `r1b`, `r2b` node cards exist; no cross-path lines are present.
    Evidence: .sisyphus/evidence/task-5-web-ui-backup-lane.png

  Scenario: Backup nodes missing or paused do not break UI
    Tool: Playwright
    Steps: Use mocked or partial `/api/state` without `r1b/r2b`, then with paused `r1b`.
    Expected: UI renders safe `시작 전`/muted state and controls remain stable.
    Evidence: .sisyphus/evidence/task-5-web-ui-backup-lane-error.png

  Scenario: Monitor detail shows fault localization
    Tool: Playwright
    Steps: Open Monitor detail after a rerouted event or mocked `/api/state` containing `last_fault_localization`.
    Expected: Detail shows `관찰된 실패 구간`, `의심 노드`, `우회 이유`, `활성 경로`, and `신뢰도`; raw JSON is not the primary UI.
    Evidence: .sisyphus/evidence/task-5-monitor-fault-localization.png
  ```

  **Commit**: YES | Message: `feat(web-ui): visualize constrained backup route` | Files: `web_ui/static/*`, `docs/reference/ui-preview/WEB_UI_SPEC.md`, `tests/*`

- [ ] 6. Canonical Docs and User Guides 업데이트

  **What to do**: Update canonical and guide docs to describe the implemented route behavior:
  - `IMPLEMENTATION_SPEC.md`: current route structure, state enum, ACK/reroute semantics, no cross-path policy, no automatic failback.
  - `IMPLEMENTATION_SPEC.md`: EVENT route trace, Monitor fault-localization semantics, and confidence wording.
  - `INTENT_ALIGNMENT_NOTE.md`: clarify that two backup relay nodes are allowed only as constrained primary/backup route, not arbitrary mesh.
  - `AI_IMPLEMENTATION_BRIEF.md`: concise latest decision and next-session handoff.
  - `README.md`: update roles/ports/controller commands only if runtime invocation changes.
  - `docs/reference/network-project/guide/CONTROL.md`: include `r1b/r2b` node controls if exposed.
  - UI spec: backup lane visual acceptance rules and Monitor diagnosis rows.

  **Must NOT do**: Do not create new root markdown. Do not duplicate long implementation history in `AI_IMPLEMENTATION_BRIEF.md`.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: canonical docs and guides.
  - Skills: [] - repository markdown governance is enough.
  - Omitted: [`webapp-testing`] - docs only.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: Task 7 | Blocked By: Task 1

  **References**:
  - Pattern: `AGENTS.md` - root markdown governance.
  - Pattern: `IMPLEMENTATION_SPEC.md:586-617` - future route extension section to convert into current behavior after implementation.
  - Pattern: `AI_IMPLEMENTATION_BRIEF.md:135-142` - open issues around item 2.
  - Pattern: `docs/reference/network-project/guide/CONTROL.md` - user command guide.

  **Acceptance Criteria**:
  - [ ] Markdown LSP or available markdown checks show no touched-doc errors.
  - [ ] No new root `.md` file exists outside allowed list.
  - [ ] Docs describe exact allowed paths and explicitly exclude cross-path mesh.
  - [ ] Docs distinguish `detail.routing` for node/controller projection from `EVENT.route_trace` for Monitor final diagnosis.

  **QA Scenarios**:
  ```
  Scenario: Docs reflect constrained route behavior
    Tool: Bash
    Steps: Run repository markdown/content checks available in environment, or inspect changed markdown paths with linter/LSP diagnostics.
    Expected: No markdown diagnostics for touched docs; route policy appears in spec and guide.
    Evidence: .sisyphus/evidence/task-6-docs-route-policy.txt

  Scenario: Root markdown governance preserved
    Tool: Bash
    Steps: Run a check that root markdown files are limited to README.md, AGENTS.md, IMPLEMENTATION_SPEC.md, INTENT_ALIGNMENT_NOTE.md, AI_IMPLEMENTATION_BRIEF.md.
    Expected: No extra root markdown files.
    Evidence: .sisyphus/evidence/task-6-docs-route-policy-error.txt
  ```

  **Commit**: YES | Message: `docs(routing): document constrained bypass path` | Files: `README.md`, `IMPLEMENTATION_SPEC.md`, `INTENT_ALIGNMENT_NOTE.md`, `AI_IMPLEMENTATION_BRIEF.md`, `docs/reference/*`

- [ ] 7. End-to-End Route QA and Regression Hardening

  **What to do**: Add final integration and regression coverage after implementation:
  - Run full tests.
  - Add or update integration tests for runtime with `r1b/r2b`.
  - Exercise primary normal path.
  - Pause/stop primary route node and verify backup route activates.
  - Pause/stop backup route node too and verify `FAILED` with no false ACK.
  - Verify Monitor dedup with same `event_id` across reroute.
  - Verify Monitor stores `route_trace` and publishes `last_fault_localization` for rerouted events.
  - Verify `/api/state` includes route metadata and Web UI consumes it.
  - Capture CLI/Web UI evidence.

  **Must NOT do**: Do not accept “looks okay” without captured evidence. Do not rely on manual user verification.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: cross-layer regression and runtime QA.
  - Skills: [`debugging-and-error-recovery`, `webapp-testing`] - failure recovery and browser evidence.
  - Omitted: [`api-and-interface-design`] - interface already implemented.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: Final Verification | Blocked By: Tasks 1-6

  **References**:
  - Pattern: `README.md:123-145` - Web UI runtime endpoints.
  - Pattern: `tests/test_hop_state_visibility.py` - hop state regression.
  - Pattern: `tests/test_status_detail_publishers.py` - status publisher regression.
  - Pattern: `web_ui/server.py` - `/api/state` and `/api/control` wiring to preserve.

  **Acceptance Criteria**:
  - [ ] `python -m unittest discover -s tests` passes.
  - [ ] `node --check web_ui/static/app.js` passes.
  - [ ] Browser QA evidence exists for primary and backup route states.
  - [ ] Integration evidence shows same `event_id` reaches Monitor through backup route.
  - [ ] Integration evidence shows Monitor reports the observed failed hop and suspected node from `route_trace`.
  - [ ] No Controller/UI code forwards EVENT/ACK data-plane messages.

  **QA Scenarios**:
  ```
  Scenario: Primary path normal operation
    Tool: Bash + Playwright
    Steps: Start Web UI runtime; wait for all nodes live; trigger normal host update/fault; inspect `/api/state` and browser path labels.
    Expected: `route_state=PRIMARY`, primary links acknowledged, backup lane idle/not selected.
    Evidence: .sisyphus/evidence/task-7-e2e-primary.png

  Scenario: Primary failure activates backup path
    Tool: Bash + Playwright
    Steps: Pause/stop primary route node according to implemented command; trigger event; inspect `/api/state`; capture browser screenshot.
    Expected: Same event id reroutes through backup path; `route_state=BYPASS_ACTIVE` or `DEGRADED`; Monitor logs once; Monitor reports failed hop/suspected node; upstream ACK follows backup success.
    Evidence: .sisyphus/evidence/task-7-e2e-bypass.png

  Scenario: Primary and backup both fail
    Tool: Bash + Playwright
    Steps: Pause/stop both primary and backup downstream nodes; trigger event.
    Expected: `route_state=FAILED`, visible failure path, no false acknowledged link, no duplicate Monitor record.
    Evidence: .sisyphus/evidence/task-7-e2e-failed.png
  ```

  **Commit**: YES | Message: `test(routing): verify bypass route end to end` | Files: `tests/*`, `.sisyphus/evidence/*`

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright for Web UI)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Use task-sized commits only after each task passes its task-local tests.
- Do not commit `.sisyphus/evidence/*` unless repository convention expects evidence artifacts to be committed; otherwise keep evidence as local QA output and mention paths in summary.
- Suggested sequence:
  1. `feat(routing): define constrained bypass route contract`
  2. `feat(runtime): register backup relay nodes`
  3. `feat(routing): reroute events through backup path`
  4. `feat(controller): show route state in node monitors`
  5. `feat(web-ui): visualize constrained backup route`
  6. `docs(routing): document constrained bypass path`
  7. `test(routing): verify bypass route end to end`

## Success Criteria
- The system still demonstrates the original primary chain clearly.
- A primary relay path failure can be induced and observed.
- The same logical event keeps the same `event_id` while moving to backup path.
- Monitor records the event once.
- Monitor can explain the observed failed hop, suspected node, reroute reason, active route, and confidence from received EVENT trace.
- Upstream ACK remains causally dependent on downstream success.
- UI displays primary vs backup route state without joining the data plane.
- Tests and QA evidence cover happy path, bypass path, and both-path failure.
