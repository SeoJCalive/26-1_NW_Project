# AI 구현 브리프

이 문서는 이 저장소의 **단일 living context / handoff 문서**다.
세션이 바뀔 때마다 이 파일을 짧게 갱신해, 다음 작업자가 현재 기준·최근 결정·열린 이슈를 바로 이어받을 수 있게 한다.

긴 구현 명세, 상세 실행법, 장문 UI 브레인스토밍은 여기로 다시 복제하지 않는다.
지속적으로 유지해야 할 사실은 아래 기준 문서를 따른다.

## 문서 목적

- 이 파일의 역할: **세션 연속성 유지용 요약 / 인계 메모**
- 하지 않을 일: `README.md`나 `IMPLEMENTATION_SPEC.md`의 내용을 장문으로 다시 복제하기
- 세션 종료 시 갱신할 것: 최근 결정, 열린 이슈, 다음 세션 시작 포인트

## 현재 기준

### 프로젝트 베이스라인

- 이 프로젝트는 운영 서비스가 아니라 **네트워크 수업용 최소 데모**다.
- 현재 런타임은 이미 **프로세스 분리 구조**다.
- 기본 구조, 메시지, 동작 규칙의 세부 기준은 `IMPLEMENTATION_SPEC.md`를 따른다.
- 이 문서에는 다음 세션이 바로 이어받아야 할 현재 상태만 짧게 유지한다.

### 현재 UI 해석

- 현재 구현된 관찰/제어 화면은 **terminal viewer**다.
- 웹 UI는 장기 방향일 수 있지만, 아직 현재 기준을 대체하지 않는다.
- 이후 UI 작업도 “새 제품형 대시보드”보다 **현재 TUI의 교육용 관찰 경험을 웹으로 옮기는 방향**이어야 한다.

### 지속 사실을 확인할 문서

- 현재 실행/런타임 사실: [`README.md`](./README.md)
- 현재 기술 기준과 구현 범위: [`IMPLEMENTATION_SPEC.md`](./IMPLEMENTATION_SPEC.md)
- 사용자 의도와 해석 가드레일: [`INTENT_ALIGNMENT_NOTE.md`](./INTENT_ALIGNMENT_NOTE.md)

이 파일은 위 문서들을 **가리키는 인계 문서**이며, durable truth 자체를 대체하지 않는다.

## 문서 우선순위

1. `IMPLEMENTATION_SPEC.md` - 현재 기술 기준과 범위의 canonical source
2. `INTENT_ALIGNMENT_NOTE.md` - 사용자 의도, 해석 금지선, UI 판단 가드레일
3. `AI_IMPLEMENTATION_BRIEF.md` - 세션 간 연속성을 위한 최신 handoff
4. `README.md` - 실행 방식과 현재 런타임 진입 정보
5. `docs/history/PROCESS_SEPARATION_ARCHITECTURE.md` - 역사적 배경과 설계 맥락 참고용

메모:

- 기술 구현 판단은 `IMPLEMENTATION_SPEC.md`를 가장 먼저 따른다.
- 의도 해석이나 UI 방향 판단은 `INTENT_ALIGNMENT_NOTE.md`를 따른다.
- 현재 실행 방식과 런타임 진입 정보는 `README.md`를 본다.
- `docs/history/PROCESS_SEPARATION_ARCHITECTURE.md`는 **현재 truth가 아니라 historical/background 문서**로 취급한다.

## 최근 결정

- `AI_IMPLEMENTATION_BRIEF.md`를 앞으로 **세션마다 갱신하는 단일 컨텍스트 문서**로 사용한다.
- root에 새 세션 로그 markdown 파일을 만들지 않는다.
- 현재 런타임은 이미 process-separated 구조라는 점을 계속 기준으로 삼는다.
- 이 파일에는 긴 실행 명령 목록, 상세 메시지 명세, 장문 UI 확장 아이디어를 반복 기록하지 않는다.
- 웹 UI 관련 판단이 필요하면, 기술 기준은 `IMPLEMENTATION_SPEC.md`, 의도 해석은 `INTENT_ALIGNMENT_NOTE.md`, 실행 진입 정보는 `README.md`를 함께 본다.
- `docs/history/PROCESS_SEPARATION_ARCHITECTURE.md`는 현재 기준 문서가 아니라 배경 문서로 낮춰 해석한다.
- live preview 자산은 `docs/reference/ui-preview/` 아래에 둔다.
- preview 기준안은 `docs/reference/ui-preview/preview.revised.jsx`와 `docs/reference/ui-preview/preview.revised.html`만 유지하고, 이전 시안은 `docs/archive/ui-preview/preview.jsx`로 archive 한다.
- `docs/reference/ui-preview/preview.revised.jsx`는 현재 Web UI runtime frontend의 visual source of truth다. production runtime 앱 자체는 아니지만, `web_ui/static` frontend는 이 파일의 layout / palette / typography / component hierarchy를 plain HTML/CSS/JS로 porting해야 한다.
- `docs/reference/ui-preview/preview.revised.jsx`는 node-first 기준으로 재정리되었다. 현재 runtime frontend는 실제 data-plane 계약에 맞춰 `host-simulator`, `local-agent`, `r1`, `r2`, `r1b`, `r2b`, `monitor`를 표시하고, `observed_liveness` lamp / `reported_state` / activity / traffic을 분리한다. 상세 inspector는 기본 닫힘이며 node 클릭 시 약 1/3 폭으로 열리고 `X`로 닫힌다. Host / Agent / Relay / Monitor 상세는 각 role별 renderer로 나뉘며, synthetic note/reason/activity log나 `비고`/`설명` 서술 섹션을 두지 않는다.
- `docs/reference/ui-preview/preview.revised.jsx`는 `reported_state` 전용 badge tone, node-card boxed key/value rows, diagram 내부 non-resizing detail overlay로 갱신되었다. Detail overlay는 `data-detail-state="open|closing"`와 `detailInspectorIn` open animation / closing transition을 제공한다. Diagram canvas는 외부 preview card 폭을 강제 추종하지 않고 자연스러운 content 폭 기준으로 조정했으며, detail overlay는 고정 높이 안에서 `overflow-y: auto` 내부 스크롤을 사용한다. 검증은 `.sisyphus/evidence/node_first_preview.spec.py`와 `task-4-reported-card-overlay-*` evidence가 담당한다. 최종 Oracle 재검토는 PASS였고, 남은 주의점은 기존 preview URL이 stale content를 제공할 수 있다는 환경 리스크뿐이다.
- `docs/reference/ui-preview/WEB_UI_SPEC.md`는 Web UI runtime frontend의 visual acceptance contract다. 현재 runtime은 `1460x700` diagram canvas, absolute node cards, SVG data path, in-canvas detail inspector overlay, slate/sky/cyan/emerald palette, system-ui typography, role별 detail renderer를 기준으로 삼는다. runtime 자료 출처는 controller / gateway의 `STATUS_REPORT` / `detail.traffic`이지만, visual structure는 preview parity를 먼저 만족해야 한다.
- `web_ui/` runtime surface를 추가했다. 실행은 `python -m web_ui.server --web-port 8080`이며, 기본적으로 controller/gateway status surface와 local role supervisor를 함께 띄운다. Web UI는 `GET /api/state`에서 `ControllerUI.runtime_state_snapshot()` 결과를 읽고, `POST /api/control`로 기존 viewer/controller 명령 문자열을 전달한다. `web_ui/static` frontend reset은 완료되었고, `web_ui/server.py`, `/api/state`, `/api/control`, `ControllerUI.runtime_state_snapshot()` wiring은 유지한다.
- 이번 세션에서 `web_ui/static/index.html`, `web_ui/static/app.css`, `web_ui/static/app.js`를 `preview.revised.jsx` parity 기준으로 reset했다. frontend는 `1460x700` diagram canvas, absolute node cards, SVG data path, diagram 내부 detail inspector overlay, liveness lamp / reported state badge 분리, Monitor 현재 상황 요약 우선 표시를 plain HTML/CSS/JS로 구현한다. `/api/state` normalized node view는 frontend adapter에서 preview-shaped model로 변환하며, `/api/control` command 버튼은 기존 command-line API에만 연결한다. `web_ui/server.py`와 `ControllerUI.runtime_state_snapshot()`는 변경하지 않았다. 검증 evidence는 `/tmp/opencode/web-ui-runtime-parity.png`이며, reference HTML은 CDN 로딩 문제로 새 screenshot 생성이 실패할 수 있으므로 source `preview.revised.jsx` 추출값과 live DOM/screenshot을 함께 확인한다.
- 이번 세션에서 Web UI node card를 중간 밀도 overview 기준으로 재조정했다. 카드에는 top liveness lamp, node display name, role line, `reported_state` row, role별 activity row 1~2개를 둔다. Host card는 CPU / 메모리 값을 직접 보여주고, 의미가 약한 `latest` footer와 간략 영어 `short` label은 제거했다. `node_id`, 중복 role row, 반복 `observed_liveness` row, 상세 counter, traffic / hop / peer 상세는 detail inspector로 넘긴다. 기본 card shadow와 장식은 과하지 않게 유지하고 선택 상태만 더 강하게 보이게 했다. `WEB_UI_SPEC.md`도 같은 기준으로 갱신했으며, 최신 browser evidence는 `/tmp/opencode/node-cards-balanced.png`다.
- Web UI 상단의 별도 브라우저 표면 안내 섹션은 현재 화면에 필요 없는 보조 설명으로 판단해 제거했다. 첫 화면은 summary header 바로 아래 diagram이 먼저 오고, 명령 팔레트는 diagram 아래에 둔다. 팔레트 내부에서는 `명령 팔레트` 제목과 `runtime-status`가 버튼 group 위쪽 한 줄 슬롯을 차지한다.
- Web UI diagram canvas는 노드가 다닥다닥 붙어 보이지 않도록 `1460x700`으로 넓히고, Host / Agent / R1 / R2 / R1B / R2B / Monitor 좌표를 primary/backup 흐름이 구분되게 배치했다. node-layer는 canvas 전체를 따라가며, card 간 최소 간격이 생기도록 조정했다.
- Web UI SVG 연결선은 더 이상 고정 topology 장식만이 아니라 runtime `hop_state`를 반영한다. 각 link는 양끝 node의 `detail.traffic.next_peer` / `previous_peer`를 읽고, `acknowledged`, active, warn, down, idle, muted tone 중 더 위험한 상태를 우선해 선 색/점선/흐름을 바꾼다. 선 사이 라벨도 `hop_state`에서 파생하며 `상태 수집 완료`, `EVENT 전달 중`, `R2 ACK 대기`, `Monitor 재전송 중`, `ACK 드롭`, `응답 시간초과`, `상태 확인 중` 같은 역할+상태 문구로 표시한다.
- Web UI 명령 팔레트는 duration fault 버튼을 수동 fault 스위치로 바꾼다. `fault cpu|service|latency on|off`가 Host fault를 켜고 끄며, 각 node 스위치는 되돌리기 어려운 `kill`이 아니라 기존 `start <node>` / `pause <node>` 제어를 사용한다. 기존 `fault <type> <sec>`는 controller/script 호환 경로로 유지한다.
- Web UI 명령 팔레트의 `runtime-status`는 상태 문구가 길어져도 아래 control group을 밀지 않는 고정 슬롯으로 유지한다. 팔레트는 모든 버튼을 같은 폭/형태로 맞추지 않고, 전체 제어 / 장애 스위치 / 노드 스위치 / 전달 실험의 역할이 보이도록 group surface와 공간 배분을 다르게 둔다. 긴 node 이름은 잘리지 않아야 하며, node 스위치 영역은 보조 명령보다 넓게 배치한다.
- 기존 root PDF/PPTX bucket 자료는 `docs/reference/network-project/`와 `docs/archive/network-project/proposals/`로 정리한다.
- 사용자가 직접 입력하고 제어할 수 있는 실행 명령, controller 명령, 종료/정리 절차는 `docs/reference/network-project/guide/CONTROL.md`에 정리한다. node별 JSON 자료형은 `docs/reference/network-project/guide/노드 자료형.md`에 축약 없이 유지한다. node 사이에서 수행하는 polling, EVENT forwarding, ACK, retry, duplicate suppression, control/status 작업 설명은 `docs/reference/network-project/guide/노드 전달.md`에 분리한다. `노드 전달.md`는 node마다 하나의 표를 쓰고, 표는 `자료 구분`, `방향`, `의미` 3열로 유지하며 첫 번째 칸에서 `받는 자료`, `전달 자료`, `확인 받는 자료`, `시스템 이외의 자료`와 적용 기술명을 함께 표시한다. Host/Monitor처럼 다음 hop 확인이 없는 end node에는 의미 없는 `확인 받는 자료 | 해당 없음` 행을 두지 않고, Monitor는 event와 host state를 사람이 읽을 수 있는 상태 문장/알림으로 해석해 Controller/UI 표시 자료로 제공하는 역할까지 문서화한다.
- control/status plane은 shared token을 유지하되, 앞으로는 더 명확한 envelope / gateway 경계로 정리하는 방향을 현재 기준으로 삼는다.
- 이후 UI는 node와 직접 결합하는 peer가 아니라 controller / gateway surface 뒤의 소비자 계층으로 계속 해석한다.
- 프로젝트의 다음 구조 단계는 `1) node-first TUI -> Web UI`, `2) 우회 경로 / critical fault`, `3) Linux / Windows 분리 실행`, `4) 실질 recovery` 순서로 본다.
- item 1은 현재 TUI/Web UI sibling surface로 진행 중이다. item 2는 constrained backup chain으로 구현 완료했다. 남은 구조 설계 대상은 item 3 multi-host와 추가 critical-fault 의미론이다.
- recovery는 위 단계가 정리된 뒤에 다루며, 현재 기준에서는 선행 주제로 올리지 않는다.
- integrated viewer는 summary-first overview로 유지하고, structured traffic forensic view는 focused node monitor로 분리한다.
- standalone controller UI는 `--focus-node <node>` mode를 지원하며, 이 mode에서 각 node의 upstream/downstream structured snapshot을 본다.
- controller/UI는 실행 중 `viewer>` 프롬프트에서 `focus host|agent|r1|r2|r1b|r2b|monitor`, `overview`, `focus all`을 지원한다. `host`는 `host-simulator`, `agent`는 `local-agent`로 해석한다. 이 명령은 local UI state만 바꾸며 노드에 `CONTROL` 메시지를 보내지 않는다.
- focused monitor의 `최근 노드 활동`은 전역 node activity가 아니라 현재 focus 대상 node 활동만 최대 10줄 표시한다.
- `focus node: monitor`는 다른 node의 technical lane dump가 아니라 Monitor가 기록한 event, host state, 전달 건강도, 확인 응답/재시도 상태를 사람이 읽는 최종 상황판으로 표시한다. TUI는 제거하지 않고, 터미널 폭과 한글 display width를 계산해 넓은 화면에서는 안전한 박스형 상황판을 쓰며 좁은 화면에서는 compact box / 섹션 / plain safe line으로 자동 fallback한다. 깨지기 쉬운 `신호 흐름` ASCII 도식은 계속 쓰지 않는다.
- interactive TUI는 `viewer>` 프롬프트를 bottom row에 직접 렌더링한다. 빈 Enter는 no-op으로 전체 화면을 다시 열지 않고, 방향키 escape sequence는 명령어로 기록하지 않고 버린다.
- traffic truth는 controller가 아니라 각 node의 `detail.traffic` payload가 가진다는 기준을 현재 구현에도 반영했다.
- control-plane request는 data-plane traffic lane truth를 덮어쓰지 않으며, focused monitor는 node-authored traffic snapshot과 controller-derived peer visibility를 함께 읽는다.
- 기본 데모 타이밍은 `2s` tick/poll/status refresh를 유지하고, hop ACK timeout은 `2s`로 둔다. Agent -> R1 도착이 늦어 보이던 문제는 tick 축소가 아니라 R1이 upstream EVENT 수신 상태를 relay processing delay 전에 publish하도록 해결했다.
- 기본 `python main.py` 실행에서 relay/monitor가 끊긴 것처럼 보이지 않도록 Local Agent는 fault가 없어도 정상 host 상태 변화마다 `HOST_STATE_UPDATE` EVENT를 R1으로 보낸다. 반복 fault는 기존처럼 같은 fault signature 동안 중복 생성하지 않는다.
- `AGENTS.md`는 workspace 공통 markdown 거버넌스를 반복 설명하지 않고, 이 저장소의 root 허용 markdown, 문서 갱신 기준, 우선순위, docs 로컬 매핑만 담는 로컬 델타 문서로 유지한다.

## 현재 세션 관점 요약

### 아키텍처 한 줄 요약

프로세스가 분리된 primary+backup 7-node 교육용 네트워크 데모이며, 현재는 TUI와 Web UI가 같은 controller/gateway runtime state를 서로 다른 화면으로 표현하는 sibling surface 구조다.

### 이번 정리에서 확정한 방향

- root markdown는 5개 current 문서로 고정하고, 역사 배경 문서는 `docs/history/` 아래에서 관리한다.
- 새 root 세션 로그는 만들지 않고 `AI_IMPLEMENTATION_BRIEF.md`만 갱신한다.
- 기술 기준은 `IMPLEMENTATION_SPEC.md`, 의도 기준은 `INTENT_ALIGNMENT_NOTE.md`, 역사 배경은 `docs/history/PROCESS_SEPARATION_ARCHITECTURE.md`로 분리한다.
- 반복 참조하는 supporting 자료는 `docs/reference/` 아래에서 관리하고, root current 문서를 대체하지 않는다.
- 외부에서 가져오거나 새로 모은 미분류 자료의 임시 진입점이 필요하면 `docs/inbox/`를 사용한다.
- UI preview는 root bucket 없이 `docs/reference/ui-preview/`에 두고, 기준안 1세트만 live로 유지하며 나머지는 archive 한다.
- 참고용 PDF/PPTX 자료는 root bucket이 아니라 `docs/` 아래 reference/archive 경로로 관리한다.
- per-node monitor/kill 계획의 task 1 기준으로 `tests/` stdlib `unittest` 하네스를 추가했고, 현재 STATUS shape를 반영한 Host/Agent/Relay/Monitor fixture builder와 계약 테스트를 먼저 고정했다.
- task 2 기준으로 `controller_ui.normalize_node_view` / `derive_node_liveness`를 추가해 reported state와 observed liveness를 분리했다.
- controller는 현재 publisher payload 확장 없이도 `STATUS` 수신 시각과 `종료 요청 수신` note를 이용해 `unknown -> live -> stale -> offline` 및 `kill_requested` 전이를 정규화한다.
- task 3 이후 기준으로 Host/Agent/Relay/Monitor publisher는 모두 structured `detail` payload를 보내고, viewer는 richer per-node detail line을 렌더링한다.
- controller client는 node-scoped `start/pause/reset/kill` 문법을 지원하고, interactive viewer 모드에서는 같은 monitoring surface에서 `viewer>` 프롬프트로 local command를 입력할 수 있다.
- control/status 경로는 shared `control_token`을 사용하되, runtime status는 raw `STATUS` 대신 authenticated `STATUS_REPORT` wrapper로 controller에 전달해 token을 visible status payload에서 제거했다.
- supervisor는 child role에 token을 argv가 아니라 `NW_CONTROL_TOKEN` environment variable로 전달하고, viewer는 token 값을 화면에 직접 출력하지 않는다.
- standalone role / standalone controller UI / external controller client는 기본적으로 token이 필요하고, 무인증 제어는 명시적 `--allow-unauthenticated-control` opt-in으로만 허용한다.
- Monitor는 별도 tmux 관찰 세션으로 띄우는 대상이 아니라 Host / Agent / R1 / R2 / R1B / R2B와 같은 supervisor-managed role node로 취급한다.
- controller/viewer의 `exit`는 `quit`와 같은 정상 종료 명령이며, external controller client도 shutdown 요청을 controller/viewer에 전달한 뒤 종료한다.
- token 방향은 옵션 2+3을 따른다.
  - shared token은 유지한다.
  - token은 data plane이 아니라 control/status plane 경계로 본다.
  - 이후 UI는 controller / gateway surface 뒤에 둔다.
- item 1인 node-first TUI 모니터링은 이미 진행 중인 작업 축이다.
- item 2인 우회 경로는 constrained backup chain 해석으로 현재 구현 완료이며, 남은 구조 설계 대상은 item 3 Linux / Windows 분리 실행과 별도 명세가 필요한 추가 critical-fault 의미론이다.
- 이후 설계와 구현은 single-path, single-host, UI-as-node 가정을 영구 구조처럼 굳히지 않는 방향을 따라야 한다.
- Host/Agent/Relay/Monitor publisher는 모두 structured `detail.traffic` snapshot을 내보내며, integrated viewer는 hop summary만, focused monitor는 상세 lane payload를 렌더링한다.
- focused monitor 대상은 controller/UI 내부 명령으로 전환할 수 있으므로, 여러 focused controller를 서로 다른 port에 동시에 띄우는 방식은 기본 사용 경로가 아니다.
- prompt 중복/갱신 정지 회귀를 막기 위해 `InPlaceRenderer.render_prompt`, blank Enter no-op regression, raw terminal input handling을 추가했다.
- 새 테스트 `test_traffic_snapshot_contracts.py`, `test_traffic_snapshot_bounds.py`, `test_hop_state_visibility.py`, `test_node_monitor_mode.py`가 추가되었다.
- unseen peer는 payload truth가 아니라 controller visibility 기준으로 `not_started`로 표시될 수 있다.
- Agent가 Host 자료를 받는데 R1 전달이 느리거나 실패해 보이면, 먼저 R2/Monitor까지 열린 full topology인지 확인한다. R1은 downstream ACK를 받아야 Agent에 ACK를 돌려주므로 R1만 살아 있어서는 충분하지 않다.
- focused monitor에서 Agent -> R1 구간을 볼 때는 R1의 `upstream 수신` note / previous peer snapshot이 먼저 보이고, 이후 R1 -> R2 processing delay와 downstream ACK가 이어져야 정상이다.
- no-arg viewer에서 fault를 주입하지 않아도 Host tick 변화가 Agent의 `HOST_STATE_UPDATE` EVENT로 relay chain을 통과해야 정상이다.
- constrained backup routing 구현이 완료되었다. Agent는 primary `local-agent -> r1` 실패 시 같은 `event_id`로 `local-agent -> r1b -> r2b -> monitor` backup 경로를 순차 시도한다. Relay는 route mismatch를 거부하고 `forwarded` route trace를 downstream payload에 추가한다. Monitor는 backup event의 upstream을 `r2b`로 기록하고 `last_route_summary`, `last_fault_localization`, `last_route_trace`를 TUI/Web UI에 제공한다.
- TUI focused Monitor와 Web UI Monitor detail은 route summary, fault localization, route trace를 표시한다. 표현은 `관찰 실패 hop`, `의심 node`, `confidence`, `basis` 중심이며 hard node failure로 단정하지 않는다.
- 2026-05-21 Web UI 상황별 브라우저 검증을 완료했다. Evidence는 `.sisyphus/evidence/web-ui-situations/`에 있으며 `task-1-harness`부터 `task-8-focus-overview`까지 모두 PASS다. 실제 Playwright/headless Chromium으로 startup topology, primary normal route, `pause r1` 후 backup failover, ACK drop/retry visibility, `delay r1|r2|r1b|r2b 1.5`, pause/reset/kill lifecycle, node inspector focus를 검증했다. 최종 검증에서 `python -m unittest discover -s tests`, `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py`, `node --check web_ui/static/app.js`가 통과했다. 검증 전 기존 stale 5-node Web UI runtime(`:28083`, control `:29110`)이 현재 7-node backup UI 검증을 방해하고 있어 `/api/control`의 `exit`로 정상 종료했다.
- 2026-05-21 추가 Web UI node sequence / middle-off 브라우저 검증을 완료했다. Evidence는 `.sisyphus/evidence/web-ui-situations/task-9-*`부터 `task-16-*`와 `.sisyphus/evidence/web-ui-situations/node-sequence-middle-off-summary.md`에 있으며 전체 PASS다. 실제 Playwright/headless Chromium으로 `--no-supervisor` 순차 role process 기동, `start/pause/reset` 논리 제어, `pause/kill r2`, `pause/kill r1`, `pause/kill r1b`, `pause/kill r2b`, SVG link `data-link-id`/`data-hop-state`/`data-hop-tone`, Monitor route summary/fault localization/route trace 정보 경계를 검증했다. 최종 리뷰에서 지적된 `kill r1` primary link stale evidence와 backup-failed Monitor same-event assertion을 강화해 재실행했고 PASS다. 최종 검증에서 `python -m unittest discover -s tests`, `python -m py_compile main.py nw_demo/*.py web_ui/*.py tests/*.py`, `node --check web_ui/static/app.js`가 통과했고 QA 포트 `18080`, `19110`, `9101`-`9107`은 cleanup 후 비어 있었다.
- 2026-05-21 Web UI SVG data-path 의미를 current active route 기준으로 보정했다. Overview link의 초록/완료 표현은 현재 active route 성공에만 쓰고, inactive route의 과거 `acknowledged` 기록은 raw `data-hop-state` / `data-raw-hop-tone`으로 보존하면서 최종 `data-hop-tone="inactive"`와 `비활성 경로` 라벨로 표시한다. `Monitor.last_route_summary`는 마지막 도달 route evidence이지 continuous liveness proof가 아니므로, missing / malformed / invalid / `FAILED` / `DEGRADED` summary에서는 `data-route-active="unknown"`으로 fallback하고 final tone은 raw tone과 같게 둔다. Evidence는 `.sisyphus/evidence/web-ui-situations/active-route-link-state/`에 있으며 isolated Playwright/headless Chromium으로 primary→backup, backup→primary, invalid route summary fallback을 검증했다.
- 2026-05-21 Web UI node card의 `observed_liveness`와 `reported_state` 표시 축을 더 명확히 분리했다. `observed_liveness`는 프로세스/노드가 controller/gateway에 최근 관측되는지 나타내는 파란 연결 램프로 표시하며 사용자 문구는 `연결됨` / `단절됨`이다. `reported_state`는 node가 스스로 보고한 실행 상태이므로 표 안의 `상태` row 대신 카드 상단의 초록 계열 상태 램프로 표시한다.

## 열린 이슈

- Web UI runtime frontend reset 및 constrained backup 표시의 현재 구현은 `.sisyphus/evidence/web-ui-situations/final-summary.md`와 `.sisyphus/evidence/web-ui-situations/active-route-link-state/` 기준 PASS다. 이후 `web_ui/server.py`, API wiring, `web_ui/static` 표시 구조를 바꾸면 같은 browser DOM/text assertion + screenshot evidence로 다시 검증해야 한다. TUI 출력 파싱으로 돌아가면 안 된다.
- `docs/reference/ui-preview/`의 preview 자산은 controller/runtime과 분리해 보존하되, `preview.revised.jsx`는 현재 frontend visual source of truth로 취급한다.
- item 2의 현재 선택은 concrete backup node `r1b` / `r2b`와 route abstraction(`primary`, `backup`, `route_trace`)을 함께 쓰는 constrained backup chain이다. 임의 mesh나 cross-path routing은 여전히 비목표다.
- item 3에서 multi-host runtime config와 location metadata를 어떤 shape로 canonicalize할지 정리가 더 필요하다.
- 이후 세션에서 런타임이나 문서 기준이 바뀌면, 이 파일의 "최근 결정"과 "현재 기준"을 함께 갱신해야 한다.
- 남은 구현/검증 단계는 item 3 multi-host 구조와 추가 critical-fault 의미론을 기술 기준으로 더 구체화하는 일이다.
- 현재 known verification gap은 local LSP diagnostics뿐이며, `basedpyright-langserver`가 설치되어 있지 않아 실행할 수 없다.

## 다음 세션 시작 체크리스트

1. 먼저 [`README.md`](./README.md)를 읽고 현재 런타임 사실이 여전히 같은지 확인한다.
2. 작업이 구현 범위/구조 판단과 관련되면 [`IMPLEMENTATION_SPEC.md`](./IMPLEMENTATION_SPEC.md)를 확인한다.
3. 작업이 UI, 표현, 사용자 의도 해석과 관련되면 [`INTENT_ALIGNMENT_NOTE.md`](./INTENT_ALIGNMENT_NOTE.md)를 확인한다.
4. 추가 critical-fault 작업을 시작할 때는 현재 constrained backup chain 위에 어떤 fault 의미론을 더할지 먼저 확인한다.
5. item 3 작업을 시작할 때는 localhost 전제와 local supervisor 전제를 어디까지 분리할지 먼저 확인한다.
6. focused monitor와 integrated overview가 같은 정보를 다른 깊이로 보여준다는 surface 분리 원칙을 유지하는지 확인한다.
7. 그 다음 이 파일의 `최근 결정`, `열린 이슈`를 읽고 이번 세션의 출발점을 정한다.
8. 세션 종료 전에는 이 파일만 간결하게 갱신해 다음 작업자에게 남긴다.

## 세션 업데이트 규칙

- 이 문서는 **짧고 고신호 상태**를 유지한다.
- 새로 확정된 결정은 `최근 결정`에 추가하거나 교체한다.
- 아직 해결되지 않은 항목은 `열린 이슈`에 남긴다.
- 영속적 사실이 바뀌면 이 파일만이 아니라 해당 기준 문서도 함께 갱신해야 한다.
- 새 root markdown 로그 파일은 만들지 않는다.
