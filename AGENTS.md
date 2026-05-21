# 저장소 root markdown 거버넌스

이 저장소는 `/home/tjwocjf0915/workspace/AGENTS.md`의 markdown 운영 규칙을 따르며, 아래 항목은 이 프로젝트의 로컬 매핑과 예외다.

## root 허용 markdown
저장소 root에 둘 수 있는 markdown 파일은 아래 5개뿐이다.

- `README.md`: 진입점. 프로젝트 개요와 빠른 실행 안내만 둔다.
- `AGENTS.md`: 이 저장소의 root markdown 운영 규칙과 로컬 예외를 둔다.
- `IMPLEMENTATION_SPEC.md`: 현재 기술 구현의 최종 기준 문서다.
- `INTENT_ALIGNMENT_NOTE.md`: 사용자 의도와 판단 가드레일의 기준 문서다.
- `AI_IMPLEMENTATION_BRIEF.md`: 현재 작업 맥락, 최근 결정, 다음 세션 인계를 유지하는 living context 문서다.

위 목록 밖의 새 root-level `.md`는 만들지 않는다. 새 메모, 세션 로그, 작업 일지, 임시 정리 문서, history/archive 성격 문서는 `docs/` 아래의 적절한 경로에 둔다.

## 문서 갱신 기준
- 작업 시작 시 `README.md`, `IMPLEMENTATION_SPEC.md`, `INTENT_ALIGNMENT_NOTE.md`, `AI_IMPLEMENTATION_BRIEF.md`를 먼저 확인한다.
- 새 결정, 진행 상태, 다음 세션 인계, 열린 이슈는 `AI_IMPLEMENTATION_BRIEF.md`에 기록한다.
- 기술 사실과 현재 구현 기준이 바뀌면 `IMPLEMENTATION_SPEC.md`도 함께 갱신한다.
- 의도 해석, 금지선, 우선순위 판단 기준이 바뀌면 `INTENT_ALIGNMENT_NOTE.md`도 함께 갱신한다.

## 문서 우선순위
문서가 충돌할 때는 아래 순서를 따른다.

1. `IMPLEMENTATION_SPEC.md`: 현재 기술 구현의 최종 기준
2. `INTENT_ALIGNMENT_NOTE.md`: 의도와 판단 가드레일의 기준
3. `AI_IMPLEMENTATION_BRIEF.md`: 현재 세션 연속성과 최신 작업 맥락
4. `README.md`: 입문과 실행 안내의 기준
5. `docs/history/PROCESS_SEPARATION_ARCHITECTURE.md`: 배경 이해를 돕는 과거 설계 문서

## docs 로컬 매핑
- `docs/reference/`: 현재 작업에서 반복 참조하는 supporting reference 자료를 둔다.
- `docs/inbox/`: 외부에서 가져오거나 새로 모은 미분류 자료의 임시 진입점이다.
- `docs/history/`: 반복 참조 가치가 있는 배경 / 변경 맥락 자료를 둔다.
- `docs/archive/`: 기본 참조 대상이 아닌 보관 자료를 둔다.

`docs/history/PROCESS_SEPARATION_ARCHITECTURE.md`는 현재 source of truth가 아니라 warm history reference다. 현재 구현과 요구 판단은 먼저 `IMPLEMENTATION_SPEC.md`와 `INTENT_ALIGNMENT_NOTE.md`를 따른다.
