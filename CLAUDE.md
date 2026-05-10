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

- **Phase 4.4 DONE** — Resource Browser sidebar (plan/13 § 13.2.3).
  좌측 vertical activity bar 옆에 QSplitter 로 ResourceBrowserSidebar +
  central QStackedWidget. 트리 4 카테고리 (Scenarios/Maps/Radars/Targets)
  + ASCII status prefix ([active]/[stale]/[builtin]) + 검색 필터 +
  더블클릭 시 자동으로 매칭 Activity 로 전환. ResourceLibrary 데이터 source 는
  Phase 5+ 에서 주입. 누적 914 PASS (+21 신규).
- **Phase 4.3 DONE** — Editor ActivitySelector + 5 placeholder activities
  + Ctrl+1~5 단축키 + WorkbenchCommand 5 (`editor.activity.*`).
  ActivitySelector(QObject signal) 패턴 = WorkspaceSelector 와 동일.
  EditorWorkspace = 좌측 vertical activity bar + 중앙 QStackedWidget.
  placeholder 5종 (Composer/Map/Radar/Targets/Browser) — Phase 4.4+
  실제 구현이 swap. main_window 가 dispatch 시 자동으로 Editor
  workspace 로 전환 후 activity 선택. 17 tests 추가, 누적 893 PASS.
- **Phase 4.2 DONE** (4 sub-step 누적):
  - 4.2a (`e99c73d`) ui/commands/ 인프라 — WorkbenchCommand (frozen+
    slots) + Registry (substring fuzzy, title>id ranking, enabled_when)
    + CommandPalette QDialog (Ctrl+Shift+P, 화살표 from search box,
    Enter dispatch).
  - 4.2b (`9fa0ffd`) Sim / Target-Run 두 레이어 toolbar — addToolBarBreak
    로 행 분리. SIM_SPEEDS=(1,2,4,8) radio. State 라벨 (IDLE/RUNNING/
    PAUSED/ENDED). builtin.py 추출로 main_window thin assembler 유지.
  - 4.2c (`24e6d8b`) MainMenuBar(QMenuBar) — File/Edit/View/Run/Plugins/
    Tools/Help 7 menu. Run 안 Speed submenu. menu strong-ref 정책으로
    libshiboken "C++ deleted" 회피.
  - 4.2d DockManager (register/toggle/save_state/restore_state) —
    Phase 4.3+ 패널들이 여기 mount.
- 누적 test **876 로컬 PASS** (4.1 808 + 4.2a 19 + 4.2b 27 + 4.2c 12 +
  4.2d 10). .venv Python 3.13.3, pytest-qt 4.5.0. ruff/mypy
  strict/import-linter all clean. 5 contracts KEPT.
- 다음: **Phase 4.3** Editor ActivitySelector + 5 placeholder activities
  (Composer / Map / Radar / Targets / Browser). 전체 sub-phase 12개 계획
  (4.1~4.12).

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

## 5. Git 작업 (Claude Code 가 직접)

- Cowork 시절 사용자가 Git Bash 로 실행했지만 **Claude Code 단계
  (2026-05-09~) 부터는 내가 직접 commit + push** (gh auth 완료 후).
- 일회성 commit 스크립트 `git_sh/<name>.sh` 는 여전히 만들어 둠
  (gitignore) — sync 가드 + commit message 내용 정리용. 실행은 직접
  bash 또는 git 명령으로.
- DCO sign-off 필수 (`git commit -s`). 모든 commit 에 `-s` 포함.
- Co-Authored-By footer 포함 (system prompt 표준).
- branch 전략 단순: `main` 직 push. 외부 PR 받기 시작하면 재고.
- push 후 CI 결과 추측 금지 — `_ci_log.md` 에 한 줄 추가 흐름 (§ 7.1).

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

## 9. 사용자 명령 매핑 (단축 트리거)

사용자가 짧은 한국어 명령을 주면 해당 워크플로 .md 따라 실행.
워크플로 진입점은 `docs/agent_workflows/README.md`.

| 트리거 | 워크플로 | 동작 |
|---|---|---|
| "phase 상태", "진행 상황", "dashboard 갱신" | `docs/agent_workflows/phase_status.md` | 진행 보고 + dashboard artifact 갱신 |
| "sync 체크", "잘림 확인", 모듈 Write 직후 | `docs/agent_workflows/sync_check.md` | py_compile + ruff + tail 검사 |
| "ci 결과", "ci 봐줘", push 직후 | `docs/agent_workflows/ci_status.md` | scheduled task `trsim-ci-status` 또는 sandbox curl |

**중요 도구 위치**:
- Phase dashboard artifact id = `trsim-phase-dashboard` (cowork 사이드바)
- Scheduled task = `trsim-ci-status` (사용자 OneDrive\Claude\Scheduled\)
- pre-commit hook = `scripts/githooks/` (사용자 PC 에서 setup_hooks.sh 1회)

새 트리거 추가 시 워크플로 .md + 위 표에 한 줄.

---
최근 갱신: 2026-05-08 — Phase 2.3c 시점 + Cowork 구현 컨벤션 + § 9 명령 매핑 추가.
