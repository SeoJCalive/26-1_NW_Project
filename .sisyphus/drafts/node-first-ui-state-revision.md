# Draft: Node-first UI State Revision

## Requirements (confirmed)
- 처리 상태와 노드/프로세스 활성화 상태는 같지 않으므로 분리한다.
- 노드 활성화 상태는 모든 노드 공통 상태등으로 통일한다.
- 상태등의 원천은 `observed_liveness`이며 초록색은 최근 `STATUS`를 받아 살아 있음, 회색은 꺼짐 또는 미관측을 뜻한다.
- 상태등은 노드 카드 외부 표시와 노드 기본 정보 양쪽에서 사용한다.
- `[처리상태: 실행 중]` 같은 텍스트 칸으로 상태등을 대체하지 않는다.
- `STATUS.state` / `reported_state`는 노드가 스스로 보고한 실행 상태이며 상태등과 합치지 않는다.
- 처리/통신 활동 상태는 노드별 실제 데이터(`hop_state`, ACK, retry, pending ACK, latest/downstream/sink/ack result 등)에서 가져온다.
- 노드 선택 전에도 기본 활동 요약을 카드에서 볼 수 있게 한다.
- Host, Agent, R1, R2, Monitor 상세는 공통 템플릿으로 억지 통일하지 않고 노드별 실제 데이터에 맞춰 개별 설계한다.
- 공통 요소는 상태등, node id, role 정도로 최소화한다.
- 실제 코드/문서에서 확인 가능한 JSON/상태 정보만 넣는다.
- `비고`, `설명`, AI가 만든 해석 문장처럼 실제 node가 제공하지 않는 서술형 정보는 제거한다.
- 상세 정보는 왼쪽 고정 영역이 아니라 노드 클릭 시 열리고 `X`로 닫히는 약 1/3 너비 패널로 만든다.
- 공간 부족을 이유로 정보를 임의로 줄이거나 의미를 뭉개지 않는다.

## Technical Decisions
- Plan artifact path: `.sisyphus/plans/node-first-ui-state-revision.md`.
- Change should remain limited to static preview/reference assets and supporting project living docs if implementation changes later require context update.
- No Python runtime/TUI/data-plane behavior changes should be planned unless research finds a hard blocker.
- Per-node detail content must be explicitly planned from code/docs:
  - Host: host metrics/fault/tick + host-agent request/response traffic.
  - Agent: host input fetch/result, detected fault, emitted event, downstream delivery result + previous/next traffic.
  - R1/R2: received event, pending ACK/retry/delivery state, dedup counters, downstream/forwarded results + previous/next traffic.
  - Monitor: sink/log result, ACK result, host state table, recent event summaries, duplicate/out-of-order/total counts + previous traffic.

## Research Findings
- Data contract: `STATUS` base fields are `msg_type`, `node_id`, `state`, `queue_length`, `pending_ack_count`, `retry_total`, `duplicate_dropped`, `note`, `timestamp`; `STATUS_REPORT` wraps `status` with `control_token` and timestamp when token exists.
- Normalized node view: `controller_ui.normalize_node_view` returns `reported_state` from `STATUS.state`, `observed_liveness` from controller `last_seen`, and keeps extra status fields under `details`.
- Canonical separation: `IMPLEMENTATION_SPEC.md` states `reported_state`, `observed_liveness`, and `hop_state` do not replace one another.
- Traffic contract: every node detail traffic snapshot has `capture_seq`, `captured_at`, `previous_peer`, `next_peer`, `recent`; peer snapshot has `peer_node_id`, `peer_role`, `hop_state`, `failure_reason`, `last_received`, `last_sent`.
- Per-node data: Host has `host_state` and detail fields for tick/fault/host state/traffic; Agent has latest input/result/fault/emitted event/downstream/traffic; Relay has recent ids, last received event, pending ACK state, downstream/forwarded results, traffic; Monitor has recent events, host state table, out-of-order/total/duplicate counts, sink/ack/traffic details.
- UI pattern: current `preview.revised.jsx` stores static node data in `revisedNodes`, selects node via `useState("r2")`, and renders `HeaderSummary`, `PageChrome`, `DiagramCanvas`, `NodeCard`, `ControlPanel`, `EventTimeline`, `DetailPanel` plus shared detail sections.
- UI gaps: current page remains overview-first, detail panel is fixed `400px` sticky right panel, liveness badge is not a standardized lamp component, and `note`/`reason`/synthetic `activityLogs` remain as narrative layers.
- Verification: no dedicated pytest/Playwright config; repo uses stdlib `unittest`, `runSanityChecks()` in `preview.revised.jsx`, Chromium/DOM evidence artifacts, and `.sisyphus/evidence/task-{N}-{slug}.{ext}` convention.
- One UI-pattern exploration failed due external provider/account 403, then succeeded through retry with `explore`; do not treat the failed agent as repository evidence.
- Additional direct verification: `host_simulator.py`, `local_agent.py`, `relay.py`, `monitor.py`, `base.py`, `messages.py`, and `IMPLEMENTATION_SPEC.md` confirm each per-node display item above and the traffic/ACK/STATUS contracts.

## Open Questions
- None currently blocking; if research finds missing field references, use conservative static-preview-only defaults and mark them in the plan.

## Scope Boundaries
- INCLUDE: revise static Web UI preview plan around node-first cards, liveness lamps, per-node details, no fabricated prose, click-open detail panel, and verification.
- EXCLUDE: production Web UI/API/WebSocket/gateway/package setup, runtime node behavior changes, TUI changes, data-plane protocol changes, extra controller graph node/hub.
