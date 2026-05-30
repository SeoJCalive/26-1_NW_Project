# 네트워크 장애 감시 및 우회 라우팅 시뮬레이션

이 저장소는 Python 표준 라이브러리만 사용해 구현한 네트워크 장애 감시 및 우회 라우팅 시뮬레이션이다. primary 경로와 constrained backup 경로를 가진 여러 node role을 독립 프로세스로 실행하고, TCP + 줄 단위 JSON 메시지로 event forwarding, ACK, retry, duplicate suppression, fault injection, monitoring을 보여준다.

구조와 실행 흐름은 이 README에서 바로 확인할 수 있고, 역할별 동작과 검증 기준은 문서 안내의 overview에 정리했다.
<img width="1645" height="898" alt="스크린샷 2026-05-30 오후 5 30 31" src="https://github.com/user-attachments/assets/779901ce-ab90-4ef4-842b-fd95861bbbe3" />

## 구성 역할

- Host Simulator
- Local Agent
- Relay R1
- Relay R2
- Relay R1B
- Relay R2B
- Monitor
- Controller/UI

## 빠른 이해

이 프로젝트는 다음 흐름을 눈에 보이게 보여준다.

- Host 관측값 기반 Local Agent event 생성
- JSON `EVENT` / `ACK` / `CONTROL` / `STATUS` / `STATUS_REPORT`
- primary `Local Agent -> R1 -> R2 -> Monitor` forwarding
- backup `Local Agent -> R1B -> R2B -> Monitor` forwarding
- hop-by-hop ACK
- ACK timeout과 최대 3회 retry
- `event_id` 기반 duplicate suppression
- `CPU_SPIKE`, `SERVICE_DOWN`, `LATENCY_HIGH` fault injection
- node 상태, retry, duplicate, host 상태, route trace, 장애 위치 추정 표시

## 빠른 실행

저장소 루트에서 실행한다.

```bash
python main.py
```

이 명령은 Controller/UI viewer와 Host / Agent / R1 / R2 / R1B / R2B / Monitor 역할 프로세스를 함께 시작한다. 비대화형 환경에서는 scripted scenario를 자동 실행하고 약 56초 후 종료한다.

별도 controller terminal을 붙이려면 shared control token을 명시해 실행한다.

```bash
python main.py --controller --host 127.0.0.1 --port 9110 --control-token <token>
```

특정 node를 집중해서 보려면 standalone controller UI의 focused mode를 사용한다.

```bash
python main.py --role controller --host 127.0.0.1 --port 9110 --control-token <token> --focus-node r1
```

실행 중에는 같은 `viewer>` 프롬프트에서 `focus <node>`, `overview`, `focus all`로 관찰 대상을 전환할 수 있다.

## 역할별 개별 실행

각 역할은 독립적으로 실행할 수 있다.

```bash
python main.py --role controller
python main.py --role host
python main.py --role agent
python main.py --role relay-r1
python main.py --role relay-r2
python main.py --role relay-r1b
python main.py --role relay-r2b
python main.py --role monitor
```

standalone role과 standalone controller UI는 기본적으로 shared control token이 필요하다. 의도적으로 무인증 제어를 허용하려면 `--allow-unauthenticated-control`을 명시한다.

## 기본 포트

아래 포트는 standalone role 실행과 `--fixed-node-ports` Web UI 실행의 기본값이다.

- Host Simulator: `9101`
- Local Agent: `9102`
- Relay R1: `9103`
- Relay R2: `9104`
- Monitor: `9105`
- Relay R1B: `9106`
- Relay R2B: `9107`
- Controller/UI: `9110`

일반 Web UI supervisor 실행은 node role process에 빈 포트를 자동 할당해 기존 `9101-9107` 점유와 충돌하지 않게 한다.

## Web UI
<img width="1312" height="936" alt="스크린샷 2026-05-30 오후 5 33 14" src="https://github.com/user-attachments/assets/92a03cee-ea92-4617-8f4c-f8c9acf73779" />

Web UI runtime은 `web_ui/`에서 실행된다. 이 화면은 TUI 출력을 파싱하지 않고, controller가 수신한 `STATUS_REPORT` / `STATUS`와 각 node의 `detail.traffic` 자료를 JSON API로 읽어 표시한다.

```bash
python -m web_ui.server --web-port 8080
```

이 명령은 기본적으로 Controller/Gateway status surface와 Host / Agent / R1 / R2 / R1B / R2B / Monitor role process를 함께 시작한다.

이미 별도 runtime을 띄운 상태에서 Web UI만 붙이려면 supervisor를 끈다.

```bash
python -m web_ui.server --web-port 8080 --no-supervisor --control-token <token>
```

주요 local endpoint는 다음과 같다.

- `GET /`: Web UI 화면
- `GET /api/state`: controller/gateway runtime state snapshot
- `POST /api/control`: viewer/controller 명령 문자열 전달
- `POST /api/power`: Web UI supervisor node process 시작/정지

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
delay r1b 1.5
delay r2b 1.5
focus host
focus agent
focus r1
focus r1b
focus r2
focus r2b
focus monitor
overview
focus all
quit
exit
```

`focus`는 Controller/UI 내부 화면 전환 명령이다. 노드에 `CONTROL` 메시지를 보내지 않는다. 유효한 대상은 `host`, `agent`, `r1`, `r2`, `r1b`, `r2b`, `monitor`다.

## 구현 정책

- Host는 raw observation만 제공하고, fault 판단은 Local Agent가 담당한다.
- primary hop 실패가 관찰되면 Agent는 같은 `event_id`로 backup 경로를 시도한다.
- 임의 mesh나 `R1 -> R2B`, `R1B -> R2` 교차 경로는 사용하지 않는다.
- Monitor는 자동 실행 대상 node 중 하나이며, 별도 tmux 세션으로 띄우는 경로는 기본 사용법이 아니다.
- viewer 화면에는 외부 controller 접속 힌트가 표시되지만 token 값은 노출하지 않는다.

## 검증

현재 기준 검증 명령은 다음과 같다.

```bash
python -m unittest
GIT_MASTER=1 git diff --check
```

최근 검증 기준으로 `python -m unittest`는 121개 테스트를 통과한다.

## 문서 안내

- `docs/PROJECT_OVERVIEW.md`: 역할별 동작, 데이터 경로, UI/API, 검증 기준
