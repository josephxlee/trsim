# 부록 B. 용어집

**최종 갱신**: 2026-05-02 (v0.40 — Physics Lab 카테고리 신설 — Physics Layer / 9 Test Objects / ParamMetadata / ForceComposition / PhysicsModelProtocol / Validation Bench / 4 시간 모드 / Symbolic Regression 등)

계획서 전반에서 쓰는 용어의 의미를 한 곳에 고정.

---

## Workbench 고유 개념

### Tracking Radar (추적 레이더)

본 Workbench가 검증하는 시스템의 유형. 단순 탐색(Search)이 아니라 **선택한 표적을
계속 따라가는 것**이 운용 목적. 특성:
- Closed-Loop: EKF 추적 결과를 포지셔너(안테나)에 피드백해 자동 회전
- 선택 표적(Primary Target)에 빔·계산·메트릭이 집중
- 다중 표적 환경에서도 선택 표적의 lock 유지가 최우선

→ 프로젝트 정체성: [01 § 1.1](01_vision_scope.md#11-프로젝트-정체성)

### Selected Target / Primary Target

Run 시점에 추적 대상으로 지정된 하나의 표적. 지정 우선순위:
1. Run 설정 덮어쓰기 (`RunConfig.primary_target_id_override`)
2. 시나리오 기본값 (`Scenario.primary_target_id`)
3. (MVP+α) 런타임 UI 클릭

Tracker는 여전히 **모든 표적을 다중 추적**하지만, 메트릭·포지셔너 제어·UI 강조는
선택 표적에 집중됨.

### Closed-Loop Tracking

Tracker 출력 → 포지셔너(안테나) 제어 → 다음 프레임 빔 방향 변경 → 다음 측정 → Tracker 입력,
이 루프가 닫혀 있는 구조. 포지셔너 동역학(속도·가속 한계)이 지연을 만들며, 이 지연 자체가
추적 성능의 구성 요소.

### Track Lock / Lock Time

Tracker가 어떤 표적을 안정적으로 유지하고 있는 상태 = lock.
- `lock_acquisition_time_s`: Run 시작부터 선택 표적을 처음 lock하기까지의 시간
- `longest_lock_s`: 중단 없이 가장 길게 유지된 lock 구간
- `lost_count`: lock이 풀린 횟수

### ID Switch

Tracker가 같은 track id를 다른 GT 표적에 붙이기 시작하는 현상.
멀티 타겟이 공간적으로 교차할 때 발생 가능. Tracker 품질의 핵심 실패 사례.

### Positioner Lag

선택 표적의 실제 방향과 포지셔너가 현재 가리키는 방향의 오차. 동역학 한계, EKF 지연,
처리 레이턴시 등이 원인. 교차 순간에 가장 커짐.

MVP부터 자함 동요(Platform Dynamics) 성분도 Lag에 합산됨 — 포지셔너 명령이 완벽해도
레이더 탑재 함선이 파도로 흔들리면 실제 빔 방향이 흔들림.

### RCS Model / Aspect Angle 의존

표적의 RCS(Radar Cross Section)를 스칼라 값이 아닌 **관측 방향·자세·주파수의 함수**로
다루는 Contract. MVP 기본: `SimpleAspectRCSModel` (측면/전방/후방 기준값을 aspect angle로
보간). 미래: `MeshRCSModel` (3D STL 기반 PO/SBR, Step 4).

→ 상세: [03 § 3.2.3a](03_data_model.md#323a-rcs-모델-자세·각도-의존)

### Ship Attitude (함선 자세)

표적 함선의 roll/pitch/yaw_rate. 파도에 의한 흔들림 때문에 매 프레임 관측 aspect이 변함 →
RCS도 변함. MVP는 Sea State 기반 간단 sinusoidal 모델. Pierson-Moskowitz 등 정밀 파도
스펙트럼은 미래 Weather Suite.

### Platform Dynamics (자함 동요)

레이더 탑재 함선 자체가 파도로 흔들림. 함선 자세(Ship Attitude)와 동일한 모델을
레이더 사이트에 적용. `RadarSite.platform_dynamics` 필드로 토글.

**v0.18 주의**: 이 용어는 Maritime Platform에서만 의미 있음. Fixed Ground Platform에서는
`stationary` 모델이 활성이라 동요 없음. "Platform Dynamics"라는 용어는 그대로 쓰되
"해당 Platform의 Motion Model 출력"으로 일반화 해석.

### Radar Platform (v0.18 신설)

레이더가 설치되는 플랫폼의 상위 개념. 두 MVP 카테고리:
- **Maritime**: 해상 이동 (함선). 기존 "자함(ownship)"이 여기 속함
- **Fixed Ground**: 지상 고정 (건물/타워/산정상을 추상화한 단일 카테고리)

플랫폼마다 Motion Model, 설치 위치, 형상, 차폐 조건이 다름. `RadarPlatform` dataclass로
표현. Scenario의 필수 필드.

→ 상세: [09_radar_platforms.md](09_radar_platforms.md)

### Ownship (자함)

Maritime Platform의 관습적 별칭. 해상 시나리오에서 여전히 "자함"으로 부름.
v0.18에서 용어는 유지하되 Platform 상위 개념의 하위로 재배치.

### Platform Motion Model (v0.18 신설)

플랫폼의 시간 경과에 따른 6자유도 운동을 제공하는 Protocol.
Sim이 RUNNING일 때만 업데이트되며, 출력은 `PlatformPose` (roll/pitch/yaw + velocity).

MVP 제공 2종:
- `sea_state`: Sea State 기반 sinusoidal roll/pitch (Maritime 기본)
- `stationary`: 움직임 없음 (Fixed Ground 기본)

미래: `road_vibration`, `wind_tower_sway`, `flight_path` 등.

### Installation (v0.18 신설)

플랫폼을 DEM 상 특정 위치에 배치하고 안테나 높이·방향을 확정하는 작업·상태.
Scenario 로드 후 Target Run 전에 **필수 게이트**. UI는 Installation 화면 (05 § 5.3.8).

시나리오 파일(`scenario_meta.toml`)에 `[platform]` 섹션이 완비되어 있으면 자동 적용,
아니면 사용자 입력 필요.

### LOS Obstruction (v0.18 신설)

레이더와 표적 사이의 직선 경로(Line-of-Sight)에 지형·구조물이 끼어 차폐되는 현상.
MVP는 DEM 기반 간단 높이 검사 (직선 세그먼트의 각 샘플 점에서 DEM 고도 비교).
풀 LOS 레이트레이싱·회절은 MVP 후 Advanced RF Suite.

### Antenna Sidelobe (안테나 사이드로브)

메인빔 외의 방향에서도 일정 레벨의 송수신이 일어남. 강한 Secondary 표적이 사이드로브로
잡혀 Primary를 오염시키는 현실적 혼선 원인. MVP: sinc² 패턴, 첫 사이드로브 -13.3dB 기본값.

### Deferred Physics / Physics Suite

MVP 범위에서 의도적으로 제외된 물리 요소들을 미래 확장 프로젝트로 그루핑한 것.
6개 Suite: Weather / Sea Clutter / Advanced RF / Interference / Target Signature / RF Hardware.

→ 상세: [06 § 6.8](06_topics.md#68-deferred-physics--미래-확장-영역)

### Workspace (Plugin Workspace)

사용자의 Plugin·Dataset·Run 결과가 모이는 **프로젝트 루트 디렉토리**.
표준 구조는 `plugins/`·`datasets/`·`scenarios/`·`runs/` 서브폴더.
"+ New Plugin" 마법사와 Dataset Builder, Trainer 연결은 이 구조를 전제로 동작하지만,
임의 경로의 Plugin도 "Add Existing"으로 등록 가능.

→ 상세: [05 § 5.3.3](05_ui_ux.md#533-plugin-manager)

### Scope View / Radar POV

3D Scene View의 두 번째 뷰. 포지셔너 보어사이트에서 정면을 바라본 장면.
십자선·빔 폭 원·FOV 원·표적 dot·EKF 명령점(`+` 마커)을 겹쳐 표시.
추적 품질(빔 내 표적 위치, Lag)을 즉시 확인하는 용도.

→ 상세: [05 § 5.3.2](05_ui_ux.md#532-3d-scene-view--3rd-person--scope-pov-이원-구조)

### EKF Command vs Positioner Actual

- **EKF Command**: Tracker가 "선택 표적은 지금 이 방향" 이라고 추정해 포지셔너에게 보낸 명령 각도
- **Positioner Actual**: 동역학 한계(속도·가속)로 실제로 따라간 결과 각도
- **둘의 차이 = Positioner Lag**

Properties 패널과 3D View에서 둘을 구분해 표시.

### New Plugin 마법사

Plugin Manager에서 `+ New Plugin` 버튼으로 시작하는 다단계 프롬프트. Contract 선택 →
NN 여부 → 이름 입력 → 템플릿 파일 자동 생성 → 외부 에디터 호출(선택).
편집 자체는 외부 에디터, Workbench는 등록·감지·검증만 담당.

### Training Target (of Dataset)

Dataset Build Job이 **어느 NN Plugin을 학습시킬지** 명시하는 참조.
`DatasetBuildJob.training_target` 필드로 표현되며 Dataset Manifest에 기록됨.
이로써 "Dataset 생성 → 학습 → 가중치 반영"이 끊김 없이 연결.

### Dataset Variant

같은 태스크에 대해 **물리 조건을 바꿔가며** 만드는 여러 Dataset. 예: Pairing NN에 대해
Variant_A (이상화) / Variant_B (자세만) / Variant_C (사이드로브만) / Variant_D (전부 on).

목적: bias/variance 진단. 각 Variant에서의 성능 차이로 "어떤 물리 현상에서 일반화가
실패하는지" 분리 분석 가능. Curriculum 학습에도 사용.

→ 상세: [07 § 7.4.5a](07_nn_integration.md#745a-dataset-variant--물리-조건별-분리-수집)

### DSP 모드 / NN 개발 모드

Workbench의 두 운용 모드. 명시적 메뉴 전환(`View > Mode`)으로 분리.

- **DSP 모드** (기본): DSP Plugin을 Pipeline에 꽂아 추적 성능 평가. 주 워크플로
- **NN 개발 모드**: 학습 데이터 추출(Step 1) + NN 평가(Step 2). 선택적 진입

DSP 모드에서는 NN 관련 UI가 완전히 숨김. NN 개발자만 후자로 진입.
두 모드는 Workspace 디렉토리(plugins·datasets·runs·scenarios)를 공유.

→ 상세: [01 § 1.1](01_vision_scope.md#두-운용-모드)

### 4-Error 진단 (Bayes / Training / Dev / Test Error)

NN 모드 Step 2의 핵심 도구. ML 표준 진단 기법으로, 네 error 간 gap으로 문제 원인을 분리:

- `Training − Bayes` = **Avoidable bias** (모델 용량·학습 부족)
- `Dev − Training` = **Variance** (과적합)
- `Test − Dev` = **Data mismatch** (학습 분포 ≠ 실전)

Bayes error는 선택적 — 일반적으로 미지수이며, 기본은 3-error(Training/Dev/Test)만 계산.
고급 모드에서 Variant A 성능을 Bayes 근사로 사용 가능.

→ 상세: [07 § 7.6.0](07_nn_integration.md#760-step-2의-핵심-개념--4-error-진단)

### Step 1 / Step 2 (NN 모드 내부)

NN 개발 모드의 두 단계:

- **Step 1 — Dataset Extraction**: 새 NN의 학습 데이터를 Pipeline Run 경유로 추출
- **Step 2 — NN Evaluation**: `<nn_file_name>.py` + weights로 4-error 분석

Step 1과 2는 UI에서 별도 화면, 순차적으로 사용.

### Program Session

Workbench 앱이 실행된 시점부터 종료까지의 생애주기.

Program Session은 **컨테이너** 개념이다. 그 안에서 **Simulation Clock**이 Start/Pause/Stop으로
제어되고, 또 그 안에서 **Target Run**이 반복 실행될 수 있다.

v0.14에서는 Session = 시뮬 시간 흐름 으로 혼용했으나, v0.15에서 Simulation Clock을 별도
레이어로 분리하면서 Session은 순수히 "앱 인스턴스 생애주기"를 의미한다.

### Simulation Clock (v0.15 신설)

시뮬 시간 자체를 제어하는 **Layer 1 (바깥 레이어)**. 환경·레이더·Pipeline·포지셔너 동역학의
기반 시간.

- 상태: `STOPPED` / `RUNNING` / `PAUSED`
- 제어: `Sim Start` / `Sim Pause` / `Sim Stop`
- 속도: `SpeedMultiplier` (×1/2/4/8), 실제 달성 배수 별도 표시

Sim Clock이 PAUSED이면 레이더 물리·환경 업데이트가 멈추며, 이 상태에서 사용자 방향키
입력은 **버퍼링** 후 재개 시 일괄 반영.

→ 상세: [03 § 3.5.0b](03_data_model.md#3505b-두-레이어-시간-제어-v015-재설계)

### Speed Multiplier (v0.15)

시뮬 시간이 wall clock 대비 몇 배로 진행할지. ×1은 real-time, ×2 이상은 "시간 와프" —
레이더 계산을 모두 수행하되 wall clock보다 빠르게.

내부 틱 간격은 유지하므로 수치 정확도에 영향 없음. 다만 계산량이 많으면 설정 배수를
달성 못 할 수 있음 (UI에 actual multiplier 병기).

### Target Run (v0.15에서 Layer 2로 명확화)

표적 trajectory 재생을 제어하는 **Layer 2 (안쪽 레이어)**. v0.14의 "Run"이 이 개념에
해당 (용어 연속).

- 상태: `IDLE` / `RUNNING` / `PAUSED` / `ENDED`
- 제어: `Target Run` / `Target Pause` / `Target Stop`
- Sim Clock이 PAUSED이면 Target RUNNING 상태여도 실제 trajectory는 멈춤 (Sim 시간에 종속)

### 두 레이어 시간 제어 (Two-Layer Time Control)

Simulation Clock (바깥) + Target Run (안쪽)의 독립된 시간 제어 구조. v0.15의 핵심 설계 변경.
Sim은 시뮬 물리의 기반 시간, Target은 trajectory 재생만 관리. 두 레이어를 UI에서도 명확히
분리 표시 (툴바 두 줄, Run Panel의 Time Layers 블록).

### Run (재정의, v0.14)

**표적 trajectory가 재생되는 구간**. Program Session의 시간축 위에서 사용자가 `Run` 버튼을
눌러 시작하고, `Stop` 또는 trajectory 자연 종료로 끝남.

- IDLE / PAUSED / ENDED 상태에서는 표적 정지 (마지막 또는 시작 위치)
- RUNNING 상태에서만 표적이 움직이고 메트릭 기록

즉 "시뮬 실행" 과 "Run" 은 다른 개념이다. 시뮬은 Session 내내, Run은 trajectory 재생 중만.

### Run State

Run의 4개 상태: **IDLE** (표적 정지, Run 시작 대기) / **RUNNING** (표적 재생 중) /
**PAUSED** (표적 일시 정지, 환경은 진행) / **ENDED** (trajectory 자연 종료, 표적 끝 위치).

상태 전이는 사용자 버튼(`▶ Run`, `⏸ Pause`, `⏹ Stop`) 또는 trajectory 종료로 발생.

### Pre-Run

Run 시작 전 IDLE 상태에 대한 별칭. Scenario 로드됨, 표적 정지 상태로 배치됨.
사용자가 FFT 관찰·방향키 포지셔너 조작·파라미터 튜닝 가능.

### PositionerCommand / CommandSource / Single Command Path

포지셔너의 목표 각도를 설정하는 유일한 타입. `source` 필드로 출처 구분:

- `TRACKER`: 자동 추적 (정상 경로, Pipeline 거침)
- `MANUAL_USER`: 사용자 방향키 수동 조작
- `INITIAL_SCAN`: Run 시작 자동 배치, 스캔 패턴

TRACKER 소스는 `source_track_id`와 `source_frame_id`를 필수로 동반하며, Run 후 검증에서
실제 그 프레임 Tracker 출력에 해당 트랙이 있었는지 확인됨. GT·Scenario에서 포지셔너로 가는
직통 경로는 타입 시스템으로 차단됨.

→ 상세: [03 § 3.5.1c](03_data_model.md#351c-포지셔너-지휘-경로의-유일성-single-command-path)

### AUTO / MANUAL 포지셔너 모드

Run 중 포지셔너 제어 방식. `M` 키로 토글:

- **AUTO**: Tracker 출력이 자동으로 포지셔너에 전달 (기본)
- **MANUAL**: 사용자 방향키(`←→↑↓`)로 직접 조작. 메트릭에 수동 구간 마킹

IDLE/PAUSED 상태에서는 항상 MANUAL. RUNNING 중에만 두 모드 구분 의미 있음.

### GT Isolation (3-Level)

DSP Plugin이 Ground Truth에 접근하지 못하도록 하는 다중 방어선:

- **Level 2 (구조)**: Contract 타입에 GT 없음 — Plugin이 받는 객체에 GT 정보 불포함
- **Level 3-1 (정적 스캔)**: Plugin 로드 시 소스 AST 분석으로 금지 심볼·파일 접근 차단
- **Level 3-2 (Command Lineage)**: Run 후 모든 PositionerCommand의 출처 검증
- **Level 3-3 (Contamination Heuristic, MVP+α)**: 결과 통계에서 의심 패턴 플래그

Level 4(샌드박스)·Level 5(별도 프로세스)는 DX/성능 비용으로 MVP에서 지양.

→ 상세: [06 § 6.3.6a](06_topics.md#636a-plugin-격리-검증--gt-isolation--command-lineage-v014-신설)

### Stage I/O Panel

Pipeline 각 스테이지의 입출력을 실시간으로 UI에 표시 + CSV/HDF5 다운로드하는 패널.
Probe 시스템의 사용자 접점. Plugin 디버깅과 DSP 검증의 핵심 도구.

→ 상세: [05 § 5.3.6c](05_ui_ux.md#536c-stage-io-panel--pipeline-각-스테이지-입출력-v014)

---

## 다른 Workbench 고유 개념

### Contract

DSP 파이프라인의 각 스테이지에 정의된 **Python Protocol**.
플러그인이 구현해야 할 메서드 시그니처와 입출력 타입을 명시.
예: `DetectorContract`, `TrackerContract`.

→ 상세: [03 § 3.3](03_data_model.md#33-dsp-pipeline-contract)

### Plugin

Contract를 구현한 **사용자 제출 Python 클래스** 또는 기본 제공 구현체.
기본 플러그인과 사용자 플러그인은 동등하게 취급됨 (원칙 3, [02](02_architecture.md#21-설계-원칙-가장-먼저-합의해야-할-것)).
예: `MyDetector(DetectorContract)`.

### Plugin Ref

한 Plugin의 참조 정보. 파일 경로, 클래스명, 버전, 소스 해시를 담는 불변 객체.
Run 재현성을 위해 **소스 해시**로 무결성 검증.

### Probe

파이프라인의 특정 지점에 부착되는 **관찰점(observation point)**.
매 프레임 값을 캡처 가능. 기본 Probe(시스템 정의) + 사용자 Probe(플러그인 선언) 둘 다 지원.

→ 상세: [06 § 6.1](06_topics.md#61-probe--trace-시스템-깊이-있게)

### Trace

한 Run의 모든 Probe 캡처 결과. 프레임별 TraceFrame의 튜플.
디버깅/재현의 기반.

### Run

한 번의 DSP 평가 실행 단위.
`{시나리오, 플러그인 세트, 설정, 시드}` → `{메트릭, Trace, 로그}`.

### Evaluation

Run이 산출하는 메트릭 계산 과정. `Evaluator`가 GT와 비교해 Pd/Pfa/RMSE 등 산출.

### Ground Truth (GT)

시뮬이 알고 있는 정답. 플러그인은 **볼 수 없음** (정직한 검증 위해 격리).
`GroundTruthLoader`만 접근.

### Golden Dataset

물리 검증용 **저장된 기대값**. 입력+기대 출력+허용 오차+참고문헌을 담은 TOML.
회귀 테스트의 기준.

→ 상세: [06 § 6.3.5](06_topics.md#635-golden-dataset-관리)

### Physics Gate

DSP 평가 Run 시작 **전에** 수행하는 경량 건전성 체크.
"시뮬 자체가 이상해서 DSP가 틀려 보이는" 상황 방지.

→ 상세: [06 § 6.3.6](06_topics.md#636-physics-gate--런타임-건전성-체크)

### Scenario

하나의 시뮬레이션 단위. 지형/건물/레이더 배치/표적 경로/FMCW 설정 등을 담은 불변 문서.
`scenario.toml` + 참조된 CSV 파일들로 구성.

### Workspace

사용자의 **IDE 상태 영속화** 단위.
도킹 배치, 열린 시나리오, 등록된 플러그인 등.
`~/.workbench/workspaces/*.toml`에 저장.

### Command

Workbench에서 수행할 수 있는 하나의 액션. `id`, `title`, `execute()` 함수를 가짐.
툴바/메뉴/팔레트/단축키가 모두 Command 참조.

→ 상세: [05 § 5.4](05_ui_ux.md#54-command-registry-설계)

### Command Palette

Ctrl+Shift+P로 여는 검색 가능한 명령 목록. VS Code 스타일.

### Event Bus

앱 전반 pub/sub 메커니즘. Qt Signal과 구분되며, Domain/App 계층이 Qt를 모르도록 격리.

→ 상세: [03 § 3.7](03_data_model.md#37-event-bus-메시지-카탈로그)

### StageSlot

Pipeline 안에서 한 스테이지가 차지하는 자리. `{slot_id, contract, required, default_plugin}`으로 정의.
옵셔널 스테이지(Classifier)와 스테이지 분리(Receiver → AngleEstimator)의 기반.

→ 상세: [07 § 7.2](07_nn_integration.md#72-stage-slot-시스템-pipeline-확장)

### NN Plugin

신경망 기반으로 구현된 Plugin. 기존 Contract(Detector, Tracker 등) + `NNPluginMixin`.
Pipeline 입장에서는 일반 Plugin과 동일하게 취급되며, 차이는 학습/시각화 도구가 추가로 인식.

→ 상세: [07 § 7.3](07_nn_integration.md#73-nn-plugin-contract)

### Internal Probe

NN Plugin이 내부 중간값(Activation, Feature Map, Attention 등)을 노출하는 Probe.
일반 Probe와 같은 시스템이지만 NN 디버깅/시각화에 특화.

### SampleSpec

Dataset Builder가 "Probe/GT에서 어떤 필드를 어떤 형태로 추출해 학습 샘플을 만들지" 기술하는 설정.
학습 태스크별(각도 추정, 분류, 추적 등)로 템플릿 제공.

→ 상세: [07 § 7.4.3](07_nn_integration.md#743-automatic-dataset-builder)

### Dataset Builder

여러 Run을 돌려 학습용 HDF5 Dataset을 자동 누적하는 도구.
"Export 데이터" 기능의 자동 모드.

### TF ↔ numpy 이식

TensorFlow/Keras로 학습한 모델을 순수 numpy forward pass로 재구현하는 과정.
두 구현의 출력이 수치적으로 일치하는지 자동 검증 (`workbench-verify-port`).

### Wave 1 / Wave 2 / Wave 3

NN 통합의 단계적 도입. Wave 1(각도 추정 + 분류), Wave 2(페어링), Wave 3(추적 + End-to-End).
복잡도와 데이터 요구가 다른 태스크를 단계적으로 붙임.

### Slot Manifest / Pipeline Manifest

Run 결과에 포함되는, **어느 Pipeline Slot에 어떤 Plugin이 꽂혔는지**의 기록.
각 Slot에 대해 `{plugin_name, version, is_nn, weights_hash, training_dataset_ref}`.
원칙 6 (부분 NN 교체)을 저장소 레벨에서 지원.

→ 상세: [07 § 7.6.4](07_nn_integration.md#764-run-manifest--어떤-스테이지가-nn인가-명시)

### 케이스 0 / 단일 스테이지 교체 (Opt-in)

원칙 6의 기본 워크플로우. Pipeline의 **한 스테이지만** NN으로 교체, 나머지는 전부 기본.
Wave 1 완료 기준의 기준점.
(케이스 A/B/C/D는 이것의 확장: A=다른 스테이지 단일 교체, B=상류 의존, C=상류 NN, D=End-to-End)

### Waveform / WaveformKind

레이더가 방사하는 신호 패턴. 본 프로젝트의 현재 타겟 레이더는 **FMCW Triangle** 단독.
WaveformKind enum은 미래 확장을 염두에 둔 개념이지만 MVP에서는 실질적으로 쓰이지 않으며,
각 RadarModel이 자기가 쓰는 Waveform을 정의하는 방식으로 대체됨.

→ 상세: [08 § 8.1](08_radar_waveforms.md#81-용어-정리-및-오류-교정)

### RadarModel

하나의 레이더 시스템을 표현하는 1급 개념. 사용하는 Waveform, 신호 경로, Pipeline 구조를
정의. MVP에는 `FMCWTriangleRadar` 하나만 존재. Hybrid/Pulse 등 다른 모델은 미래 확장.

→ 상세: [08 § 8.2](08_radar_waveforms.md#82-radarmodel-추상화--미래-확장의-경계)

### Pipeline Graph

RadarModel이 정의하는 Pipeline 실행 구조. 선형 시퀀스가 아니라 **DAG + 피드백 엣지**.
FMCW Triangle은 Up 경로와 Down 경로가 병렬 실행 후 Pairing에서 합류, Tracker 출력은
Target Gate를 거쳐 다음 프레임 Detector로 피드백.

→ 상세: [08 § 8.3.4](08_radar_waveforms.md#834-pipeline-graph-triangle-한-가지)

### Pairing (Triangle Up/Down)

본 프로젝트의 Pairing 정의: **FMCW Triangle의 Up-sweep 피크와 Down-sweep 피크를 매칭**.
거리·속도 분리 목적. 알고리즘 자체가 현재 DSP 펌웨어에서 구현 전 상태이며,
Workbench의 주요 검증 대상 중 하나.

### Signal Path

Pipeline Graph 내의 하나의 신호 처리 경로. FMCW Triangle에서는 Up 램프와 Down 램프
두 개의 Signal Path가 병렬로 존재.

### Target Gate

**멀티 타겟 상황에서 EKF Tracker가 탐지를 엉뚱한 트랙에 연관시키는 것을 방지**하기 위한
Tracker 보조 장치. 이전 프레임의 각 트랙 근처로 다음 프레임의 검색 범위를 좁힌다.

본질적으로 **Tracker 선택에 종속**됨:
- `DefaultEKFTracker`: Gate 필요 (`requires_target_gate = True`)
- NN 기반 Tracker: 보통 Gate 불필요 (모델이 data association을 학습으로 해결)
- 단일 타겟 Tracker: Gate 불필요

활성화 조건 3가지가 AND로 만족되어야 실제 효과: Tracker가 요구 + 사용자가 enable + 활성 트랙 존재.
DSP 펌웨어의 `__USE_TARGET_GATE__` 가드에 대응.

→ 상세: [08 § 8.3.5](08_radar_waveforms.md#835-target-gate의-역할-왜-옵션인가)

### SIL / HIL

- **SIL** (Software in the Loop): 소프트웨어 내부에서 완결. 시뮬이 RX로 바로 전달.
- **HIL** (Hardware in the Loop): 실제 하드웨어 경유. AWG → 실제 ADC → DSP.

MVP는 SIL, 미래에 HIL 확장 여지.

### SignalSink

Receiver 직전 신호 경로의 추상화. SILSink(기본) / HILSink(미래) 구현체로 교체 가능.

---

## v0.27~v0.35 신규 개념

### MotionKind (v0.21 도입, v0.27 확장)

표적·플랫폼의 운동 카테고리. 7종: FIXED_GROUND / GROUND_VEHICLE / SURFACE_VESSEL /
FLOATING_STATIC / AIRCRAFT / POWERED_FLIGHT / BALLISTIC. 각 카테고리는 자체 동역학 모델·자유도·외력 적용 방식을 가짐. 14 § 14.5.

### RigidBodyState (v0.27)

표적 동역학의 6DOF 상태 (위치·속도·자세·각속도). MVP는 자세를 velocity vector로 derived (coordinated flight 가정), Level 2 6DOF는 MVP+α. 14 § 14.3.

### Trajectory Reference (v0.27)

`trajectory.csv`의 의미가 v0.27 이후 **reference**로 재정의. 동역학이 reference를 추적, 실제 거동은 외력·한계 제약 안에서 결정. 비현실 trajectory 입력도 안전.

### AircraftDynamics / PoweredFlightDynamics / BallisticDynamics (v0.27)

motion_kind별 동역학 파라미터 dataclass. Aircraft는 max_climb_rate·bank·load_factor, PoweredFlight은 ThrustProfile, Ballistic은 무동력 (외력만).

### AtmosphereState (v0.28)

대기 상태의 단일 추상 — 시각·동역학·전파 세 측면 모두. visibility/sky/pressure/temperature/rain_rate/refractivity 등 포함. ISA density·rain_attenuation 함수가 사용. 15.

### Refractivity / Effective Earth Radius (v0.34)

대기 굴절 — 빔이 약간 휘어짐. MVP는 4/3 earth radius (Schelleng 1933 표준)로 단순화 — 빔은 직선 + Earth는 4/3배 큰 가짜 Earth. 장거리(>10km) 차폐·horizon 정확도. 15 § 15.5.4, 16 § 16.3.5.

### SimulationDomain (v0.29)

Map(DEM 정밀)과 분리된 시뮬 가능 전체 영역. 레이더 빔이 50km 갈 수 있는데 Map이 10km일 때 처리. Map ⊂ SimulationDomain. 11 § 11.11.

### OutsideEnvironment (v0.29)

Map 밖 영역의 처리 정책 enum: open_sea / open_land / blocked / infinite_plane. `sample_terrain_safe()` 가 Map 안은 정밀 DEM, 밖은 outside 정책 적용.

### Scatterer (v0.34)

표적의 한 reflector. body frame offset + RCS (dBsm). MVP: 점 표적이 아닌 ExtendedTarget의 구성 요소. 14 § 14.10.

### ExtendedTarget (v0.34)

Multi-scatterer 표적 모델 — 3~5 reflector로 표적 구성. 표적 attitude 따라 reflector 회전, 받음 신호는 scatterer 합성. **Glint 자동 발생** — 우리 차별점("단일 표적 추적 안정성")의 핵심 변수. 14 § 14.10.

### Glint (각도 noise / scintillation)

Extended target의 reflector 간 phase 합성으로 도래각이 흔들리는 현상. monopulse error에 노이즈로 작용 → 추적 안정성 저하. σ_glint ≈ L_target / (2√N_scatterers). 14 § 14.10.5.

### Two-ray Multipath (v0.34)

해상에서 직접 경로(LOS) + sea bounce 반사 경로 두 신호의 phase 합성. 거리·고도에 따라 lobing pattern → SNR 변동. 함정 추적의 핵심. Toggle 가능 (multipath_enabled). 08 § 8.5b.1, 16 § 16.3.1.

### UKF (Unscented Kalman Filter) (v0.34)

Sigma point 기반 비선형 추적기. EKF 대비 강한 비선형성(고기동·먼 거리)에서 안정. Stone Soup 호환. Editor에서 EKF/UKF 선택 가능. 03 § 3.2.1j, 16 § 16.3.3.

### GNN (Global Nearest Neighbor) Data Association (v0.34)

다중 표적 환경에서 detection ↔ track 1:1 최적 매칭. Hungarian (scipy.optimize.linear_sum_assignment) 사용. 다중 환경에서 단일 표적 추적 시뮬에 필수. 03 § 3.2.1j, 16 § 16.3.4.

### CA-CFAR / OS-CFAR (v0.34 보강)

CA-CFAR (Cell-Averaging) — 균일 클러터 가정. OS-CFAR (Ordered Statistics) — multi-target/clutter edge robust. v0.34에 OS-CFAR 추가, Editor에서 선택. 08 § 8.5c.

### Apparent Position / Glint Offset (v0.34)

Extended target 받음 신호의 amplitude-weighted center. 실제 표적 중심과 다름 (glint_offset). monopulse가 보는 위치. 14 § 14.10.4.

---

## v0.35 오픈 플랫폼 / DLC 용어

### `.trsim-pkg` (v0.35)

DLC 패키지 형식. zip(또는 디렉토리)에 manifest.toml + plugins/ + resources/ + ui/ + tests/ 묶음. VS Code Extension 모델. 17 § 17.2.4.

### Plugin Manifest (v0.35)

`.trsim-pkg` 의 manifest.toml 메모리 표현. PackageInfo / Compatibility / EntryPoint / PackageDependency / PythonRequires / PackageManifest / InstalledPackage 7개 dataclass. 03 § 3.2.1l, 17 § 17.2.4.

### DLC (Downloadable Content) (v0.35)

VS Code Extension 모델 차용. 알고리즘 + 자원 + 시각화를 묶어 install 가능한 사용자 확장. Apache 2.0 코어 + 자유 라이선스 DLC. 17.

### Plugin SDK Layer / `trsim.sdk` (v0.35)

Domain Layer 위·App Layer 아래에 신설된 안정 API 계층. DLC 작성자에게 Plugin Protocol·Resource 스키마·Package Builder·Test Harness 제공. Domain refactor가 DLC를 깨뜨리지 않게 격리. 02 § 2.6b, 17 § 17.2.6.

### PackageManager (v0.35)

설치된 `.trsim-pkg` 관리하는 App Layer 컴포넌트. `~/.trsim/packages/<id>/` 스캔, manifest 검증, entry_points 등록. 17 § 17.4.2.

### PanelRegistry (v0.35)

DLC가 추가한 UI 패널 등록·조회 컴포넌트 (App Layer). Editor/Simulator UI에 동적으로 노출. 17 § 17.4.4.

### Apache 2.0 (v0.35)

TRsim 코어 라이선스 (Q1-rev). 특허 grant 명시 + DLC 자유 라이선스 호환 + 기업 친화. 17 § 17.2.1.

### DCO (Developer Certificate of Origin)

기여자가 commit message에 `Signed-off-by: Name <email>` 추가하는 가벼운 라이선스 동의. CLA보다 가벼움, Linux/GitHub 표준. 17 § 17.8.

### BDFL (Benevolent Dictator For Now)

프로젝트 창시자가 모든 결정을 단독으로 내리는 거버넌스 단계. v0.35 시작 ~ MVP+α 초기. 그 후 Core team 3~5명으로 진화. GOVERNANCE.md.

### Core Team (v0.35)

Phase 2 거버넌스 — 신뢰 기여자 3~5명 합의 그룹. 6개월+ 활동 + PR 10개+ 머지 등 승격 기준. GOVERNANCE.md.

### awesome-list (v0.35)

DLC marketplace 의 가벼운 시작 형태 — Core repo 안 `awesome-trsim-packages.md` 큐레이션 리스트. Trackers / Detectors / Targets / Visualizations 카테고리. 17 § 17.2.5.

### Stone Soup 호환 (v0.34/v0.35)

추적 framework Stone Soup (Dstl, MIT) 와의 알고리즘 호환. EKF/UKF/GNN 사양이 Stone Soup 동일 알고리즘. DLC adapter 형태로 통합 가능 (MVP+α). 16, 17.

---

## v0.38 HIL 통합 용어

### HIL (Hardware-in-the-Loop) 통합 (v0.38)

실제 하드웨어 (펌웨어·FPGA·DSP 보드 등) 를 시뮬 루프에 직접 연결하여 검증. SIL (Software-in-the-Loop) 외에 v0.38 에서 5번째 차별점으로 추가. 18.

### DUT (Device Under Test) (v0.38)

검증 대상 하드웨어. 외부 신호처리 장치 — C6678 펌웨어, FPGA 보드, DSP 보드 등. TRsim 이 시뮬 신호를 보내고 결과를 받음. 18 § 18.1.

### DUTAdapter Protocol (v0.38)

10번째 Plugin Protocol (SDK Layer). DUT 통신 추상화 — transport 자유 (TCP/UDP/gRPC/Custom binary). 첫 sample 구현체는 `TCPJsonDUTAdapter`. 18 § 18.7, 17 § 17.4.1.

### TCPJsonDUTAdapter (v0.38)

기본 sample DUTAdapter — TCP socket + JSON encoding. 펌웨어 측 부담 최소 (lwIP·NDK 같은 임베디드 TCP stack + sprintf 로 충분). `plugins_builtin/tcp_json_dut_adapter.py`. 18 § 18.7.

### L1~L5 (DUT RX 5단계, v0.38)

DUT 가 보낼 수 있는 결과의 5단계. 모두 **선택적** — DUT 능력·선호 따라.
- **L1**: ADC raw IQ (수십 MB/s, Phase 8.3)
- **L2**: FFT spectrum (Phase 8.2)
- **L3**: Detection peaks
- **L4**: Paired detections (Phase 8.2)
- **L5**: Tracks ⭐ (MVP HIL 의 베이스라인, Phase 8.1)

각 dataclass 는 `domain/hil/dut_messages.py`. 18 § 18.5.

### TXSignalDigital / TXSignalAnalog (v0.38)

TRsim 이 DUT 에 보낼 신호 형식 양방향:
- **Digital baseband** (MVP): IQ samples → Ethernet/TCP
- **AWG analog** (MVP+α, Phase 8.3): IQ samples → AWG vendor SDK → RF analog

18 § 18.6.

### GT / SIL / HIL 3-way 비교 (v0.38)

HIL 검증 모델. 한 시점·한 표적의 3가지 결과 비교:
- **GT** (Ground Truth): 실제 가상 표적 위치
- **SIL** (Software-in-the-Loop): Python DSP 결과
- **HIL** (Hardware-in-the-Loop): DUT 결과

`HILComparisonResult` dataclass. 18 § 18.9.

### DUT-Bias (v0.38)

펌웨어 (HIL) 와 Python DSP (SIL) 의 결과 gap. `|hil - sil|`. SIL 정확도와 별개 차원으로, "펌웨어가 Python 기준 알고리즘과 얼마나 다른가" 를 정량화. 18 § 18.9.

### sim_time / real_time sync mode (v0.38)

HIL 시간 동기화 모드 두 종류:
- **sim_time** (MVP): 시뮬 시간 기준, DUT 응답 timestamp 매칭. 재현성 ⭐
- **real_time** (Phase 8.3): wall-clock 기준, DUT 응답 늦으면 sample loss

18 § 18.8.

### HILEvaluator (v0.38)

App Layer 컴포넌트. DUT 메시지 (L1~L5) 받아 GT/SIL/HIL 3-way 비교 결과 생성. `app/hil/hil_evaluator.py`. 18 § 18.4, 18 § 18.9.

### HIL Sink (v0.38)

기존 SignalSink 인터페이스의 HIL 구현체. SIL Sink 와 같은 인터페이스, 다른 transport. 02 § 2.6, 18 § 18.4.

---

## v0.39 Reference Timing 용어

### Reference Timing Mode (v0.39)

시뮬 시간을 사용자 명시 target_latency 기준으로 보정하는 시간 모드. 모드 1 (sim_time) / 모드 2 (real_time) 외 3번째 모드. PC 가 더 느리면 시뮬 시간을 비율로 느리게, 더 빠르면 sleep 으로 늦춤. Vivado simulation 패턴. SIL + HIL 둘 다 적용. 18 § 18.16.

### PerformanceClock (v0.39)

SimulationClock 의 옵션 layer. wall_clock ↔ reference_time ↔ sim_time 3 시간 매핑 담당. Reference Timing Mode 활성 시만 동작. frame 단위 결정성 보장. 02 § 2.2c, 18 § 18.16.3.

### StageTimingProfile (v0.39)

사용자가 시나리오 [timing.profiles] 섹션에 명시하는 한 Stage 또는 Pipeline 의 timing 명세. `target_latency_ms` (기본) 또는 `scale_factor` (보조, target 모호 시) 입력. 03 § 3.2.1n.

### LockStepHandshake (v0.39)

HIL 모드에서 Reference Timing 활성화 시 frame 단위 sync barrier. PC 와 DUT 가 frame_id 매칭으로 진행. DUTAdapter Protocol 의 `sync_frame_start` / `sync_frame_end` 메서드. Vivado simulation 의 clock cycle 동기와 가장 유사. 18 § 18.16.4.

### Frame Profiler (v0.39)

테스트 코드를 미리·또는 백그라운드로 측정하여 한 frame 당 stage·pipeline timing 통계 (avg / p50 / p95 / p99) 표시. Reference Timing 의 짝꿍 — 사용자가 target_latency 입력 전에 PC 측 실측 알 수 있게. Vivado timing report 패턴. 18 § 18.17.

### FrameTimingReport (v0.39)

Frame Profiler 의 결과 dataclass. profile_frames + warmup_frames + measurement_context (CPU/OS/load) + stage_stats + pipeline_stat. JSON / Markdown 출력. 03 § 3.2.1n.

### StageTimingStat (v0.39)

한 Stage 의 측정 통계 — avg_ms / p50 / p95 / p99 / min / max / sample_count. 03 § 3.2.1n.

### Frame Boundary Detector (v0.39)

Reference Timing Mode 의 자동 frame 추론. `frame_unit = "auto"` 시 TrackOutputProbe 의 출력 시점 (표적 AZ/EL 결론) 마다 frame 갱신. 사용자가 frame 정의 안 명시해도 동작. 18 § 18.16.2.

### scale_factor (v0.39)

Reference Timing 의 보조 입력 — `target_latency_ms` 가 정수 배수 아닐 때 직접 비율 입력. `wall_clock × scale_factor = reference_time`. 예: scale_factor=0.5 → 시뮬 시간이 wall_clock 의 절반 속도. 03 § 3.2.1n.

### frame_unit (v0.39)

Reference Timing 의 frame 정의 단위. 옵션: `fmcw_sweep` / `fft_window` / `auto` (자동 추론) / `custom`. Scenario [timing] 섹션에 명시. 18 § 18.16.2.

---

## v0.40 Physics Lab 용어

### Physics Layer (v0.40)

domain 에서 분리된 별도 계층. 모든 물리 코드 (전파·반사·동역학·대기·안테나·platform_motion) 를 단일 `physics/` 디렉토리에 통합. 의존: numpy + scipy 만. domain 참조 X. 02 § 2.6c, 19 § 19.4.

### Physics Lab (v0.40)

3번째 Workspace (Editor / Simulator / Physics Lab). 물리 모델 검증·디버깅·진화 환경. 3-pane 인터랙티브 (Code | Visualization | Parameters). Bret Victor 스타일 + 추적 IDE. 19 § 19.5.

### 3-pane Interactive Pattern (v0.40)

Physics Lab 의 핵심 레이아웃. Code Pane (적용 코드) / Visualization Pane (2D pyqtgraph + 3D PyVista) / Parameters Pane (모든 파라미터 자동 슬라이더). 라이브 갱신. 19 § 19.5.

### 9 Test Objects (v0.40)

Physics Lab 의 표준 검증 객체 — 분석 공식이 알려진 단순 객체. Sphere / Cube / Plate / Cylinder / Cone / Point / Plane / Wall / Trihedral. `physics/test_objects.py`. 19 § 19.7.

### Sphere (Test Object, v0.40)

구. 점질량 + 반지름 + drag_coefficient (기본 0.47) + restitution. 가장 핵심 — RCS = πr² (large), 9πr²(kr)⁴ (Rayleigh) 등 분석 공식 풍부. drag = ½ρv²C_d·πr².

### Trihedral (Test Object, v0.40)

Trihedral corner reflector. RCS 측정 표준. boresight RCS = 4π·a⁴/(3λ²). 산업 측정장비의 calibration target.

### 4 Time Modes (v0.40)

Physics Lab 의 시간 처리 4 모드:
1. **Static**: 정지 상태, 한 시점의 물리 값 (시간 X)
2. **Single Run**: 시간 진화 trajectory + Play/Pause/Stop (가장 자주)
3. **Compare**: 두 모델 동시 시간 진화 — Overlay/Split/Diff
4. **Sweep**: 파라미터 sweep × 시간 = 2D heatmap

19 § 19.6.

### PhysicsClock (v0.40)

Physics Lab 격리 PhysicsClock — SimulationClock 의 격리 인스턴스. 메인 시뮬과 분리된 시간 진행. 19 § 19.6.5.

### PhysicsModelProtocol (v0.40)

11번째 SDK Plugin Protocol. 사용자 물리 모델 plugin (06 § 6.7 결정 변경). 5 카테고리 (`propagation` / `reflection` / `dynamics` / `atmosphere` / `antenna`). Physics Lab Validation Bench 통과한 것만 시뮬에서 사용 가능. 17 § 17.4.1, 19 § 19.8.

### ParamMetadata (v0.40)

슬라이더 자동 노출용 parameter metadata. `@physics_param` decorator 또는 `Annotated[float, ParamMetadata(...)]` type hint 로 명시. min / max / default / unit / scale (linear/log) / is_integer. 19 § 19.5.5.

### @physics_param decorator (v0.40)

Physics 함수의 파라미터를 Physics Lab 슬라이더로 자동 노출. 예: `@physics_param(name="mass", min=0.1, max=100, scale="log", unit="kg")`. 03 § 3.2.1o, 19 § 19.5.5.

### ForceModel / ForceComposition (v0.40)

Physics Lab 의 다중 force 조합 모델. ForceModel = 단일 force (gravity, drag, lift 등). ForceComposition = 활성화된 force 들의 합산 + integration_method (euler / rk4 / verlet). 모델 selector 의 ☑/☐ toggle 이 ForceComposition 갱신. 03 § 3.2.1o, 19 § 19.5.6.

### Validation Bench (v0.40)

Physics Lab 안의 검증 환경. 분석 공식 vs 구현 비교 + 17~20+ 종 회귀 시나리오 + 외부 측정 데이터 비교. RMSE / Max diff / PASS/FAIL. 사용자 plugin 의 안전망. 19 § 19.10, 16 § 16.9.

### Code Pane Hybrid (v0.40)

Physics Lab 의 Code Pane 정책 — Read-only default + "Edit mode" toggle. 사용자가 명시 활성화 시 라이브 편집 가능 (위험 인지). Pygments syntax highlight + 시간 진행 따라 current line highlight. 19 § 19.5.3.

### External Dataset (v0.40)

Physics Lab 에 업로드된 외부 측정 데이터. CSV / HDF5 / .npz 형식. independent_var (range, time, angle 등) + dependent_vars 구조. 형태 5 (검증·비교) + 형태 1 (파라미터 학습) 의 입력. 03 § 3.2.1o, 19 § 19.9.

### Fitted Parameters (v0.40)

형태 1 (파라미터 학습) 의 결과 — 외부 측정 데이터로 기존 모델의 파라미터 fit. scipy.optimize.curve_fit 기반. fit_quality (R², RMSE) + fitted_params + 측정 데이터 참조. Resource Library 에 저장 (Editor 와 일관). 03 § 3.2.1o, 19 § 19.9.3.

### Symbolic Regression (v0.40, Phase 9.2)

측정 데이터에서 수식 자체 발견 — PySR 같은 도구 사용. 형태 4 (점진 진화 단계 중 하나). 발견된 수식의 sympy 표현 + Python 코드 생성. 해석 가능 (interpretable) 모델. 19 § 19.9.5.

### NN Replacement (형태 2, v0.40, Phase 9.3)

물리 함수를 NN 으로 대체 — Phase 6 NN 통합 인프라 활용. 학습 영역 vs 외삽 영역 명확 표시 (위험 영역 경고). 19 § 19.9.5.

### 형태 1~5 (외부 자료 학습 단계, v0.40)

Physics Lab 의 외부 자료 학습 5 형태:
1. **파라미터 학습** (MVP) — 기존 모델의 파라미터를 측정 데이터로 fit
2. **NN 대체** (Phase 9.3) — 물리 함수를 NN 으로 대체
3. **논문 PDF → 자동 코드** (명시 제외, 신뢰성 X)
4. **Symbolic regression** (Phase 9.2) — 측정 데이터로 수식 발견
5. **검증·비교** (MVP) — 학습 X, 측정 데이터와 비교만

19 § 19.9.

### 추측 3 (의도 분류, v0.40)

사용자 의도 ≈ "측정 데이터 + 논문 참조하면서 모델 진화 — 사람이 보면서". 형태 1+5 즉시, 형태 2/4 점진, 형태 3 명시 제외. 논문 PDF 는 참조 자료 (metadata) 만. 19 § 19.2.

### Bret Victor Pattern (v0.40)

Physics Lab 의 디자인 영감 — "Inventing on Principle" 인터랙티브 코드 + 시각화 + 파라미터 슬라이더. Observable Notebook / Phet Simulations / Mathematica Manipulate 와 같은 계열. 추적 레이더 도메인에서 시장 부재. 19 § 19.2.

### MVP+α Wave 4 (v0.40)

Physics Lab 의 Phase 위치. Wave 1 (NN, Phase 6) / Wave 2 (DLC, Phase 7) / Wave 3 (HIL, Phase 8) 다음. Phase 9.1 (MVP 인터랙티브 환경 + 검증) / 9.2 (학습 보강 + plugin) / 9.3 (NN 대체). 04 Phase 9, 19 § 19.11.

---

## 레이더 도메인 용어

### FMCW (Frequency Modulated Continuous Wave)

주파수 변조 연속파. 송신 주파수가 시간에 따라 선형 증가(Up)/감소(Down).

### IF (Intermediate Frequency) / Beat Frequency

송신 신호와 수신 신호의 차이 주파수. 거리·속도 정보 포함.

### CFAR (Constant False Alarm Rate)

일정 오경보율 유지 검출기. 주변 셀 통계로 임계값 적응.
예: CA-CFAR(Cell-Averaging), OS-CFAR(Ordered-Statistic).

### Up/Down Pairing

FMCW에서 Up-sweep과 Down-sweep에서 각각 검출된 피크를 매칭.
범위·속도 분리에 필요.

### Monopulse

하나의 펄스만으로 각도 추정하는 기법. 4채널 배열의 위상차 기반.

### Boresight

안테나의 주 빔 축. 포지셔너가 이 축을 표적 방향으로 정렬.

### RCS (Radar Cross Section)

레이더 단면적. 표적의 반사 특성을 면적(㎡ 또는 dBsm)으로 표현.

### Swerling Models

표적 RCS의 시간적 변동 모델(I~V). Swerling I: pulse-to-pulse 고정, scan-to-scan 독립.

### Positioner

안테나를 방위각(AZ)·고각(EL)으로 회전시키는 기계 장치. 서보 제어.
예: Orbit AL-4018D.

### ENU (East-North-Up)

지역 접평면 좌표계. 레이더 원점 기준 동쪽/북쪽/위쪽.

### DEM (Digital Elevation Model)

지형 고도 격자 데이터.

### LOS (Line of Sight)

시선 경로. 장애물 없는 직선 가시성.

### Multipath

직접 경로 외에 해면/지면 반사를 거친 경로. 신호 왜곡 원인.

### Douglas Sea State

해상 상태 분류 0~9. 파고와 시각적 특성 기반.

---

## 아키텍처 / 소프트웨어 용어

### Layered Architecture

계층 구조. 안쪽 계층은 바깥쪽을 모름.
본 프로젝트: Primitives → Domain → App → UI.

### Protocol

Python의 구조적 서브타이핑. 메서드 시그니처만 맞으면 "해당 Protocol을 구현"으로 간주.
명시적 상속 불필요.

### God Class

한 클래스에 너무 많은 책임이 몰린 안티 패턴.
기존 `view/main_window.py` (1,583줄)가 교과서 예.

### LGPL (Lesser General Public License)

동적 링크 사용 시 소스 공개 의무 없음. PySide6가 이 라이선스.

### QMainWindow / QDockWidget / QWidget

Qt의 핵심 위젯. QMainWindow는 기본 앱 프레임, QDockWidget은 분리 가능한 패널.

### Signal / Slot

Qt의 이벤트 통신 메커니즘. 신호 발신(emit) → 수신자(slot)에 연결.

### pytest-qt

Qt 앱의 단위/통합 테스트 지원 pytest 플러그인.

---

## 데이터 / 직렬화 용어

### TOML

사람이 읽기 좋은 설정 파일 포맷. Python 3.11+ `tomllib` 내장.

### HDF5

계층 데이터 포맷. 대용량 배열 + 메타데이터 조합에 적합.

### Parquet

컬럼 지향 저장 포맷. 빅데이터 에코시스템 표준.

### JSON-serializable

JSON으로 변환 가능한 타입만 사용. dict/list/str/int/float/bool/None.

### Dataclass (frozen)

Python 3.7+ 불변 데이터 클래스. `@dataclass(frozen=True)`.

---

## 지리 / 좌표계

### WGS84

GPS에서 사용하는 지구 타원체 모델.

### MSL (Mean Sea Level)

평균 해수면. 기준 고도로 사용.

### Bilinear Interpolation

격자 4점 기반 이차선형 보간. 지형 높이 조회에 사용.

---

## 약어

| 약어 | 전체 |
|---|---|
| ADC | Analog-to-Digital Converter |
| AWG | Arbitrary Waveform Generator |
| AZ | Azimuth (방위각) |
| EL | Elevation (고각) |
| BDFL | Benevolent Dictator For Now / For Life (v0.35) |
| CA-CFAR | Cell-Averaging CFAR |
| CFAR | Constant False Alarm Rate |
| CLA | Contributor License Agreement (v0.35) |
| DCO | Developer Certificate of Origin (v0.35) |
| DEM | Digital Elevation Model |
| DLC | Downloadable Content (v0.35) |
| DSP | Digital Signal Processing |
| DUT | Device Under Test (v0.38) |
| EKF | Extended Kalman Filter |
| ENU | East-North-Up |
| FFT | Fast Fourier Transform |
| FMCW | Frequency Modulated Continuous Wave |
| FOV | Field of View |
| GNN | Global Nearest Neighbor (data association, v0.34) |
| GT | Ground Truth |
| GUI | Graphical User Interface |
| HDF | Hierarchical Data Format |
| HIL | Hardware in the Loop |
| IDE | Integrated Development Environment |
| IF | Intermediate Frequency |
| ISA | International Standard Atmosphere (v0.28) |
| JPDA | Joint Probabilistic Data Association (MVP+α) |
| LGPL | Lesser General Public License |
| LOD | Level of Detail |
| LOS | Line of Sight |
| MHT | Multiple Hypothesis Tracking (MVP+α) |
| MSL | Mean Sea Level |
| MVC-P | Model-View-Controller-Presenter |
| MVP | Minimum Viable Product |
| NN | Neural Network |
| OS-CFAR | Ordered Statistics CFAR (v0.34) |
| OSM | OpenStreetMap |
| Pd | Probability of Detection |
| Pfa | Probability of False Alarm |
| RCS | Radar Cross Section |
| RF | Radio Frequency |
| RMSE | Root Mean Square Error |
| RNG | Random Number Generator |
| RX | Receiver (수신) |
| SDK | Software Development Kit (v0.35 — `trsim.sdk`) |
| SIL | Software in the Loop |
| SNR | Signal-to-Noise Ratio |
| SPDX | Software Package Data Exchange (라이선스 ID 표준) |
| STL | STereoLithography (3D 메시 포맷) |
| TBD | To Be Determined |
| TX | Transmitter (송신) |
| UI/UX | User Interface / Experience |
| UKF | Unscented Kalman Filter (v0.34) |
| WGS | World Geodetic System |

---

## 상태 태그 (계획서 자체의 메타)

- **✅ Decided** — 합의 완료
- **🟡 Proposed** — 제안, 재검토 가능
- **⏳ TBD** — 의도적 미결정
- **🔒 Out of scope** — 범위 밖
- **🎯 MVP 주 타겟** — 우선순위 높음

---

## 섹션 상태

- ✅ 전체 작성 완료

---

끝.
계획서 전체는 [00_README.md](00_README.md) 에서 시작.
