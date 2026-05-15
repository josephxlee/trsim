# CLAUDE.md — TRsim 새 Cowork 세션 진입점

이 파일은 새 Cowork 세션이 자동 로드한다. 짧게 유지 (≤ 200 lines).
설계 단계 가이드는 `AGENT_GUIDE.md` (정체성·17 plan 진입점)
참고 — 이 파일은 **Cowork 구현 단계** 의 작업 규약만 담는다.

## 0. 새 세션이 가장 먼저 읽을 것 (5 분 안에)

1. `SESSION_SUMMARY.md` — 최근 milestone (Phase 단위) 누적 로그
2. `docs/sessions/` 안의 **가장 최근** `phase_*.md` — sub-step 상태
3. `AGENT_GUIDE.md` — 정체성 + 불변 원칙 (필요할 때만)
4. `plan/04_migration.md` § 4.3 — 전체 Phase 0~8 흐름
5. `git log --oneline -10` — 최근 commit

`spaces/.../memory/MEMORY.md` (auto-memory) 는 자동 로드됨 —
재읽기 불필요.

## 1. 현재 진행 상황 (이 단락만 수시로 갱신)

> **TRsim MVP 완성 후 polish 단계.** MVP 본체는 P1~P8 로 완성
> (인계 `docs/sessions/mvp_completion_2026_05_14.md`). 2026-05-15 세션:
> Scene3D 리사이즈 잔상 수정 (디바운스 정착 렌더) + 카메라 단축키 /
> 프리셋 실동작 + actor lifecycle 리팩터 + `debug/` 격리 디버깅 폴더
> (frontend / backend) 신설. 누적 **2814 PASS**, 5 contracts KEPT,
> ruff / mypy --strict / import-linter all clean. 이 세션 인계 =
> `docs/sessions/session_2026_05_15_scene3d_polish.md`.
> Post-MVP punch list: Phase 8 HIL / Pipeline real binding /
> NN per-category real loss.
>
> 사용자 우선순위: **physics_lab > simulator > editor**.

직전 cycle 들의 sub-step 표·학습·commit 해시는 `SESSION_SUMMARY.md`
(milestone 누적) 와 `docs/sessions/phase_*.md` (sub-step 상세) 가
권위. **CLAUDE.md § 1 은 현재 상태 한 단락만 유지** — 새 cycle 완료
시 위 blockquote 를 교체하고, 상세 로그는 handoff doc 에 적는다.

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

### 3.4 Lint 트랩 회피

- RUF002 ASCII-confusable: `α`/`τ`/`−`/`×` → `alpha`/`tau`/`-`/`x`.
  docstring 도 검사됨.
- RUF043: regex meta-char 는 raw string + `\.` escape.
- RUF007: `zip(strict=False)` 대신 `itertools.pairwise` 우선.
- RUF046: Python 3 `round()` 는 이미 int — `int(round(x))` redundant.
- N818: custom exception subclass 는 항상 `-Error` suffix.
- mypy --strict 의 `[unused-ignore]` 가 stale `# type: ignore` 잡음 —
  파일 손댈 때 함께 cleanup.
- I001: `ruff check --fix` 자동. `ruff format` 도 항상 통과 (commit 전
  sandbox 1 차 검증).

### 3.4b PySide6 / Qt 트랩

- `QPen.setStyle` 가 raw int 거부 — `Qt.PenStyle.DashLine` enum 필수.
- `QComboBox.itemData` 가 Python Enum identity 잃음 — StrEnum 이면
  `.value` 저장 + `MyEnum(value)` 로 round-trip.
- pyqtgraph `ImageItem.boundingRect()` 는 local pixel rect — data
  좌표 검증은 `mapRectToView()` 변환 후.

### 3.5 셸 문법 — 사용자 환경은 **PowerShell**

handoff / 사용자에게 명령 제시할 때는 PowerShell 우선:

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"
& $PY -m pytest -q
```

Bash (`VAR=value cmd`) 한 줄 prefix 패턴은 PowerShell 에서 cmdlet
인식 실패. 반드시 `$env:VAR = "value"` 별도 줄 + `& $exe args` call
operator 로 분리. 내가 Bash 도구로 실행할 때는 Bash 문법 OK 지만,
**사용자에게 보여주는 명령**은 PowerShell 변형이 기본.

### 3.6 MVP 매트릭스 자동 갱신 (모든 sub-step push 직후)

`docs/MVP_STATUS.md` 가 plan/04 § 4.3 의 Phase 0~9 list vs 실제 구현
상태 매트릭스. **매 sub-step push 직후 해당 행을 갱신**하고 follow-up
commit (`docs: update MVP_STATUS — <항목> ✓ after <sub-step>`) 로
같은 push 에 묶어 origin/main 으로 보냄. 절차는
[`docs/agent_workflows/mvp_status_update.md`](docs/agent_workflows/mvp_status_update.md).

상태 마크: ✓ (완전) / △ (skeleton·placeholder 만) / ✗ (미구현).
새 작업 결정 시 `docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 가
첫 참조. 매트릭스가 실제 코드와 어긋나면 `grep` + `Glob` cross-check
후 정정.

## 4. Cowork ↔ Windows mount sync 트랩

bindfs 가 가끔 파일 끝 1~5 char 잘라먹음 (Phase 1 부터 반복 발생).
대응:

- 파일 쓸 때 Python `open + flush + os.fsync()` 강제 sync.
- 매 commit 스크립트 첫 줄에 `tail -3 + grep <마지막_식별자>`
  자동 truncation 감지.

`git_sh/commit_*.sh` 의 sync 확인 블록이 표준 패턴.

## 5. Git 작업 (Claude Code 가 직접)

- Claude Code 단계 (2026-05-09~) 부터는 내가 직접 commit + push.
- 일회성 commit 스크립트 `git_sh/<name>.sh` 는 만들어 둠 (gitignore)
  — sync 가드 + commit message 정리용.
- DCO sign-off 필수 (`git commit -s`). 모든 commit 에 `-s` 포함.
- Co-Authored-By footer 포함 (system prompt 표준).
- branch 전략 단순: `main` 직 push.
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
3. **expected 손계산** — Python 으로 계산한 정확값을 expected 로
   박고 tolerance 좁히는 게 정답.
4. **Toolbox 호출** — Octave 는 base 만. `aer2enu`, `wgs84Ellipsoid`,
   `chirp` 류 전부 금지 — 직접 NIMA TR8350.2 / Mahafza 공식 작성.
5. **계획서 정체성 재정의** — `AGENT_GUIDE.md` § 1 의 불변 원칙
   충돌 시 사용자 합의 필수.
6. **bindfs 잘림 무시** — `tail -3` 으로 파일 끝 검사 안 하면
   `Pyt` 같은 import 쓰레기로 commit 됨.

## 8. 이 파일 갱신

- 새 트랩 발견 → § 7 또는 § 3.4 추가.
- Phase 진행 → § 1 blockquote 교체 (한 단락 유지, 누적 금지).
- 작업 규약 합의 변화 → § 2~6 갱신.
- 200 줄 초과하면 § 1 부터 줄인다 — 이력은 handoff doc 권위.

설계 정체성·plan 인덱스는 여기 안 둠. `AGENT_GUIDE.md` 가 권위.

## 9. 사용자 명령 매핑 (단축 트리거)

사용자가 짧은 한국어 명령을 주면 해당 워크플로 .md 따라 실행.
워크플로 진입점은 `docs/agent_workflows/README.md`.

| 트리거 | 워크플로 | 동작 |
|---|---|---|
| "phase 상태", "진행 상황", "dashboard 갱신" | `docs/agent_workflows/phase_status.md` | 진행 보고 + dashboard artifact 갱신 |
| "sync 체크", "잘림 확인", 모듈 Write 직후 | `docs/agent_workflows/sync_check.md` | py_compile + ruff + tail 검사 |
| "ci 결과", "ci 봐줘", push 직후 | `docs/agent_workflows/ci_status.md` | scheduled task `trsim-ci-status` 또는 sandbox curl |
| "다음 작업?", "남은 작업?", "MVP 상태?", sub-step push 직후 | `docs/agent_workflows/mvp_status_update.md` | `docs/MVP_STATUS.md` 매트릭스 갱신 + 우선순위 리스트 참조 |

**중요 도구 위치**:
- Phase dashboard artifact id = `trsim-phase-dashboard` (cowork 사이드바)
- Scheduled task = `trsim-ci-status` (사용자 OneDrive\Claude\Scheduled\)
- pre-commit hook = `scripts/githooks/` (사용자 PC 에서 setup_hooks.sh 1회)

새 트리거 추가 시 워크플로 .md + 위 표에 한 줄.

---
최근 갱신: 2026-05-15 — CLAUDE.md 정리 (1310 → 197 줄, § 3.4b PySide6
트랩 신설) + § 1 을 Scene3D polish 세션 상태로 갱신. 작업 규약 (§ 2~9)
불변.
