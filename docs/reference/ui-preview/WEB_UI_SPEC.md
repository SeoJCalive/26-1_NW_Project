# Web UI 표현 명세

이 문서는 NW 프로젝트의 Web UI runtime frontend가 따라야 할 **visual acceptance contract**다.
현재 기술 기준의 최종 판단은 root의 `IMPLEMENTATION_SPEC.md`를 따르고, 사용자 의도와 금지선은 `INTENT_ALIGNMENT_NOTE.md`를 따른다.
이 문서는 `docs/reference/ui-preview/preview.revised.jsx`의 시각 구조를 실제 Web UI runtime frontend로 옮길 때 보존해야 할 기준을 정리한다.

## 1. 목적

이번 Web UI 작업의 목표는 새 preview/demo를 더 만드는 것이 아니라, 기존 reference preview와 TUI에서 검증된 관찰 경험을 바탕으로 **실제 Web UI runtime frontend를 preview visual parity 기준으로 구현하는 것**이다.

- TUI는 최종 UI가 아니다.
- TUI는 Web UI 설계를 위한 정보 구조, 상태 모델, node-first monitoring 경험의 참고 자료다.
- Web UI는 TUI 출력이나 TUI 렌더링 결과를 파싱하지 않는다.
- TUI와 Web UI는 같은 runtime 자료 구조를 서로 다른 surface로 표현한다.
- `preview.revised.jsx` / `preview.revised.html`은 현재 Web UI frontend의 visual source of truth다.
- 기존 preview 원본은 보존하고, 실제 runtime Web UI는 새 `web_ui/` 위치에서 같은 visual structure를 porting한다.
- runtime 연결 때문에 layout, palette, typography, component hierarchy를 임의로 새로 설계하지 않는다.
- mock data만으로 완성 처리하지 않는다.

## 2. Visual source of truth

현재 Web UI runtime frontend는 아래 preview 기준을 따른다.

- 기준 파일: `docs/reference/ui-preview/preview.revised.jsx`
- preview host: `docs/reference/ui-preview/preview.revised.html`
- 핵심 화면 구조: `1460x700` diagram canvas, absolute node cards, SVG data path, diagram 내부 detail inspector overlay
- 핵심 component 구조: `HeaderSummary`, `DiagramCanvas`, `NodeCard`, `LivenessLamp`, `ReportedStateBadge`, `NodeInfoRow`, `TrafficSection`, `DetailInspector`, role별 detail renderer
- 핵심 visual token: `#f3f6fb` 배경, slate / sky / cyan / emerald 계열 상태색, white card, compact border/shadow, system-ui typography
- 핵심 interaction: node click selection ring, diagram 내부 detail open / closing state, `X` close, path-flow animation

runtime 구현은 React/Tailwind를 그대로 써야 한다는 뜻이 아니다.
plain HTML/CSS/JS로 구현하더라도 위 구조와 시각 인상은 유지해야 한다.
다른 palette, 다른 typography, 별도 dashboard layout, viewport-fixed drawer를 새로 도입하려면 먼저 이 문서와 `INTENT_ALIGNMENT_NOTE.md`를 갱신해 사용자 확인을 받아야 한다.

## 3. 핵심 UI 원칙

Web UI는 **교육용 관제판**이어야 한다.

- 일반적인 예쁜 SaaS dashboard가 아니다.
- topology만 화려한 네트워크 그림이 아니다.
- 각 node의 상태, 수치, 최근 활동, 송수신 구조를 사람이 이해하도록 돕는 화면이다.
- 사용자는 화면을 보고 primary `Host -> Agent -> R1 -> R2 -> Monitor`와 backup `Agent -> R1B -> R2B -> Monitor` 흐름에서 지금 어떤 일이 일어나는지 따라갈 수 있어야 한다.

우선순위는 다음 순서다.

1. 교육적 가시성
2. 구조적 명확성
3. 실제 runtime과의 연결 가능성
4. 제어 가능성
5. 시각적 완성도

## 4. Runtime 자료 출처

Web UI의 정보 출처는 TUI가 아니라 **controller / gateway가 가진 runtime state와 node가 보고하는 자료 구조**다.

기준 흐름은 다음과 같다.

```text
각 node
  -> STATUS_REPORT / STATUS / detail.traffic
  -> Controller / Gateway
  -> Web UI
```

따라서 Web UI는 다음을 지켜야 한다.

- TUI 화면 문자열, terminal 렌더링 결과, TUI 전용 layout state를 데이터 소스로 삼지 않는다.
- Web UI는 controller / gateway surface 뒤의 소비자다.
- Web UI는 node에 직접 붙는 data-plane peer가 아니다.
- Web UI와 TUI는 같은 node-authored status / traffic 자료를 각자 다른 화면으로 표현한다.
- Web UI 구현 중 필요한 자료가 TUI에만 있다면, TUI에서 긁어오지 말고 controller / gateway 자료 구조로 승격할 수 있는지 먼저 검토한다.

Web UI control palette는 사용자 조작 의미가 바로 드러나야 한다.

- fault 제어는 `fault cpu|service|latency on|off` 형태의 수동 스위치를 우선 노출한다.
- node 제어는 각 node별 `start <node>` / `pause <node>` 스위치를 제공한다.
- `kill <node>`는 되돌리기 어려운 shutdown 제어이므로 기본 Web UI 스위치로 사용하지 않는다.
- diagram heading 우측의 전원 버튼은 Web UI가 직접 supervisor를 가진 local runtime에서만 node role 프로세스 전체를 켜고 끄는 lifecycle control이다. Web UI HTTP surface는 유지하고 node role process만 start / terminate 한다.
- 일반 Web UI supervisor mode에서는 node listen port를 빈 포트로 동적 할당한다. 전원 버튼이 다시 켤 때도 fixed `9101-9107`에 의존하지 않으며, UI는 `유동 포트` 힌트를 표시한다.
- 전원 버튼은 start / stop 전환 중 예상 소요 시간만큼 비활성화되어야 한다. 현재 기준은 start 약 6초, stop 약 4초이며, 연속 클릭으로 중복 start/stop을 보내면 안 된다.
- `--fixed-node-ports` 실행처럼 고정 node port를 쓰는 경우에는 켜기 전에 node listen port 점유를 확인하고, 다른 프로세스가 먼저 점유한 경우에는 일부 node만 올라가는 상태를 만들지 말고 실패 메시지를 보여준다.
- 기존 duration 기반 fault 명령은 controller/script 호환 경로로 남더라도 Web UI의 주 조작면에는 초 단위 버튼으로 노출하지 않는다.
- 팔레트의 `runtime-status`는 갱신 문구 길이에 따라 아래 control 요소를 밀어내지 않도록 고정 슬롯으로 점유한다.
- 팔레트는 모든 버튼을 같은 폭/같은 형태로 강제하지 않고, 전체 제어 / 장애 스위치 / 노드 스위치 / 전달 실험의 역할이 구분되도록 group surface와 공간 배분을 다르게 둔다.
- 장애 스위치는 CPU / service / latency 토글을 한 줄에 압축하지 않고 세로로 나열해, 켜짐/꺼짐 상태와 라벨이 각 항목별로 읽히게 한다.
- 긴 node 이름은 잘리지 않아야 하며, node 스위치 영역은 다른 보조 명령보다 넓게 배치한다.

Web UI가 우선 소비해야 하는 자료 축은 다음이다.

- `STATUS_REPORT`
- `STATUS`
- `detail`
- `detail.traffic`
- `reported_state`
- `observed_liveness`
- `hop_state`
- `previous_peer`
- `next_peer`
- `recent`
- `last_route_summary`
- `last_fault_localization`
- `last_route_trace`

## 5. 화면 구조

### 5.1 첫 화면

첫 화면은 **preview parity diagram overview**다.

- Host Simulator, Local Agent, R1, R2, R1B, R2B, Monitor node 카드를 모두 보여준다.
- node 카드는 preview처럼 diagram canvas 안에서 absolute position으로 배치한다.
- primary `Host -> Agent -> R1 -> R2 -> Monitor`와 backup `Agent -> R1B -> R2B -> Monitor` topology는 별도 상단 strip이 아니라 diagram canvas 안의 SVG path와 label로 표현한다.
- topology는 node 관찰 경험을 돕는 시각 구조이며, node card / activity / traffic 정보를 밀어내면 안 된다.
- 단순한 5열 CSS grid dashboard로 재해석하지 않는다.

### 5.2 Node 상세

node를 선택하면 **diagram 내부 right detail inspector overlay**를 연다.

- overview의 전체 맥락은 유지한다.
- 선택한 node의 상세는 preview처럼 diagram 내부 우측 overlay에서 깊게 보여준다.
- detail inspector는 화면 전환이 아니라 관찰 깊이 확장이다.
- overlay open / closing state, close button, 다른 node 선택 흐름을 명확히 둔다.
- viewport에 고정된 별도 drawer처럼 보여서는 안 된다.

공통 상세 섹션 순서는 다음을 기본으로 한다.

1. 상태
2. 지표
3. traffic snapshot
4. 최근 활동

## 6. Node 카드 기준

node 카드의 우선 정보는 **상태가 먼저 보이는 중간 밀도 요약**이다.

각 node 카드는 최소한 아래를 보여준다.

- node 이름, role line
- `reported_state`
- `observed_liveness`
- role별 핵심 신호 1~2줄
  - Host: CPU / memory 값
  - Agent: detected fault / downstream result 중 현재 의미가 큰 값
  - Relay: pending ACK / retry 요약
  - Monitor: logged / sink 요약

node 카드에서 긴 payload, raw JSON dump, 긴 설명 문단을 직접 보여주지 않는다.
node card의 geometry와 density는 preview의 compact card 기준을 따르되, 같은 정보 축을 반복하지 않는다.
`node_id`, role 중복 row, 반복 `observed_liveness` row, 상세 counter, traffic / hop / peer 상세는 detail inspector에서 보여준다.
최근 event id처럼 의미가 약한 보조 값은 card에서 제거하고 detail inspector에서 필요할 때 확인한다.

반드시 보존할 card primitive는 다음이다.

- `LivenessLamp`
- `ReportedStateBadge`
- boxed key/value rows는 상태 row + role별 activity row 1~2개 수준으로 제한
- role별 핵심 activity row
- selected ring / hover state

## 7. 상태 표현 기준

상태는 **색 + 문구 + 아이콘**을 함께 사용한다.

- 색만으로 상태를 구분하지 않는다.
- 사용자-facing 문구는 한국어 중심으로 둔다.
- `reported_state`, `observed_liveness`, `hop_state`는 서로 다른 축으로 보존한다.
- 이 세 축을 하나의 “정상/비정상” 상태로 뭉개지 않는다.

구분해야 하는 상태 축은 다음과 같다.

### 7.1 reported_state

node가 스스로 보고한 실행 상태다.
node card에서는 표 안의 `상태` row가 아니라 카드 상단의 초록 계열 상태 램프로 표시한다.

- 실행 중
- 정지
- 중지
- 알 수 없음

### 7.2 observed_liveness

controller / gateway가 `last_seen` 기준으로 파생한 관찰 상태다.
사용자-facing card 문구는 작업 상태처럼 보이는 `live`가 아니라 연결 의미로 표시한다.
`live`는 파란 연결 램프의 `연결됨`, 그 외 관찰 상태는 `단절됨`으로 요약한다.

- live
- stale
- offline
- unknown
- kill_requested

### 7.3 hop_state

이웃 node와의 request / response 상호작용 상태다.

- unknown
- not_started
- idle
- request_sent
- acknowledged
- timeout
- connection_error
- ack_dropped
- not_applicable

## 8. Traffic 표현 기준

traffic snapshot은 overview 카드에서는 **요약만** 보여주고, detail inspector overlay에서 구조적으로 보여준다.

SVG data path는 고정 이미지가 아니라 각 link 양끝 node의 `detail.traffic.previous_peer` / `next_peer`에서 읽은 `hop_state`를 반영한다.
선 사이의 상태 라벨도 고정 문구가 아니라 같은 `hop_state`에서 파생한다.

- `acknowledged`: 정상 확인 완료 선
- `request_sent`, `request_received`, `pending`: 흐르는 active 선
- `retrying`, `invalid_response`: 경고 선
- `timeout`, `connection_error`, `ack_dropped`, `delivery_failed`, `rejected`: 끊김/장애 선
- `idle`: 대기 선
- `unknown`, `not_started`, `paused`, `not_applicable`: 흐린 muted 선

양끝 node가 서로 다른 `hop_state`를 보고하면 더 위험한 상태를 우선해 link tone을 정한다.
라벨 문구는 각 link의 역할과 상태를 함께 드러내야 한다. 예: `상태 수집 완료`, `EVENT 전달 중`, `R2 ACK 대기`, `Monitor 재전송 중`, `ACK 드롭`, `응답 시간초과`, `상태 확인 중`.

Endpoint freshness는 `hop_state`와 별도 표시 축이다. Web UI overview SVG path는 양끝 node의 기존 `observed_liveness`만 읽어 `data-link-freshness="fresh|stale|offline|unknown"`와 `data-link-freshness-overlay="true|false"`를 둘 수 있다. 이 값은 새 API field가 아니며 raw `data-hop-state`, route projection, detail inspector traffic truth를 바꾸지 않는다. Stale/offline overlay는 lifecycle override가 없고 최종 표시 tone이 `ok` 또는 `idle`인 neutral link에만 적용하며, `active`, `warn`, `down`, `inactive`, `muted` link의 기존 의미와 라벨을 숨기지 않는다.

### 8.1 카드 영역

카드에서는 아래 수준만 보여준다.

- previous hop 상태
- next hop 상태
- 최근 logical id 또는 event id
- retry / duplicate 여부 요약

### 8.2 Detail inspector overlay

detail inspector overlay에서는 node 자신의 `detail.traffic`을 기준으로 보여준다.

- previous_peer
  - peer node
  - hop state
  - last_received
  - last_sent
- next_peer
  - peer node
  - hop state
  - last_sent
  - last_received
- recent lineage
  - logical_id
  - attempt_no
  - phase
  - peer
  - preview

controller가 node-authored traffic truth를 임의로 재구성한 것처럼 보여주면 안 된다.
raw `JSON.stringify(node.details)`나 raw JSON dump를 primary UI로 사용하지 않는다.
구조화된 key/value rows, table, role별 section으로 표현한다.

## 9. Monitor 표현 기준

Monitor는 별도 관제 허브가 아니다.
Monitor는 data plane의 최종 sink이며, Web UI에서는 사람이 읽는 **상황판 + 근거**로 표현한다.

Monitor detail inspector의 첫 섹션은 **현재 상황 요약**이다.

우선순위는 다음과 같다.

1. 현재 상황 요약
   - 마지막으로 처리한 event
   - 현재 host 상태
   - ACK / retry 상황
2. 최근 이벤트
3. 전달 건강도
   - duplicate
   - out-of-order
   - retry 관련 지표
4. route / traffic 근거
   - active route
   - 관찰 실패 hop
   - suspected node와 confidence
   - R2 또는 R2B에서 받은 자료
   - R2 또는 R2B에 반환한 ACK

Monitor를 새 중앙 관제 엔티티처럼 표현하지 않는다.

## 10. 제어 명령 표현 기준

이번 표현 명세에서는 Web UI 제어 명령의 **표시 위치와 의미**만 정의한다.
구체적인 API shape나 runtime 연결 방식은 구현 명세나 실제 구현 단계에서 확정한다.

표현해야 하는 제어는 다음 범위를 기준으로 한다.

- start / pause / reset
- fault cpu / service / latency
- ackdrop
- delay r1 / r2 / r1b / r2b
- focus 또는 node 선택

제어 버튼은 node에 직접 붙는 data-plane peer처럼 보이면 안 된다.
Web UI는 controller / gateway surface 뒤에서 상태를 읽고 제어 요청을 보내는 소비자다.

## 11. 언어 기준

사용자-facing 라벨은 한국어 중심으로 둔다.

영어로 유지할 수 있는 기술 토큰은 다음과 같다.

- ACK
- EVENT
- CONTROL
- STATUS
- event_id
- seq_no
- reported_state
- observed_liveness
- hop_state
- traffic
- previous_peer
- next_peer

화면 제목, 안내 문구, 버튼 설명, 상태 설명은 가능한 한 한국어로 쓴다.
다만 preview의 visual hierarchy와 component 위치를 바꾸기 위해 영어 라벨 제거를 핑계로 삼지 않는다.
`Node-first Dashboard`, `SELECTED NODE`처럼 preview 성격이 강한 영어 라벨은 한국어로 옮길 수 있지만, 해당 영역의 시각 위계와 역할은 유지한다.

## 12. Preview parity에서 보정할 점

기존 static preview는 현재 visual source of truth지만, runtime 구현에서는 아래 점을 보정한다.

- mock data를 완료물처럼 제출하지 않는다.
- static preview의 sample data를 그대로 runtime truth처럼 표시하지 않는다.
- user-facing 문구는 한국어 중심으로 정리한다.
- preview의 visual hierarchy와 component structure는 유지하되, 자료 출처는 controller / gateway runtime state로 교체한다.
- runtime 자료 shape가 preview sample과 맞지 않으면 adapter를 두고, visual structure를 먼저 무너뜨리지 않는다.

## 13. 이번 Web UI reset 금지선

이번 Web UI frontend reset에서 하지 않는다.

- 새 관제 허브 엔티티 추가
- Web UI를 data-plane peer로 구현
- TUI 출력 또는 TUI 렌더링 결과를 Web UI 데이터 소스로 사용
- static preview/demo를 최종 산출물로 제출
- preview visual structure를 무시한 새 dashboard layout 구현
- cream / olive / serif 등 preview와 다른 새 visual direction 도입
- 상단 text topology strip + 5열 grid card 구조로 재해석
- viewport-fixed side drawer를 detail inspector 대체물로 사용
- raw JSON dump를 primary detail UI로 사용
- recovery 구현
- multi-host 구현
- route 표시 UI가 Monitor detail의 `last_route_summary`, `last_fault_localization`, `last_route_trace`를 소비하는 범위를 넘어 새 routing truth를 만들어내는 것
- topology 중심의 일반 dashboard화
- TUI를 주 작업 대상으로 삼는 것

## 14. 완료 기준

Web UI runtime 구현은 최소한 아래를 만족해야 완료 후보로 본다.

- 새 runtime Web UI 위치에서 실행 가능해야 한다.
- 기존 static reference preview 원본은 보존해야 한다.
- mock data는 fixture/demo mode로만 허용하고 runtime 화면과 명확히 분리해야 한다.
- 실제 runtime 상태 읽기까지 구현해야 한다.
- `preview.revised.jsx`의 diagram canvas / node card / SVG path / detail inspector 구조와 시각적으로 맞아야 한다.
- node card는 liveness lamp와 reported state badge를 분리해서 보여야 한다.
- node 선택 시 diagram 내부 detail inspector overlay가 열리고 닫혀야 한다.
- Monitor는 현재 상황 요약을 먼저 보여줘야 한다.
- raw JSON dump가 primary UI로 보이면 완료가 아니다.
- browser screenshot 또는 DOM 검사로 preview parity를 확인해야 한다.
- 기존 Python runtime 테스트가 계속 통과해야 한다.

구성요소가 헷갈리면 임의 구현하지 말고, 이 문서를 갱신할 수 있도록 먼저 선택지와 장단점을 제시한다.
