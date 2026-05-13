# Phase 5 추가 후속 (5.7b/5.8b/5.11b/5.12b) — 4 sub-step 인계 (2026-05-13)

phase_6_augmentation handoff § 1 의 권고 "Phase 5 추가 후속" 4 sub-step
완료. test-only, src 변경 0. element_power / ballistic / timing 영역의
scaling / monotonicity / boundary invariant 보강.

## 0. 현재 상태 (한 줄)

- HEAD = `2349a99` (`5.11b + 5.12b — timing layer invariants`)
- 누적 **2131 PASS** local (2117 → 2131, +30 across 4 sub-steps
  including 5.7b which preceded this cycle's commit batch by one
  hop). Net from cycle entry (2101) = +30.
- ruff / mypy --strict / import-linter 5 contracts KEPT 매 commit
- 이 cycle 3 commits + 1 handoff main 직접 push

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> Phase 9 ✓ + Phase 5 후속 ✓ + Phase 6 NN 보강 ✓ + **Phase 5 추가
> 후속 ✓ (이 cycle)**. 다음 진입점 후보 (MVP_STATUS § 우선순위):
> 1. **Phase 7 DLC CLI 완성** — sdk build / install / sdk test +
>    io/package_io + package_manager_panel + sample DLC + tutorial.
>    가장 큰 사용자 가시 가치.
> 2. **Phase 3 MVP 누락 4 모듈** — bundle_service / evaluator
>    (Command Lineage) / physics_gate / dem_import.
> 3. Phase 8 HIL 전체.
> 4. Phase 4 UI 실 데이터 binding.

## 2. 이 cycle 누적 push (3 commits + 1 handoff)

| sub | commit | new | 범위 |
|---|---|---|---|
| 5.7b | `39f23ca` | +11 | Planar array element_power sign/quadrant/boundary |
| 5.8b | `2ab426e` | +5 | Ballistic drag/mass/v0/theta scaling |
| 5.11b + 5.12b | `2349a99` | +14 | PerformanceClock factory cross + FrameBoundaryDetector monotonicity |
| (handoff) | (this) | — | 이 문서 |

## 3. 각 sub-step 요약

### 3.1 — 5.7b Planar array element_power 보강

11 신규 tests (parametrised + scalar):
- Theta sign symmetry (4 cases via parametrize).
- Phi sign symmetry (4 cases).
- Four-quadrant hypot equivalence (6 points sharing |hypot|=30°).
- 90° boundary discontinuity (89.999 > 0, 90.0 == 0 hard clamp).
- Isotropic invariance across wide phi (-179° .. +179° all 1.0).

### 3.2 — 5.8b Ballistic drag/mass/v0/theta scaling

5 신규 tests + 1 helper:
- Drag-Cd monotonic in descent reduction (0.0 / 0.5 / 1.0).
- 30°/60° vacuum throw range symmetry (sin(2*30°) = sin(2*60°)).
- Range quadratic in v0 (v0 = 25 vs 50 -> range × 4).
- Vacuum free-fall mass-independent (1 kg vs 100 kg identical).
- Apex height quadratic in v0 (30 vs 60 m/s -> apex × 4).
- Helper `_oblique_throw_range(v0, theta_rad)`.

### 3.3 — 5.11b PerformanceClock 보강

10 신규 tests (5 parametrised cases + 5 scalar):
- Factory cross-check across 5-point latency sweep (10/25/50/100/250
  ms) — `from_target_latency_ms(t) == from_frame_rate_hz(1000/t)`.
- `from_target_latency_ms` rejects non-positive inputs (3 cases).
- `sleep_remaining` bounded above by budget (zero-cost frame can't
  oversleep).
- Latency / frame-rate inverse relationship (doubling latency doubles
  budget exactly).

### 3.4 — 5.12b FrameBoundaryDetector 보강

4 신규 tests:
- Monotonic strictly-increasing sequence (10 calls -> [0..10]).
- `reset()` idempotent (two consecutive calls safe).
- Reset always drops to 0 even after explicit non-zero initial id.
- Linear increment from explicit initial id (42 + 7 -> 49).

## 4. 정합성 검사 결과 (Phase 5 cycle 끝)

`docs/MVP_STATUS.md` 매트릭스:
- Phase 5 (물리 검증) 행 본래 ✓ — 이 cycle 은 보강만 (footer 갱신).
- 변경 이력 footer 에 4 sub-step 한 줄씩 추가.
- 누적 test count 2101 → 2131.
- 5 contracts KEPT 매 commit. ruff / mypy --strict / import-linter
  모두 clean.

## 5. 운영 학습 (이 cycle)

1. **`@pytest.mark.parametrize` + 4-quadrant invariant** (5.7b) —
   sign symmetry 단일 axis (theta or phi) 외에 4-quadrant hypot
   equivalence 가 더 강한 invariant. 6 points (axial + diagonal +
   sign-flipped) 한 번에 검사.
2. **Helper extraction for parametric scaling** (5.8b) —
   `_oblique_throw_range(v0, theta)` 추출해서 같은 integration setup
   을 multiple scaling tests 가 공유. test 코드 중복 회피.
3. **Factory duality 5-point parametrize** (5.11b) — `from_target_
   latency_ms(t)` vs `from_frame_rate_hz(1000/t)` 의 duality 를
   single test 가 아니라 5-point sweep 으로 검증. 후속 implementation
   가 한 endpoint 만 fix 하고 다른 쪽 drift 하는 케이스 방어.
4. **Reset semantics 가 explicit initial id 무시** (5.12b) — `reset()`
   이 0 으로 가는 게 정상 (다음 Run 의 boundary semantics). 명시적
   document + test 가 있는 게 안전.

## 6. 다음 세션 진입 명령

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m pytest -q
# 2131 PASS expected

& ".\.venv\Scripts\lint-imports.exe"
# 5 contracts KEPT
```

그 다음:
1. CLAUDE.md § 1 + `docs/MVP_STATUS.md § "미구현 우선순위 리스트"`
   참조 (5 분).
2. 다음 cycle 결정 — Phase 7 DLC CLI 완성 (큰 가치) / Phase 3 누락
   4 모듈 (MVP 정의 포함) / Phase 8 HIL (가장 큰 작업).

## 7. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/sessions/phase_5_followup_2026_05_13.md` | Phase 5 후속 12 sub-step |
| `docs/sessions/phase_6_augmentation_2026_05_13.md` | Phase 6 NN 보강 4 sub-step |
| `docs/sessions/phase_5_additional_followup_2026_05_13.md` | **이 인계** (Phase 5 추가 후속 4 sub-step) |
| `docs/MVP_STATUS.md` | Phase 0~9 매트릭스 (4 footer entry 추가) |
| `CLAUDE.md` § 1 | 누적 진행 log (이 cycle 끝 갱신) |
