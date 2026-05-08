# CLAUDE.md — TRsim 새 Cowork 세션 진입점

이 파일은 새 Cowork 세션이 자동 로드한다. 짧게 유지 (≤ 200 lines).
설계 단계 가이드는 `AGENT_GUIDE.md` (295 줄, 정체성·17 plan 진입점)
참고 — 이 파일은 **Cowork 구현 단계** 의 작업 규약만 담는다.

## 0. 새 세션이 가장 먼저 읽을 것 (5 분 안에)

1. `SESSION_SUMMARY.md` — 최근 milestone (Phase 단위) 누적 로그
2. `docs/sessions/` 안의 **가장 최근** `phase_*.md` — sub-step 상태
3. `AGENT_GUIDE.md` — 정체성 + 불변 원칙 (필요할 때만)
4. `plan/04_migration.md` § 4.3 — 전체 Phase 0~8 흐름
5. `git log --oneline -10` — 최근 commit

`spaces/.../memory/MEMORY.md` (auto-memory) 는 자동 로드됨 —
재읽기 불필요.

## 1. 현재 진행 상황 (이 줄만 수시로 갱신)

- **Phase 2.3c** 완료 (BuildingEntity + Anchor 4 + MeshOrigin 3, push 대기)
- 누적 test ~258, CI 6 환경 PASS
- 다음: 2.3d Target → 2.5 Atmosphere → 2.6 Antenna → 2.4 Dynamics …
  (`docs/sessions/phase_2_progress.md` 참조)

## 2. 사용자 커뮤니케이션

- 한국어 **반말**, 간결.
- "추천대로" / "그렇게 가자" 한 마디 = full GO. 의문 다시 묻지 말 것.
- 누적 결정 ~100 개는 **이미 끝남**. 블로커 0. 재논의 회피.
- 완곡 표현 ("괜찮으시면", "제 생각엔") 최소화.

## 3. 코드 작업 규약

### 3.1 모듈 작성 패턴

- `frozen=True, slots=True` 기본. 도메인 dataclass 전부.
- `from __future__ import annotations` 항상.
- mypy strict 통과 — `**` 결과 Any 회피, `math.pow()`/`math.sqrt()` 사용.
- numpy 타입: `numpy.typing.NDArray[np.float64]`, `NDArray[np.bool_]`.
- 레이어 import 방향 (`02_architecture` § 2.6): UI → App → SDK →
  Domain → Physics → Primitives. `import-linter` 강제.

### 3.2 테스트

- 모든 모듈에 pytest 짝꿍 (`tests/unit/<layer>/test_<name>.py`).
- `pytest.approx` 는 **expected 우측** (`actual == approx(expected)`)
  — Yoda 회피 (SIM300 은 tests/ 에 per-file-ignore 적용).
- `pytest.raises(match=r"...")` 는 raw string + `\.` escape (RUF043).

### 3.3 Octave 짝꿍 (cross-validation)

- 위치: `docs/matlab_validation/`
- **base 함수만** 사용 — Mapping/Signal/Aerospace Toolbox 호출 금지
  (사용자 PC 는 GNU Octave).
- function-with-subfunctions 패턴 (Octave 의 script 안 local function
  미지원).
- Python 정확값을 expected 로 — 손계산 정밀도 낮으면 1e-3 → 1e-9 좁힘.

### 3.4 Lint 트랩 회피 (Phase 1 누적)

- RUF002 ASCII-confusable: `α`/`τ`/`−`/`×` → `alpha`/`tau`/`-`/`x`.
  docstring 도 검사됨.
- RUF043: regex meta-char 는 raw string + `\.` escape.
- I001: `ruff check --fix` 자동.
- ruff `format` 도 항상 통과 (commit 전 sandbox 에서 1 차 검증).

## 4. Cowork ↔ Windows mount sync 트랩

bindfs 가 가끔 파일 끝 1~5 char 잘라먹음 (Phase 1 부터 반복 발생).
대응:

- 파일 쓸 때 Python `open + flush + os.fsync()` 강제 sync.
- 매 commit 스크립트 첫 줄에 `tail -3 + grep <마지막_식별자>`
  자동 truncation 감지.

`git_sh/commit_*.sh` 의 sync 확인 블록이 표준 패턴.

## 5. Git 작업 (사용자 Git Bash 로)

- Cowork 가 commit 안 함. **사용자가 Git Bash 로 실행**.
- 일회성 commit 스크립트는 `git_sh/<name>.sh` (gitignore).
- DCO sign-off 필수 (`git commit -s`). 모든 commit 스크립트에 `-s` 포함.
- branch 전략 단순: `main` 직 push. 외부 PR 받기 시작하면 재고.

## 6. 세션 끝나면

사용자가 "오늘 여기까지" 또는 phase 완료 신호 주면:

1. `docs/sessions/phase_<N>_<topic>.md` 작성 또는 갱신 (1-3 페이지).
   컨벤션은 `docs/sessions/README.md` 참조.
2. `SESSION_SUMMARY.md` 의 milestone 줄 갱신 (Phase 단위 끝 시).
3. 새로운 결정·교정·트랩이 있으면 auto-memory 에 저장
   (`feedback_*.md` / `project_*.md`).

## 7. 흔한 함정 (Cowork 구현 단계 누적)

1. **CI 결과 추측** — 사용자가 push 한 뒤 CI 결과 받기 전에 "통과했을
   것" 추측 금지. 항상 "사용자 push 완료 → CI 결과 알려줘" 흐름.
2. **이미 한 결정 다시 묻기** — `MEMORY.md` 에 "결정 다시 묻지 말기"
   feedback 있음. 누적 ~100 결정은 끝난 사항.
3. **expected 손계산** — Phase 1.1 Seoul ECEF 2km 어긋남 / 1.3 beat
   freq 0.006 Hz 어긋남 사례. **Python 으로 계산한 정확값을 expected
   로** 박고 tolerance 좁히는 게 정답.
4. **Toolbox 호출** — Octave 는 base 만. `aer2enu`, `wgs84Ellipsoid`,
   `chirp` 류 전부 금지 — 직접 NIMA TR8350.2 / Mahafza 공식 작성.
5. **계획서 정체성 재정의** — `AGENT_GUIDE.md` § 1 의 불변 원칙
   (Primary Target / FMCW Triangle 단독 / Closed-loop 등) 충돌 시
   사용자 합의 필수.
6. **bindfs 잘림 무시** — `tail -3` 으로 파일 끝 검사 안 하면
   `Pyt` 같은 import 쓰레기로 commit 됨.

## 8. 이 파일 갱신

- 새 트랩 발견 → § 7 추가.
- Phase 진행 → § 1 한 줄 갱신.
- 작업 규약 합의 변화 → § 2~6 갱신.

설계 정체성·plan 인덱스는 여기 안 둠. `AGENT_GUIDE.md` 가 권위.

---
최근 갱신: 2026-05-08 — Phase 2.3c 시점 + Cowork 구현 컨벤션 신규 정리.
