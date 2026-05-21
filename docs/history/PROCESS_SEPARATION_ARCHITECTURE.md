# 프로세스 분리 아키텍처 제안서

## 역사 문서 안내

이 문서는 **현재 구현의 source of truth가 아니라 역사적 / 배경적 아키텍처 문서**다.

- 현재 실행 방식과 현재 런타임 사실: [`README.md`](../../README.md)
- 현재 기술 구조와 구현 기준: [`IMPLEMENTATION_SPEC.md`](../../IMPLEMENTATION_SPEC.md)

즉, 이 문서는 “왜 이런 구조를 원했고 어떤 설계 논리로 정리했는가”를 이해하는 데 사용한다.
현재 상태 판단은 이 문서보다 `README.md`와 `IMPLEMENTATION_SPEC.md`를 우선한다.

---

## 1. 문서 목적

이 문서는 프로젝트가 6단 구조를 어떤 이유로 유지하는지,
그리고 프로세스 경계, transport 선택, ACK ownership, STATUS 보고 설계를 어떤 철학으로 잡았는지를 설명한다.

초기 논의 시점에는 프로세스 분리를 미래 목표처럼 다뤘던 흔적이 있지만,
현재 저장소 기준으로는 이미 프로세스 분리 런타임이 구현되어 있다.
이 문서는 그 변화의 **배경과 rationale**을 보존하는 문서로 읽어야 한다.

---

## 2. 프로젝트 방향

### 2.1 당시 유지 대상으로 본 것

이 문서가 정리되던 시점에는 다음 논리 구조를 유지 대상으로 보았다.

`Host Simulator -> Local Agent -> Relay R1 -> Relay R2 -> Monitor`

`Controller/UI`는 데이터 경로 밖에 둔다.

### 2.2 왜 이 구조를 유지 대상으로 보았는가

- 사용자가 처음부터 명시적으로 원한 구조다.
- relay 역할과 hop-by-hop 전달을 눈에 보이게 설명할 수 있다.
- 제어 경로와 데이터 경로를 분리해 교육적 설명과 디버깅이 쉬워진다.

### 2.3 무엇을 피하려 했는가

- 모든 역할을 하나의 로컬 결합 구조로 다시 묶는 것
- 복잡한 서비스형 분산 시스템으로 과도하게 확장하는 것
- 외부 인프라가 relay의 의미를 가려 버리는 것

---

## 3. 아키텍처 요약

### 3.1 프로세스 목록

장기적으로나 현재 구조적으로나 역할은 다음 6개다.

1. Host Simulator
2. Local Agent
3. Relay R1
4. Relay R2
5. Monitor
6. Controller/UI

### 3.2 권장 실행 모델의 의미

`main.py` 하나를 유지하되 역할 플래그로 다른 프로세스를 실행하는 방식은,
코드베이스를 불필요하게 쪼개지 않으면서도 실제 프로세스 경계를 살리는 방법으로 제안되었다.

이 접근의 장점은 다음과 같다.

- 저장소 구조를 단순하게 유지할 수 있다.
- 로컬 실행이 쉽다.
- 이후 다중 호스트나 다른 실행 환경으로 확장해도 개념 변화가 작다.

---

## 4. 핵심 통신 구조 rationale

### 4.1 데이터 경로

`Host Simulator -> Local Agent -> Relay R1 -> Relay R2 -> Monitor`

이 경로는 단순한 설명용 라인이 아니라,
프로젝트의 핵심 교육 흐름을 설명하기 위한 기준선으로 보았다.

### 4.2 제어 경로

`Controller/UI -> 각 노드`

제어는 별도 경로로 두는 편이 적절하다고 정리했다.
그래야 controller가 시스템을 조작하더라도 데이터 plane 일부처럼 보이지 않기 때문이다.

### 4.3 상태 보고 경로

`각 노드 -> Controller/UI`

상태 보고도 데이터 경로와 분리하는 편이 적절하다고 보았다.
그래야 문제가 데이터 전달 문제인지 제어 / 관찰 문제인지 구분하기 쉽다.

---

## 5. 전송 방식 선택 rationale

기본 전송 방식은 **TCP + 줄 단위 JSON 메시지**로 정리되었다.

이 선택을 선호한 이유는 다음과 같다.

- 수업 프로젝트 수준에서 충분히 단순하다.
- 로컬과 멀티호스트 모두에서 같은 개념을 유지할 수 있다.
- EVENT와 ACK의 흐름을 직접 추적하기 쉽다.
- 외부 브로커가 relay의 역할을 가리지 않는다.

다음 선택지는 의도적으로 기본 설계에서 제외했다.

- `multiprocessing.Queue`: 로컬 결합이 강함
- Unix domain socket: 기본값으로는 확장성 제약이 큼
- HTTP: 파이프라인형 EVENT/ACK 흐름을 설명하기에 덜 자연스러움
- Kafka / Redis / RabbitMQ: 교육용 relay 의미보다 운영 복잡도가 커짐

---

## 6. 역할별 책임 설계 rationale

### 6.1 Host Simulator

- host 상태를 생성한다.
- forwarding node처럼 행동하지 않는다.

이유:
원시 상태와 해석된 event를 분리해야 Local Agent의 의미가 살아난다.

### 6.2 Local Agent

- host 상태를 읽는다.
- EVENT 발생 여부를 판단한다.

이유:
상태 관측이 네트워크 EVENT로 바뀌는 의미적 경계를 분명히 보여준다.

### 6.3 Relay R1 / Relay R2

- 단순 통과 노드가 아니라 신뢰성 전달 hop이다.
- duplicate 검사와 ACK / timeout / retry ownership을 가진다.

이유:
multi-hop forwarding과 hop-by-hop reliability를 눈에 보이게 설명할 수 있다.

### 6.4 Monitor

- 최종 sink 역할을 한다.
- 이벤트 기록과 상태 집계를 수행한다.

이유:
최종 수용 지점을 명확히 해야 파이프라인의 의미가 흐려지지 않는다.

### 6.5 Controller/UI

- CONTROL 명령을 보낸다.
- STATUS를 수집한다.
- 전체 상태를 보여준다.

이유:
관찰과 제어의 중심일 수는 있지만, forwarding node가 되어서는 안 된다.

---

## 7. Host-Agent 경계 설계

이 경계는 relay forwarding과 같은 의미로 다루지 않는다.

- Host Simulator는 최신 host 상태 스냅샷을 제공한다.
- Local Agent는 사람이 볼 수 있는 주기로 polling 또는 요청한다.
- EVENT 생성 여부는 Local Agent가 결정한다.

이유:

- host 상태는 forwarding 되는 네트워크 EVENT와 성격이 다르다.
- Local Agent는 관측을 alert / event 생성으로 바꾸는 의미적 경계로 남아야 한다.

---

## 8. ACK / Retry / Duplicate 처리 원칙

### 8.1 소유권 원칙

각 forwarding hop에서 송신자는 다음을 소유한다.

- pending ACK table
- timeout timer
- retry count
- 최종 실패 판정

수신자는 다음을 소유한다.

- 로컬 검증
- duplicate 검사
- 로컬 수용 / 처리
- ACK 반환

### 8.2 duplicate에도 ACK를 다시 보낼 수 있는 이유

duplicate는 원래 메시지의 중복 생성이 아니라,
ACK 유실 때문에 생긴 재전송일 수 있다.

따라서 duplicate를 조용히 버리기만 하면 송신자는 끝까지 재시도할 수 있다.
duplicate 재-ACK은 hop-by-hop reliability를 더 깔끔하게 만든다.

---

## 9. STATUS 보고 설계

각 노드는 Controller/UI에 STATUS를 보낸다.

권장 STATUS 항목 예시는 다음과 같다.

- `node_id`
- `state`
- queue 또는 backlog 길이
- `pending_ack_count`
- `retry_total`
- `duplicate_dropped`
- 최근 활동 / note
- 마지막 heartbeat 시각

이 구조를 선호한 이유는 다음과 같다.

- controller polling 중심 구조보다 단순하다.
- heartbeat 모델을 자연스럽게 만들 수 있다.
- stale / disconnected 판단이 쉬워진다.

---

## 10. 설정 설계

토폴로지와 시간 관련 기본값은 하나의 공통 설정 소스에 두는 것이 바람직하다고 정리했다.

대표 항목:

- node ID
- listen host / port
- downstream host / port
- controller host / port
- tick interval
- poll interval
- relay artificial delay
- ACK timeout
- max retry count

이유:

- 처음에는 한 서버에서 쉽게 실행되어야 한다.
- 나중에 멀티호스트로 옮길 때 대부분 설정 변경만으로 끝나는 편이 좋다.

---

## 11. 관측성과 로그 지침

이 프로젝트의 관측성은 단순하게 유지해야 한다.

권장 항목:

- Controller/UI의 viewer
- 프로세스별 단순 로그
- 최근 활동 텍스트 표시
- retry / duplicate 카운터 표시
- heartbeat freshness 표시

이유:

- 교육적 가치를 유지할 수 있다.
- 무거운 telemetry stack 없이도 시스템을 이해할 수 있다.

---

## 12. 비목표

다음은 의도적으로 범위 밖으로 두었다.

- 디스크 기반 영속 메시지 저장
- 전체 프로세스 재시작 후 replay
- 고급 failover routing
- fan-out 구조
- consensus / leader election
- 무거운 orchestration / recovery engine
- production-grade distributed tracing stack

---

## 13. 마이그레이션 논리

이 문서가 쓰이던 시점에는,
시스템을 더 명확한 프로세스 경계로 정리하기 위한 안전한 migration 순서를 다음처럼 생각했다.

1. 공통 메시지 스키마와 transport abstraction 추출
2. Monitor 분리
3. Relay R2 분리
4. Relay R1 분리
5. Local Agent 분리
6. Host Simulator 분리
7. Controller/UI 정리

현재는 이미 프로세스 분리 런타임이 구현되어 있으므로,
이 순서는 **현재 작업 지시**가 아니라 과거 설계 논리와 이행 순서의 기록으로 읽어야 한다.

---

## 14. 최종 요약

이 문서가 보존하려는 핵심은 다음이다.

- 6단 구조 유지
- controller는 데이터 경로 밖
- TCP + 줄 단위 JSON 기반의 단순한 transport
- hop별 ACK / retry ownership
- duplicate-safe 전달
- push 기반 STATUS 보고
- 과도한 인프라 도입 금지

이 문서는 현재 truth를 직접 선언하는 문서가 아니라,
그러한 구조를 왜 선택했고 어떤 trade-off를 의도했는지를 설명하는 **배경 문서**다.
