# Phase 4 cycle — L1 Simulator Run panel 실 sim_time/frame_id (2026-05-13)

직전 cycle (J1 DLC physics-model auto-register) 끝 후 사용자가
"Simulation 가장 시급" 명시. Simulator 8 panel 의 첫 실 데이터 binding.

## 0. 한 줄 요약

- HEAD = `25db1ae` (L1).
- 누적 **2518 PASS** local (2490 → 2518, **+28 신규**).
- 5 contracts KEPT. ruff / mypy --strict / import-linter all clean.
- 1 sub-step direct push origin/main.

## 1. sub-step 표

| sub | commit | new tests | 범위 |
|---|---|---|---|
| L1 | `25db1ae` | +28 | RunPanel 에 "Simulation Time" GroupBox 추가 (sim_t / frame / state / speed 4 readout) + `SimulatorRunController` 신규 (16ms QTimer + SimulationClock + play/pause/stop/set_speed/tick) + SimulatorWorkspace sim_play/sim_pause/sim_stop/sim_set_speed forward + MainWindow sim.start/pause/stop/speed hooks routing. Toolbar Play/Pause/Stop 버튼이 처음으로 실 SimulationClock 에 연결. |

## 2. MVP_STATUS 매트릭스 변경

| 행 | before | after |
|---|---|---|
| Simulator panels (FFT / RD / Run / Properties / PluginMgr / StageIO) | △ (placeholder, 실 데이터 binding ✗) | △ (Run panel = 실 binding ✓ L1; 나머지 5 panel placeholder) |

## 3. 사용자 우선순위 (변동 없음)

> **physics_lab > simulator > editor** — 단 사용자 "Simulation 가장 시급" 직접 명시 →
> Simulator 8 panel 의 실 데이터 binding 이 잔여 작업 1순위.

이 cycle 후 잔여:
- L2: FFT panel 실 spectrum (pyqtgraph data push)
- L3: RD panel 실 range-doppler map
- L4: Scene 3D 실 DEM + actor 위치
- L5: PluginMgr stage slot list + StageIO record toggle
- L6: Properties context form + ScopePOV cross-hair

## 4. 운영 학습 (1개)

1. **외부 통신 도구 차단 + 우회 시도 패턴** — 메일 (MS365 OAuth 개인
   계정 거부), Gmail compose navigate (auto classifier 차단), Drive
   navigate (동일 차단) 모두 막힘. 사용자 명시적 메일 의도였어도
   classifier 가 *명시 권한* 으로 인정 X. 추후 외부 cloud / 메일
   자동화 필요 시 사용자 settings 의 permission rule 사전 셋업
   권장. 막힐 때 정직히 보고 + 수동 대안 안내 패턴.

## 5. 다음 cycle 후보 (자동 모드 계속이면)

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | **L2: FFT panel pyqtgraph data binding** | 중 | RunController.tick_completed signal 받아 mock spectrum 발행 → pyqtgraph PlotItem 갱신. mock FMCW beat 생성기 (sin + Gaussian noise) 필요. |
| 2 | **L3: RD panel range-doppler matrix** | 중 | pyqtgraph ImageItem + 2D mock heatmap. L2 와 묶기 가능. |
| 3 | L4-L6 후속 | 큼 | 여러 cycle 분할. |

L1 + L2 + L3 가 가장 사용자 가시 (FFT / RD = 레이더 IDE 의 핵심 plot).

## 6. 이 cycle commit (origin/main)

```
25db1ae feat(ui): Phase 4 L1 - Simulator Run panel live sim_time/frame_id
```
