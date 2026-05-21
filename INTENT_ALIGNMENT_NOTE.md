# 의도 정렬 메모

이 문서는 사용자가 실제로 원한 방향과, 이후 작업에서 흔들리면 안 되는 **의도 / 해석 가드레일**을 정리한 기준 문서다.

현재 실행 방법과 런타임 사실은 [`README.md`](./README.md)를 따르고,
기술 구조와 메시지 규칙은 [`IMPLEMENTATION_SPEC.md`](./IMPLEMENTATION_SPEC.md)를 따른다.
이 문서는 그보다 한 단계 위에서 **왜 그렇게 해석해야 하는지**를 정리한다.

---

## 1. 가장 핵심적인 한 줄 요약

사용자가 원하는 것은 **예쁜 일반 웹 대시보드**가 아니라,
**현재 TUI에서 보이는 교육용 관찰 경험을 웹 관제 화면으로 옮긴 구조적 모니터링 UI**다.

우선순위는 다음 순서에 가깝다.

1. 교육적 가시성
2. 구조적 명확성
3. 구현 단순성
4. 제어 가능성
5. 시각적 완성도

---

## 2. 사용자가 지속적으로 강조한 핵심 원칙

### 2.1 구조는 유지하고 과정은 단순화한다

사용자는 구조 자체를 무너뜨리는 단순화를 원하지 않았다.
유지해야 하는 구조는 다음과 같다.

- `Host Simulator -> Local Agent -> Relay R1 -> Relay R2 -> Monitor`
- 두 개의 relay 유지
- `Controller/UI`는 데이터 경로 밖

### 2.2 속도보다 사람이 따라갈 수 있는 가시성이 중요하다

이 프로젝트는 실제 서비스처럼 빠르게 동작하는 것이 아니라,
ACK / timeout / retry / duplicate suppression을 눈으로 이해할 수 있게 보여주는 데 의미가 있다.

### 2.3 node-first monitoring이 핵심이다

웹 UI나 viewer는 단순한 전체 상태판이 아니라,
각 node가 독립된 관찰 대상으로 보여야 한다.

각 node 안에서는 최소한 다음이 함께 읽혀야 한다.

- 현재 상태
- node 특화 정보
- 최근 활동 로그

### 2.4 전역 로그보다 node 내부 로그가 우선이다

전역 로그는 보조일 수 있지만,
사용자가 중요하게 본 것은 **각 node가 자기 패널 안에서 자기 활동 로그를 가지는 경험**이다.

여기서 말하는 활동 로그는 단순 문자열 스크롤보다,
**자기 시점에서 받은 자료 / 응답한 자료 / 다음으로 보낸 자료 / 다음에서 받은 응답**을 구조화해서 읽을 수 있는 경험에 더 가깝다.

### 2.5 제어와 관찰은 같은 화면 안에서 이어져야 한다

이 프로젝트의 화면은 보기만 하는 정적 상태판이 아니라,
현재 TUI처럼 관찰과 제어가 이어지는 운영 화면이어야 한다.

---

## 3. 웹 UI에 대해 사용자가 실제로 의도한 것

### 3.1 TUI 경험을 웹으로 옮긴다

웹 UI는 현재 terminal viewer와 다른 별도의 새 제품을 만드는 것이 아니다.
이미 TUI에서 성립한 교육용 관찰 경험을 웹에 맞게 옮기는 방향이다.

### 3.2 topology는 수단이지 목적이 아니다

흐름과 구조는 보여야 하지만,
그 목적은 topology 자체가 아니라 **각 hop과 각 node의 의미를 더 잘 설명하는 것**이다.

따라서 topology 표현이 node-first monitoring을 밀어내면 안 된다.

### 3.3 화면은 정적 상태판이 아니라 관제 화면이어야 한다

각 node의 활동이 계속 갱신되는 느낌이 있어야 한다.
즉, “현재 값만 보이는 화면”보다 “상태와 행동이 함께 보이는 화면”이 맞다.

### 3.4 Controller/UI는 시스템 외부 관점이지만 data plane 일부처럼 보이면 안 된다

`Controller/UI`는 제어와 관찰의 중심일 수 있지만,
새로운 forwarding node나 data plane 일부처럼 해석되면 안 된다.

### 3.5 이후 Web UI도 controller / gateway surface 뒤에 있어야 한다

사용자가 선택한 방향은 token 구조를 없애는 것이 아니라,
**shared token을 유지하되 control-plane 경계를 더 명확히 정리하는 것**이다.

따라서 이후 Web UI도 node에 직접 붙는 새 runtime peer라기보다,
controller / gateway surface를 통해 상태를 보고 제어를 보내는 표현 계층으로 해석해야 한다.

### 3.6 현재 Web UI runtime은 preview visual parity를 먼저 맞춘다

현재 단계에서 Web UI runtime frontend는 `docs/reference/ui-preview/preview.revised.jsx`를 visual source of truth로 삼는다.
runtime data source는 controller / gateway로 바꾸되, 화면의 layout, palette, typography, component hierarchy는 preview 기준을 먼저 따른다.

다음 해석은 금지한다.

- preview를 단순 분위기 참고로만 취급하고 새 visual direction을 만드는 것
- cream / olive / serif 계열의 새 dashboard 스타일을 도입하는 것
- diagram canvas를 버리고 5열 grid card dashboard로 재해석하는 것
- detail inspector를 viewport-fixed side drawer로 대체하는 것
- raw JSON dump를 주요 상세 UI로 삼는 것

---

## 4. Monitor와 관제 허브에 대한 정리

이 부분은 과거에 해석이 자주 어긋났던 지점이다.

### 4.1 잘못된 해석

- `Monitor`와 별개인 독립 `관제 허브`를 새 엔티티처럼 추가하는 해석

### 4.2 사용자 의도에 더 가까운 해석

- `Monitor`는 데이터 경로의 최종 sink 역할을 가진 실제 시스템 요소다.
- 사람이 보는 화면은 그 `Monitor` 관점을 확장한 UI로 표현될 수 있다.
- 하지만 그것이 **새로운 독립 엔티티**처럼 보이면 과한 해석이다.

정리하면,

> 사용자는 Monitor와 관제 허브를 분리하려던 것이 아니라,
> Monitor를 사람이 보는 관리 화면으로 확장하려던 것이다.

---

## 5. 여러 차례 잘못 해석했던 지점

### 5.1 관제 허브를 독립 요소처럼 추가한 해석

- 잘못된 방향: `Monitor`와 별개인 새 허브 시각화
- 더 맞는 방향: 현재 화면 전체가 곧 Monitor UI / 관찰 화면

### 5.2 topology 중심으로 과도하게 기울어진 해석

구조 이미지와 연결 표현은 필요하지만,
그것은 node 관찰 경험을 더 잘 드러내기 위한 수단이어야 한다.

### 5.3 전역 관리 개념을 너무 크게 잡은 해석

사용자는 복잡한 운영 플랫폼이 아니라,
네트워크 수업용 시스템 구성 데모를 원했다.

### 5.4 한국어 중심 표현을 흔들리게 한 해석

기술 토큰은 필요할 수 있지만,
전체 사용자 경험은 한국어 중심 표현을 선호하는 방향으로 맞추는 편이 사용자 기대에 더 가깝다.

### 5.5 단일 localhost / 단일 경로를 영구 구조처럼 굳히는 해석

- 잘못된 방향: 현재 로컬 데모 구조를 최종 구조처럼 해석하는 것
- 더 맞는 방향: 현재 구조는 교육용 최소 데모의 출발점이고,
  이후 우회 경로와 multi-host 실행을 받아들일 수 있게 읽어야 한다.

---

## 6. 앞으로 절대 흔들리면 안 되는 기준

### 비타협 요소

1. 6개 역할 구조 유지
2. `R1`, `R2` 두 relay 유지
3. `Controller/UI`는 데이터 경로 밖
4. 교육적 가시성 우선
5. node별 monitoring 경험 유지
6. 각 node의 자체 로그가 기본, 전역 로그는 보조
7. `Monitor`를 별도 새 허브가 아닌 관찰 / 집계 축의 중심으로 해석
8. 웹 UI도 결국 TUI 관찰 경험의 확장으로 이해
9. UI는 node에 직접 붙는 새 data-plane peer가 아니라 controller / gateway surface 뒤의 소비자여야 함
10. 현재 token은 data plane이 아니라 control / status plane 경계라는 해석 유지
11. 현재 Web UI reset은 `preview.revised.jsx` visual parity를 먼저 만족

### 유연한 요소

1. preview parity를 만족한 뒤 topology를 어느 정도까지 전면에 둘지
2. preview parity를 만족한 뒤 node를 동시에 크게 보여줄지, 선택형 detail을 얼마나 섞을지
3. 전역 타임라인 / 이벤트 trace를 어디에 둘지
4. 한국어와 기술 토큰의 경계를 어디까지 둘지
5. 우회 경로를 node 추가로 먼저 드러낼지, route abstraction으로 먼저 드러낼지
6. multi-host 배치를 어떤 단계에서 실제 런타임으로 승격할지

### 6.1 roadmap 순서 가드레일

앞으로의 프로젝트 진행 순서는 아래 순서를 기준으로 해석한다.

1. 각 node별 TUI 모니터링을 먼저 정교화하고, 그 경험을 Web UI로 옮긴다.
2. 우회 node / 우회 경로와, 그것이 필요해지는 critical fault를 설계한다.
3. 프로세스 실행 위치를 Linux / Windows 등 여러 host로 분리한다.
4. 위 단계들이 정리된 이후에, reboot를 넘는 실질 recovery를 다룬다.

이 순서를 건너뛰어 recovery부터 크게 설계하거나,
Web UI를 현재 controller surface와 무관한 별도 제품처럼 해석하는 것은 사용자 의도와 어긋난다.

### 6.2 forward-compatibility 가드레일

이후 구현이나 문서화에서는 아래 함정을 피해야 한다.

- 단일 고정 경로만 영구 기준처럼 가정하는 것
- localhost 단일 배치를 영구 기준처럼 가정하는 것
- UI가 node와 직접 같은 수준의 protocol peer가 되도록 키우는 것
- token을 data plane 핵심 개념처럼 확대 해석하는 것

### 6.3 monitoring surface 가드레일

- integrated viewer는 계속 summary-first overview여야 한다.
- 전체 overview에 full payload body나 multiline raw log를 직접 쏟아붓지 않는다.
- deep inspection은 node-focused monitor 같은 별도 상세 surface로 분리한다.
- 단, 별도 상세 surface는 여러 controller 프로세스나 여러 port를 의미하지 않는다. 하나의 controller/UI 안에서 `focus <node>`로 관찰 대상을 바꾸는 방식이 사용자 의도에 더 가깝다.
- 런타임 focus 명령은 사용자가 입력하기 쉬운 `focus host`, `focus agent` 별칭을 우선 노출하고, focused 화면의 최근 노드 활동은 현재 관찰 대상 node 기준으로 좁혀 보여준다.
- `focus` / `overview`는 관찰 화면의 local UI state 전환이며, node 제어 명령이나 data-plane protocol 변화로 해석하지 않는다.
- structured traffic 사실의 source of truth는 controller가 아니라 각 node 자신이어야 한다.
- `reported_state`, `observed_liveness`, `hop_state`를 한 문장으로 뭉개거나 같은 의미처럼 다루지 않는다.

---

## 7. 현재 preview 기준 해석 시 주의사항

현재 `preview.revised.jsx`는 Web UI reset의 visual source of truth다.
다만 기술 구조와 사용자 의도 기준보다 위에 있는 문서는 아니므로, 아래 위험은 계속 같이 본다.

- `Monitor`와 관제 허브가 분리된 것처럼 보일 수 있음
- topology가 node 동시 관찰보다 앞서 보일 수 있음
- 일부 표현이 아직 기술 중심 / 혼합 언어일 수 있음

이후 수정은 다음 방향이 바람직하다.

- `Monitor`를 별도 허브가 아니라 **관찰 / 집계 축**으로 해석
- node별 관찰성과 구조 시각화를 균형 있게 유지
- 설명용 새 개체를 추가하기보다 기존 개체의 역할 표현을 정교화
- visual structure 변경이 필요하면 구현으로 먼저 바꾸지 말고 `WEB_UI_SPEC.md`와 이 문서를 먼저 갱신

---

## 8. 실무용 결론

앞으로 UI / 시안 관련 판단을 할 때는 아래 문장을 기준으로 삼는다.

> 이 프로젝트의 웹 UI는 별도의 새로운 운영 플랫폼을 설계하는 것이 아니라,
> 현재 TUI에서 이미 드러나는 교육용 관찰 경험을 웹으로 확장하는 것이다.
> 구조는 유지하고, 각 node의 역할과 활동을 더 잘 보이게 하며,
> Monitor는 별도 새 허브가 아니라 사람이 보는 관찰 / 집계 화면의 중심으로 해석해야 한다.
