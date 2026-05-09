# Phase 2.7 — physics/reflection/extended_target.py (Multi-scatterer + Glint)

## Status

- 날짜: 2026-05-09
- CI: push 후 확인
- Test 추가: 34 (누적 512)

## Added

`src/workbench/physics/reflection/extended_target.py` (single file):

- `Scatterer` (frozen+slots): `offset_body_m: tuple[float, float, float]` (x_fwd, y_right, z_down) + `rcs_dbsm` + `label`. Validation: 3-tuple offset.
- `ExtendedTarget` (frozen+slots): `target_id` + `scatterers: tuple[Scatterer, ...]`. Validation: non-empty target_id + non-empty scatterers. `total_rcs_dbsm` property (incoherent linear sum).
- `ScatteringResult` (frozen+slots): `total_signal: complex` + `apparent_position_m` + `glint_offset_m`.
- `body_to_world_rotation(yaw, pitch, roll) -> NDArray[np.float64]` — body (x_fwd, y_right, z_down) → ENU rotation, ZYX intrinsic, project heading convention (CW from N about +Up).
- `compute_extended_target_return(radar_pos, target, target_pos, attitude, freq) -> ScatteringResult`:
  - 각 scatterer body offset → ENU rotation 적용
  - Round-trip phase φ = 4πR/λ
  - Amplitude A = √σ_linear / R²
  - Coherent complex sum + amplitude-weighted apparent centroid
  - Glint = apparent − target_ref
- 상수: `C_LIGHT_M_S = 299_792_458.0` (antenna / fmcw / multipath와 공유)

`tests/unit/physics/test_extended_target.py` — 34 tests:
- Scatterer/ExtendedTarget/ScatteringResult dataclass + validation (10)
- body_to_world_rotation: zero attitude 3축 / yaw=π/2 / pitch=π/2 / roll=π/2 / 직교성 / det=1 / yaw 수평 평면 보존 (9)
- 단일 scatterer: apparent==target_pos, 1/R² scaling, 알려진 amplitude (3)
- 단일 offset scatterer: apparent = scatterer 위치 (1)
- Multi-scatterer / Glint: 대칭 쌍 (centroid≈target), 비대칭 (밝은 쪽으로 끌림), λ/4 destructive, λ/2 constructive (4)
- Attitude rotation: yaw=π/2 → forward East (1)
- Frequency dependence: 다른 f → 다른 phase 패턴 (1)
- Validation: f≤0, range==0 거부 (2)
- ScatteringResult frozen + C_LIGHT 잠금 (3)

`docs/matlab_validation/test_extended_target.m` — Octave 짝꿍 (rotation / 1/R² / λ/2 constructive / λ/4 destructive / total RCS dBsm / amplitude-weighted centroid).

## 핵심 결정

- **Body frame = aerospace (x_fwd, y_right, z_down)** + project heading (CW from N) → 두 frame을 explicit 식으로 매핑 (ZYX intrinsic).
- **Layering**: physics layer는 domain (TargetEntity 등) 의존 안함 — `target_id: str` 으로 받고, scatterer 데이터는 caller가 준비. domain ↔ physics 어댑터는 Phase 3 RadarPipeline 책임.
- **Round-trip phase = 4πR/λ** (one-way 2πR/λ × 2). plan/14 § 14.10.4 "phase = 2 * (2 * np.pi * R / wavelength)" 와 등가.
- **Amplitude = √σ/R²** — 모노스태틱 radar equation `Pr ∝ σ/R⁴` 에서 amplitude는 √Pr ∝ √σ/R².
- **Apparent centroid = amplitude-weighted** scatterer positions → Skolnik 정의와 일치.
- **Glint emerges from coherent sum** — 별도 noise 모델 추가 없이 자연 발생.
- **MVP+α 제외** (plan/14 § 14.10.7): aspect/freq/polarimetric RCS, micro-Doppler, range glint, Swerling.
- **numpy 사용** — body_to_world matrix + complex sum. `numpy.typing.NDArray[np.float64]` 명시.

## 트랩 / 교정

- **Body frame 회전 유도** — ENU 세계 + body NED-style 의 매핑이 헷갈림 (특히 zero attitude 에서 body x → North 가 아니라 East 라고 착각). 단계별 검증으로 해결: zero 에서 (forward → +N, right → +E, down → -Up) 명시 → yaw=π/2 forward → East 검증.
- **Yaw CW from N** vs **right-hand rotation about +Up** — yaw_CW = -rotation_about_+Up. R_z(-yaw) 로 처리. `forward_unit_vector` (aircraft.py) 와 동일 컨벤션.
- **SIM108 lint** — `if/else assignment` → ternary 권장. ruff `--fix` 자동 적용 안되는 (unsafe) 부류라 수동 적용. 주석으로 pathological branch 의도 보존.

## 다음 sub-phase

phase_2_progress.md 우선순위:

1. **2.6b** PlanarArray + Monopulse 4ch (plan/08 § 8.5a.3, 8.5a.4) — Phase 2.6 후속 + 2.7 glint 와 결합 (monopulse_extended angle error)
2. **2.8** Tracker — EKF / UKF / GNN (plan/03 § 3.2.1k)
3. **2.9** CFAR — CA / OS (plan/03 § 3.2.1j)
4. **2.10** Pipeline + Scenario
5. **2.11** Platform
6. **2.12** Timing model
