# Security Policy

## 지원 버전

현재 프로젝트는 초기 개발 단계 (v0.x) 입니다. 보안 패치는 **최신 릴리스에만** 제공됩니다.

| 버전 | 보안 패치 지원 |
|---|---|
| 최신 v0.x | ✅ |
| 그 외 | ❌ |

v1.0 정식 릴리스 후 LTS 정책을 별도 정의할 예정.

## 취약점 신고

### 비공개 신고 (권장)

보안 취약점을 **공개 Issue로 등록하지 마세요**. 다음 경로로 비공개 신고:

- **GitHub Security Advisory**: 저장소 Security 탭 → "Report a vulnerability"
- **이메일**: security@trsim.org (TODO: 실제 도메인 확보 후 갱신)
- **PGP 키**: TODO (Phase 2 진입 시 발급)

### 신고 시 포함할 정보

- 영향받는 버전·구성요소
- 재현 단계
- 잠재적 영향 (정보 유출·코드 실행·DoS 등)
- 가능하면 패치 제안

### 응답 시간 (목표)

| 단계 | 목표 시간 |
|---|---|
| 첫 응답 | 72시간 이내 |
| 재현 확인 | 7일 이내 |
| 패치 릴리스 | 30일 이내 (심각도에 따라 단축) |

본 프로젝트는 BDFL/Core team 운영이므로 24/7 대응은 보장 못 합니다. 양해 부탁드립니다.

## 책임 공개 (Coordinated Disclosure)

- 신고자와 협의해 **패치 릴리스 후 공개**
- CVE 발급 필요 시 GitHub Security Advisory를 통해 발급
- 신고자 크레딧을 보안 권고문에 명시 (희망 시)

## DLC 보안

`.trsim-pkg` DLC는 **임의 Python 코드를 실행**합니다. 다음 주의사항을 따르세요:

- **신뢰 가능한 출처에서만 install** — 본 프로젝트는 DLC 코드를 검증하지 않습니다 (MVP)
- DLC가 의심스러우면 [awesome-trsim-packages](https://github.com/.../awesome-trsim-packages) 큐레이션 리스트의 검증된 항목만 사용
- DLC 보안 정책은 MVP+α 에서 강화 예정 — 코드 서명·sandbox·verified badge (`plan/17_open_platform.md` § 17.2.8)

## 알려진 한계

본 프로젝트는 **추적 레이더 시뮬레이션 워크벤치**로, 다음은 **위협 모델 밖** 입니다:

- 악의적 사용자가 자기 PC에서 시뮬을 조작 (당연히 가능)
- 시뮬 결과를 신뢰성 표시 없이 공유 (사용자 책임)
- DLC가 자기 PC 자원에 접근 (Python 표준 권한)

본 프로젝트는 **의도된 사용자가 신뢰 환경에서 사용**하는 모델을 가정합니다.

---

**License**: 본 문서는 [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) 으로 배포됩니다.
