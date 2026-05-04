# Governance

본 문서는 TRsim 프로젝트의 의사결정 구조와 거버넌스 단계를 정의합니다.
상세 배경은 [plan/17_open_platform.md](plan/17_open_platform.md) § 17.7 참조.

## 거버넌스 단계

TRsim은 프로젝트 성숙도에 따라 3 단계로 거버넌스를 진화시킵니다.

### Phase 1: BDFL (현재 ~ MVP+α 초기)

**Benevolent Dictator For Now** — 프로젝트 창시자가 모든 결정을 단독으로 내립니다.

- **결정권자**: 프로젝트 창시자 (1인)
- **결정 범위**: 라이선스·아키텍처·로드맵·기여 승인 등 모든 결정
- **PR 정책**: 모든 PR을 창시자가 직접 리뷰·머지
- **목표**: 빠른 의사결정으로 초기 안정화

이 단계는 **Core team 후보 모집 단계**이기도 합니다. 신뢰할 만한 기여자가 등장하면 Phase 2 로 전환.

### Phase 2: Core team (MVP+α 안정 후)

신뢰 기여자 3~5명으로 구성된 합의 그룹.

- **결정권자**: Core team (3~5명)
- **결정 방식**: 합의 우선, 합의 불가 시 다수결 (창시자가 결정타)
- **PR 정책**: Core team 멤버가 리뷰·머지 권한 보유
- **승격 기준**: 다음 모두 충족 시 Core team 후보 (창시자 추천 + 기존 Core team 합의)
  - 6개월 이상 지속 기여
  - PR 10개 이상 머지
  - 행동 강령 준수
  - 프로젝트 비전 이해
- **임기**: 무기한, 단 6개월 이상 비활동 시 명예직 전환

### Phase 3: Foundation (수년 후, 트래픽 충분 시)

공식 비영리 재단 또는 Apache Incubator 같은 외부 기구.

- **전환 기준**:
  - 활성 기여자 50명+
  - 월 활성 사용자 1000명+
  - 정기 후원 또는 기업 지원 확보
  - 법인 설립·관리 비용 감당 가능
- **세부 정관**: 전환 시점에 별도 작성

## 의사결정 유형

| 유형 | 결정권 | 비고 |
|---|---|---|
| 일상 PR (버그 수정·문서 개선) | Core team 단독 | 1명 승인 충분 |
| 기능 추가 (큰 변경) | Core team 합의 | RFC 또는 Issue 사전 논의 권장 |
| 아키텍처 변경 | Core team 합의 | ADR 작성 의무 (`plan/DECISIONS.md`) |
| 라이선스 변경 | 만장일치 + 기여자 공지 | 매우 신중 |
| 거버넌스 변경 | 만장일치 + 30일 공지 | 본 문서 자체 개정 |
| 멤버 제명 (행동 강령 위반) | Core team 다수결 | `CODE_OF_CONDUCT.md` 참조 |

## RFC (Request for Comments) 절차

큰 변경 (새 RadarModel·새 motion_kind·아키텍처 변경 등) 은 RFC 절차를 따릅니다:

1. GitHub Discussion 또는 Issue에 RFC 초안 작성
2. 최소 14일 공개 토론
3. Core team 검토·합의
4. 승인 시 PR로 구현 시작

상세 RFC 템플릿: TODO (Phase 2 진입 시 추가)

## 기여자 분류

| 분류 | 정의 | 권한 |
|---|---|---|
| Contributor | PR 1개 이상 머지된 사람 | 일반 GitHub 권한 |
| Trusted Contributor | PR 5개 이상 + 6개월 이상 활동 | Triage 권한 (Issue 라벨링) |
| Core team | § Phase 2 승격 기준 충족 | Merge 권한 |
| Founder / BDFL | 프로젝트 창시자 | 모든 권한, Phase 1 종료 후에도 Core team 자동 멤버 |

## 충돌 해결

기여자 간 또는 Core team 내 의견 충돌:

1. **GitHub Discussion** 에서 공개 토론 우선
2. 합의 안 되면 **Core team 합의**
3. Core team 내 분열 시 **창시자 결정타** (Phase 1 ~ 2)
4. Phase 3 진입 후 정관 절차 따름

## 변경 이력

| 일자 | 버전 | 변경 |
|---|---|---|
| 2026-04-28 | 0.1 | 초안 (Phase 1 BDFL 시작, v0.35 결정 반영) |

---

**License**: 본 문서는 [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) 으로 배포됩니다.
