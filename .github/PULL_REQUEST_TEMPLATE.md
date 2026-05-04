# Pull Request

## 요약

이 PR이 무엇을 하는지 간단히 설명해 주세요.

## 동기·배경

이 변경이 왜 필요한가요? 관련 Issue가 있다면 링크해 주세요.

- Closes #
- Related #

## 변경 내용

- [ ] ...
- [ ] ...

## 영향 범위

이 변경이 영향을 미치는 영역:

- [ ] Core (Domain Layer)
- [ ] App Layer
- [ ] UI
- [ ] SDK (DLC 호환성에 영향)
- [ ] 문서만
- [ ] CI / 빌드
- [ ] 그 외:

## 테스트

- [ ] 새 단위 테스트 추가
- [ ] 기존 테스트 모두 통과
- [ ] 수동 테스트 시나리오: (설명)

## 체크리스트

- [ ] 모든 commit에 `Signed-off-by:` 가 있음 (DCO — `CONTRIBUTING.md` 참조)
- [ ] `ruff check .` 통과
- [ ] `ruff format --check .` 통과
- [ ] `mypy src/` 통과
- [ ] `lint-imports` 통과 (의존 규칙)
- [ ] `pytest` 통과
- [ ] 새 의존성을 `pyproject.toml` 에 추가 (있는 경우)
- [ ] `plan/` 문서를 갱신 (아키텍처·결정 변경의 경우)
- [ ] CHANGELOG 또는 릴리스 노트 갱신 (사용자 가시 변경)
- [ ] Breaking change면 명시 (DLC SDK·Public API)

## 호환성

- [ ] 기존 시나리오 파일 호환
- [ ] 기존 `.trsim-pkg` DLC 호환 (또는 SDK 버전 bump 필요)
- [ ] 기존 ResourceLibrary 호환

## 추가 컨텍스트

스크린샷·로그·관련 토론 링크 등.
