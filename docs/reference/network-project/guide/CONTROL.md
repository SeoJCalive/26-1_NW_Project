# 사용자 제어 가이드

이 문서는 사용자가 NW 프로젝트를 실행하면서 직접 입력하고 조작할 수 있는 명령을 정리한다. 현재 구현의 최종 기준은 root의 `README.md`와 `IMPLEMENTATION_SPEC.md`를 우선한다.

## 기본 실행

저장소 root에서 실행한다.

```bash
python main.py
```

이 명령은 terminal viewer를 시작하고 Host / Agent / R1 / R2 / Monitor 역할 프로세스를 supervisor-managed child process로 자동 실행한다. Monitor는 별도 tmux 관찰 세션이 아니라 일반 node 역할 중 하나다.

비대화형 환경에서 자동 demo를 강제로 실행하려면 다음을 사용한다.

```bash
python main.py --scripted
python main.py --duration 20
```

`--duration <seconds>`는 viewer/controller 실행 시간을 제한한다. stdin이 TTY가 아니어도 viewer 모드를 유지하려면 `--interactive`를 사용한다.

```bash
python main.py --interactive --control-token demo123
```

## 외부 Controller Terminal

이미 viewer가 떠 있는 상태에서 별도 terminal로 controller client를 붙이려면 같은 control token을 사용한다.

```bash
python main.py --controller --host 127.0.0.1 --port 9110 --control-token demo123
```

`--controller` 모드는 반드시 `--control-token <token>` 또는 `NW_CONTROL_TOKEN` 환경 변수가 필요하다. no-arg viewer는 private token을 자동 생성하지만 화면에 token 값을 출력하지 않으므로, 외부 controller를 쓸 계획이면 viewer도 명시 token으로 시작한다.

```bash
NW_CONTROL_TOKEN=demo123 python main.py
NW_CONTROL_TOKEN=demo123 python main.py --controller
```

## Focused Node Monitor

특정 node만 자세히 보려면 standalone controller UI를 focused mode로 실행한다.

```bash
python main.py --role controller --host 127.0.0.1 --port 9110 --control-token demo123 --focus-node r1
```

`--focus-node`는 `--role controller`에서만 사용할 수 있다. 가능한 값은 다음과 같다.

```text
host-simulator
local-agent
r1
r2
monitor
```

실행 중에는 viewer 프롬프트에서 `focus <node>`, `overview`, `focus all`로 화면을 바꿀 수 있다.

## 개별 Role 실행

각 역할은 독립 프로세스로도 실행할 수 있다.

```bash
python main.py --role controller --control-token demo123
python main.py --role host --control-token demo123
python main.py --role agent --control-token demo123
python main.py --role relay-r1 --control-token demo123
python main.py --role relay-r2 --control-token demo123
python main.py --role monitor --control-token demo123
```

standalone role은 기본적으로 shared control token이 필요하다. 의도적으로 인증 없는 제어를 허용할 때만 다음 옵션을 사용한다.

```bash
python main.py --role host --allow-unauthenticated-control
```

role process의 listen 주소와 controller 보고 대상은 필요할 때 바꿀 수 있다.

```bash
python main.py --role host --listen-host 127.0.0.1 --listen-port 9101 --controller-host 127.0.0.1 --controller-port 9110 --control-token demo123
```

## Viewer / Controller 프롬프트 명령

interactive viewer에서는 `viewer>` 프롬프트에 입력한다. 외부 controller terminal에서는 `controller>` 프롬프트에 입력한다.

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
focus host
focus agent
focus r1
focus r2
focus monitor
focus all
quit
exit
```

## 명령 의미

`help`는 사용 가능한 controller 명령을 출력한다.

`start [node]`는 전체 또는 특정 node를 실행 상태로 전환한다. node를 생략하면 `all`로 처리한다.

`pause [node]`는 전체 또는 특정 node를 일시 정지한다. node를 생략하면 `all`로 처리한다.

`reset [node|all]`은 전체 또는 특정 node 상태를 초기화한다. node를 생략하면 전체 reset이다.

`kill <node>`는 지정한 node에 shutdown 제어를 보낸다. `kill all`은 지원하지 않는다.

`fault cpu on|off`는 Host Simulator의 `CPU_SPIKE` fault를 사용자가 직접 켜고 끈다.

`fault service on|off`는 Host Simulator의 `SERVICE_DOWN` fault를 사용자가 직접 켜고 끈다.

`fault latency on|off`는 Host Simulator의 `LATENCY_HIGH` fault를 사용자가 직접 켜고 끈다.

`fault cpu 6`처럼 시간을 주는 형태는 controller/script 호환 경로로 유지되지만, Web UI 팔레트에서는 수동 on/off 스위치를 기본으로 쓴다.

`ackdrop`은 Monitor가 다음 ACK를 한 번 드롭하게 만들어 retry / duplicate suppression 흐름을 보기 위한 demo 명령이다.

`delay r1|r2 [sec]`는 relay 처리 지연을 조정한다. 시간을 생략하면 기본 `0.75`초이며, demo timing model상 내부 반영은 최대 `3.0`초로 제한된다.

`focus <node>`는 viewer/controller UI 내부 화면만 특정 node monitor로 전환한다. node에 `CONTROL` 메시지를 보내지 않는다.

`overview`와 `focus all`은 전체 요약 화면으로 돌아간다.

`quit`와 `exit`는 현재 controller/viewer를 정상 종료한다. 기본 viewer 모드에서는 supervisor가 자동 실행한 Host / Agent / R1 / R2 / Monitor role도 함께 정리된다. 외부 controller terminal에서 `exit`를 입력하면 viewer/controller에 shutdown 요청을 보낸 뒤 client도 종료한다.

## Node 이름과 Alias

제어 대상 node는 아래 이름을 사용한다.

```text
host-simulator
local-agent
r1
r2
monitor
all
```

입력 편의를 위해 일부 alias도 허용된다.

```text
host -> host-simulator
agent -> local-agent
relay-r1 -> r1
relay-r2 -> r2
```

`focus` 명령에서는 `host`와 `agent` alias를 자주 사용한다.

## 기본 포트

```text
Host Simulator: 9101
Local Agent:    9102
Relay R1:       9103
Relay R2:       9104
Monitor:        9105
Controller/UI:  9110
```

## 종료와 잔여 프로세스 정리

정상 종료는 viewer/controller 프롬프트에서 `exit` 또는 `quit`를 입력하는 것이다.

```text
viewer> exit
controller> exit
```

standalone role을 별도 terminal이나 tmux에서 직접 띄운 경우에는 supervisor가 회수하지 못할 수 있다. 먼저 현재 role process를 확인한다.

```bash
ps -ef | grep 'main.py --role' | grep -v grep
```

현재 프로젝트의 demo token으로 띄운 role만 정리하려면 다음을 사용한다.

```bash
pkill -f 'python main.py --role .*--control-token demo123'
```

PID를 알고 있으면 직접 종료할 수 있다.

```bash
kill <pid1> <pid2>
```

그래도 남아 있을 때만 마지막 수단으로 강제 종료한다.

```bash
kill -9 <pid1> <pid2>
```

tmux session으로 viewer나 role을 띄웠다면 session도 함께 확인한다.

```bash
tmux ls
tmux kill-session -t <session-name>
```

## 자주 쓰는 조합

명시 token으로 viewer를 시작하고 외부 controller를 붙이는 기본 조합이다.

```bash
python main.py --interactive --control-token demo123
python main.py --controller --control-token demo123
```

R1 집중 관찰 화면으로 controller UI를 띄우는 조합이다.

```bash
python main.py --role controller --control-token demo123 --focus-node r1
```

retry 흐름을 확인하는 조작 순서다.

```text
ackdrop
fault cpu on
fault cpu off
```

relay 지연 효과를 확인하는 조작 순서다.

```text
delay r1 1.5
fault latency on
fault latency off
```

전체 상태를 초기화하고 다시 진행시키는 조작 순서다.

```text
reset
start
```
