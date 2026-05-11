# TRsim — 세션 요약 (v0.40 기준)

**마지막 갱신**: 2026-05-11 — Phase 5 + Phase 6 마감
**직전 완료 버전**: v0.40 (v0.39 + Physics Lab — 5번째 차별점)
**현재 main**: Phase 6.7 (TrainerService stub) — NN 통합 MVP 7 sub-step
**누적 test**: 1344 PASS local, 5 contracts KEPT

---

## 0. 이 문서 목적

새 세션 또는 Cowork 환경의 Claude가 빠르게 맥락을 따라잡기 위한 요약.

---

## 1. TRsim 한 줄 정의

> **다중 표적 환경에서 사용자가 선택한 단일 표적을 안정적으로 추적하는 것이 목표인
> 추적 레이더(Tracking Radar)에 대해, DSP·웨이브폼 개선안의 추적 성능을 시뮬레이션으로
> 검증하는 IDE 스타일 워크벤치. NN 개발 + 자원 편집 + 시뮬 실행을 통합 지원.**

## 2. 전체 구조 (v0.19+)

**단일 프로그램 + 두 Workspace**:

```
TRsim
├── Editor Workspace       자원 편집·조립 (Map / Radar / Targets / Scenario Composer)
└── Simulator Workspace    실행·평가 (기존 설계의 연속)
     ├── DSP Mode          추적 성능 검증 (기본)
     └── NN Mode           NN 개발 (Step 1 Dataset / Step 2 Eval)
```

전환은 Activity Selector + 단축키 (`Ctrl+Shift+E`/`S`/`Tab`).

## 3. 자원 라이브러리 (v0.20+)

```
~/my_workbench_proj/
├── resources/
│   ├── maps/<map_id>/      map.toml + terrain.npz + buildings.toml + source/
│   ├── radars/<radar_id>/  radar.toml ([antenna], [rx_array] 포함)
│   └── targets/<targets_id>/ targets.toml + trajectories.csv
├── scenarios/<scenario_id>/  scenario.toml ([refs] + [composition] + [platform_install])
├── plugins/
└── runs/<run_id>/          manifest.toml (자원 hash 포함)
```

- 자원 독립 저장, Scenario는 ID + content hash로 참조
- 수정해도 과거 Run hash로 검증 가능
- `.scnbundle` / `.runbundle` export로 다른 PC에서 재현

## 4. 좌표계 정합 (v0.21~v0.22 — 이전 프로젝트 핵심 문제 해결)

- **Workspace = 단일 Map = 단일 Origin** (불변)
- WGS84 위경도 + Map ENU (m)
- **Vertical Reference 명시 필수** (egm96 기본, AWS DEM 대응)
- 외부 DEM은 **import 소스만**, 시뮬은 **자체 규격 `terrain.npz`** (격자 + `land_mask`)
- `land_mask=False` 영역은 sea_surface.z 반환 → **DEM 부정확 해저값 차단**
- 건물 anchor 4 mode + DEM bilinear 샘플링 → **건물이 더는 안 뜸**
- Coherence Validator 5종 (자원 변경 시점마다)

## 5. MotionKind 7 카테고리 (v0.21 도입, v0.27 확장)

| MotionKind | x,y | z | 비고 |
|---|---|---|---|
| FIXED_GROUND | 정적 | DEM/explicit | 건물·고정 시설 |
| GROUND_VEHICLE | trajectory | DEM 샘플 | MVP 후 |
| SURFACE_VESSEL | trajectory | sea_surface + wave | 항해 함정 |
| FLOATING_STATIC | 정적 | sea_surface + wave | 정박 함정·부표 |
| **AIRCRAFT** | 동역학 (reference) | 동역학 (target alt) | 비행기 (v0.27) |
| **POWERED_FLIGHT** | 동역학 | 동역학 (thrust+drag) | 미사일·드론 (v0.27) |
| **BALLISTIC** | 동역학 (trajectory 무시) | 동역학 (gravity+drag) | 자유낙하·탄도 (v0.27) |

**v0.27 핵심**: 항공·탄도 표적은 단순 보간 폐기, **trajectory = reference, 실제 = 동역학 적분**.
사실적 거동으로 추적 검증의 신뢰도 ↑. 상세는 14_dynamics_model.md.

## 6. 표적 동역학 모델 (v0.27)

- **MVP Level 1**: 3DOF point-mass + 외력 (gravity/drag/lift/thrust/PD control)
- **자세는 velocity vector 기반 추정** (coordinated flight 가정)
- **Level 2 6DOF (자세 동역학)는 MVP+α**
- RK4 적분, sub-step 0.005s
- 표적 Preset 9종: aircraft_fighter_jet/airliner, missile_cruise/ballistic, drone, artillery, ship/boat/buoy

## 7. Antenna Model (v0.25)

- **AntennaType**: Parabolic (sinc²) + Planar Array (array factor × element pattern)
- **RX 채널**: Single SUM 또는 **Monopulse 4ch (Σ/Δaz/Δel/Δ²)**
- Monopulse Pipeline → error_az/el_rad → Tracker (v0.13 4-error의 EKF Command Error 근원)
- Radar Editor: 통합 폼, 안테나 타입 드롭다운 → 동적 필드, Beam Pattern Preview 실시간

## 8. Run·시간 모델 (v0.14~v0.15)

```
[Sim Start] → Sim RUNNING (sim_t 진행, 모든 환경·Pipeline 시작)
   ↓
[Scenario Load] 표적 정지, Target IDLE
   ↓
[Target Run] → Target RUNNING (trajectory 재생, 메트릭 기록)
   ↕ Target Pause/Stop, Sim Pause/Stop, Speed ×1/2/4/8
```

- Sim Clock = 모든 물리의 기반 시간
- Target Run = 위에 올라탄 상위 레이어 (Sim에 종속)
- Sim PAUSED 중 UI 입력 → InputBuffer
- 포지셔너 명령은 **CommandBus** 단일 경로 (TRACKER / MANUAL_USER / INITIAL_SCAN)

---

## 9. 계획서 구조 (v0.40 — 19개 문서 + 부록 2)

| 파일 | 주요 내용 | 헤더 버전 |
|---|---|---|
| 00 README | 진입점, 변경 이력, 핵심 방향 | v0.36 |
| 01 vision_scope | 정체성 (v0.35), 두 Workspace, MVP, Journey | v0.35 |
| 02 architecture | 4계층, 블록도, SDK Layer, 의존 규칙 | v0.35 |
| 03 data_model | Scenario, Map, Placement, Antenna, Dynamics, **Plugin Manifest § 3.2.1l** | v0.35 |
| 04 migration | Phase 0~7 신규 구현 순서, 모듈 지도 | v0.36 |
| 05 ui_ux | 🟡 **참조 보존** (권위는 13 + 02 § 2.2) | v0.25 (보존) |
| 06 topics | 🟡 **참조 보존** (권위는 17 + 02 § 2.6b) | v0.14 (보존) |
| 07 nn_integration | NN Mode, Stage Slot 9 (DataAssociator 추가), Variant axis v0.34 6개 | v0.35 |
| 08 radar_waveforms | RadarModel, FMCW Triangle, multipath, OS-CFAR | v0.34 |
| 09 radar_platforms | Maritime/Fixed Ground, motion_kind | v0.35 |
| 10 workspaces | Editor/Simulator, 자원 라이브러리 (User > Packages > Built-in) | v0.35 |
| 11 coordinate_systems | WGS84·ENU, Vertical Reference, **SimulationDomain (v0.29)** | v0.35 |
| 12 placement_and_motion | base/current 분리, MotionKind 7, anchor | v0.35 |
| 13 editor_workspace | Editor 5 Activity, Flatten Area (v0.33) | v0.35 |
| 14 dynamics_model | 사실적 동역학 6 모듈, **ExtendedTarget (v0.34)** | v0.34 |
| 15 atmosphere_model | ISA + rain attenuation + **refraction (v0.34)** | v0.34 |
| 16 baseline_audit | **베이스라인 5종 + OS-CFAR** (v0.34 신규) | v0.34 |
| 17 open_platform | **오픈소스 + DLC** (v0.35 신규) — Apache 2.0, .trsim-pkg, SDK Layer | v0.35 |
| 18 hil_integration | **HIL 통합** (v0.38 신규) — DUTAdapter Protocol (10번째), GT/SIL/HIL 3-way, Phase 8 + **v0.39 Reference Timing Mode + Frame Profiler** (§ 18.16/18.17) | v0.39 |
| 19 physics_lab | **Physics Lab** (v0.40 신규) — 3-pane 인터랙티브 + 9 Test Objects + 4 시간 모드 + PhysicsModelProtocol (11번째) | v0.40 ⭐ |
| A code_audit | 🚫 **DEPRECATED** (sim_3d 평가 무효, v0.36) | v0.36 |
| B glossary | 용어집 870줄 (v0.27~v0.35 신규 21 용어 포함) | v0.35 |

> 참고: **05/06 헤더가 옛 버전인 건 의도적** (참조 보존 라벨). 정합 노트 19개로 옛 표현 함정 차단됨.

## 10. 루트 문서

- `README.md` — 패키지 진입점 (v0.37 변경 요약)
- `COWORK_HANDOFF.md` — cowork 첫 진입 종합 가이드 ⭐
- `TRsim_README.md` — 프로젝트 아카이브 안내
- `AGENT_GUIDE.md` — Claude·기여자 작업 규약
- `ROADMAP.md` — 작업 로드맵 + 6단계 큰 흐름
- `SESSION_SUMMARY.md` — 이 문서
- `OPEN_QUESTIONS.md` — 미결 질문 (블로커 0, 결정 43)
- `REVIEW_REPORT_v0.35.md` — 정합성 검토 종합 보고서
- `repo_root_drafts/` — Phase 0 시 레포 루트로 복사 (LICENSE/CI/pyproject.toml/.importlinter 등 13종)
- `competitive_analysis/` — 경쟁 환경 분석

---

## 11. 세션 요약 — v0.25 → v0.37

| 버전 | 핵심 |
|---|---|
| v0.26 | Editor Workspace 전체 레이아웃 (`13_editor_workspace.md` 신규, 654줄) |
| v0.27 | 사실적 표적 동역학 (`14_dynamics_model.md` 신규, MotionKind 5→7, trajectory=reference) |
| v0.28 | 시각화 스택 (pyqtgraph + PyVista 하이브리드) + 대기 모델 (`15_atmosphere_model.md` 신규) |
| v0.29 | Simulation Domain 분리 (Map + Outside Environment, 11 § 11.11) — 빔이 Map 넘어가도 안전 |
| v0.30 | 07 NN 모드 보강 (T11) — v0.25~v0.29 정합, 확장 Variant 6종, Sample 형식 확장 |
| v0.31 | 04 migration Phase 체크리스트 갱신 (T10) — v0.18~v0.30 모듈 모두 반영, Phase 6 NN 신설 |
| v0.32 | 02 architecture 의존 그래프 전면 갱신 (T9) — 블록도·디렉토리·의존 규칙 v0.18~v0.31 반영, § 2.9 모듈 도입 이력 표 신설 |
| v0.33 | Map Editor 평탄화 도구 추가 (12 § 12.11 Flatten Area) — 함정 정박지·활주로·건물 부지 |
| v0.34 | **베이스라인 점검 + 5종 MVP 추가** (Q-BL1~5) — 16 baseline_audit 신규, Two-ray multipath / Multi-scatterer + Glint / EKF+UKF / GNN / Refraction |
| v0.35 | **오픈소스 + DLC 플랫폼 정체성 전환** (Q1-rev/Q2~Q9) — 17 open_platform 신규, Apache 2.0, .trsim-pkg, Core team, SDK Layer, 루트 문서 11개 |
| v0.36 | **정합성 검토 5세션 완료** — 약 52~55개 정정, § 3.2.1l Plugin Manifest 신설(108줄), 정합 노트 19개, 21 신규 용어, 05/06 "참조 보존" 라벨 |
| v0.37 | **Phase 0 인프라 보강 + sim_3d 분리** — pyproject.toml(257줄)·.importlinter(106줄) 신설, 02 § 2.3 디렉토리 갱신, 04 migration 큰 재작성 (이식 → 신규 구현), appendix_A DEPRECATED, 정체성·검증 기준에서 sim_3d 제거 |
| v0.38 | **HIL 통합 신설 (4번째 차별점)** — `plan/18_hil_integration.md`(635줄), DUTAdapter Protocol (10번째 SDK), L1~L5 RX 표준 + 양방향 TX, GT/SIL/HIL 3-way 검증, Phase 8 (8.1/8.2/8.3), `domain/hil/`·`app/hil/`·`ui/simulator/hil_panel/` 디렉토리 분산, `tcp_json_dut_adapter.py` 기본 sample, Q-HIL1~7 등록. 차별점 3+1 → 4+1 |
| v0.39 | **Reference Timing Mode + Frame Profiler** — 18 § 18.16/18.17 신설 (총 1,054줄로 확장), PerformanceClock (02 § 2.2c, SimulationClock 의 보정 layer), 03 § 3.2.1n dataclass (StageTimingProfile/FrameTimingReport/StageTimingStat 등), `domain/timing/`+`app/timing/`+`profiler_panel/` 디렉토리, DUTAdapter Lock-step sync 메서드, Phase 2/3/4/5 분산 + Phase 8.1 보강, Q-RT1~8 등록. 차별점 4+1 유지 (당연한 기능) |
| v0.40 | **Physics Lab 신설 (5번째 차별점) ⭐** — `plan/19_physics_lab.md`(1086줄). **3-pane 인터랙티브** (Code | Visualization | Parameters), **9 표준 Test Objects** (Sphere/Cube/Plate/Cylinder/Cone/Point/Plane/Wall/Trihedral), **4 시간 모드** (Static/Single Run/Compare/Sweep), **PhysicsModelProtocol** (11번째 SDK). **Physics Layer 분리** — `domain/dynamics`·`domain/atmosphere`·`domain/radar` 의 물리 → `physics/` 통합. `app/physics_lab/` + `ui/physics_lab/` Workspace (3번째). **06 § 6.7 결정 변경** — 사용자 물리 plugin 영구 제외 → 가능 (Validation Bench 안전망). **17종 → Physics Lab 통합** (16 § 16.9). 외부 자료 학습 점진 — 형태 1+5 MVP, 형태 2/4 Phase 9.2/9.3, **형태 3 (논문 PDF → 자동 코드) 명시 제외**. **Phase 9 신설** (MVP+α Wave 4) — 9.1/9.2/9.3. PL-1~15 closed, Q-PL1~10 등록. 차별점 4+1 → 5+1 |

### 사용자 통찰의 흐름
1. "Editor Workspace 깊게 파야" → 전체 레이아웃 확정 (v0.26)
2. **"중력이 적용되어야, 모든 동적 오브젝트에"** → 사실적 동역학 도입 (v0.27)
3. **"가장 사실적으로"** → 타입별 자유도, 외력 균형 모델, 표적 Preset 9종 (v0.27)
4. **"파도·표적 출렁·대기 상태 표현 적합한 라이브러리?"** → 하이브리드 + 대기 3측면 모델 (v0.28)
5. **"맵 10km인데 레이더 빔이 그 이상 갈 수 있잖아"** → Simulation Domain 분리 (v0.29)
6. **"맵 편집에 평탄화 기능도 있어?"** → Flatten Area 도구 추가 (v0.33)
7. **"이 프로그램이 생명력을 얻으려면 베이스라인 점검을 해야겠어"** → 16 baseline_audit 신설, 5종 MVP 추가 (v0.34)
8. **"오픈소스로 공개 + DLC 같은 확장 가능 플랫폼"** → 17 open_platform 신설, Apache 2.0, 정체성 "워크벤치" → "플랫폼" (v0.35)
9. **"검토하고 정합성 다듬자"** → 5세션 검토, 옛 표현 정합 노트, Plugin Manifest 신설 (v0.36)
10. **"sim_3d는 정상 동작 보장 안 됨"** → 회귀 비교 기준에서 제거, 신규 구현 원칙 명시, 정체성에서도 제거 (v0.37)
11. **"HIL 로 펌웨어를 시뮬 루프에 연결"** → 18 hil_integration 신설, DUTAdapter Protocol (10번째 SDK), GT/SIL/HIL 3-way 검증, 차별점 4번째로 추가 (v0.38)
12. **"테스트 코드 PC 측 동작 시간이 실 보드보다 느릴 수 있다 → 시뮬 시간 보정. Vivado simulation 같은 느낌"** → Reference Timing Mode + Frame Profiler 신설, PerformanceClock (시뮬 시간 ↔ wall_clock ↔ reference_time 매핑), Lock-step Handshake (HIL frame 단위 sync), 차별점 유지 (당연한 기능) (v0.39)
13. **"물리 코드를 한 곳에 모아 검증 룸을 만들고, 시간 차원 위에서 인터랙티브하게 다루자"** → Physics Lab 신설 (3번째 Workspace), Physics Layer 분리 (domain → physics 통합), 9 표준 Test Objects (Sphere/Cube 등), 4 시간 모드, 사용자 물리 plugin 가능 (06 § 6.7 결정 변경), PhysicsModelProtocol (11번째), 17종 → Physics Lab 통합, 차별점 4+1 → 5+1 (v0.40) ⭐

이 패턴 유지: **사용자가 "왜 이게 안 되지/이래야" 짚으면 → 진단 → 추상 일반화 → 모듈 추가**.

---

## 12. 다음 세션 즉시 할 일 후보

**설계 + 정합성 검토 + Phase 0 인프라 + sim_3d 분리 + HIL 통합 + Reference Timing + Physics Lab 모두 완료.** 다음 큰 단계는 **Phase 0 구현 착수**:

1. **T3 Phase 0 인프라 셋업** ⭐ — `repo_root_drafts/` 13종을 새 GitHub repo에 적용, 디렉토리 구조 생성, 빈 QMainWindow 띄우기 (자세한 체크리스트: `plan/04_migration.md` § 4.3)
2. **T1 UI 목업 마무리** (Phase 0 과 병렬 가능) — Editor Workspace + 동역학·glint·DLC Plugin Manager 신규 시각화
3. **T6 DECISIONS.md ADR** (점진적 — 결정 43개 ADR 화)
4. **첫 외부 sample DLC 검토** (Q-OP1 — Stone Soup adapter? IMM tracker?)

cowork 환경 활용 가능 (디렉토리 일괄 생성·코드 작성·테스트 자율).
GitHub repo 생성·push만 사용자 수동.

---

## 13. 핵심 통찰 모음 (새 Claude를 위한)

- **모든 자원은 단일 Map Origin 위에**. Origin은 불변, 변경하려면 Save As New
- **외부 DEM은 import 소스, 시뮬은 자체 규격 (`terrain.npz`)**. land_mask로 해상 영역 분리
- **base_* (Editor) ≠ current_* (Sim Running)**. PAUSED는 정지된 그 순간 유지
- **trajectory = reference, 실제 = 동역학** (v0.27 핵심). 사용자 비현실 입력도 동역학 한계 내 처리
- **표적은 multi-scatterer, glint 자동 발생** (v0.34). 점 표적이면 우리 차별점("단일 추적 안정성")의 핵심 변수가 사라짐
- **EKF는 기본, UKF는 선택 가능** (v0.34, Stone Soup 호환). 강한 비선형성에 UKF
- **AIRCRAFT는 max_climb_rate 등 자동 적용**. BALLISTIC은 초기 조건만, 이후 외력만
- **CommandBus 단일 경로**. RunManager / UI 방향키 / InputBuffer만 publish 권한
- **Run Manifest에 모든 hash 박힘**. 자원 수정해도 과거 Run 재현 검증 가능
- **MVP에서 trajectory 편집 GUI는 제외**. CSV import + 메타 편집만
- **Workspace ≠ Mode**. Workspace는 Editor/Simulator, Mode는 Simulator 안의 DSP/NN
- **크로스 플랫폼** (Win/Linux/Mac 명시적, v0.27)

## 14. 새 Claude 시작 가이드

새 세션이 열리면:
1. `COWORK_HANDOFF.md` (있으면) — cowork 진입 종합 가이드 ⭐
2. `AGENT_GUIDE.md` (작업 규약·정체성)
3. 이 문서 (SESSION_SUMMARY.md) — 5분 맥락 잡기
4. `ROADMAP.md` § 큰 흐름 — 다음 작업 (6단계)
5. `REVIEW_REPORT_v0.35.md` — 정합성 검토 결과 (어느 게 권위)
6. `OPEN_QUESTIONS.md` — 블로커 확인 (현재 0)
7. 필요시 `plan/00_README.md` + 해당 주제 문서

**자연스러운 시작**: "Phase 0 시작하자" 또는 "T1 UI 목업부터" 등.

---

## 15. UI Mockup 9 영역 완료 (v0.41 → cowork 이동 시점, 2026-05-04)

### 추가 mockup 영역 6개
이전 (v0.40) 까지: Editor Workspace 개요 + Reference Timing + HIL + Physics Lab + Simulator. 5 영역.

v0.41 (cowork 이동 직전) 추가:
- **Plugin Manager** — 3 화면 (Installed / Browse / Detail), 모자이크 색
- **Welcome / Project Picker** — 1 화면 + 모달, 회청+hint
- **NN Training Workflow** — 3 화면 + Deploy Wizard, 보라 (Physics Lab 통일)
- **Scenario Editor 상세** — 5 Activity (SE-1~5), Editor teal + Activity hint

### 9 영역 완성 — 차별점 5+1 모두 시각화
| 영역 | accent | 화면 | 핵심 |
|---|---|---|---|
| Editor 개요 | teal | 5 Activity | 좌측 stripe + 상시 sidebar |
| Reference Timing | 파란 | - | frame 시간 보정 |
| HIL | 주황 | - | DUTAdapter |
| Physics Lab | 보라 | 4 | 3-pane + 9 Objects + 4 모드 |
| Simulator | 회청+빨강 | 6 | SIM-1~6 |
| Plugin Manager | 모자이크 | 3 | Installed / Browse / Detail |
| Welcome | 회청+hint | 1+모달 | Recent + 4 Quick Start |
| NN Training | 보라 | 3+wizard | 5 단계 + 학습 영역 |
| Scenario Editor | teal+hint | 5 Activity | SE-1~5 깊이 |

### 추가 결정 — Plugin Manager
- Q-PM-1=(c) 3 화면 / Q-PM-2=(d) 모든 출처 / Q-PM-3=(b) 카테고리 그룹 / Q-PM-4=(a)+(c) 검증 표시 + 경고 / Q-PM-5=(c) 카테고리별 영역 색

### 추가 결정 — Welcome
- Q-W-1=(d) 단순 4 액션 / Q-W-2=(c) Tutorial 5개 / Q-W-3=(d) What's New 박스 / Q-W-4=(b) 풍부 정보 / Q-W-5=(b)+hint 절제

### 추가 결정 — NN Training
- Q-NN-1=(b) 5 단계 / Q-NN-2=(a)+(b) 3 화면 / Q-NN-3=(d) 모든 출처 / **Q-NN-4 권고** — Plugin code edit X (View source + External IDE link 만, 학습 시간·라이선스 책임) / Q-NN-5=(b) Wizard / Q-NN-6=(b) 4-error + 학습 영역 / Q-NN-7=(a) 보라 통일

### 추가 결정 — Scenario Editor
- Q-SE-1=(a) 5 화면 / Q-SE-2=(a) Maritime · Missile Defense (Simulator 와 동일, 흐름 추적) / **Q-SE-3=(b) + Left-Right 단면 추가** ⭐ Phase 4 보강 / **Q-SE-4=(b) 빔포밍 only — 환경 영향은 Simulator/Physics Lab 영역, Editor 안 [▶ Quick Test in Simulator] 버튼 추가** / **Q-SE-5=(b) + 표적 종류별 차별** ⭐ Phase 4 보강 (해상/육상 vs 공중 z + 한계속도 조언) / Q-SE-6=(b) Coherence Validator / Q-SE-7=(c) Editor teal + Activity hint

### 결정 누계
v0.16~v0.40: 72 결정 → v0.41 (mockup 추가): **약 100 결정**, 블로커 0.

---

## 16. Cowork 이동 시점 (2026-05-04)

### 작성 완료 — cowork 인계 자료
- **`COWORK_HANDOFF.md`** ⭐ — v0.40 최종 갱신 (UI mockup 9 영역 + Phase 0 진입 안내)
- **`PHASE_0_GUIDE.md`** ⭐ NEW — cowork 의 즉시 작업 가이드 (Phase 0.1~0.5)
- **`TRsim_v0.41_cowork_handoff.zip`** — 모든 자료 zip (458KB, 71 파일)

### Cowork 의 첫 turn 흐름
1. `COWORK_HANDOFF.md` 읽기 (10분)
2. `AGENT_GUIDE.md` 읽기 (5분)
3. `PHASE_0_GUIDE.md` 읽기 (10분)
4. 사용자에게 "Phase 0 시작 — 어디부터?" 짚을 점:
   - (a) Repo 셋업 + GitHub 연결
   - (b) 디렉토리 구조 + 첫 dataclass
   - (c) pre-commit + CI
   - (d) 다른 우선순위
5. 사용자 결정 받고 진행

### Cowork 환경 특이점
- 파일 직접 편집 가능 (claude.ai 보다 ↑)
- bash / git / pip 직접 실행
- gh CLI 또는 push 로 GitHub 연동
- PySide6 / pyqtgraph / PyVista 코드 단계 본격

### 이 세션 종료 시점
**설계 + UI mockup 모두 완성. Phase 0 진입 직전.**
- 결정 약 100개, 블로커 0
- 19 plan + 부록 2 (14,000+ 줄)
- UI mockup 9 영역 (HTML + SPEC.md 한 쌍)
- Repo root drafts 8 종 준비

다음 단계: cowork 환경에서 Phase 0 인프라 셋업.

---

## 17. Cowork 첫 세션 — Phase 0.1 + 0.3 + 0.4 (2026-05-04)

### 진행 흐름
1. `files.zip` 압축 해제 → `handoff/` 정착
2. 핸드오프 문서 정독 (COWORK_HANDOFF / AGENT_GUIDE / PHASE_0_GUIDE / SESSION_SUMMARY / ROADMAP / OPEN_QUESTIONS / REVIEW_REPORT) + plan 19 + UI mockup 9 영역 + repo_root_drafts
3. 메모리 정착 (user/feedback/project/reference 7 파일)
4. GitHub repo: `https://github.com/josephxlee/trsim.git` 사용자 생성
5. **Phase 0.1**: `Tracking Radar Simulator/trsim/` subfolder 생성, repo_root_drafts 정착, .gitignore 추가, git init + DCO sign-off + 첫 commit (`789ba52`) + push
6. **Phase 0.3**: `src/workbench/` 디렉토리 트리 (40 `__init__.py` + `py.typed`), `tests/` 트리
7. **Phase 0.4**: `__main__.py`, `domain/types.py` (PositionENU/VelocityENU/Time, frozen+slots), `sdk/protocols.py` (11 Plugin Protocol stubs), `sdk/__init__.py` re-export, `tests/conftest.py`, `tests/unit/domain/test_types.py` (5 unit tests)
8. `.importlinter` 단순화 — Contract 1-4 활성, 5(pyvista)/6(nn) Phase 4/6 활성 예정
9. 두 번째 commit + push (Phase 0.3 + 0.4 통합)

### 이 세션 산출물
- repo `josephxlee/trsim` GitHub public, Apache 2.0
- branch: `main` (DCO sign-off)
- 2 commits: Initial + Phase 0.3+0.4
- src 패키지 트리 완성, types/protocols 첫 코드, 5 unit test
- `setup_phase0.sh`, `setup_phase0_4.sh` 스크립트 (Cowork sandbox 가 Windows mount git lockfile 못 다뤄서 사용자가 Git Bash 로 실행)

### Cowork 환경 학습
- Sandbox bash 가 Windows bindfs 마운트의 `.git/config.lock` unlink 권한 없음 → git 명령은 사용자가 Git Bash 로
- 파일 작성·편집은 Cowork 측이 직접 가능 (Windows 마운트로 정상 write)
- `repo_root_drafts/.github/workflows/ci.yml` 이미 존재 (ruff + ruff format check + mypy strict + import-linter + pytest matrix Ubuntu/Windows/macOS × Py 3.11/3.12)

### 다음 세션 시작점
- **CI 결과 확인 먼저** — Phase 0.4 push 후 GitHub Actions 통과 여부
- **CI fail 시**: mypy strict 가 빈 Protocol class 문제일 가능성 → `pass` 추가 또는 method stub
- **CI pass 시**: Phase 1 진입 — `physics/fmcw.py`, `physics/ray_tracing.py`, `physics/geometry.py` 등 primitive 함수 + 분석 공식 검증 (수계산: range 1km → beat 666.7Hz 등)
- 또는 Phase 2 (Domain Contract) 와 병행 시작

### 결정 누계
v0.41 까지 ~100. 이번 세션 신규 결정:
- Repo 위치: `Tracking Radar Simulator/trsim/` subfolder (사용자 선택)
- Repo 이름: `trsim` 소문자
- DCO 식별자: joseph / huvluv14@gmail.com
- 첫 dataclass = PositionENU/VelocityENU/Time, frozen+slots
- 첫 Protocol = 11 (DetectorProtocol ~ PhysicsModelProtocol), `@runtime_checkable`
- importlinter Phase 0 시점: Contract 1-4 활성, 5/6 비활성 (Phase 4/6 활성)

---

## 18. Phase 1~5 누적 milestone (2026-05-04 ~ 2026-05-11)

Phase 0.4 → Phase 5.18 까지 약 1 주, 누적 commit ~60, 누적 test
1185 PASS local, 5 contracts KEPT 매 commit. ruff / mypy strict /
import-linter / pytest 매 commit green.

### Phase 단위 한 줄 요약

- **Phase 1** Primitives — `physics/` 첫 모듈 (fmcw / antenna / ray_tracing
  / geometry / radar_equation / multipath / horizon). +47 physics tests.
- **Phase 2** Domain — 11 contract Protocol → concrete dataclasses
  (target / map / scenario / detector / tracker / data_associator).
  +800 tests 누적.
- **Phase 3** App layer — `app/` (pipeline / timing / cli).
  +50 tests, CLI `trsim run / profile`.
- **Phase 4** UI 골격 — Editor 5 Activity + Resource Browser +
  Simulator 8 panel + Profiler tab. 12 sub-phase (4.1~4.12), +190 ui
  tests. 누적 998 PASS.
- **Phase 5** 물리 검증 프레임워크 마감 — 18 카테고리 (14 physics +
  app/timing 3 + domain 5), +236 verification tests. 5.15/5.16 도
  src 신규 구현 후 verification 완료. 누적 **1234 PASS**.

### Phase 5 카테고리 14종 누적
| sub-phase | 산출 | tests |
|---|---|---|
| 5.1 | Golden infra (`tests/physics/golden_dataset.py`) | 9 |
| 5.2 | FMCW propagation | 8 |
| 5.3 | Parabolic antenna | 11 |
| 5.4 | ISA atmosphere + rain | 13 |
| 5.5 | Dynamics forces (gravity/drag) | 6 |
| 5.6 | Monopulse error | 9 |
| 5.7 | Planar array element_power | 22 |
| 5.8 | Ballistic analytic vs RK4 | 12 |
| 5.9 | Single-scatterer RCS | 14 |
| 5.10 | CFAR detector (CA + OS) | 16 |
| 5.11 | PerformanceClock | 9 |
| 5.12 | FrameBoundaryDetector | 6 |
| 5.13 | FrameProfiler + StageTimingProbe | 12 |
| 5.14 | ExtendedTarget multi-scatterer + glint | 19 |
| 5.17 | EKF + UKF CV scenario regression | 9 |
| 5.18 | GNN data association regression | 12 |
| 5.19 + 5.20 | Multipath + horizon golden 회귀 | 14 |
| 5.21 | σ_glint Monte Carlo (Skolnik rule) | 6 |
| 5.22 | EKF + UKF maneuver scenario | 5 |
| 5.15 | coherence_validator (src 신규 + test) | 15 |
| 5.16 | simulation_domain.sample_terrain_safe (src 신규 + test) | 9 |

Phase 5 전체 마감 — 누적 +236 신규 (998 → 1234 PASS).

### 다음 진입점 권고 (Phase 6 또는 5.15/5.16 코드 구현)
- **Phase 6 (NN 통합)** — Pairing NN MVP, Step 1 (Dataset Builder)
  + Step 2 (Eval) wiring. UI 는 4.11 끝, 도메인 + dataset 형식
  (plan/07).
- **5.15 + 5.16 도메인 구현** — `coherence_validator.py` +
  `simulation_domain.py` 를 plan/11 § 11.7 / § 11.11.7 에 따라
  신규 작성. 작성 시점에 verification 도 따라감.

### Phase 5 운영 학습 (이번 세션)
1. **Plan-only 카테고리 발견 시 skip** — kickoff doc 의 카테고리 list
   는 "verifiable" 가정. src/ 에 코드 없으면 verification 의 의미
   없음. Phase 6+ implementation task 로 옮김 (5.15/5.16 사례).
2. **물리 검증 패턴 안정화** — golden JSON closed-form + invariant +
   validation 3 layer. 매 phase 8-22 tests 적당.
3. **기존 unit test 와 중복 회피** — Phase 5.x 는 multi-frame
   scenario / 글로벌 invariant / golden geometry 위주. Phase 2~3 의
   단일 호출 unit test 와 다른 각도.
4. **EKF/UKF/GNN 시나리오는 deterministic + closed-form 가능** —
   RNG seed 고정 안 해도 perfect-measurement 시나리오로 충분 검증.
5. **bindfs 잘림 발생 0** — 이 세션은 모든 commit 에서 tail 검사
   통과.

---

## 19. Phase 6 NN 통합 MVP (2026-05-11)

Phase 5 마감 직후 같은 세션. 7 sub-step (6.1~6.7) — schema layer
부터 TrainerService stub 까지. 누적 1234 → 1344 PASS (+110 신규).
5 contracts KEPT 매 commit.

### Sub-step 한 줄 요약

| sub | 모듈 | tests | 핵심 |
|---|---|---|---|
| 6.1 | `domain/nn/sample_spec.py` | 24 | FieldSpec / SampleSpec / DatasetVariant / DatasetMeta frozen schema |
| 6.2 | `sdk/protocols.py` NNPluginMixin | 5 | runtime_checkable Protocol + FrameworkOrigin Literal |
| 6.3 | `app/nn/data_exporter.py` | 10 | write_dataset / read_dataset HDF5 (meta/schema/variant JSON attrs + inputs/labels groups) |
| 6.4a | `app/nn/dataset_builder.py` | 11 | streaming append + progress callback + cancel/finalize |
| 6.4b | `domain/pipeline.py` probes | 9 | step() 4-stage probe hook (predict/associate/update/spawn) |
| 6.4c | `ui/simulator/nn_mode/step1_controller.py` | 8 | Editor "Build Dataset" 버튼 → DatasetBuilder (pytest-qt) |
| 6.5 | `app/nn/pairing_nn.py` | 13 | NumpyPairingNN NNPluginMixin 첫 reference (Hungarian baseline) |
| 6.6 | `app/nn/evaluator.py` | 9 | 4-error 진단 (training/dev/test/bayes + avoidable_bias/variance/data_mismatch + diagnosis hint) |
| 6.7 | `app/nn/trainer.py` | 21 | TrainingJob schema + TrainerService fake-loop + placeholder weights |

### 파이프라인 전체 흐름 (현재 상태)

```
Editor Step 1 panel  ←  scenario / probe / frames / output path
    ↓ build_requested
NNStep1Controller (6.4c)
    ↓ creates
DatasetBuilder (6.4a)  ←  현재 random demo loop (real Pipeline 통합은 6.4b probe wire 후속)
    ↓ progress_callback → panel.set_status
    ↓ finalize → write_dataset
write_dataset (6.3) → HDF5 file
    ↓
Editor Step 2 (controller wiring 후속)
    ↓ evaluate (6.6)
NNEvalResult → 4-error 진단 table
    ↑ plugin = NumpyPairingNN (6.5) 또는 학습된 NN
    ↑ 학습은 TrainerService (6.7) 또는 workbench-train CLI
```

### 다음 진입점 권고
- **Phase 7 (DLC 시스템)** — `.trsim-pkg` packaging, PackageManager,
  ResourceLibrary 3-source 통합 (plan/17).
- **Phase 6 후속** — 6.4c random demo loop → 실제 Pipeline.step()
  probe wire, Step 2 UI controller wiring, Training Panel UI.

### Phase 6 운영 학습
1. **Schema → IO → Service → UI** 흐름이 자연스러움. 도메인 layer
   schema (6.1) 부터 → SDK Protocol (6.2) → IO (6.3) →
   streaming service (6.4a) → Pipeline hook (6.4b) → UI wiring
   (6.4c) → reference plugin (6.5) → evaluator (6.6) → trainer
   (6.7). 매 sub-step 가 다음 step 의 dependency 만 추가.
2. **NN 첫 구체 plugin = closed-form baseline** — "no-NN" reference
   가 학습된 weights 평가의 zero point. NumpyPairingNN 가 Hungarian
   로 동작하지만 NNPluginMixin 만족 → 인터페이스 일관성 검증.
3. **fake-loop stub 가 합리적 MVP** — TrainerService 가 실제 학습
   안 하지만 UI / config / weights 경로 contract 검증. 외부
   workbench-train CLI 가 같은 schema 로 swap-in 가능.
4. **HDF5 의 strict-shape 검증이 디버그 비용 절약** — DataExporter
   가 write 전 shape/dtype 검사로 partial file 방지. DatasetBuilder
   도 per-sample append 검증 — 디버그 시 어느 sample 에서 fail
   했는지 명확.
5. **itertools.pairwise vs zip(strict=True)** — 길이 다른 list
   에서 `zip(a, a[1:], strict=True)` 가 ValueError 던짐 (5.17 +
   6.7 둘 다 함정). `itertools.pairwise(a)` 가 표준.
