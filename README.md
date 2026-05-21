# 네트워크 프로젝트 최소 데모

이 문서는 이 저장소의 **첫 진입점 README**다. 먼저 여기서 실행 방법과 런타임 구성을 확인하고, 더 자세한 기술 기준·의도·작업 맥락·배경은 아래 `문서 안내`의 각 문서로 이동하면 된다.

이 프로젝트는 Python 표준 라이브러리만 사용하여 다음 6개 역할을 유지하는 네트워크 교육용 데모를 구현한다.

- Host Simulator
- Local Agent
- Relay R1
- Relay R2
- Monitor
- Controller/UI

현재 런타임은 **프로세스 분리 구조**를 사용한다.

- 각 역할은 독립 프로세스로 실행 가능하다.
- 역할 간 통신은 TCP + 줄 단위 JSON 메시지를 사용한다.
- 기본 viewer 모드는 로컬에서 각 역할 프로세스를 자동으로 띄운다.
- 외부 controller 터미널은 별도로 접속해 명령을 보낸다.

## 문서 안내

- `README.md`: 가장 먼저 읽는 문서. 실행 방법, 런타임 구성, 데모 확인 포인트만 빠르게 안내한다.
- `IMPLEMENTATION_SPEC.md`: 구현의 기술 기준이 되는 정본 문서. 구조, 메시지 흐름, 동작 규칙의 상세는 여기서 확인한다.
- `INTENT_ALIGNMENT_NOTE.md`: 사용자 의도와 비타협 원칙을 정리한 가드레일 문서. 해석이 흔들릴 때 기준점으로 본다.
- `AI_IMPLEMENTATION_BRIEF.md`: 현재 구현 상태와 작업 맥락을 요약한 living context 문서. 세션 인수인계나 다음 작업 출발점으로 사용한다.
- `docs/history/PROCESS_SEPARATION_ARCHITECTURE.md`: 프로세스 분리 방향을 설명한 배경 문서. 현재 정답이라기보다 설계 변화의 맥락과 역사적 배경을 확인할 때 본다.
- `docs/reference/`: 현재 작업에서 반복 참조하는 supporting reference 자료 경로. 사용자용 guide는 `docs/reference/network-project/guide/`에서 확인하고, preview 자산이나 참고용 PDF/PPTX 자료처럼 root current 문서를 대체하지 않는 live reference 자료도 여기서 관리한다.
- `AGENTS.md`: root markdown 거버넌스 문서. 어떤 문서를 어디에 두는지, 새 root markdown를 만들지 말아야 하는지, 세션 맥락을 어디에 갱신해야 하는지의 기준을 정의한다.

외부에서 가져오거나 새로 모은 미분류 자료의 임시 진입점이 필요하면 `docs/inbox/`를 사용한다.
`docs/inbox/`는 OpenCode 자동 분류 대기 구역이며, 이후 자료 성격에 따라 `docs/reference/`, `docs/history/`, `docs/archive/` 또는 기존 canonical 문서로 이동·병합한다.

## 빠른 이해

이 데모는 다음 흐름을 눈에 보이게 보여주는 데 초점을 둔다.

- host 상태 기반 event 생성
- JSON `EVENT` / `ACK` / `CONTROL` / `STATUS`
- `R1 -> R2 -> Monitor` forwarding
- hop-by-hop ACK
- `2s` hop ACK timeout, 최대 `3`회 retry
- `event_id` 기반 duplicate suppression
- `2s` 단위의 눈에 보이는 tick
- `CPU_SPIKE`, `SERVICE_DOWN`, `LATENCY_HIGH` fault injection
- 노드 상태 / retry / duplicate / host 상태 / 최근 이벤트 표시

## 빠른 실행

저장소 루트에서 실행한다.

```bash
python main.py
```

이 명령은 다음을 한 번에 수행한다.

- Controller/UI viewer 시작
- Host / Agent / R1 / R2 / Monitor 역할 프로세스 자동 실행

Monitor는 별도 tmux나 별도 관찰 세션으로 띄우지 않고, 다른 node와 같은 supervisor-managed role로 실행한다.

별도 터미널에서 controller client를 붙이려면 다음을 실행한다.

```bash
python main.py --controller
```

이 separate controller 모드는 shared control token이 필요하다.
`--control-token <token>` 또는 `NW_CONTROL_TOKEN` 환경 변수를 함께 제공해야 한다.

특정 node만 깊게 보려면 standalone controller UI를 focused mode로 실행한다.

```bash
python main.py --role controller --host 127.0.0.1 --port 9110 --control-token <token> --focus-node r1
```

이 mode는 integrated viewer처럼 전체 topology를 요약하지 않고,
선택한 node의 structured traffic snapshot만 집중해서 보여준다.
실행 중에는 같은 `viewer>` 프롬프트에서 `focus <node>`, `overview`, `focus all`로
별도 controller 프로세스를 다시 띄우지 않고 관찰 대상을 전환할 수 있다.

비대화형 환경에서는 viewer가 scripted demo를 자동 실행하고 약 56초 후 종료한다.

## 역할별 개별 실행

각 역할은 독립적으로도 실행할 수 있다.

```bash
python main.py --role controller
python main.py --role host
python main.py --role agent
python main.py --role relay-r1
python main.py --role relay-r2
python main.py --role monitor
```

standalone role / standalone controller UI도 기본적으로 shared control token이 필요하다.
의도적으로 무인증 제어를 허용하려면 `--allow-unauthenticated-control`을 명시해야 한다.

`--focus-node`는 `--role controller`에서만 허용된다.

## 기본 포트

- Host Simulator: `9101`
- Local Agent: `9102`
- Relay R1: `9103`
- Relay R2: `9104`
- Monitor: `9105`
- Controller/UI: `9110`

## 자주 쓰는 실행 예시

```bash
python main.py --duration 20
python main.py --scripted
python main.py --controller --host 127.0.0.1 --port 9110 --control-token <token>
python main.py --role controller --host 127.0.0.1 --port 9110 --control-token <token> --focus-node r1
python main.py --role host --controller-host 127.0.0.1 --controller-port 9110 --control-token <token>
python main.py --role host --allow-unauthenticated-control
```

## Web UI runtime

실제 Web UI runtime은 새 `web_ui/` 위치에서 실행한다.
이 화면은 TUI 출력이나 terminal 렌더링 결과를 파싱하지 않고,
controller가 수신한 `STATUS_REPORT` / `STATUS`와 각 node의 `detail.traffic` 자료를 JSON API로 읽어 표시한다.

```bash
python -m web_ui.server --web-port 8080
```

이 명령은 기본적으로 Controller/Gateway status surface와 Host / Agent / R1 / R2 / Monitor role 프로세스를 함께 시작한다.
이미 별도 runtime을 띄운 상태에서 Web UI만 붙이려면 다음처럼 role supervisor를 끈다.

```bash
python -m web_ui.server --web-port 8080 --no-supervisor --control-token <token>
```

Web UI의 주요 local endpoint는 다음과 같다.

- `GET /`: `docs/reference/ui-preview/WEB_UI_SPEC.md`와 `preview.revised.jsx` visual parity를 따라야 하는 Web UI
- `GET /api/state`: controller/gateway runtime state snapshot
- `POST /api/control`: viewer/controller 명령 문자열 전달

## Controller 명령어

```text
help
start
start r1
pause
pause r1
reset
reset r2
kill monitor
fault cpu on
fault cpu off
fault service on
fault service off
fault latency on
fault latency off
ackdrop
delay r1 1.5
delay r2 1.5
focus local-agent
focus host
focus agent
focus r1
focus monitor
overview
focus all
quit
exit
```

`focus`는 controller/UI 내부 화면 전환 명령이다.
노드에 `CONTROL` 메시지를 보내지 않으며, 유효한 대상은
`host`, `agent`, `r1`, `r2`, `monitor`다.
`host`는 `host-simulator`, `agent`는 `local-agent`로 전환한다.
`overview`와 `focus all`은 전체 요약 화면으로 돌아간다.
`quit`와 `exit`는 현재 controller/viewer를 정상 종료하며, 기본 viewer 모드에서는 supervisor가 자동 실행한 Host / Agent / R1 / R2 / Monitor role도 함께 정리한다.

별도 controller 터미널은 viewer / controller UI와 **같은 shared control token**을 사용해야 제어 요청이 수락된다.
보안상 viewer 화면은 token 값을 그대로 출력하지 않는다.
- 사용자가 `--control-token <token>` 또는 `NW_CONTROL_TOKEN`으로 명시적으로 shared token을 준 경우: 화면에는 접속 명령만 보이고, 같은 token을 별도 terminal에 직접 넣어 사용한다.
- no-arg viewer가 내부적으로 private token을 자동 생성한 경우: token 값은 화면에 표시되지 않으며, 외부 controller가 필요하면 명시적 `--control-token`으로 다시 시작해야 한다.

## 데모 메모

- version 1에서는 recovery를 필수로 구현하지 않는다.
- Web UI 팔레트의 fault 제어는 초 단위 일회성 주입보다 사용자가 직접 켜고 끄는 `fault cpu|service|latency on|off` 흐름을 우선 노출한다. 기존 `fault cpu 6` 형태는 controller client 호환 명령으로 유지된다.
- 기본 scripted demo는 Monitor ACK를 한 번 드롭하여 retry / dedup 흐름을 보이게 한다.
- 상위 hop의 응답 대기 시간은 하위 hop의 전체 retry 창보다 길게 잡아, 하위 relay가 아직 정상 처리 중일 때 상위 relay가 먼저 실패하지 않도록 했다.
- relay delay 명령은 데모 timing model을 유지하기 위해 내부적으로 최대 `3.0`초까지만 반영된다.
- supervisor가 자동으로 띄운 역할 프로세스는 `[NW] : <node>` 형식의 라벨로 표시된다.
- Monitor는 자동 실행 대상 node 중 하나이며, 별도 tmux 세션으로 띄우는 경로는 기본 사용법이 아니다.
- 최근 활동은 시스템 / 제어 / 노드 활동으로 나누어 표시된다.
- viewer 화면에는 외부 controller 접속 힌트가 표시되지만, token 값은 노출하지 않는다.
- no-arg viewer 모드는 로컬 편의 실행용이며, 실제 구조는 역할별 독립 프로세스 기준이다.
- integrated viewer는 summary-first overview를 유지하고, full payload dump는 직접 출력하지 않는다.
- focused node monitor는 이전 node에서 받은 자료 / 이전 node로 응답한 자료 / 다음 node로 보낸 자료 / 다음 node에게서 받은 응답을 structured snapshot으로 보여준다.
- 하나의 controller/UI 안에서 `focus <node>`로 focused node monitor 대상을 바꿀 수 있으며, 여러 controller port를 띄우지 않는다.
- focused node monitor의 최근 노드 활동은 전역 활동이 아니라 현재 focus 대상 node 활동만 최대 10줄 보여준다.
