# 네트워크 프로젝트 구현 명세서

이 문서는 이 저장소의 **기술 canonical source**다.
현재 구현의 구조, 메시지, 동작 규칙, 구현 범위의 최종 기준은 여기 둔다.

문서 역할은 다음처럼 분리한다.

- 실행 방법과 현재 런타임 진입 정보: [`README.md`](./README.md)
- 사용자 의도와 해석 가드레일: [`INTENT_ALIGNMENT_NOTE.md`](./INTENT_ALIGNMENT_NOTE.md)
- 여러 세션의 현재 작업 맥락과 최근 결정: [`AI_IMPLEMENTATION_BRIEF.md`](./AI_IMPLEMENTATION_BRIEF.md)
- 과거 설계 배경과 역사적 맥락: [`PROCESS_SEPARATION_ARCHITECTURE.md`](./docs/history/PROCESS_SEPARATION_ARCHITECTURE.md)

---

## 1. 프로젝트 목표

이 프로젝트는 **운영 서비스**가 아니라 **네트워크 수업용 시스템 구성 데모**다.
목표는 네트워크 개념이 눈에 보이고 설명 가능한 구조를 만드는 것이다.

- 이벤트 기반 통신
- hop-by-hop 전달
- ACK
- timeout 및 retry
- duplicate suppression
- fault injection의 가시적 효과

시스템은 복잡한 분산 시스템 기능보다 **교육적 가시성**, **구조적 명확성**, **구현 단순성**을 우선한다.

---

## 2. 핵심 설계 원칙

### 2.1 구조는 유지하고 과정은 단순화한다

기본 구조는 다음을 유지한다.

`Host Simulator -> Local Agent -> Relay R1 -> Relay R2 -> Monitor`

현재 우회 구조는 위 primary chain 옆에 제한된 backup chain을 둔다.

`Host Simulator -> Local Agent -> Relay R1B -> Relay R2B -> Monitor`

`Controller/UI`는 데이터 경로 밖에서 제어와 관찰을 담당한다.

단순화 대상은 구조 자체가 아니라 각 단계 내부 로직의 깊이다.

### 2.2 속도보다 가시성을 우선한다

사람이 ACK, timeout, retry, duplicate suppression을 따라갈 수 있을 만큼 충분히 천천히 움직여야 한다.

사용자는 최소한 다음 흐름을 읽을 수 있어야 한다.

1. fault 발생
2. event 생성
3. R1 forwarding
4. R2 forwarding
5. Monitor logging
6. ACK 반환
7. 필요 시 timeout / retry 발생
8. duplicate 재전송 시 중복 처리 방지

### 2.3 기능 수보다 교육적 가치가 우선이다

드러나야 하는 핵심 개념은 다음과 같다.

- message passing
- ACK / retry를 통한 신뢰성 전달
- `event_id` 기반 duplicate 처리
- `seq_no` 기반 순서 관찰
- relay node의 역할
- fault injection과 그 가시적 효과

### 2.4 control plane은 shared token을 유지하되 envelope 경계로 정리한다

현재 `control_token`은 data plane 개념이 아니라 `Controller/UI`와 각 role process 사이의
**control / status plane 경계**를 위한 공통 인증 장치다.

- shared token 자체는 유지한다.
- token은 가능한 한 payload 본문이 아니라 **control-plane envelope / wrapper 경계**에 둔다.
- TUI와 이후 Web UI는 node에 직접 붙는 별도 peer가 아니라,
  **controller / gateway surface를 통해** 제어와 관찰을 수행하는 소비자로 본다.
- 이후 구조 확장 시에도 EVENT / ACK data plane과 control / status plane을 섞지 않는다.

### 2.5 앞으로의 확장을 고려한 설계를 현재 기준에 포함한다

이 프로젝트는 현재 최소 데모이지만, 이후 작업이 아래 순서로 이어질 것을 전제로 한다.

1. node-first TUI 모니터링을 먼저 정교화하고, 그 표현 경험을 Web UI로 옮긴다.
2. 우회 node / 우회 경로와 그것을 강제하는 critical fault를 도입한다.
3. 프로세스 실행 위치를 Linux / Windows 등 여러 host로 분리한다.
4. 위 세 단계가 정리된 이후에, reboot를 넘는 실질 recovery를 다룬다.

따라서 현재 구조와 문서도 아래 조건을 만족해야 한다.

- 단일 고정 경로 가정을 영구 기준처럼 박지 않는다.
- 단일 localhost 배치를 영구 기준처럼 박지 않는다.
- UI를 node와 같은 protocol peer로 키우지 않는다.
- 나중 단계가 오더라도 현재 control-plane 의미를 다시 해석하지 않도록 확장 지점을 남긴다.

---

## 3. 최종 시스템 구조

### 3.1 구성 요소

#### Host Simulator
- 주기적으로 host 상태를 생성한다.
- 정상 상태와 fault 상태를 시뮬레이션한다.
- 네트워크 EVENT를 직접 forwarding 하지 않는다.

#### Local Agent
- Host Simulator의 상태를 읽는다.
- 정상 host 상태 변화와 임계치 초과 fault를 감지한다.
- 정상 상태 변화는 `HOST_STATE_UPDATE` EVENT로, fault는 해당 fault EVENT로 생성해 Relay R1으로 전달한다.
- primary hop 실패가 관찰되면 같은 `event_id`를 유지해 Relay R1B backup 경로를 순차 시도한다.

#### Relay R1
- Local Agent의 EVENT를 수신한다.
- 최소 필드를 검증한다.
- `event_id` 기준 duplicate를 검사한다.
- Relay R2로 전달하고 ACK / timeout / retry를 소유한다.

#### Relay R2
- Relay R1의 EVENT를 수신한다.
- 최소 필드를 검증한다.
- `event_id` 기준 duplicate를 검사한다.
- Monitor로 전달하고 ACK / timeout / retry를 소유한다.

#### Relay R1B
- Local Agent가 primary hop 실패를 관찰한 뒤 보낸 backup `EVENT`만 처리한다.
- Relay R2B로만 전달한다.
- `R1B -> R2` 같은 primary/backup 교차 경로는 허용하지 않는다.

#### Relay R2B
- Relay R1B의 backup `EVENT`만 처리한다.
- Monitor로만 전달한다.
- `R2B -> R2`나 `R2B -> R1` 같은 mesh forwarding은 허용하지 않는다.

#### Monitor
- 최종 sink 역할을 한다.
- 이벤트를 기록하고 현재 상태 뷰를 갱신한다.
- 처리 후 ACK를 반환한다.

#### Controller / UI
- 시스템 start / pause / reset과 fault injection을 수행한다.
- 각 노드의 STATUS를 받아 표시한다.
- 데이터 경로 안의 forwarding node가 아니다.

#### Web UI
- `web_ui/` 아래의 Python stdlib HTTP + plain HTML/CSS/JS runtime surface다.
- TUI 출력이나 terminal 렌더링 결과를 데이터 소스로 삼지 않는다.
- Controller/Gateway가 수신한 `STATUS_REPORT` / `STATUS`와 각 node의 `detail.traffic` 자료를 JSON snapshot으로 읽어 표시한다.
- Host / Agent / R1 / R2 / R1B / R2B / Monitor data path에 새 peer로 참여하지 않는다.
- frontend visual structure는 `docs/reference/ui-preview/WEB_UI_SPEC.md`와 `docs/reference/ui-preview/preview.revised.jsx`를 따른다.
- runtime 연결을 붙인다는 이유로 preview의 diagram canvas, node card, SVG path, in-canvas detail inspector, palette, typography를 임의로 다른 dashboard로 재설계하지 않는다.
- visual structure를 바꾸려면 먼저 `WEB_UI_SPEC.md`와 `INTENT_ALIGNMENT_NOTE.md`를 갱신해 기준 변경을 명시한다.

### 3.2 경로 정의

#### 데이터 경로
Primary: `Host Simulator -> Local Agent -> Relay R1 -> Relay R2 -> Monitor`

Backup: `Host Simulator -> Local Agent -> Relay R1B -> Relay R2B -> Monitor`

허용 data-plane edge는 아래로 제한한다.

- `local-agent -> r1 -> r2 -> monitor`
- `local-agent -> r1b -> r2b -> monitor`

다음 교차 경로는 허용하지 않는다.

- `r1 -> r2b`
- `r1b -> r2`

#### 제어 경로
`Controller/UI -> Host Simulator, Local Agent, Relay R1, Relay R2, Relay R1B, Relay R2B, Monitor`

#### 상태 / 보고 경로
`각 프로세스 -> Controller/UI`

### 3.3 control-plane surface

현재 TUI viewer와 이후 Web UI는 모두 **동일한 controller / gateway surface의 다른 표현 계층**으로 본다.

- role process는 controller에 상태를 publish하고 controller에서 제어를 받는다.
- viewer는 이 controller surface를 terminal에 표현한 것이다.
- Web UI는 이 controller surface를 HTTP/JSON + browser 화면으로 표현한 것이다.
- Web UI가 추가되더라도 node에 직접 붙는 새 data-plane 주체로 해석하지 않는다.
- external controller client도 같은 control-plane surface의 입력 채널로 본다.

---

## 4. 범위 결정

### 4.1 반드시 구현할 것

- Host / Agent / primary relays / backup relays / Monitor / Controller-UI 역할 의미 유지
- primary relay(`R1`, `R2`)와 backup relay(`R1B`, `R2B`) 유지
- host 상태 기반 event 생성
- JSON 메시지 형식
- `event_id`
- `seq_no`
- hop-by-hop ACK
- timeout 및 retry
- duplicate suppression
- 눈에 보이는 fault injection
- monitor logging 및 current-state 표시
- 시스템 진행 상황이 보이는 UI 또는 control 화면

### 4.2 단순화할 것

- 작고 고정된 timeout 값
- 작고 고정된 retry 횟수
- 최소한의 message type
- 최소한의 state table
- 복잡한 scheduling 로직 없음
- 고급 persistence 요구 없음
- 무거운 orchestration / failover engine 없음

### 4.3 첫 구현에서 필요하지 않은 것

- 고급 failover routing
- 다중 backup target
- production-grade durability
- 복잡한 buffering / replay
- 고성능 동시성 최적화

### 4.4 기본 타이밍 기준

기본 데모 타이밍은 README의 빠른 이해 기준과 맞춘다.

- host tick / agent poll / status refresh는 기본 `2.0`초 단위다.
- hop ACK timeout은 기본 `2.0`초다.
- relay processing delay는 기본 `1.5`초이며, `delay r1|r2|r1b|r2b <sec>` 명령으로 조정할 수 있다.
- relay는 upstream EVENT 수신 사실을 processing delay 전에 publish해, Agent -> R1 같은 hop 도착 여부가 늦게 보이지 않게 한다.

---

## 5. 메시지 명세

### 5.1 메시지 종류

- `EVENT`: fault 또는 상태 변화 이벤트
- `ACK`: hop-by-hop acknowledgment
- `CONTROL`: controller가 보내는 제어 명령
- `STATUS`: 각 node가 controller/viewer에 보고하는 상태
- `STATUS_REPORT`: shared `control_token`이 있을 때 `STATUS`를 감싸 인증하는 controller 전용 wrapper

### 5.2 EVENT 형식

```json
{
  "msg_type": "EVENT",
  "event_id": "evt-host1-42",
  "seq_no": 42,
  "host_id": "host-1",
  "agent_id": "agent-1",
  "event_type": "CPU_SPIKE",
  "severity": "WARN",
  "timestamp": "2026-04-21T12:00:00",
  "payload": {
    "cpu": 95
  }
}
```

필수 필드:

- `msg_type`
- `event_id`
- `seq_no`
- `host_id`
- `event_type`
- `timestamp`

### 5.3 ACK 형식

```json
{
  "msg_type": "ACK",
  "ack_for": "evt-host1-42",
  "from_node": "r2",
  "timestamp": "2026-04-21T12:00:03"
}
```

### 5.4 CONTROL 형식

```json
{
  "msg_type": "CONTROL",
  "command": "inject_fault",
  "target": "host-simulator",
  "params": {
    "fault_type": "CPU_SPIKE",
    "duration_sec": 6
  }
}
```

### 5.5 STATUS 형식

```json
{
  "msg_type": "STATUS",
  "node_id": "r1",
  "state": "RUNNING",
  "queue_length": 1,
  "pending_ack_count": 1,
  "retry_total": 2,
  "duplicate_dropped": 0
}
```

Controller/UI는 이 `STATUS.state`를 **node가 스스로 보고한 상태**로 그대로 보존한다.
`unknown` / `live` / `stale` / `offline` 같은 관찰 liveness와 `last_seen` freshness는 controller 수신 시각을 기준으로 **별도로 정규화해 파생**하며, `shutdown` 요청 직후에는 관찰상 즉시 offline으로 단정하지 않는다.

### 5.6 STATUS_REPORT 형식

shared `control_token`이 설정된 런타임에서는 node가 raw `STATUS`를 그대로 노출하지 않고, 아래 wrapper로 controller/UI에 전송한다.

```json
{
  "msg_type": "STATUS_REPORT",
  "control_token": "shared-secret",
  "status": {
    "msg_type": "STATUS",
    "node_id": "r1",
    "state": "RUNNING"
  }
}
```

즉, `control_token`은 인증 wrapper에만 존재하고 node status payload 자체에는 포함되지 않는다.

### 5.7 control-plane 확장 규칙

현재 구현은 `CONTROL`과 `STATUS_REPORT`의 구체적인 shape가 완전히 대칭인 것은 아니지만,
개념적으로는 둘 다 동일한 control-plane 경계에 속한다.

- 앞으로 control/status protocol을 정리할 때는 **token을 payload 본문에서 더 바깥쪽으로 밀어내는 방향**을 우선한다.
- 이후 Web UI나 multi-host 구조가 추가되더라도, UI 쪽 소비자는 token 세부 shape보다 controller / gateway contract를 우선 사용한다.
- 새 구조가 필요해져도 shared token 모델을 즉시 폐기하지 않고, 먼저 envelope / gateway 경계를 정리하는 쪽을 우선한다.

---

## 6. 런타임 시간 규칙

가시성을 위한 권장 기본값은 다음과 같다.

- host update tick: `1-2 sec`
- agent polling interval: `1-2 sec`
- relay processing delay for display: `0.5-1.5 sec`
- ACK timeout: `2-4 sec`
- max retry count: `3`
- status / UI refresh interval: `1-2 sec`

초기 버전은 설정 가능성을 열어 두더라도, 눈으로 흐름이 보이는 고정 기본값을 우선한다.

---

## 7. 프로세스 수준 동작

### 7.1 Host Simulator

#### 책임
- 현재 시뮬레이션된 host 상태 유지
- 시간에 따라 정상 또는 fault 상태 생성

#### 최소 상태
- `cpu_usage`
- `memory_usage`
- `service_state`
- `latency_state`
- `fault_mode`
- `last_update_time`

#### 최소 지원 fault
- `CPU_SPIKE`
- `SERVICE_DOWN`
- `LATENCY_HIGH`

### 7.2 Local Agent

#### 책임
- Host Simulator polling
- 의미 있는 상태 변화 감지
- EVENT 생성
- `seq_no` 증가
- Relay R1으로 EVENT 전송

#### 이벤트 생성 규칙
- 의미 있는 변화 또는 임계치 초과 때만 생성
- 같은 이벤트를 매 tick마다 spam 하지 않음

### 7.3 Relay R1

#### 책임
- EVENT 수신
- 최소 필드 검증
- dedup cache 검사
- R2로 전달
- R2의 ACK 대기
- timeout 시 retry

#### 내부 상태
- `received_id_cache`
- `pending_ack_table`
- `retry_count`
- `running_state`

### 7.4 Relay R2

#### 책임
- EVENT 수신
- 최소 필드 검증
- dedup cache 검사
- Monitor로 전달
- Monitor의 ACK 대기
- timeout 시 retry

#### 내부 상태
- `received_id_cache`
- `pending_ack_table`
- `retry_count`
- `running_state`

### 7.5 Monitor

#### 책임
- 최종 EVENT 수신
- 필드 검증
- `event_id` 기준 deduplicate
- event log 추가
- host state view 갱신
- 처리 후 ACK 반환

### 7.6 Controller / UI

#### 최소 명령
- `start` / `start <node>`
- `pause` / `pause <node>`
- `reset` / `reset <node>`
- `shutdown` 기반의 node-scoped `kill <node>`
- `fault cpu|service|latency on|off` 기반의 수동 fault toggle. Web UI는 이 형태를 우선 노출하고, duration 기반 `inject_fault`는 controller/script 호환 경로로 유지한다.
- `focus <node>` / `overview` / `focus all`은 node 제어가 아니라 controller/UI 내부 화면 전환 명령이다.
- `quit` / `exit`는 controller/viewer 종료 명령이며, supervisor-managed viewer에서는 child role process도 함께 정리한다.

viewer의 node monitor는 같은 TUI surface 안에서 local command 입력을 받을 수 있고,
별도 external controller terminal도 동일한 제어 경로를 사용한다.
이때 controller와 role process 사이의 `CONTROL` 요청과 `STATUS_REPORT` wrapper는 shared `control_token`으로 인증되며,
token이 맞지 않는 요청은 수락하지 않는다.

기본 viewer/demo 모드는 shared token이 없으면 private token을 내부적으로 자동 생성해 child role에만 전달한다.
이 private token은 화면이나 argv에 그대로 노출하지 않는다.

standalone role / standalone controller UI / external controller client는 기본적으로 shared token이 있어야 하며,
의도적으로 무인증 제어를 허용하려면 명시적 `--allow-unauthenticated-control`이 필요하다.

Monitor는 데이터 경로의 최종 node/sink이며, 별도 tmux 관찰 세션으로 취급하지 않는다.
로컬 기본 viewer에서는 Host / Agent / R1 / R2 / R1B / R2B와 같은 supervisor-managed child role로 기동하고 종료한다.

#### 최소 표시 항목
- node reported state 및 observed liveness
- recent events
- retry count
- duplicate count
- current host status

#### monitoring surface 분리 원칙
- integrated viewer는 **summary-first overview**로 유지한다.
- full payload body나 긴 raw log dump는 integrated viewer에 직접 출력하지 않는다.
- node forensic 관찰은 standalone controller UI의 focused mode(`--role controller --focus-node <node>`)에서 다룬다.
- focused mode는 단일 node의 structured traffic snapshot과 role detail을 함께 보여준다.
- `--focus-node`는 시작 시 초기 focused mode를 정하는 seed이며, 실행 중에는 같은 controller/UI의 `viewer>` 프롬프트에서 `focus host|agent|r1|r2|r1b|r2b|monitor`로 대상을 바꾼다.
- runtime focus 명령에서 `host`는 `host-simulator`, `agent`는 `local-agent`의 사용자용 별칭이다.
- `overview`와 `focus all`은 `focus_node = None`으로 돌아가는 local UI state 전환이다.
- `focus` / `overview`는 `CONTROL` 메시지, `STATUS`, `STATUS_REPORT`, node-authored `detail.traffic` schema를 변경하지 않는다.
- interactive TUI의 `viewer>` 입력줄은 terminal bottom row에 고정하고, 입력 중에도 renderer가 같은 row를 직접 갱신한다. 빈 Enter는 no-op이며 전체 화면을 다시 열지 않는다.
- 방향키 escape sequence는 command로 처리하지 않고 버린다. 현재 viewer는 shell-style history navigation을 지원하지 않는다.
- focused mode의 `최근 노드 활동`은 전역 node activity가 아니라 현재 focus 대상 node의 활동만 최대 10줄 표시한다.

#### node별 richer detail
- Host: tick, fault active 여부, 현재 host_state
- Local Agent: latest input state/result, detected fault, emitted event, downstream result
- Relay: recent received event, pending ACK state, downstream result, forwarded result
- Monitor: recent event summaries, last processed event, sink result, ack result

#### structured traffic snapshot 규칙
- 각 node는 자신의 시점에서 본 송수신 사실만 `detail.traffic`에 기록한다.
- controller는 이 traffic 사실을 재구성하거나 보정하지 않고 projection만 수행한다.
- `detail.traffic`의 최소 축은 다음과 같다.
  - `capture_seq`
  - `captured_at`
  - `previous_peer`
  - `next_peer`
  - `recent`
- `previous_peer` / `next_peer`는 각각 아래 필드를 가진다.
  - `peer_node_id`
  - `peer_role`
  - `hop_state`
  - `failure_reason`
  - `last_received`
  - `last_sent`
- capture record는 최소한 아래 필드를 가진다.
  - `logical_id`
  - `attempt_no`
  - `phase`
  - `captured_at`
  - `payload`
  - `truncated`
  - `original_size`
  - `preview`
- lane별로 latest snapshot 1개와 recent history 5개까지만 유지한다.
- payload preview는 JSON 직렬화 기준 최대 1200자까지만 유지한다.
- payload가 너무 크면 `payload` 전체 대신 truncated preview만 남긴다.
- role에 따라 lane가 의미 없으면 fake data를 만들지 않고 `hop_state = not_applicable`를 사용한다.

#### 상태 축 분리 규칙
- `reported_state`는 node가 스스로 보고한 실행 상태다.
- `observed_liveness`는 controller가 `last_seen` 기준으로 파생한 관찰 상태다.
- `hop_state`는 이웃 node와의 request/response 상호작용 결과다.
- 이 세 축은 서로 대체하지 않는다.
- Web UI overview의 SVG data-path tone은 위 `hop_state`를 그대로 지우지 않고, Monitor가 마지막으로 수신한 `last_route_summary`의 현재 active route 증거를 별도 projection 축으로 함께 본다. DOM에서는 raw hop 상태(`data-hop-state`), raw hop tone(`data-raw-hop-tone`), route membership verdict(`data-route-active`), 최종 overview tone(`data-hop-tone`)을 분리한다.
- `last_route_summary`는 마지막으로 Monitor에 도달한 route evidence이며 wire-level continuous liveness proof가 아니다. 따라서 route-aware overview projection은 `active_route`가 `primary` 또는 `backup`이고 `route_state`가 `PRIMARY` 또는 `BYPASS_ACTIVE`일 때만 적용한다. missing / malformed / invalid / `FAILED` / `DEGRADED` summary에서는 `data-route-active="unknown"`으로 두고 최종 overview tone은 raw hop tone과 같아야 한다.
- inactive route projection은 raw `acknowledged` + raw `ok`인 오래된 성공 기록만 inactive/stale overview tone으로 낮출 수 있다. raw `down`, `warn`, `active`, `paused`, `timeout`, `connection_error`, `delivery_failed`, `rejected` 같은 현재 실패 또는 진행 신호는 inactive projection으로 가리면 안 된다.

#### partial-topology / hop taxonomy 규칙
- configured peer가 있지만 controller가 아직 그 peer의 `STATUS`를 한 번도 보지 못했고,
  현재 peer snapshot의 `hop_state`도 여전히 `unknown`이면,
  controller 표시층은 이를 `not_started`로 보여줄 수 있다.
- `not_started`는 controller-derived visibility 표현이며, node가 직접 저작한 data-plane truth를 덮어쓰지 않는다.
- 현재 최소 hop taxonomy는 다음을 포함한다.
  - `unknown`
  - `not_started`
  - `idle`
  - `request_sent`
  - `acknowledged`
  - `timeout`
  - `connection_error`
  - `ack_dropped`
  - `not_applicable`
- `unknown`, `not_started`, `timeout`, `connection_error`, `not_applicable`는 같은 의미로 취급하지 않는다.

---

## 8. ACK / Retry / Dedup 규칙

### 8.1 ACK 규칙

- R1은 R2의 ACK를 기다린다.
- R2는 Monitor의 ACK를 기다린다.
- R1B는 R2B의 ACK를 기다린다.
- R2B는 Monitor의 ACK를 기다린다.
- ACK는 “이 단계에서 메시지를 수용하고 처리했다”는 의미다.
- ACK는 end-to-end가 아니라 hop-by-hop이다.

### 8.2 Retry 규칙

- timeout 안에 ACK를 받지 못하면 동일 EVENT를 재전송한다.
- retry 시에도 같은 `event_id`를 재사용해야 한다.
- `max_retry_count` 이후에는 중단한다.
- 최대 retry 후에는 전달 실패가 UI / log에 드러나야 한다.
- Agent는 primary `local-agent -> r1` hop 실패를 관찰하면 같은 `event_id`와 route trace를 유지한 채 backup `local-agent -> r1b`를 순차 시도한다. primary와 backup에 동시에 fan-out하지 않는다.

### 8.3 Dedup 규칙

- dedup key는 `event_id`다.
- R1, R2, R1B, R2B, Monitor는 각각 처리된 ID cache를 유지한다.
- duplicate 메시지는 다시 처리하지 않는다.
- 필요하면 duplicate에도 ACK를 다시 보낼 수 있다.

---

## 9. 시연용 fault 시나리오

### 9.1 정상 전달
- Host fault 발생
- Agent가 EVENT 생성
- R1 forwarding
- R2 forwarding
- Monitor logging
- ACK 정상 반환

### 9.2 ACK loss / retry
- Monitor가 event 수신
- Monitor의 ACK를 의도적으로 한 번 drop
- R2가 timeout 후 retry
- Monitor는 duplicate를 식별하고 두 번 기록하지 않음

### 9.3 Relay delay
- R1 또는 R2에 눈에 보이는 delay 추가
- pending ACK와 지연된 완료를 관찰

### 9.4 Relay down (선택)
- Relay가 forwarding 중단
- timeout / retry가 눈에 보이게 발생
- 최종 실패가 log / UI에 표시됨

---

## 10. Recovery 정책

Recovery는 **첫 구현 완료의 필수 조건이 아니다**.

버전 1에서 생략하면:

- 시스템은 fault 전달 시스템으로 계속 동작한다.
- 현재 fault 해제 상태는 완전히 표현되지 않을 수 있다.

나중에 추가한다면:

- `*_RECOVERED` event type을 사용한다.
- recovery도 동일 transport 규칙을 따르는 EVENT로 다룬다.
- Monitor 상태를 abnormal에서 normal로 다시 갱신한다.

---

## 11. 향후 구조 확장 기준

### 11.1 item 1 - node-first TUI에서 Web UI로의 확장

- 현재 우선순위는 각 node별 TUI 모니터링 경험을 먼저 다듬는 것이다.
- 이후 Web UI는 이 경험을 옮기는 consumer layer로 추가한다.
- Web UI는 node와 직접 결합하지 않고 controller / gateway surface를 통해 상태와 제어를 사용한다.

### 11.2 item 2 - 우회 node / critical fault 구조 제안

item 2의 목표는 단순 fault 표시를 넘어서,
**특정 구간이 critical 상태일 때 우회 경로가 필요해지는 구조와 그 가시성**을 도입하는 것이다.

초기 제안 기준은 다음과 같다.

- 기존 Host / Agent / Relay / Monitor / Controller-UI 역할 구조를 무너뜨리지 않는다.
- 먼저 고정 chain 위에 **primary path / bypass-capable segment / reroute reason** 개념을 추가한다.
- 우회는 임의의 mesh routing이 아니라, 교육용으로 설명 가능한 제한된 alternate path만 다룬다.
- controller / monitor surface에는 현재 경로, 우회 진입 이유, degraded 여부를 함께 표시한다.

구조 제안:

1. routing state를 명시적으로 둔다.
   - 예: `PRIMARY`, `BYPASS_ACTIVE`, `DEGRADED`, `FAILED`
2. 우회 대상은 먼저 “새 node 이름”보다 **alternate downstream contract**로 정의한다.
   - 예: 특정 relay가 primary downstream과 bypass downstream 후보를 가진다.
3. critical fault는 일반 fault와 분리해 정의한다.
   - 단순 CPU spike가 아니라, 경로를 유지할 수 없어 우회가 필요한 fault를 별도로 둔다.
4. reroute는 제어 plane의 구조 변경이 아니라, data path 선택 변화로 취급한다.
5. `event_id` continuity는 유지한다.
   - 우회가 발생해도 같은 event는 같은 identity를 유지해야 duplicate / retry 규칙이 무너지지 않는다.

현재 단계의 비목표:

- full mesh routing
- production-grade failover engine
- 다중 정책 기반 path selection

### 11.3 item 3 - Linux / Windows 분리 실행 구조 제안

item 3의 목표는 role의 논리적 의미는 유지하면서,
**프로세스의 실제 실행 위치를 여러 host / OS로 나누는 것**이다.

초기 제안 기준은 다음과 같다.

- `node_id`와 role semantics는 유지한다.
- local supervisor 편의 실행과 multi-host 배치를 같은 개념으로 보지 않는다.
- controller / gateway surface는 계속 중앙 control-plane 진입점으로 유지한다.
- token은 role 간 data plane이 아니라 controller와 role 사이의 control/status 경계에만 둔다.

구조 제안:

1. endpoint 설정을 localhost 고정값에서 분리한다.
   - node별 listen address, controller address, host metadata를 독립적으로 다룬다.
2. process placement layer를 도입한다.
   - “어떤 role이 어느 host / OS에서 실행되는가”를 runtime config로 분리한다.
3. local supervisor는 개발 편의용 mode로 낮춘다.
   - multi-host에서는 각 role을 host별로 개별 기동하고, controller는 remote endpoint를 본다.
4. UI에는 node 상태뿐 아니라 location 정보도 들어갈 수 있어야 한다.
   - host name, OS, connectivity state, last_seen 기준이 확장 가능해야 한다.
5. failure semantics를 나눈다.
   - process failure
   - host failure
   - network partition / controller reachability loss

현재 단계의 비목표:

- full orchestration platform
- container scheduler 의존
- production fleet management

### 11.4 item 4 - 실질 recovery는 이후 단계다

recovery는 item 1~3이 정리된 이후에 다룬다.

- 현재는 reboot 이상의 lifecycle recovery를 기술 기준으로 고정하지 않는다.
- 이후 recovery를 추가할 때는 reroute 구조와 multi-host 상태 모델을 먼저 반영해야 한다.
- 즉 recovery는 지금 당장 선행 구현할 주제가 아니라, 앞선 구조 정리가 끝난 뒤에 올라오는 단계다.

---

## 12. 권장 구현 순서

1. 공통 JSON 메시지 스키마 정의
2. Host Simulator 상태 tick 구현
3. Local Agent polling 및 EVENT 생성 구현
4. Relay R1 ACK / retry / dedup 구현
5. Relay R2 ACK / retry / dedup 구현
6. Monitor logging 및 ACK 구현
7. Controller/UI 제어와 상태 표시 구현
8. fault injection 시나리오 추가
9. 시간이 남으면 optional recovery support 추가

---

## 13. 최종 결정 요약

이 프로젝트는 다음을 유지한다.

- 원래의 6단 구조
- 두 개의 relay
- 교육용 네트워크 파이프라인
- 단순화된 내부 프로세스 로직
- 사람이 인지할 수 있을 만큼 느린 동작
- ACK, retry, dedup, 시연 가시성 우선

이 프로젝트는 다음을 목표로 하지 않는다.

- production-grade distributed system
- 고처리량 실시간 서비스
- 기능이 많은 failover 플랫폼

올바른 목표는 다음이다.

**네트워크 교육을 위한 단순하고, 눈에 보이며, 신뢰성 있는 이벤트 전달 실험 시스템**
