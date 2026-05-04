# 01. 기획 & 우선순위

**최종 갱신**: 2026-05-02 (v0.40 — Physics Lab 추가, 차별점 4+1 → 5+1, MVP+α Wave 4 신설)

## 1.1 프로젝트 정체성

### 한 줄 정의 (v0.40)

> **TRsim은 추적 레이더 알고리즘·자원·시각화·물리 모델을 자유롭게 다루는 오픈소스 워크벤치 플랫폼이다. Apache 2.0 코어에 커뮤니티가 만든 `.trsim-pkg` 를 더해, 어떤 추적 시나리오라도 시뮬·검증·NN 학습이 가능하며, HIL 통합으로 실제 펌웨어·하드웨어를 시뮬 루프에 연결한 검증까지 지원한다. Physics Lab 으로 물리 모델을 3D 시각화·검증·진화시킬 수 있다.**

### 한 단락 정의 (기능 중심, v0.34/v0.38/v0.40 진화)

**TRsim은 다중 표적 환경에서 사용자가 선택한 단일 표적을 안정적으로 추적하는 것이
목표인 추적 레이더(Tracking Radar)에 대해, DSP·웨이브폼 개선안의 추적 성능을
시뮬레이션으로 검증하는 IDE 스타일 워크벤치다. NN 개발을 위한 별도 모드도 제공하며,
DLC 패키지 시스템으로 알고리즘·자원·시각화를 자유롭게 확장 가능하다. v0.38 부터는
HIL 통합 (Hardware-in-the-Loop) 으로 실제 펌웨어·FPGA·DSP 보드를 시뮬 루프에 연결,
GT/SIL/HIL 3-way 비교로 펌웨어 정확도와 DUT-Bias (펌웨어 vs Python DSP gap) 를 정량화한다.
v0.40 부터는 Physics Lab 으로 물리 모델 (전파·반사·동역학·대기·안테나) 을 3-pane 인터랙티브
환경에서 검증·디버깅·진화 가능 — 9 표준 Test Objects (Sphere/Cube/Plate/etc.) + 4 시간 모드 +
사용자 물리 plugin (PhysicsModelProtocol, 11번째 SDK).**

### 정체성 진화 (v0.35 → v0.40)

| 단계 | 정체성 | 메시지 |
|---|---|---|
| MVP | 추적 레이더 IDE | "Stone Soup의 IDE 버전" |
| MVP+α (Wave 1) | + NN 통합 | "DSP↔NN 동일 인터페이스 비교" |
| MVP+α (Wave 2) | + DLC 시작 | "VS Code Extension 모델로 추적 시뮬 확장" |
| MVP+α (Wave 3) | + HIL 통합 | "펌웨어·하드웨어를 시뮬 루프에" (v0.38) |
| **MVP+α (Wave 4)** | **+ Physics Lab** | **"물리 모델 3D 시각화·검증·진화" (v0.40)** ⭐ |
| 성장기 | 플랫폼 | "Blender의 추적 레이더 버전" — 코어 + 커뮤니티 콘텐츠 |
| 성숙기 | 학술·산업 표준 | "추적 레이더 분야의 GitHub" |

상세: [17 open_platform.md](17_open_platform.md), [18 hil_integration.md](18_hil_integration.md), [19 physics_lab.md](19_physics_lab.md).

### 핵심 차별점 (5 + 1)

1. **추적 알고리즘 검증 IDE** — Stone Soup이 라이브러리, MATLAB이 종합 도구. 그 사이의 가벼운 IDE는 시장에 없음
2. **DSP ↔ NN 동일 인터페이스 교체·비교** — 학술 NN 연구의 표준 환경 부재 → TRsim이 그 자리
3. **4-error 진단 (Bayes/Training/Dev/Test)** — Andrew Ng 패턴을 추적 레이더에 적용
4. **HIL 통합** — GT/SIL/HIL 3-way 검증. 오픈소스 추적 IDE+HIL 의 첫 사례 (v0.38)
5. **Physics Lab — 인터랙티브 물리 실험실** ⭐ v0.40 — 3-pane (Code | Visualization | Parameters) + 9 Test Objects + 4 시간 모드 + 사용자 물리 plugin. 추적 IDE + 인터랙티브 물리 시각화 = 시장에 부재한 조합 (MATLAB / Stone Soup / Ansys / AWR / Phet 어느 곳도 동일 조합 X)
6. ➕ **DLC 에코시스템** — 알고리즘·자원·시각화·물리 자유 확장

### 두 Workspace (v0.19)

단일 프로그램이지만 성격이 다른 두 작업을 분리한다:

#### 📐 Editor Workspace

**목적**: 시뮬에 쓰일 자원을 편집·조립.

- Map (DEM, 건물, 지형) 편집
- Radar (Platform + RadarModel + Waveform) 편집
- Targets (표적 trajectory) 편집
- Scenario (Map + Radar + Targets 조합 + 메타) 조립
- 시간 진행 없음, 주 동작은 Save

**MVP 범위**: ResourceBrowser + Scenario Composer 뼈대. 풀 편집 기능은 MVP 후.

#### ▶ Simulator Workspace (기본, 기존)

**목적**: 조립된 Scenario로 DSP/NN 검증.

아래 **두 운용 모드**는 Simulator Workspace 안에서만 의미 있다.

→ Workspace 구조 상세: [10_workspaces.md](10_workspaces.md)

### 두 운용 모드 (Simulator Workspace 안)

Simulator Workspace는 명확히 분리된 **두 가지 운용 모드**를 가진다. 사용자가 메뉴
(`View > Mode`)에서 명시적으로 전환한다.

#### 🎯 DSP 모드 (기본)

**목적**: DSP Plugin의 추적 성능을 시뮬레이션으로 검증.

- 사용자는 DSP Plugin(`.py`)을 작성해 Pipeline의 특정 스테이지에 꽂음
- Run을 실행하면 기본 구현 또는 사용자 Plugin으로 Pipeline이 돌아감
- 선택 표적에 대한 추적 지표(Continuity, ID Switches, Positioner Lag 등)로 평가
- 두 Plugin을 나란히 비교(Compare Run)
- **NN 관련 UI는 보이지 않음** — 모드 전환 전까지 사용자는 NN 개념을 의식할 필요 없음

이 모드가 본 Workbench의 **주 목적**이다. 대부분의 사용 시간이 여기서 소비된다.

#### 🧠 NN 개발 모드 (선택적 진입)

**목적**: 새로운 NN 모델을 만들기 위한 학습 데이터 추출과 NN 평가.

명시적으로 모드 전환 시에만 관련 UI가 나타남. 두 단계(Step)로 구성:

```
Step 1: 학습 데이터 추출
  - SampleSpec으로 뽑을 샘플 정의
  - Dataset Variant로 물리 조건 분리 수집 (A: 이상화 / D: 현실 등)
  - 여러 시나리오 × 시드로 배치 실행
  - HDF5로 저장

Step 2: NN 평가
  - <nn_file_name>.py 로드
  - 4가지 error 분석:
      Bayes error (선택적, 이론 하한 근사)
      Training error (학습셋)
      Dev error     (검증셋)
      Test error    (미지 시나리오)
  - Variant 격자 분석으로 bias/variance/data mismatch 진단
```

NN 모드에서 학습된 NN은 **표준 Plugin 포맷(`.py` + `weights/*.npz`)**으로 저장되며,
이를 DSP 모드에서 일반 Plugin처럼 Pipeline 슬롯에 꽂아 쓸 수 있다 — 두 모드를 관통하는
유일한 연결점.

### 세 문장 정의 (DSP 모드 기준)

1. **추적 성능 평가가 최우선 지표**. 시나리오는 다중 표적을 포함하며, 그 중 **선택된
   하나의 표적(Selected Target)**을 얼마나 안정적으로 유지·추적하느냐로 성공을 측정한다.
   전체 탐지 확률 같은 지표는 보조적.
2. 사용자는 탐지·페어링·추적·분류 등 DSP 스테이지를 Python 클래스로 구현해 제출한다.
   개별 스테이지만 교체하거나 여러 스테이지를 동시에 실험 가능. 모든 교체안은
   **같은 선택 표적 추적 시나리오에서 동일한 메트릭으로 비교**된다.
3. 시뮬 자체의 물리 모델(레이더 방정식, 레이트레이싱, 클러터, 멀티패스, 포지셔너 동역학 등)도
   독립적으로 검증되어, "시뮬이 이상해서 DSP가 틀려 보이는" 상황을 배제한다.

### 추적 레이더(Tracking Radar)의 기본 전제

본 Workbench가 검증하는 시스템은 다음 특성을 가진다:

- **Closed-Loop Tracking**: EKF 추적 결과를 포지셔너(안테나)에 피드백하여
  안테나가 선택 표적 방향으로 자동 회전. 포지셔너 동역학(속도/가속 제한) 때문에
  완벽히 즉시 따라가지는 못하며, 이 지연 자체가 성능 요소가 됨.
- **멀티 트래킹 + 단일 포커스**: Tracker는 시나리오 내 **모든 표적에 대한 트랙을 유지**하되,
  포지셔너 제어·평가 메트릭·UI 강조는 **선택 표적**에 집중.
- **선택 표적은 변할 수 있음**: 시나리오 메타에 기본값이 있고, Run에서 덮어쓸 수 있고,
  (MVP+α) 런타임에 3D 뷰에서 클릭으로 바꿀 수 있음.
- 🆕 **두 레이어 시간 제어** (v0.15) — Simulation Clock (Start/Pause/Stop + Speed ×1/2/4/8)
  와 Target Run Clock (Run/Pause/Stop)이 독립된 레이어로 분리. Sim 시간이 모든 레이더·환경
  물리의 기반이며, Target Run은 표적 trajectory 재생만 제어.
- **Single Command Path** (v0.14) — 포지셔너 목표 각도는 `PositionerCommand` 타입으로만
  설정 가능. 정상 경로는 Pipeline → Tracker → `PositionerCommand(source=TRACKER)`.
  GT나 Scenario에서 포지셔너로 가는 직통 경로 없음 — 타입 시스템으로 강제.
- 🆕 **두 Workspace 구조** (v0.19) — 단일 프로그램이지만 **Editor Workspace**(자원 편집·조립)와
  **Simulator Workspace**(실행·평가)로 UI를 분리. Workspace는 DockLayout·Toolbar·Command Set을
  독립 구성하며 상태 보존·전환 가능. Mode(DSP/NN)는 Simulator Workspace 안의 하위 개념.
  상세: [10_workspaces.md](10_workspaces.md).
- 🆕 **자원 참조 구조 + 재현성** (v0.20) — Map·Radar·Targets는 독립 자원으로 라이브러리에 저장,
  Scenario는 ID + content hash로 참조. 자원 수정해도 과거 Run 재현 가능 (Run Manifest에
  자원 hash 기록, 불일치 시 경고). 다른 PC 재현용 **Reproducibility Bundle** export/import 지원.
  상세: [10 § 10.9–10.11](10_workspaces.md#109-자원-저장-구조--참조-기반-v020).
- 🆕 **단일 워크스페이스 기준 좌표** (v0.21) — 워크스페이스의 단일 Map이 절대 기준점 (Origin 불변).
  WGS84 + ENU + 명시적 vertical reference (egm96/msl/ellipsoid). DEM 기본 EGM96 가정,
  bilinear 샘플링 표준. **Coherence Validator** 가 자원 변경 시점마다 일관성 검증.
  이전 프로젝트의 "건물 뜸·해안선 불일치" 문제 근본 해결.
  상세: [11_coordinate_systems.md](11_coordinate_systems.md).
- 🆕 **정적 배치 vs 동적 운동 분리** (v0.21) — 모든 자원의 위치는 `base_*` (Editor 정적)과
  `current_*` (Sim Running 동적)로 분리. **MotionKind 5 카테고리** (FIXED_GROUND, GROUND_VEHICLE,
  SURFACE_VESSEL, FLOATING_STATIC, AIRBORNE)로 운동 종류 명시. 해상 자원은 wave 응답으로
  출렁임. 건물은 **anchor 시스템** (BASE_TO_TERRAIN/EXPLICIT_ALT/FLOOR_AT_MSL/TERRAIN_OFFSET)
  으로 자동 정합. **MVP에서 표적 trajectory 편집 GUI 제외** (CSV import만).
  상세: [12_placement_and_motion.md](12_placement_and_motion.md).
- 🆕 **자체 규격 지형 + 편집 도구** (v0.22) — 외부 DEM은 import 소스, 시뮬은 자체 규격
  (`terrain.npz` — 격자 + `land_mask`). DEM의 부정확한 해저 z 누설 차단. Editor에서 **Land/Sea
  Mask Brush + Spot Edit**로 사용자 편집 가능 (Smooth는 MVP 후). Land/Sea 구분 4방식 사용자 선택
  (자동/Nodata/외부 해안선/모두 육상). 원본 DEM은 `source/`에 보관 — 재변환 가능.
  상세: [11 § 11.10 Workbench Native Map Format](11_coordinate_systems.md#1110-workbench-native-map-format-v022-신설),
  [12 § 12.11 지형 편집 도구](12_placement_and_motion.md#1211-지형-편집-도구-editor-workspace-v022).
- 🆕 **사실적 표적 동역학** (v0.27) — 추적 알고리즘 검증의 신뢰도 위해 표적이 실제처럼 거동.
  단순 trajectory 보간 폐기, **trajectory = reference, 실제 = 동역학 적분**. MotionKind 5→7
  확장 (AIRCRAFT, POWERED_FLIGHT, BALLISTIC 신설). Level 1 MVP = 3DOF + 외력 모델
  (gravity, drag, lift, thrust, PD control). RK4 적분. AIRCRAFT는 max_climb_rate 등 동역학
  한계 자동 적용. BALLISTIC은 trajectory 무시 (초기 조건만). Level 2 (6DOF 자세 동역학)는 MVP+α.
  상세: [14_dynamics_model.md](14_dynamics_model.md).
- 🆕 **플랫폼 다양화** (v0.18) — 레이더는 Maritime(함선) 또는 Fixed Ground(건물/타워/산정상)
  플랫폼에 설치. 설치는 Scenario 준비의 필수 게이트 (Installation 화면). 플랫폼마다 운동
  모델이 다르며 (`sea_state` / `stationary`) 설치 위치에 따라 DEM 차폐·가시 영역이 결정됨.
  "자함(ownship)"은 Maritime Platform의 관습적 별칭으로 유지.
  상세: [09_radar_platforms.md](09_radar_platforms.md).
- **GT Isolation** (v0.14) — DSP Plugin은 Ground Truth 접근 불가 — Contract 타입에 GT 없음
  (Level 2) + Plugin 코드 정적 스캔으로 의심 심볼·파일 접근 차단(Level 3) + Run 후 휴리스틱
  오염 검증. 상세: [03 § 3.5.1d](03_data_model.md#351d-gt-격리-강화-v014), [06 § 6.3](06_topics.md#63-테스팅-전략).

### 비슷한 참고 제품 (아날로지)

이런 느낌이라고 보면 됨 — 하나에 완전히 맞아떨어지는 기존 제품은 없음:

- **MATLAB Radar Toolbox + Simulink** 의 검증 루프 (단, 오픈 가능하고 플러그인 교체가 쉬운 버전)
- **CARLA/Gazebo** 같은 시뮬-검증 통합 툴의 레이더 버전
- **VS Code**의 플러그인/레이아웃 철학 (패널/팔레트/도킹)

---

## 1.2 MVP 정의 — "첫 동작 가능"의 의미

✅ **Decided**

> **MVP = 다중 표적 시나리오에서 선택 표적 하나를 EKF+포지셔너로 안정 추적 +
> Tracker Plugin 교체 시 추적 성능 비교가 가능한 상태.**
> v0.16~v0.35 계획서 기반으로 신규 구현.

### MVP에 들어가는 것 ✅

| 영역 | MVP 범위 |
|---|---|
| 레이아웃 | QMainWindow + QDockWidget, 기본 3~4개 패널 배치 |
| 툴바 | 기본 Command Registry, 정적 툴바 (커스터마이저블은 최소) |
| 커맨드 팔레트 | Ctrl+Shift+P, 기본 몇 개 명령 |
| 시나리오 | 기존 `scenarios/*.csv` + `scenario.toml` 로드, 재생(play/pause/seek) |
| **운용 모드** | **DSP 모드(기본) + NN 개발 모드(구조)** — 메뉴로 전환 |
| **RadarModel** | **FMCW Triangle 1종** (`fmcw_triangle_v1`) — 상세: [08](08_radar_waveforms.md) |
| **선택 표적 지정** | 시나리오 기본값(`primary_target_id`) + Run 설정에서 덮어쓰기 |
| **멀티 타겟 트래킹** | 모든 표적에 대한 트랙 유지 (기본 EKF), **선택 표적에 메트릭 집중** |
| **포지셔너 Closed-Loop** | 선택 트랙 방향으로 포지셔너 자동 회전 (동역학 제한 반영) |
| **함선 자세 (roll/pitch)** | 🆕 Sea State 기반 간단 sinusoidal, 파도에 의한 흔들림 |
| **RCS aspect 의존** | 🆕 SimpleAspectRCSModel (방향에 따른 RCS 변동) |
| **안테나 사이드로브** | 🆕 sinc² 기본 가정 (-13.3dB 첫 사이드로브), 멀티 타겟 오염 시뮬 가능 |
| **자함 동요** | 🆕 함선 자세와 동일 모델 재사용, Positioner에 성분 합산 |
| 3D 뷰 | 기존 `radar_viewer_3d` 이식, 선택 표적 강조 표시, 함선 roll/pitch 애니메이션 |
| FFT 패널 | 기존 `data_panel`에서 FFT 부분만 분리·이식 |
| DSP 플러그인 | Detector / Pairing / Tracker 중 하나 교체 가능 |
| 평가 Run | 실행→추적 메트릭 산출→저장 |
| **추적 메트릭** | track_continuity, lock_time, track_id_switches, 선택 표적 RMSE |
| **NN 모드: Step 1 (Dataset Extraction)** | 🆕 SampleSpec · Dataset Variant · 배치 실행 · HDF5 저장 |
| **NN 모드: Step 2 (NN Evaluation)** | 🆕 `<nn_file>.py` 로드 · Training/Dev/Test error (Bayes는 고급 옵션) · Variant 격자 진단 |
| **구현된 NN (MVP 내)** | Pairing NN **1개** (Wave 1) — 다른 NN은 미래 |
| **Program Session ≠ Run** | 🆕 환경 상시 동작, Run은 표적 재생 구간 (IDLE/RUNNING/PAUSED/ENDED) |
| **두 레이어 시간 제어** | 🆕 Simulation Clock (Start/Pause/Stop + ×1/2/4/8) + Target Run (Run/Pause/Stop) 분리 (v0.15) |
| **Run 제어 버튼** | 🆕 Run/Pause/Stop — Stop 시 저장 여부 다이얼로그 |
| **방향키 포지셔너 조작** | 🆕 AUTO/MANUAL 토글 + 수동 중에도 시뮬 진행, 초기 위치 잡기용 |
| **Stage I/O 실시간 + CSV Export** | 🆕 Probe 시스템 확장, 각 스테이지 입출력 UI 표시 + CSV/HDF5 다운로드 |
| **GT 격리 강화** | 🆕 Level 2 구조 분리 + Level 3 정적 스캔 (Plugin Manager 로드 시 경고, 공식 Run 시 거부) |
| **플랫폼 다양화** | 🆕 Maritime(함선) + Fixed Ground(건물·타워·산정상) — 운동 모델 2종(sea_state/stationary), DEM 차폐 간단 LOS (v0.18) |
| **Installation 화면** | 🆕 Scenario 로드 후 필수 게이트 — Preset 선택, DEM 위 위치 지정, 차폐 Preview (v0.18). Editor Workspace의 Scenario Composer 안으로 통합 (v0.19) |
| **두 Workspace 구조** | 🆕 Editor + Simulator 분리 (v0.19). Editor는 MVP에서 ResourceBrowser + Scenario Composer 뼈대만, 풀 편집 기능은 MVP 후 |
| **자원 참조 구조** | 🆕 Map·Radar·Targets 독립 저장, Scenario는 ID + hash로 참조 (v0.20) |
| **재현성 보장** | 🆕 Run Manifest에 자원 content hash 기록, 과거 Run 재실행 시 hash 검증 + 경고 (v0.20) |
| **Reproducibility Bundle** | 🆕 Scenario/Run을 단일 `.scnbundle`/`.runbundle` 파일로 export → 다른 PC에서 Import로 재현 (v0.20) |
| **단일 좌표 기준** | 🆕 Workspace는 단일 Map이 절대 기준, WGS84+ENU+명시적 vertical reference (egm96 기본). DEM bilinear 샘플링 (v0.21) |
| **Coherence Validator** | 🆕 자원 배치/저장/Sim 전환 시 일관성 검증 5종 — 건물·해안선·DEM 정합 (v0.21) |
| **정적/동적 위치 분리** | 🆕 base_* (Editor)와 current_* (Sim Running) 분리, MotionKind 5종, 해상 wave 응답 (v0.21) |
| **건물 Anchor 시스템** | 🆕 BASE_TO_TERRAIN 기본 — DEM 자동 샘플링으로 건물 정확 부착, 4가지 mode (v0.21) |
| **Antenna Model 일반화** | 🆕 파라볼릭 + 평면 어레이 (array factor) + 모노펄스 4채널 (Σ/Δaz/Δel/Δ²). MIMO·DBF는 MVP 후 (v0.25) |
| **Radar Editor 통합** | 🆕 안테나 타입 드롭다운, Beam Pattern Preview, 4종 Preset (v0.25) |
| **Editor Workspace 레이아웃** | 🆕 Activity Selector(5종) + 탭 + Resource Browser 상시 사이드바. Phase A 핵심: Composer + Radar Editor + 전환 (v0.26) |
| **Scenario Composer** | 🆕 References 블록 + Installation 인라인 + Validation 자동 실행 (v0.26) |
| **Map Editor 경량** | 🆕 Pan/Zoom + Land/Sea Brush + Spot Edit + **Flatten Area** + Add Building + DEM Import (v0.26 통합, v0.33 Flatten) |
| **사실적 표적 동역학** | 🆕 trajectory=reference, 실제=동역학 적분 (gravity+drag+lift+thrust+PD). MotionKind 5→7. AIRCRAFT max_climb_rate 등 자동 적용. Level 1 MVP, 6DOF는 MVP+α (v0.27) |
| **표적 Preset 라이브러리** | 🆕 9종 (fighter_jet/airliner/missile_cruise/missile_ballistic/drone/artillery_shell + 기존 함정/건물) (v0.27) |
| **크로스 플랫폼** | 🆕 Win/Linux/Mac 모두 명시적 지원 (v0.27 Q-P1 결정) |
| **시각화 스택 (하이브리드)** | 🆕 pyqtgraph (데이터 패널) + PyVista (3D Scene View). VTK는 PyVista 의존성으로 자동 (v0.28 Q-P2 closed) |
| **대기 모델 (3측면)** | 🆕 시각(fog/sky) + 동역학(ISA air density) + 전파(rain attenuation). plan/15 신규 (v0.28 Q-A1 closed) |
| **Simulation Domain** | 🆕 Map(DEM 정밀) + SimulationDomain(시뮬 전체) 분리. Map 밖은 OutsideEnvironment 정책 (open_sea 기본). 레이더 빔이 Map 넘어가도 안전 (v0.29) |
| **Two-ray multipath** | 🆕 Sea bounce (해상 시나리오 핵심). Toggle 가능 (v0.34, 베이스라인 보강) |
| **Multi-scatterer 표적 + Glint** | 🆕 표적이 3~5 reflector로 구성, monopulse glint 자동 발생. 표적 Preset 9종에 scatterer 분포 (v0.34) |
| **EKF + UKF 선택 가능** | 🆕 Editor에서 드롭다운 선택. Stone Soup 호환 (v0.34) |
| **GNN 다중 표적 데이터 연관** | 🆕 Hungarian assignment. 다중 환경에서 단일 표적 추적 (v0.34) |
| **Atmospheric refraction (4/3 earth)** | 🆕 장거리 추적의 기본 (v0.34) |
| **OS-CFAR (CA-CFAR와 선택)** | 🆕 클러터 환경 표준 (v0.34) |
| **오픈소스 (Apache 2.0)** | 🆕 GitHub public repo, 적극 커뮤니티 권장. 17 open_platform.md 신규 (v0.35) |
| **DLC 시스템 (`.trsim-pkg`)** | 🆕 알고리즘·자원·시각화 패키지 install. VS Code Extension 모델 (v0.35) |
| **Plugin SDK** | 🆕 Core에 포함 (`trsim.sdk`). Plugin Protocol + Builder + Validator (v0.35) |
| **PackageManager** | 🆕 install/uninstall/list/load. ~/.trsim/packages/ 관리 (v0.35) |
| **자체 규격 지형 (Workbench Native)** | 🆕 외부 DEM은 import 소스, 시뮬은 `terrain.npz` (격자 + land_mask). 해상 영역의 부정확한 z 차단 (v0.22) |
| **지형 편집 도구 (경량)** | 🆕 Editor에서 Land/Sea Mask Brush + Spot Edit (v0.22). 지형 Smooth는 MVP 후 |
| **해수면 파도 애니메이션** | 🆕 Sim RUNNING 중 해수면 sinusoidal 출렁임 시각화 (v0.21) |
| **표적 궤적 편집** | ❌ MVP 제외 — CSV import만, 메타 편집·시각화는 가능. GUI 편집은 MVP 후 (v0.21) |
| 물리 검증 | 프레임워크 뼈대 + 회귀 테스트 2~3개 (추적 기여도 높은 영역 우선) |

### MVP에 들어가지 않는 것 ❌

| 영역 | 미래로 미룸 |
|---|---|
| 완전히 커스터마이저블 툴바 | 사용자가 드래그로 버튼 추가/제거 |
| 디버거급 타임라인 스크럽 | 프레임 간 이동하며 중간값 비교 |
| 전체 물리 영역 검증 스위트 | 모든 영역 자동 회귀 테스트 |
| 사용자 정의 물리 모델 플러그인 | Environment Contract 공개 — **영구 제외** |
| **HIL 통합** (v0.38) | DUTAdapter Protocol + TCP/JSON 기본 — Phase 8.1 MVP HIL. 상세: [18](18_hil_integration.md) |
| AWG HIL 확장 | Spectrum/Keysight 등 vendor 어댑터 — Phase 8.3 |
| 외부 언어 플러그인 | C/C++/MATLAB — 인터페이스만 |
| 다중 사용자/샌드박싱 | 비신뢰 환경 대응 |
| **런타임 표적 선택 전환** | 3D 뷰에서 클릭해서 선택 표적 변경 (MVP+α) |
| **추가 NN 구현** | Tracker NN, Detector NN, AngleEstimator NN, Classifier NN 등 |
| 레이더 파형 확장 | CW, Hybrid, Pulse 등 — 상세: [08](08_radar_waveforms.md) |
| 함선 3D 기반 RCS (고정밀) | PO/SBR 기반 MeshRCSModel — MVP+α 후보. MVP는 [14 § 14.10 ExtendedTarget](14_dynamics_model.md) (multi-scatterer + glint, v0.34) 가 차별점 핵심 |
| **고급 물리 6개 Suite** | Weather / Sea Clutter / Advanced RF / Interference / Target Signature / RF Hardware — 상세: [06 § 6.8](06_topics.md#68-deferred-physics--미래-확장-영역) |

### MVP 완료 기준 (Definition of Done)

다음 사용자 여정이 **전부 막힘없이 동작**하면 MVP 완성:

```
1. Workbench 실행 → 기본 레이아웃이 뜬다
2. 커맨드 팔레트 → "Open Scenario" → B_Conflict 선택 (2척 시나리오)
3. 3D 뷰에 지형·건물·두 척 함선이 로드된다
   → 시나리오 기본 `primary_target_id` 에 따라 한 척이 강조 표시됨
4. Play 버튼 → 시나리오 재생
   → EKF가 두 척 모두 추적 (멀티 트랙 유지)
   → 포지셔너가 선택 표적 방향으로 자동 회전
   → FFT 스펙트럼이 실시간 갱신, 선택 표적 피크 하이라이트
   → Run Panel에 선택 표적 기준 track_continuity, lock_time 실시간 표시
5. 커맨드 팔레트 → "Register Plugin" → 예제 Tracker.py 선택
6. "Run Evaluation" → 내 Tracker로 한 번 재생
7. Run 결과 패널에 선택 표적 추적 메트릭이 뜬다
   → 기본 EKF Tracker 결과와 내 Tracker 결과를 나란히 비교
   → 두 척이 교차할 때 Track ID 스위칭이 발생했는지 확인
8. Run 결과 저장, 툴 재시작 후 같은 결과 다시 불러올 수 있다
9. Run 설정에서 primary_target_id를 2번 함선으로 바꾸고 재실행
   → 메트릭이 그 표적 기준으로 바뀌어 나옴
```

9단계 중 **4, 7번이 "추적 레이더 워크벤치"의 핵심**. 이 둘이 동작하지 않으면 MVP 미달.

---

## 1.3 사용자 시나리오 (User Journeys)

### Journey A: "교차 항로에서 Track ID 스위칭을 줄여보자" (MVP 핵심)

**페르소나**: DSP 엔지니어, 1인
**상황**: 기본 EKF Tracker가 두 척 교차 시 Track ID를 잘못 바꾸는 문제를 겪고 있음.

```
1. Workbench 실행
2. Scenario Explorer에서 C_Limit (2척 교차) 더블클릭 → 로드
   → 시나리오 기본 primary_target_id = 1번 함선
3. Play → 기본 EKF로 먼저 돌려봄
   → 두 척이 교차하는 순간 Track ID가 바뀌는 것을 3D 뷰에서 관찰
   → Run 결과: track_id_switches = 3, lock_time 저하
4. Plugin Manager → "새 플러그인" → Tracker Contract 템플릿
   → 내가 개선한 연관 로직을 담은 MyTracker.py 작성 (외부 에디터)
5. Tracker slot에 MyTracker 활성화 → Run 재실행
6. Run 결과 비교 패널: 기본 EKF vs MyTracker
   → track_id_switches 감소, lock_time 개선 확인
7. 다른 교차 시나리오(B_Conflict)로도 돌려 일반화 여부 확인
```

### Journey A': "Pairing 알고리즘을 NN으로 바꿔보자" (MVP+α, Wave 1 핵심)

`target_pairing.c`가 미구현이므로 NN으로 먼저 탐색.

```
1. Scenario B_Conflict 로드, primary_target_id = 1번 함선
2. Dataset Builder: 기본 Pipeline으로 여러 시나리오 실행해 pairing 학습 데이터 수집
3. TF/Keras로 Pairing NN 학습 → weights/v1.npz
4. Workbench가 v1.npz 감지 → Plugin Manager에 MyPairingNN 등록
5. Pairing slot에 MyPairingNN 활성화 → Run
6. 비교: 기본 Pairing vs MyPairingNN, 선택 표적 기준 메트릭
7. 좋으면 NN 구조·가중치를 C로 포팅 후 target_pairing.c 구현
```

### Journey B: "두 Tracker를 선택 표적 기준으로 비교" (MVP 핵심)

```
1. 시나리오 C_Limit, primary_target_id = 1번 함선
2. Batch Run: 같은 시나리오에 기본 EKF로 한 번, MyTracker로 한 번 (같은 시드)
3. Run 목록에서 둘 선택 → "Compare"
4. 비교 패널:
   - 선택 표적의 track_continuity 시계열 오버레이
   - track_id_switches 카운트
   - 포지셔너 지연(Positioner Lag) 비교 — 표적 교차 시 포지셔너가
     얼마나 빠르게 회복했는지
   - 어느 프레임에서 트랙이 끊겼는지 하이라이트
```

### Journey C: "실패한 프레임 디버깅" (MVP 후반/확장)

```
1. Run 결과에서 "Frame 127에서 False Alarm 발생"
2. 해당 프레임으로 타임 시크
3. Probe 패널에서 그 프레임의 스펙트럼·CFAR threshold·Peak 리스트를 단계별 확인
4. "내 Detector는 threshold를 너무 낮게 잡고 있음" 발견
```

### Journey D: "회귀 재현" (MVP 후반/확장)

```
1. 지난주 Run에서 버그 발견 → 스냅샷이 이미 저장되어 있음
2. 오늘 코드 수정 후 "Replay Run #42" 명령
3. 동일 시나리오·동일 시드·동일 플러그인 버전으로 재실행
4. 결과가 기대대로 개선됐는지 diff로 확인
```

### Journey E: "시뮬 물리 모델 자가 검증" (개발자=나 전용, MVP 동반)

```
1. 내가 해면 클러터 모델을 수정함
2. Physics Validation 패널에서 "Run Sea Clutter Regression"
3. Golden Dataset(지난달 저장)과 현재 출력 비교
4. 차이가 허용 범위 내이면 ✓, 아니면 ✗
5. ✗면 "이건 버그인지, 의도된 모델 개선인지" 판단 후 골든 갱신 여부 결정
```

### Journey F: "물리 건전성 게이트" (모든 DSP 평가 시 자동)

```
1. 사용자가 DSP 평가 실행
2. Run 시작 전, Workbench가 자동으로 시나리오에 대한 건전성 체크 수행
    - 스펙트럼 노이즈 바닥이 정상 범위?
    - 에너지 보존?
    - GT 라벨 개수가 예상 범위?
3. 문제 있으면 사용자에게 경고 — "시뮬 자체가 이상할 수 있으니 결과 해석 주의"
4. OK면 평가 진행
```

---

## 1.4 In / Out of Scope (범위 경계)

### ✅ In Scope (MVP)

- Python `.py` 플러그인 기반 DSP 검증
- RadarPipeline의 6개 스테이지(TX/RX/Detector/Pairing/Tracker/Positioner) 개별/전체 교체
- 시나리오 CSV 기반 재생 (기존 포맷)
- 3D 시각화 (지형, 건물, 함선, 빔, 표적, 탐지 오버레이)
- FFT 스펙트럼·각도·트랙 시계열 시각화
- 평가 Run 저장/로드/비교
- 물리 모델 자가 검증 프레임워크 (뼈대)
- IDE 스타일 UI (도킹, 팔레트, 툴바)

### ✅ In Scope (MVP 이후)

- 스테이지별 타임라인 디버깅 (Probe 시스템 심화)
- 물리 영역 전체 회귀 테스트 스위트
- 회귀 스냅샷 포맷 표준화 및 재실행 UI
- 플러그인 마켓플레이스 느낌의 Preset 관리
- 설정 영속화 (Workspace, 기본 경로, 단축키 재매핑)

### 🔒 Out of Scope (영구 제외)

- **사용자 정의 물리 모델 플러그인**: 시뮬은 개발자가 관리하는 "진실"로 둠. 사용자가 물리 모델까지 바꿀 수 있으면 "검증 워크벤치"가 아니라 "또 하나의 모델링 툴"이 됨 — 정체성이 흐려짐
- **비신뢰 사용자 대응 샌드박싱**: 현재는 개인/소규모 팀 범위. 외부 배포 시점에 재검토
- **모바일/웹 UI**: 데스크톱 전용
- **실시간 하드웨어 연결 (MVP 시점)**: HIL 통합은 **MVP+α (Phase 8)**, MVP 코어는 SIL만. SignalSink·DUTAdapter 인터페이스는 Phase 2부터 정의됨 ([18](18_hil_integration.md))
- **GPU 가속 신호처리**: 필요해지면 검토, MVP는 NumPy 중심

### 🔒 Out of Scope (도메인 제외) — 베이스라인 점검 결과 (v0.34)

**16 § 16.5** 의 의도적 제외 5종. 우리 niche(추적 레이더 단일 표적 + DSP↔NN IDE)와 다른 영역으로, MATLAB·Stone Soup·RadarSimPy를 권장:

- **STAP** (Space-Time Adaptive Processing) — 공중·우주 레이더 영역. 사용자는 MATLAB Phased Array Toolbox 사용
- **Massive MIMO / Hybrid beamforming** — 5G/SATCOM 통신 영역
- **SAR / ISAR** — Synthetic Aperture 영상 도메인
- **PHD / GM-PHD / LMB / GLMB** — Random Finite Set 다중 표적 추적 (Stone Soup 풍부)
- **RIS** (Reconfigurable Intelligent Surface) — 신기술 통신 영역

### ⏳ TBD (의사결정 필요)

- **배포 방식**: 소스 / PyInstaller / Docker → 비신뢰 환경 배포 시점에
- **저장 포맷**: JSON / HDF5 / Parquet → 03 데이터 모델에서 제안

---

## 1.5 성공의 정의 (프로젝트 수명 기준)

단기(MVP 완료 시):
- 내가 만든 DSP 3~5개를 **플러그인 교체 방식**으로 비교 평가할 수 있다
- 내가 물리 모델을 수정했을 때 **어느 영역이 회귀했는지 자동 감지**된다
- **GitHub public repo + 오픈소스 인프라** (Apache 2.0, README, CI) 갖춤

중기(MVP+6개월):
- 팀원 2~3명이 같은 툴을 써서 각자 DSP를 제출·비교
- 물리 모델 검증 스위트가 최소 5개 이상의 주요 영역에서 돌아감
- **외부 기여자 첫 PR 머지** (Issue·PR 흐름 검증)
- **첫 `.trsim-pkg` DLC 출시** (자체 또는 커뮤니티)

장기(열린 목표) — v0.35 정체성 반영:
- **DLC 에코시스템 활성화** — `awesome-trsim-packages`에 10+ 항목, 학술 인용
- **Stone Soup·MATLAB 비교 demo 공개** — 신뢰도 확보
- **HIL 통합 활성화**으로 펌웨어·하드웨어를 시뮬 루프에 연결한 검증 (Phase 8)
- **AWG HIL** Spectrum/Keysight vendor 어댑터 sample 제공 (Phase 8.3)
- **Core team 3~5명** 구성 (BDFL → 합의 거버넌스)

---

## 1.6 실패의 모습 — 이런 것만 피하자

- 새 프로젝트가 또 God Class가 된다 (`MainWindow`에 1500줄)
- IDE 레이아웃이 예쁜데 실제 DSP 검증이 번거롭다
- 물리 검증 스위트가 만들어지긴 했으나 아무도 돌리지 않는다
- 물리 코드 (ray_tracing, fmcw) 가 분석 공식·문헌값과 어긋남 — 검증 누락
- "이 버튼을 누르면 되지만 그게 어떤 Command인지 알 수 없다" (Command Registry 미통합)

---

## 섹션 상태

- 1.1 정체성 — ✅
- 1.2 MVP — ✅
- 1.3 시나리오 — ✅
- 1.4 범위 — ✅ In / 🔒 Out / ⏳ TBD 표시
- 1.5 성공 정의 — 🟡 (MVP 후 다시 볼 것)
- 1.6 실패 모습 — 🟡

---

👉 다음 섹션: [02_architecture.md](02_architecture.md)
