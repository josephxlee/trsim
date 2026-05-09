# Phase 2 — Domain Contract & dataclass (진행 중)

매 sub-phase 끝에 갱신.

## Status (현재 시점)

- 완료: 2.1 / 2.2 / 2.3a / 2.3b / 2.3c / 2.3d / 2.4(a-f) / 2.5 / 2.6
- CI: 2.4 push 후 확인 (Cowork→Claude Code 전환 후 첫 6 sub-module
  bundle, 9 모듈 + 8 test + 7 octave)
- Phase 0 + 1 + 2 부분 누적 test: 478 (2.4 + 180)

## Sub-phase 진척

| sub | 모듈 | 핵심 추가 | test |
|---|---|---|---|
| **2.1** ✓ | `domain/types.py` 확장 | CommandSource / PositionerCommand / RunState / RunTerminationReason / SimulationState / SpeedMultiplier | 18 |
| **2.2** ✓ | `domain/map_resource.py` | MapBounds / SeaSurface / WorkbenchTerrain (numpy + land_mask) / Map | 18 |
| **2.3a** ✓ | `domain/placement.py` | MotionKind 7 / PlacedEntity / CurrentPose | 12 |
| **2.3b** ✓ | `domain/wave_response.py` | WaveResponsePreset 4 / WaveResponseModel + 4 factory | 17 |
| **2.3c** ✓ | `domain/building.py` | AnchorMode 4 / MeshOrigin 3 / BuildingEntity / make_default_building | 16 |
| **2.3d** ✓ | `domain/target.py` | TargetEntity / TargetWaypoint / make_default_aircraft_target | 17 |
| **2.4** ✓ | `physics/dynamics/` (9 모듈) | RigidBodyState / Forces / RK4 / Reference / Aircraft / Ballistic / PoweredFlight / SurfaceVessel / GroundVehicle | 180 |
| **2.5** ✓ | `physics/atmosphere.py` | ISA (T/P/ρ) + ITU-R P.838 rain attenuation + two_way_loss | 22 |
| **2.6** ✓ | `physics/antenna.py` | ParabolicAntenna + sinc² beam pattern + 3-dB bw / peak gain | 21 |
| 2.7 | `physics/reflection/extended_target.py` | Multi-scatterer + Glint | TBD |
| 2.8 | `domain/tracker/` | EKF / UKF / GNN | TBD |
| 2.9 | `domain/detector/cfar.py` | CA-CFAR + OS-CFAR | TBD |
| 2.10 | `domain/pipeline.py` + `scenario.py` | RadarPipeline + Scenario | TBD |
| 2.11 | `domain/platform.py` | RadarPlatform | TBD |
| 2.12 | `domain/timing/` | Reference Timing data model (v0.39) | TBD |

## Phase 2 핵심 결정 (지금까지)

- **Single Command Path**: TRACKER source 시 `source_track_id` + `source_frame_id` 필수 (validation)
- `SimulationState` ⊥ `RunState` (완전히 별개 enum 타입)
- WMO sea_state 0..9 strict
- WaveResponse 4 preset 표준값 (heave 0.95 / 0.7 / 0.3 / 0.0)
- WorkbenchTerrain numpy `setflags(write=False)` 강제
- AnchorMode 4 — BASE_TO_TERRAIN default
- MeshOrigin 3 — BASE_CENTER default
- BuildingEntity placement.motion_kind 반드시 FIXED_GROUND
- `Map.content_hash` empty default (Phase 4 bundle 시점에 채움)
- 모든 도메인 dataclass `frozen=True, slots=True`
- `entity_id` / `map_id` non-empty validation

## 다음 sub-phase 후보

**우선순위 (의존 그래프 기준)**:
1. **2.6b** PlanarArray + Monopulse 4ch — plan/08 § 8.5a.3, 8.5a.4
   (Phase 2.6 의 후속 slice)
2. **2.7** Extended Target — Multi-scatterer + Glint (plan/14 § 14.10).
   1.5 (rcs_single) 의존
3. **2.8** Tracker — Phase 2 핵심, EKF/UKF/GNN
4. **2.9** CFAR — 작음
5. **2.10** Pipeline + Scenario — 여러 sub 의존
6. **2.11** Platform — 작음
7. **2.12** Timing model — 작음

## Phase 2 끝나면

- Phase 3 (App layer) — CommandBus / ResourceLibrary / SimulationClock / Run Manager
- Phase 4 (UI layer) — PySide6 Editor + Simulator workspace
- Phase 5 (검증 프레임워크) — 17 + 종 회귀
- Phase 6+ (NN / DLC / HIL / Physics Lab) — MVP+α
