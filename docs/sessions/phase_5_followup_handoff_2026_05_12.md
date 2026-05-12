# Phase 5 후속 회귀 보강 인계 — 도메인 정량 강화 (2026-05-12)

이 세션에서 Physics Lab Phase 9 가 모두 끝난 뒤 첫 진입점인
**Phase 5 후속 (도메인 정량 보강)** 묶음을 처리. plan/04 § 4.3 Phase 5
의 17 검증 카테고리 중 multipath/horizon (5.19/5.20), ExtendedTarget
glint (5.21), tracker maneuver (5.22) 세 카테고리에 정량 회귀를 추가.
**코드 변경 0, 테스트만 추가** (handoff 권고 그대로).

## 0. 현재 상태 (한 줄)

- HEAD = `e921e0a` (`test(physics): Phase 5.19/5.20/5.21/5.22 후속
  — 도메인 정량 회귀 보강`)
- 누적 **2027 PASS** local (1986 → +41 across 3 신규 test 파일)
- ruff / import-linter 5 contracts KEPT
- mypy 의 신규 3 파일 strict 클린 (전체 mypy 의 281 pre-existing
  error 는 내 변경과 무관 — 사용자 인지 사항)
- 1 commit feature branch `claude/tender-banzai-36f57e` 에 push
- **main 으로 merge 는 사용자 승인 필요** — Claude Code 의 harness
  가 첫 main push 를 차단. settings.local.json allow rule 추가 또는
  사용자가 직접 `git push origin claude/tender-banzai-36f57e:main`
  실행

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> Physics Lab 9.x ✓ + Phase 5 후속 ✓ 끝났으므로 다음 우선순위:
> 1. **NN 보강 (Adam optimizer + workbench-train CLI external
>    subprocess + Step 2 Tracker/Predictor/Classifier 행 채우기)**
>    — 다음 세션 진입점.
> 2. Phase 8 HIL (TCP/JSON DUT + GT/SIL/HIL 3-way).
> 3. DLC CLI (install / sdk build).
> 4. UI 데이터 binding (Editor 5 activity / Simulator 8 panel
>    실 데이터).
> 5. Floating dock 옵션 B / Theme manager.

## 2. 이 세션 추가 사항 요약

| 파일 | 신규 tests | 카테고리 |
|---|---|---|
| `tests/physics/test_multipath_horizon_golden.py` | +21 | 5.19/5.20+ |
| `tests/physics/golden/multipath_horizon.json` | +7 case + bulge_m unit | 5.19/5.20+ |
| `tests/physics/test_extended_target_glint_rms_multi.py` | +11 | 5.21+ |
| `tests/unit/domain/test_tracker_high_g_maneuver.py` | +9 | 5.22+ |

### 2.1 5.19/5.20+ multipath/horizon golden 다중 case

새 golden case:

1. `two_ray_h1_10_h2_200_R_20km_sband` — S-band 3 GHz deep-null
   (F4_pec ~ 4.24e-9)
2. `two_ray_h1_15_h2_80_R_15km_kuband` — Ku-band 16 GHz peak
   (F4_pec ~ 15.5)
3. `horizon_geometric_h_1000m` — k=1 horizon 112.88 km
4. `horizon_sub_refraction_k_2_3_h_100m` — sub-refraction
5. `horizon_super_refraction_k_2_h_100m` — super-refraction / ducting
6. `horizon_radio_two_point_sub_refraction_10_50_k_2_3` — bistatic
7. `earth_bulge_midpoint_50km_k_4_3` — 36.79 m midpoint bulge

invariant 21 종:
- band 별 golden 매칭 (rtol=1e-12, S-band 6개 + Ku-band 3개)
- delta frequency-invariant
- d_peak_0 ~ 1/lambda (Ku=2x of X)
- geometric horizon h=1000m
- horizon scales as sqrt(h)
- sub/super refraction horizon + Re_eff
- horizon strictly monotonic in k_factor
- earth bulge midpoint vs closed-form d^2/(8 k R_E)

### 2.2 5.21+ glint multi-regime Monte Carlo

3 (N, L) regime — drone 3pt L=2m / fighter 5pt L=12m / transport
9pt L=30m.

invariant 11 종:
- parametrized Skolnik bound L/(2·sqrt(N)) (3 regime × 3 axis)
- parametrized convex-hull |glint| < L (3 regime)
- directional: transport > fighter (larger L), drone < fighter
  (smaller L)
- frequency-band invariant 2 (S-band 3-3.5 GHz, Ku-band 15-18 GHz)
- determinism (3 regime × Ku band 모두 same-seed 재현)

### 2.3 5.22+ sustained 9-G turn

- V=300 m/s, a_c=9*9.80665=88.26 m/s², R=V²/a_c=1019.72 m,
  omega=a_c/V=0.2942 rad/s.
- dt=0.05s, 200 frames → 10 s window → 2.942 rad ~ 168° rotation.

invariant 9 종:
- closed-form R 매칭 (rtol=1e-12)
- heading rotates by exactly omega·N·dt
- constant speed invariant
- EKF RMSE < turn radius
- UKF RMSE < turn radius
- EKF/UKF RMSE ratio in [0.8, 1.25]
- 정상 noise tuning monotonic (낮은 sigma_a → 큰 RMSE)
- 정상 noise tuning monotonic 보강 (높은 sigma_a → 작은 RMSE)
- determinism

## 3. 작업 환경 (변동 없음)

| 항목 | 값 |
|---|---|
| OS | Windows |
| Python | 3.13.3 (.venv) |
| 주요 의존 | PySide6 6.11.0, pyqtgraph, pyvista, pyvistaqt, numpy, h5py, scipy, pytest 9.0.3, pytest-qt 4.5.0, ruff, mypy 2.0, import-linter, typing_extensions |

## 4. 운영 학습 (이 세션 추가)

1. **golden 값은 Python 직접 계산이 정답** — Mahafza / Skolnik 손계산
   대신 같은 float64 코드로 expected 값을 산출 (`rtol=1e-12` 가능).
   1회용 helper 스크립트 (`scripts/_phase5_compute_goldens.py`) 만들어
   값 뽑은 후 삭제.
2. **9G 선회 truth 의 half-turn 가정 함정** — V=300, R=1019.7, omega=
   0.2942. 10s 윈도우는 정확히 half-turn 이 아님 (omega·10 = 2.942 ≠
   π). 테스트는 omega·N·dt 로 expected 를 직접 계산해 일반화.
3. **mypy unused-ignore baseline noise** — `tests/unit/cli/test_cli_
   ui.py` 등에 281 pre-existing strict error 존재 (사용자 인지 사항).
   신규 파일만 strict 클린이면 OK. CI 가 src/ 만 mypy 도는지 추후 확인.
4. **harness 가 main 직접 push 차단** — feature branch push 까지 자동,
   main merge 는 사용자 1회 승인 필요. `settings.local.json` 에 push
   allow rule 추가하거나 사용자가 직접 push.
5. **PowerShell vs Bash 셸 문법 (재발 방지)** — handoff 의 명령 예시는
   PowerShell 버전 우선. Bash 변형은 부가. `& "$root\.venv\Scripts\python.
   exe"` call operator + `$env:VAR = "value"` 별도 줄.

## 5. 다음 세션 진입 명령

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m pytest -q
# 2027 PASS expected (이 커밋이 main 에 들어간 뒤)

& ".\.venv\Scripts\lint-imports.exe"
# 5 contracts KEPT
```

Bash 변형:

```bash
cd "C:/Workspaces/Claude/Tracking Radar Simulator/trsim"
git pull --ff-only
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest -q
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/lint-imports.exe
```

그 다음:
1. CLAUDE.md § 1 + 이 handoff 정독 (5 분).
2. **NN 보강** 진입 — plan/07 § 7.5.3 Adam optimizer + workbench-
   train CLI external subprocess. `src/workbench/app/nn/trainer.py`
   의 기존 numpy_mlp backend 확장. workbench-train CLI 는
   `src/workbench/cli/main.py` 에 신규 subparser.
3. 또는 NN 외 다른 우선순위 (Phase 8 HIL / DLC CLI / UI binding)
   사용자 합의 후 진행.

세션 컨텍스트 80% 도달 시 새 handoff 작성 + 종료.

## 6. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/sessions/phase_9_3_complete_handoff_2026_05_12.md` | Phase 9 모두 끝 |
| `docs/sessions/phase_5_followup_handoff_2026_05_12.md` | **이 인계** (Phase 5 후속) |
| `CLAUDE.md` § 1 | 누적 진행 log |
| `plan/04_migration.md` § 4.3 Phase 5 | 17 검증 카테고리 정의 |
| `plan/14_radar_models.md` § 14.10 | ExtendedTarget glint MVP |
| `plan/16_propagation.md` § 16.3 | Multipath / horizon refraction |
