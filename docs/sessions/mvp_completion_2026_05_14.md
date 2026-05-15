# TRsim MVP 완성 handoff (2026-05-14)

Phase 4 UI 실 데이터 binding sweep 마감 (L1~L6 + M1+M2) 후, 사용자
결정 "HIL 은 post-MVP, MVP 완성 우선" 에 따라 P1~P8 8 sub-step 으로
MVP 잔여 punch list 본격 마감.

## 0. 한 줄 요약

- HEAD = `d25f27e` (P8).
- 누적 **2790 PASS** local (Phase 4 sweep 끝 시점 2707 → 2790, **+83
  신규** across P1-P8).
- 5 contracts KEPT. ruff / mypy --strict / import-linter all clean.
- 8 commits direct push origin/main.

## 1. P-series 표 (8 sub-step 누적)

| sub | commit | +tests | 범위 |
|---|---|---|---|
| P1 | `cfd7fe8` | 0 | **HIL post-MVP lock** — `app/hil/`, `domain/hil/`, `ui/simulator/hil_panel/` empty package docstring 명시. `sdk/protocols.py::DUTAdapterProtocol` "reserved-name shell" 안내 docstring. MVP_STATUS 의 Phase 8 section 에 "POST-MVP, 자리만 예약" 헤더 + 우선순위 리스트에서 post-MVP 분리. |
| P2 | `1632246` | +14 | **Validation Bench 일반화** — `app/physics_lab/validation_bench.py` 신규 `ValidationBench` + `ValidationConfig`: 임의 `PhysicsModelProtocol` 받아 dynamic (state propagation) 또는 static (axis sweep) 평가. GravityOnly / BouncingBall / FreeSpaceLoss self-validation. plan/19 § 19.7.5+ ✓. |
| P3 | `31ea90b` | +17 | **Phase 3 Profile 모드 toggle Q4** — `domain/timing/profile_mode.py` 신규 `ProfileMode` StrEnum + `ProfileGate` (LIVE / OFF / EXPLICIT 1-shot latch). `trsim profile --mode --explicit-every` CLI flag + `recorded_frames` payload key. |
| P4 | `7c6d6db` | +23 | **Phase 5 #18 / #19 재현성 정량** — `tests/physics/test_reference_timing_reproducibility.py` (frozen dataclass 동일성 + tuple 순서) + `test_frame_profiler_reproducibility.py` (same sample sequence → same StageReport + alphabetic ordering + reset idempotent + percentile 단조 + multi-stage 독립). |
| P5 | `e8849c8` | +13 | **방향키 manual pointing** — `SimulatorWorkspace.keyPressEvent`: Left/Right ±AZ 0.5°, Up/Down ±EL 0.5°, Home·0 reset. `PrimaryTargetController` 가 `manual_az_offset_deg` / `manual_el_offset_deg` 누적 → ScopePOVPanel + Properties 즉시 repaint. |
| P6 | `9437320` | +5 | **A1-c + A1-d stub lock** — `tests/unit/app/test_nn_evaluator_postmvp_stubs.py` 가 Tracker/Predictor/Classifier loss + multi-step rollout 의 NotImplementedError 컨트랙트 잠금. Real impl 은 TrackerNNPlugin / PredictorNNPlugin / ClassifierNNPlugin 출시 후 post-MVP. |
| P7 | `bdd01ea` | +11 | **Editor preview 3종** — RadarEditor `_BeamPatternPreview` (sinc² gain pattern, pyqtgraph), TargetsEditor `_TrajectoryPreview` (7 motion-kind synthetic path, 자동 swap), AtmospherePanel rain attenuation vs frequency (ITU-R P.838 simplified). |
| P8 | `d25f27e` | 0 | **SDK manifest 이동** — `src/workbench/domain/dlc/manifest.py` → `src/workbench/sdk/manifest.py`. `domain/dlc/` 디렉토리 완전 제거. 7 import site 갱신 + tests/unit/domain/test_dlc_manifest.py → tests/unit/sdk/test_manifest.py. `sdk/__init__.py` 5 신규 re-export. |

**총 +83 신규 test** (2707 → 2790).

## 2. MVP_STATUS 매트릭스 변경 요약

| 행 | before | after |
|---|---|---|
| Phase 3 Profile 모드 toggle (Q4) | △ | **✓ (P3)** |
| Phase 5 #18/#19 재현성 정량 | △ | **✓ (P4)** |
| Phase 4 UI 잡 (방향키 / Mode / 단축키) | △ | **✓ (P5)** |
| Phase 4 Editor remainder (Radar/Targets/Atmosphere preview) | △ | **✓ (P7)** |
| Phase 6 Step 2 per-category + multi-step rollout | △ | **✓-MVP (P6, real impl post-MVP)** |
| Phase 9 § 19.7.5+ Validation Bench 일반화 | △ | **✓ (P2)** |
| SDK: manifest.py | △ | **✓ (P8)** |
| Phase 8 HIL 전체 | △/✗ | **post-MVP placeholder (P1)** |

## 3. MVP 완성 — 잔여 active 항목

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | Polish (Floating dock B / Theme manager / Stone Soup adapter) | 소 | 미루기 가능, 본격 MVP 완료 후 후속 lane. |

## 4. Post-MVP punch list (의도적 미완)

| 작업 | 크기 | 트리거 |
|---|---|---|
| Phase 8 HIL 전체 (8.1 → Lock-step → 8.2 → 8.3) | 매우 대 | 사용자 신호 후 별도 cycle. |
| Phase 6 Tracker/Predictor/Classifier real loss + multi-step rollout | 중 | TrackerNNPlugin / PredictorNNPlugin / ClassifierNNPlugin Protocol + sequence dataset spec 출시 후. |
| Phase 4 L-series real Pipeline binding | 큼 | mock generators → 실 `Pipeline.step()` probe 교체. Phase 6+ probe recorder 와 짝. |

## 5. 운영 학습 (P-series 누적, 1개)

1. **regex 함정 — re.sub 의 word-boundary 부재** (L4 cycle 끝 시점 발견,
   P-series 에서도 재확인) — `re.sub(r'MainWindow\(...)', ...)` 가
   word-boundary `\b` 없이 `QMainWindow` / `WorkbenchMainWindow` 도
   잡음. 항상 `\b<Name>\(` 패턴 사용 또는 패치 후 specific 검사.

## 6. Phase 별 진척 (MVP 기준)

| Phase | 영역 | 상태 |
|---|---|---|
| 0 | 레포 뼈대 + OSS | ✓ |
| 1 | Primitives | ✓ |
| 2 | Domain | ✓ |
| 3 | Application (+ Profile mode toggle Q4) | **✓** (P3 완료) |
| 4 | UI 골격 + 실 데이터 binding (L1-L6 + M1+M2 + Editor remainder P7 + UI 잡 P5) | **✓** |
| 5 | 물리 검증 (17 카테고리 + 후속 + #18/#19 재현성 P4) | **✓** |
| 6 | NN MVP (frame ✓ + Adam ✓ + CLI ✓ + A1-c/d stub lock P6) | **✓-MVP** |
| 7 | DLC (Wave 2, runtime + CLI + UI + manifest sdk 이동 P8) | **✓** |
| 8 | HIL (Wave 3) | **post-MVP placeholder** (P1) |
| 9 | Physics Lab (Wave 4 + 19.7.5+ Validation Bench 일반화 P2) | **✓** |

## 7. 이 묶음 commit (origin/main)

```
cfd7fe8 P1 HIL placeholder lock
1632246 P2 Validation Bench generalization
31ea90b P3 Phase 3 Profile mode toggle
7c6d6db P4 Phase 5 #18/#19 reproducibility
e8849c8 P5 arrow-key manual pointing
9437320 P6 A1-c + A1-d stub lock
bdd01ea P7 Editor preview 3 (Radar/Targets/Atmosphere)
d25f27e P8 SDK manifest move
```

## 8. MVP 완성 선언

**TRsim MVP 본격 완성** — 사용자 우선순위 (physics_lab > simulator >
editor) 의 모든 핵심 영역이 ✓. 잔여는 Polish (deferrable) 와 의도적
post-MVP 항목 3 건 (HIL / Pipeline real / NN per-category real). 다음
사용자 신호 시 post-MVP lane 으로 전환 가능.
