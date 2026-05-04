# 05. UI / UX 설계

**최종 갱신**: 2026-04-28 — v0.25 시점 본문 보존

**상태**: 🟡 **참조 보존**. v0.27~v0.35 의 UI 변경 (Editor Workspace 5 Activity, Domain Settings 패널, Atmosphere Panel, Glint 시각화, DLC Plugin Manager 확장 등) 은 다음 문서가 권위:
- **Editor 측 사양**: [13 editor_workspace.md](13_editor_workspace.md) (v0.35)
- **Simulator 측 패널 + 전체 블록도**: [02 § 2.2 architecture.md](02_architecture.md) (v0.35)
- **DLC Plugin Manager 확장**: [17 § 17.4 open_platform.md](17_open_platform.md) (v0.35)

본 문서는 **v0.13~v0.25 시점 컨셉·목업 참조용**. 정합 노트 (⚠️) 가 § 5.3.2/§ 5.3.3 에 있어 권위 위치 안내.

## 5.1 설계 철학

### 원칙 1: IDE처럼 느껴져야 한다

사용자가 처음 봤을 때 "아 VS Code / IntelliJ 쓰던 그 느낌"이 와야 함.
- 좌측에 Explorer, 중앙에 주 에디터/뷰, 우측/하단에 보조 패널
- Ctrl+Shift+P로 명령 검색
- 패널 드래그하면 어디든 도킹/분리
- 상태바가 현재 상태를 정확히 알려줌

### 원칙 2: 모든 액션이 Command

"버튼이 있으니까 누르면 뭔가 된다"가 아니라
**모든 액션이 Command로 등록**되어 있어서:
- 툴바 버튼 = Command 참조
- 메뉴 항목 = Command 참조
- 단축키 = Command에 바인딩
- 팔레트 검색 = Command 목록 검색
- 매크로/자동화 = Command 시퀀스 (미래)

### 원칙 3: 패널은 독립적

각 패널은 다른 패널 몰라도 혼자 돌아가야 함.
상호작용은 **EventBus를 통해서만**. 직접 참조 금지.

### 원칙 4: "실수로 파괴되지 않는" UX

- 시나리오 수정 중 다른 걸 로드하려 하면 저장 프롬프트
- Run 중에 앱 종료하면 경고
- Plugin 코드에 문제 생기면 Workbench 자체는 죽지 않음

### 원칙 5: 영속성

사용자의 **워크스페이스 상태**(어떤 패널을 어디 도킹, 어떤 시나리오 열림)가
재시작 후 복원된다. 이게 "개인 작업 공간"이라는 느낌을 준다.

### 원칙 6: 두 운용 모드의 UI 분리

[01 § 1.1](01_vision_scope.md#두-운용-모드)의 두 모드(DSP / NN 개발)는 **UI 레벨에서도 명확히 분리**된다:

- **메뉴 전환**: `View > Mode > DSP Mode | NN Development Mode`
- **DSP 모드**: NN 관련 패널·메뉴·명령이 **전혀 보이지 않음**
- **NN 개발 모드**: Step 1 (Dataset Extraction), Step 2 (NN Evaluation) 전용 레이아웃
- **상단 타이틀바**: 현재 모드가 상시 표시됨 (예: `Workbench — B_Conflict [DSP Mode]`)
- **모드 간 공유**: Workspace(`plugins/`, `datasets/`, `scenarios/`, `runs/`)는 공통
- **모드 전환 시 안전성**: 진행 중 Run이 있으면 전환 차단, 사용자에게 확인 프롬프트

이 분리 덕에:
- DSP 모드 사용자는 NN 개념을 학습할 필요 없음
- NN 개발자는 전용 워크플로(Step 1 → Step 2)로 집중
- 두 모드 공통 인프라(Plugin Manager, Scenario Explorer)는 중복 없이 재사용

---

## 5.2 기본 레이아웃 (MVP)

```
┌──────────────────────────────────────────────────────────────────┐
│ File  Edit  View  Run  Plugins  Tools  Help               [─][□][×]│  ← MenuBar
├──────────────────────────────────────────────────────────────────┤
│ [▶][⏸][⏹] [⏮][⏭] [⚡ Run] [🔌 Plugins] [🔍 Palette]    [F]  [⚙]│  ← ToolBar
├──────────────┬───────────────────────────────────┬───────────────┤
│              │                                   │               │
│  Scenario    │                                   │   Properties  │
│  Explorer    │         3D Scene View             │   Panel       │
│  (Dock)      │         (Central / Dock)          │   (Dock)      │
│              │                                   │               │
│  - A_Base    │                                   │   - Radar     │
│  - B_Conf..  │                                   │   - Target    │
│  - C_Limit   │                                   │   - FMCW      │
│  (Dock)      │                                   │               │
│              ├───────────────────────────────────┤               │
│  Plugin      │                                   │               │
│  Manager     │         FFT Spectrum              │               │
│  (Dock)      │         (Dock)                    │               │
│              │                                   │               │
├──────────────┴───────────────────────────────────┴───────────────┤
│  Run Panel (Dock, 하단)                                           │
│  [Running]  Frame 127/200   Target#1 🎯 Lock ✓  IDSw=0  Lag=0.4° │
├──────────────────────────────────────────────────────────────────┤
│ ● B_Conflict | Primary=Target#1 | Tracker: my_tracker@v1 | 10 FPS│  ← StatusBar
└──────────────────────────────────────────────────────────────────┘
```

**Run Panel 상태 줄 해석**: `Target#1 🎯` 은 현재 선택 표적(Primary).
`Lock ✓` 이면 lock 유지 중. `IDSw=0` 은 현재까지의 Track ID Switch 횟수.
`Lag=0.4°` 은 포지셔너와 실제 방향의 각도 오차(Positioner Lag).
즉 이 한 줄에 **추적 레이더의 건강 상태 전체가 요약**된다.

### 핵심 패널 (MVP)

| 패널 | 기본 위치 | 주 역할 |
|---|---|---|
| **Scenario Explorer** | 좌측 상단 | 시나리오 목록, 선택, 미리보기 |
| **Plugin Manager** | 좌측 하단 | 로드된 플러그인 목록, 활성화, 경로 추가 |
| **3D Scene View** | 중앙 좌 | 지형/건물/함선/빔/탐지 시각화 (3rd-person) |
| **Radar POV (Scope)** | 중앙 우 | 보어사이트 조준경 — 십자선·빔폭·표적 위치 |
| **FFT Spectrum** | 중앙 하단 | 매 프레임 FFT up/down, Peak 오버레이 |
| **Properties** | 우측 | 선택된 객체의 속성/파라미터 편집 |
| **Run Panel** | 하단 | 현재 Run 진행/메트릭/로그 |

### 중앙 영역 = 멀티 탭

3D View와 FFT는 사용자 기호에 따라:
- 상하 분할 (기본)
- 탭으로 전환 (한 번에 하나만)
- 별도 창으로 분리

이 모든 게 **QDockWidget의 기본 기능**으로 제공됨.

---

## 5.3 패널 상세 설계

### 5.3.1 Scenario Explorer

```
┌─ Scenario Explorer ─────────────┐
│ 🔍 Filter...                     │
├──────────────────────────────────┤
│ ▾ Built-in                       │
│   📄 A_Base       (12km, Evas.)  │
│   📄 B_Conflict   (2 ships)      │
│   📄 C_Limit      (crossing)     │
│   📄 D_Static                    │
│   📄 E_Decoy                     │
│   📄 F_Stealth                   │
│                                  │
│ ▾ My Scenarios                   │
│   📄 my_custom_01                │
│                                  │
│ [+ New]  [⟳ Rescan]              │
└──────────────────────────────────┘
```

- 트리 형태 (built-in / user)
- 더블클릭 = 로드
- 우클릭 메뉴: 복사, 삭제, 폴더 열기, 속성
- 호버 시 툴팁에 시나리오 요약

### 5.3.2 3D Scene View — 3rd-person + Scope POV 이원 구조

> ⚠️ **v0.27~v0.34 정합**: 본 섹션의 3D View 사양은 **v0.13 시점 사고**. 다음 후속 변경 반영 필요:
>
> - **v0.27 동역학 가시화** (14 § 14.10): 표적 attitude (roll/pitch 출렁), max_climb_rate 도달, BALLISTIC 포물선, AIRCRAFT autopilot trajectory
> - **v0.28 시각화 스택** (02 § 2.6a): **PyVista** (VTK 기반) — 3rd-person View 렌더, atmosphere fog, sky color, sea wave 셰이더
> - **v0.28 대기** (15 atmosphere_model): visibility_km → fog distance, rain particle 효과
> - **v0.29 Simulation Domain** (11 § 11.11): Map 영역 (정밀) vs Map 밖 (단순 평면) 시각화
> - **v0.34 Multi-scatterer + Glint** (14 § 14.10): extended target의 scatterer 점 표시 (디버그용), apparent_position vs actual_position 표시
> - **v0.34 Two-ray multipath** (08 § 8.5b.1): sea bounce ray 표시 (multipath 레이어)
>
> 본 섹션의 3rd-person + Scope 이원 구조 자체는 v0.35까지 유효. 위 추가 시각화 요소는
> SceneLayer enum에 추가하거나 별도 패널로 분리 가능.

기존 `radar_viewer_3d.py`를 두 패널로 재설계:

#### (a) 3rd-person View — 전체 조망

- 지형·건물·함선·레이더·TX 빔을 3D로
- 카메라 프리셋: Top / Side / Free
- 오버레이 토글 가능
- **두 종류 빔을 동시 표시**:
  - 실선 빔 = 포지셔너 **실제** 방향 (현재 물리적으로 안테나가 향하는 곳)
  - 점선 빔 = EKF가 **명령**한 방향 (따라가야 할 목표)
  - 둘 사이 각도가 곧 Positioner Lag

#### (b) Radar POV (Scope) — 조준경 뷰

포지셔너 보어사이트에서 정면을 바라본 장면. 추적 레이더 운용자가 실제로 주시하는 시점.

- 화면 중심 = 포지셔너 보어사이트 (십자선)
- **안쪽 원** = -3dB 빔 폭 (표적이 이 안이면 in-beam)
- **바깥 원** = 전체 FOV (점선)
- **Primary Target**: 주황 dot + 트래킹 브래킷, 보어사이트 기준 Δaz/Δel 표기
- **Secondary Targets**: 회색 dot, 빔 밖일 수도 있음
- **EKF 명령점**: 파란 `+` 마커 — EKF가 포지셔너에게 "여기로 가라"고 명령한 위치. 십자선 중심과의 차이 = Lag
- 좌상단 오버레이: AZ/EL 수치 (실제 / 명령 / Lag)

#### 왜 두 뷰를 같이 두는가

3rd-person은 **객관적 진실** (GT 표적과 레이더의 기하 관계)을, Scope는 **레이더가 보는 세계**(빔 내 표적 위치)를 보여줌. 추적 품질 문제(예: 표적이 빔을 벗어나는 순간)는 Scope에서 즉각 시각화되고, 원인(포지셔너 Lag, EKF 오추정 등)은 3rd-person과 Properties에서 대조하며 파악.

#### MVP에서는 기본 나란히 배치

- 기본 레이아웃: 중앙 영역을 좌(3rd-person) / 우(Scope) 분할
- 사용자가 원하면 도킹 드래그로 재배치 (탭으로 묶기, 한쪽만 보기 등)
- 단축키 `T/S/F` = 3rd-person 카메라 프리셋, `V` = Scope 토글 표시 여부

#### 오버레이 레이어 (3rd-person)

```python
class SceneLayer(Enum):
    TERRAIN = "terrain"
    SEA = "sea"
    BUILDINGS = "buildings"
    SHIPS = "ships"
    TX_BEAM_ACTUAL = "tx_beam_actual"     # 포지셔너 실제 (실선)
    TX_BEAM_COMMAND = "tx_beam_command"   # EKF 명령 (점선)
    GT_TARGETS = "gt_targets"
    DETECTIONS = "detections"
    TRACKS = "tracks"
    PRIMARY_HIGHLIGHT = "primary_highlight"  # 선택 표적 강조
    MULTIPATH_RAYS = "multipath"          # 디버깅용, 기본 off
```

각 레이어는 toggle 가능. 툴바에 레이어 그룹 버튼 배치.

### 5.3.3 Plugin Manager

> ⚠️ **v0.35 정합**: 본 섹션의 UI는 **v0.13 시점 단일 .py 플러그인 모델** 기준.
> v0.35 DLC 시스템 (`.trsim-pkg`, PackageManager, ~/.trsim/packages/) 은
> 17 § 17.2.4·17 § 17.4.2 가 권위.
>
> **MVP UI**: 본 섹션의 단순 Plugin Manager (~/my_workbench_project/plugins/ 스캔)
> **MVP+α UI** (Phase 7, v0.35): 본 패널 확장 — `[Install Package...]` 버튼,
> 설치된 `.trsim-pkg` 목록, manifest 정보 (id/version/author/license), enable/disable 토글.
>
> 자세한 DLC 패키지 UI는 13 § 13.x (Editor Workspace 의 Resource Browser 확장) 참조.

```
┌─ Plugin Manager ─────────────────────────────┐
│ Workspace: ~/my_workbench_proj               │
│ Plugins dir: ./plugins/                      │
├──────────────────────────────────────────────┤
│ Detector                                     │
│ ◉ default_cfar                   built-in    │
│ ○ my_cfar_v2                                 │
│   plugins/my_cfar_v2/plugin.py               │
│                                              │
│ Pairing 🎯                                    │
│ ○ default_pairing                built-in    │
│ ◉ my_pairing_nn                 [NN v1.2]    │
│   plugins/my_pairing_nn/plugin.py            │
│   weights/v1.2.npz (1.4 MB)                  │
│   edited 3m ago · auto-reload ✓              │
│                                              │
│ Tracker                                      │
│ ◉ default_ekf                    built-in    │
│ ...                                          │
├──────────────────────────────────────────────┤
│ [+ New Plugin]  [+ Add Existing...]  [⟳]     │
└──────────────────────────────────────────────┘
```

#### Plugin 파일 위치 — Workspace 개념

Workbench는 사용자의 **워크스페이스 디렉토리** 한 곳에 Plugin·Dataset·Run 결과를 모은다:

```
~/my_workbench_project/
├── workspace.toml              ← 워크스페이스 메타 (경로·기본값)
├── plugins/                    ← 사용자 Plugin 루트
│   ├── my_cfar_v2/
│   │   └── plugin.py
│   └── my_pairing_nn/
│       ├── plugin.py           ← Plugin 클래스
│       ├── architecture.toml   ← 네트워크 구조 (NN용)
│       ├── weights/
│       │   ├── v1.0.npz
│       │   └── v1.2.npz        ← 여러 가중치 버전 공존
│       └── training_log.json
├── datasets/                   ← Dataset Builder 출력
│   └── pairing_ds_v2.h5
├── scenarios/                  ← 내 커스텀 시나리오 (선택)
└── runs/                       ← Run 결과 (자동 저장)
    ├── run_0041/
    └── run_0042/
```

이 구조는 **관례일 뿐 강제되지 않음** — 사용자가 원하는 임의 경로의 파일도 "Add Existing"으로 등록 가능. 하지만 Workbench가 제공하는 워크플로(New Plugin 마법사, Dataset Builder, Trainer 연결)는 이 관례를 따를 때 가장 매끄럽게 동작.

#### New Plugin 마법사

"+ New Plugin" 버튼이 눌리면 다단계 프롬프트:

```
Step 1: 어떤 Contract?
  ● Detector        ● Pairing 🎯      ● Tracker
  ○ AngleEstimator  ○ Classifier     ○ TargetGate

Step 2: 일반 Plugin? NN Plugin?
  ○ Plain Python (함수 기반)
  ● NN Plugin (가중치 로드 + forward pass)

Step 3: 이름
  [ my_pairing_nn_v2 ]

Step 4: 결과
  → plugins/my_pairing_nn_v2/
      plugin.py               (템플릿 생성)
      architecture.toml       (NN일 때만)
      weights/                (빈 디렉토리)
  → Plugin Manager에 자동 등록
  → [외부 에디터로 열기] / [닫기]
```

- 편집 자체는 **외부 에디터**에서. Workbench는 IDE의 "에디터" 역할을 하지 않는다(Qt 안에 편집기 만드는 게 유지비용이 큼).
- VS Code가 시스템에 있으면 감지해서 `code plugins/my_pairing_nn_v2/` 로 자동 호출 옵션 제공.

#### Plugin 생명 주기

```
[1] New Plugin 마법사 → 템플릿 파일 생성
[2] 외부 에디터에서 구현 작성
[3] Workbench가 파일 변경 감지 (watchdog) → 자동 재로드
[4] Contract 검증 (메서드 존재? 임포트 성공?)
[5] Pipeline Slot에 활성화 → Run 사용 가능
[6] (NN일 때) Dataset Builder로 학습 데이터 수집
[7] (NN일 때) Trainer로 학습 → weights/ 경로에 저장
[8] Workbench가 가중치 파일 감지 → Plugin이 새 버전 로드
[9] 다시 Run
```

- 스테이지별 필터 (Detector / Pairing / Tracker / ...)
- 라디오 버튼으로 활성 플러그인 선택
- "Open" = 외부 에디터로 열기 (VS Code 감지 시 자동)
- "Reload" = 파일 변경 감지하면 자동, 수동도 가능
- Validation 상태 아이콘 (Contract 준수 여부)

### 5.3.4 FFT Spectrum Panel

기존 `data_panel.py`에서 FFT 부분만 분리.

- Up / Down sweep 두 곡선 동시 표시
- Peak 마커 (색상으로 up/down 구분)
- GT 목표 주파수 오버레이 (녹색 수직선)
- 임계값 라인 (CFAR threshold)
- **Probe 데이터에 연결** — 프레임 시크하면 해당 프레임 FFT 표시

### 5.3.5 Properties Panel

범용 속성 편집기. 컨텍스트에 따라 내용 변화:

- Scenario 선택 시 → 시나리오 파라미터 (sea_state, frame_rate 등)
- Radar 마커 클릭 시 → FMCW 파라미터, 안테나 설정
- Target 클릭 시 → 해당 표적 정보, RCS
- Plugin 선택 시 → 플러그인 configure() 파라미터

**읽기 전용 vs 편집 가능**을 명확히 구분. 시나리오 파라미터 편집은 "Scenario 수정 모드" 진입 필요.

### 5.3.6 Run Panel

```
┌─ Run Panel ─────────────────────────────────────────────────────────┐
│ History        │  Current Run                                       │
│ ─────────────  │  ─────────────                                     │
│ ▸ run_0042  ✓  │  Scenario: B_Conflict                              │
│ ▸ run_0041  ✓  │  Primary Target: #1 (corvette_1000t)  🎯            │
│ ▸ run_0040  ✗  │  Tracker: my_tracker@v1.0                          │
│ ▸ run_0039  ✓  │                                                    │
│                │  ── Time Layers ──                                 │
│                │  Sim:    🏃 RUNNING   sim_t = 12.7s   ×2 (actual 1.8x) │
│                │  Target: 🏃 RUNNING   run_t = 12.7s   Run #3        │
│                │                                                    │
│                │  Progress: [▸▸▸▸▸▸▸▸··] 127/200 frames              │
│                │                                                    │
│                │  ── Primary Target ── 🎯                           │
│                │  Lock: ✓ (since frame 18)                          │
│                │  Track Continuity: 0.94                            │
│                │  ID Switches: 0                                    │
│                │  Range RMSE: 3.2 m   AZ RMSE: 0.12°                │
│                │  Positioner Lag: avg 0.4°, max 1.8° (frame 94)     │
│                │                                                    │
│                │  ── Secondary Targets ──                           │
│                │  Target #2: continuity 0.88, crossed @ frame 94    │
│                │                                                    │
│                │  Physics Gate: ✓ All OK                            │
│                │  Positioner: AUTO [M to toggle]                    │
│ [+ Compare]    │  Target: [▶ Run] [⏸ Pause] [⏹ Stop]                │
└────────────────┴────────────────────────────────────────────────────┘
```

- 좌측: Run 히스토리 (시간순, 최근 위). 중단된 Run은 `⊘` 표시
- 우측: 현재/선택된 Run 상세. **Primary Target 블록을 최상단**에 크게, Secondary는 축약
- **Time Layers 블록 (v0.15 신설)**: Sim/Target 두 레이어 상태를 나란히
  - Sim: `sim_t` 시뮬 시간, 현재 Speed 설정 + actual
  - Target: `run_t` Run 내부 시간, Run 번호
- Positioner AUTO/MANUAL 상태 표시, `M` 키로 토글
- Target 버튼은 **Target 접두사**로 명시 (Sim 버튼은 상단 툴바에 있음)
- Compare 선택 → 별도 창에서 메트릭 나란히

### 5.3.6a Run State 제어 상세 (v0.14)

```
           ┌─────────────┐
           │    IDLE     │  ← 시작 상태 (Scenario 로드 후)
           │ 표적 정지   │
           └──────┬──────┘
                  │
          [▶ Run] │
                  ▼
           ┌─────────────┐
           │  RUNNING    │  ── [⏸ Pause] ──▶ ┌─────────────┐
           │ 표적 재생   │                   │   PAUSED    │
           │ 메트릭 기록 │◀── [▶ Run] ─────── │ 표적 정지   │
           └──┬───────┬──┘                   └──────┬──────┘
              │       │                             │
  [⏹ Stop]    │       │   [trajectory 끝]    [⏹ Stop]
   + 저장 확인│       │                      + 저장 확인
              │       ▼                             │
              │  ┌──────────┐                       │
              │  │  ENDED   │                       │
              │  │ 끝 위치  │                       │
              │  │ 정지     │                       │
              │  └──────────┘                       │
              ▼                                     ▼
           ┌─────────────┐               ┌─────────────┐
           │    IDLE     │               │    IDLE     │
           └─────────────┘               └─────────────┘
```

#### Stop 버튼 다이얼로그

```
┌─ Stop Run ─────────────────────────────────┐
│ ⚠ 이 Run을 중단하시겠습니까?              │
│                                            │
│ 지금까지 진행: 127/200 frames (12.7s)     │
│ 정상 종료가 아닙니다.                      │
│                                            │
│ ◉ 결과 저장 (termination=ABORTED)          │
│ ○ 결과 폐기                                │
│                                            │
│ ☐ 이 선택 기억, 다시 묻지 않기             │
│                                            │
│               [Cancel]  [Stop Run]         │
└────────────────────────────────────────────┘
```

#### 환경 시뮬의 독립성

- Run State가 IDLE/PAUSED여도 환경(바람·파도·자함 동요)은 계속 업데이트
- Pipeline도 계속 동작 → FFT 패널에 잡음·정지 표적 에코 실시간 표시
- 방향키로 포지셔너 수동 조작 가능 → FFT 변화 즉시 확인
- 이 덕분에 Run 시작 전 **초기 위치 잡기**·**파라미터 튜닝** 가능

### 5.3.6b 방향키 포지셔너 수동 조작 (v0.14)

#### AUTO ↔ MANUAL 토글

- **AUTO 모드**: Run 중 Tracker 출력이 자동으로 포지셔너 명령. `PositionerCommand.source=TRACKER`
- **MANUAL 모드**: 사용자가 방향키로 직접 조작. `PositionerCommand.source=MANUAL_USER`
- 토글 방법:
  - Run Panel 하단 `Positioner: AUTO/MANUAL` 표시 클릭
  - 단축키 `M`
  - Command Palette: "Positioner: Toggle Auto/Manual"

#### 방향키 매핑

| 키 | 동작 |
|---|---|
| `←` / `→` | AZ -/+ (한 번 누를 때마다 기본 1°, `Shift`로 5°) |
| `↑` / `↓` | EL +/- |
| `Ctrl + ←/→` | 연속 회전 (누르고 있는 동안) |
| `Home` | Scenario 기본 포지션으로 복귀 |

#### 상태 표시

- 상단 상태바: `[MANUAL] AZ 183.2° / EL 1.4°`
- 3D View 오버레이: 포지셔너 방향 + "MANUAL" 라벨
- MANUAL 모드 중 Run이 진행 중이면 메트릭에 **수동 조작 구간 마킹** — 평가 시 이 구간을 제외하거나 별도 집계

#### 사용 시나리오

1. **Run 시작 전 초기 위치 잡기**: IDLE 상태에서 방향키로 표적 방향으로 돌려둠. `InitialPositionerPolicy.KEEP_CURRENT`로 Run 시작 시 그 위치 유지.
2. **FFT 스펙트럼 확인**: IDLE/PAUSED 상태에서 다양한 방향 돌려가며 잡음·정지 표적 에코 관찰.
3. **Run 중 수동 개입 실험**: RUNNING 중 `M` 눌러 MANUAL 전환 → 사용자 결정으로 빔 이동 → 자동 복귀 후 Tracker 복구 성능 관찰.

### 5.3.6c Stage I/O Panel — Pipeline 각 스테이지 입출력 (v0.14)

사용자가 자기 DSP 코드가 **파이프라인 각 단계에서 뭘 입력받고 뭘 출력하는지** 실시간 확인 + 다운로드.

```
┌─ Stage I/O ────────────────────────────────────────────────────────┐
│ Frame 127 / 200   t = 12.7s                                        │
│                                                                    │
│ ┌─ Transmitter ──────────────┐ ┌─ Environment ─────────────────┐   │
│ │ OUT: TXBeam                │ │ IN:  TXBeam                   │   │
│ │   center_freq_hz: 9.4e9    │ │ OUT: 3 reflections            │   │
│ │   bw_hz: 80e6              │ │   [0] range=12.4km RCS=-8.2   │   │
│ │   [📥 CSV] [📥 HDF5]       │ │   [1] range=11.9km RCS=-11.0  │   │
│ └────────────────────────────┘ │   [2] range=  0.5km RCS=-22.1 │   │
│                                │   [📥 CSV] [📥 HDF5]          │   │
│ ┌─ Receiver ─────────────────┐ └───────────────────────────────┘   │
│ │ IN:  3 reflections         │                                     │
│ │ OUT: FFTSpectrum           │ ┌─ Detector (my_cfar_v2) ───────┐   │
│ │   up: N=1024               │ │ IN:  FFTSpectrum              │   │
│ │   down: N=1024             │ │ OUT: (up=4 peaks, down=4)     │   │
│ │   [📥 CSV] [📥 HDF5] [📊]  │ │   [📥 CSV] [📥 HDF5]          │   │
│ └────────────────────────────┘ └───────────────────────────────┘   │
│                                                                    │
│ ┌─ Pairing (default) ────────┐ ┌─ Tracker (default_ekf) ───────┐   │
│ │ IN:  4up × 4down peaks     │ │ IN:  2 PairedDetections       │   │
│ │ OUT: 2 PairedDetections    │ │ OUT: 2 Tracks                 │   │
│ │   [📥 CSV] [📥 HDF5]       │ │   Track #1: locked 🎯         │   │
│ └────────────────────────────┘ │   Track #2: tentative         │   │
│                                │   [📥 CSV] [📥 HDF5]          │   │
│                                └───────────────────────────────┘   │
│                                                                    │
│ [⏺ Recording: ALL stages]  [📁 Export all to CSV]                 │
└────────────────────────────────────────────────────────────────────┘
```

- 각 스테이지마다 **IN/OUT 박스**. 현재 프레임의 입출력 요약
- `📥 CSV` / `📥 HDF5` 버튼: **현재 프레임 스냅샷** 다운로드
- `📊` 버튼: 해당 데이터를 상세 시각화 (FFTSpectrum이면 별도 창에 플롯)
- 상단: 프레임 번호, 시간
- 하단: **전체 Run 기간 녹음** 토글. 녹음 중이면 모든 프레임 저장. 끝나면 ZIP 또는 HDF5 번들로 일괄 다운로드
- **Plugin 사용자 정의 추가 probe**도 여기 표시

#### Probe 프리셋

- **OFF** (기본): 녹음 없음, 패널 UI만 표시
- **DEBUG**: 모든 스테이지 모든 프레임 녹음 (메모리 많이 소모)
- **SAMPLED**: 10프레임당 1회 녹음
- **CUSTOM**: `RunConfig.probe_config`에 선언된 것만

상세: [06 § 6.1 Probe/Trace](06_topics.md#61-probetrace-시스템)

### 5.3.7 Physics Validation Panel (MVP 후반)

```
┌─ Physics Validation ─────────────────────┐
│ Domain           Status   Last Run       │
│ ────────         ──────   ────────────   │
│ Radar Equation   ✓ PASS   2m ago         │
│ FMCW Signal      ✓ PASS   2m ago         │
│ Multipath        ⚠ WARN   2m ago (1/5)   │
│ Clutter          - SKIP   (no golden)    │
│ Ray Tracing      ✗ FAIL   2m ago (2/8)   │
│                                          │
│ [Run All] [Update Golden] [View Report]  │
└──────────────────────────────────────────┘
```

### 5.3.8 Installation 화면 (v0.18 신설)

**상세는 [09_radar_platforms.md](09_radar_platforms.md) 참조.** 여기는 UI 요구사항.

#### 5.3.8a 진입 조건

Scenario 로드 시 **자동 진입**:
- `scenario_meta.toml`에 `[platform]` 완비 → 자동 적용, Installation 화면 건너뜀
- `[platform]` 불완전/없음 → Installation 화면 필수 통과
- 사용자 수동 진입: 메뉴 `Scenario > Edit Installation`

**Target Run 버튼은 Installation 미완료 시 비활성화** (툴팁: "Installation을 먼저 완료해주세요").

#### 5.3.8b 레이아웃

```
┌─ Installation — B_Conflict ────────────────────────────────────────────┐
│                                                                        │
│  ┌─ Platform Preset ─────────────┐  ┌─ Installation Position ──────┐  │
│  │ ○ Corvette 500t               │  │ East:  [_____] m              │  │
│  │ ● Coastal Tower 50m  🎯        │  │ North: [_____] m              │  │
│  │ ○ Destroyer 5000t             │  │ Alt:   [_____] m  (DEM+struct)│  │
│  │ ○ Rooftop 30m                 │  │                               │  │
│  │ ○ Hilltop Observatory          │  │ Initial AZ: [180.0]° 🧭        │  │
│  │                               │  │ Initial EL: [  0.0]°           │  │
│  │ [+ Custom Preset]             │  │                               │  │
│  └───────────────────────────────┘  │ Antenna h: [50.0] m above base│  │
│                                     └───────────────────────────────┘  │
│                                                                        │
│  ┌─ DEM Map (Top-down) ──────────────────────────────────────────────┐ │
│  │                                                                   │ │
│  │         (contour lines)                                           │ │
│  │                                                                   │ │
│  │                ⬢ ← 설치 지점 (클릭/드래그)                          │ │
│  │               / \                                                 │ │
│  │              /   \   ← 가시 영역 (빔이 닿는 곳)                     │ │
│  │             /     \                                               │ │
│  │                                                                   │ │
│  │    음영: 차폐 영역                                                  │ │
│  │                                                                   │ │
│  │    [ZOOM 1.0×] [-+][R]                                            │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌─ 3D Preview ──────────────┐  ┌─ Coverage Stats ──────────────────┐  │
│  │  (설치 위치에서의 뷰)       │  │ Max range (10m target): 28.4 km   │  │
│  │  플랫폼 형상 + 주변 지형    │  │ Obstructed sectors: 3 of 72 (4%)  │  │
│  │                           │  │ Blind bearings: 045°, 120°, 280°  │  │
│  └───────────────────────────┘  └───────────────────────────────────┘  │
│                                                                        │
│                        [Cancel]  [Save & Continue]                     │
└────────────────────────────────────────────────────────────────────────┘
```

#### 5.3.8c 인터랙션

**DEM Map**:
- 클릭: 설치 지점 지정 (DEM에서 자동 고도 샘플)
- 드래그: 지점 이동
- 휠: 줌 (Google Maps 방식, § 5.5.4d와 동일)
- 설치 지점 표시: 육각형 마커 + 방향 표시 (보어사이트 화살표)

**Preset 선택**:
- 드롭다운 또는 라디오 목록
- 선택 시 Platform의 기본값(antenna_height, motion_model 등)이 오른쪽 폼에 자동 채움
- 사용자가 세부 값 수정 가능

**차폐 Preview**:
- 실시간 계산 (위치 변경 시 즉시 업데이트)
- 72 방위 × 거리 샘플링으로 차폐 맵 생성
- 알고리즘: [09 § 9.7](09_radar_platforms.md#97-dem-차폐-계산-간단한-높이-기반)

**Coverage Stats 블록**:
- "기준 표적 고도 10m" 가정 하에 방위별 최대 가시 거리
- 차폐된 섹터 수와 방위 요약

#### 5.3.8d Save & Continue 동작 (v0.18)

저장 정책 상세는 [09 § 9.5.2](09_radar_platforms.md#952-installation-저장-정책-v018).

**기본 동작**: `[Save & Continue]` 클릭 시 **현재 Scenario의 `scenario_meta.toml`에 직접 반영**.
별도 파일·별도 이름 관리 없음. Scenario와 Installation은 한 몸.

**분기**:
- 사용자 소유 Scenario (my_scenarios/) → 즉시 덮어쓰기
- Built-in Scenario → 경고 다이얼로그 → 새 이름 입력 → 새 Scenario 복제 생성 후 저장

**관련 메뉴**:
- `Scenario > Edit Installation`: 이 화면 진입
- `Scenario > Save Scenario As...`: 현재 Scenario(Installation 포함)를 새 이름으로 복제. Installation 실험용으로 유용

**다이얼로그 예시 (Built-in 경고)**:

```
┌─ Read-only Scenario ────────────────────────────────┐
│ ⚠ "B_Conflict"는 Built-in 시나리오입니다.           │
│                                                     │
│ Installation을 수정하려면 새 이름으로 저장해야 합니다.│
│                                                     │
│ 새 이름: [B_Conflict_hilltop_________]              │
│                                                     │
│              [Cancel]  [Save as New]                │
└─────────────────────────────────────────────────────┘
```

#### 5.3.8e Run 중에는 Installation 진입 불가

Target RUNNING 또는 PAUSED 상태에서는 Installation 메뉴 비활성화. 이유:
- 플랫폼 교체는 시뮬 기반 좌표계 변경 → Trace·메트릭 무효화
- Target Stop 후에만 허용 (Stop 다이얼로그 거쳐 결과 저장)

### 5.3.9 Radar Editor (Editor Workspace, v0.25 신설)

**상세**: [08 § 8.5a Antenna Model](08_radar_waveforms.md#85a-antenna-model--형태와-채널-v025-신설),
[03 § 3.2.1h Antenna Configuration](03_data_model.md#321h-antenna-configuration-v025-신설).

#### 5.3.9a 진입 경로

Editor Workspace의 **Resource Browser → Radars** 에서 자원을 선택하면 Radar Editor 탭 열림.
또는 메뉴 `Radar > New` 로 새 자원 생성.

#### 5.3.9b 통합 에디터 — 안테나 타입 드롭다운 중심 (Q3 결정)

안테나 타입을 선택하면 **그 타입에 해당하는 필드만 표시**되는 동적 폼:

```
┌─ Radar Editor — fmcw_corvette ────────────────────────────────────┐
│                                                                   │
│  Name:   [fmcw_corvette_______]    Description: [_____________]    │
│  Version: 1.1                       Hash: sha256:gh789...          │
│                                                                   │
│  ┌─ Platform ────────────────┐  ┌─ Radar Model ──────────────┐    │
│  │ Platform: [corvette_500t▾]│  │ Model: [fmcw_triangle_v1▾] │    │
│  │ Category: maritime         │  │ Carrier: [9.5e9    ] Hz    │    │
│  │ Motion:   floating_static  │  │ Bandwidth:[150e6   ] Hz    │    │
│  │ ... (link to Platform UI) │  │ Sweep:    [1.0e-3  ] s     │    │
│  └────────────────────────────┘  │ Tx Power: [1e3     ] W     │    │
│                                  └────────────────────────────┘    │
│                                                                   │
│  ┌─ Antenna ─────────────────────────────────────────────────┐    │
│  │ Type: ( ) Parabolic                                        │    │
│  │       (•) Planar Array                                     │    │
│  │                                                            │    │
│  │  ┌─ [Planar Array 선택 시 표시] ────────────────────────┐  │    │
│  │  │ N elements (Az):  [16     ]                          │  │    │
│  │  │ N elements (El):  [16     ]                          │  │    │
│  │  │ Spacing:          [0.0158 ] m  (= λ/2 @ 9.5GHz)      │  │    │
│  │  │ Element pattern:  [cos    ▾]                          │  │    │
│  │  │ Grid shape:       [rectangular ▾]                     │  │    │
│  │  │ Weighting:        [uniform     ▾]  (taper은 MVP+α)    │  │    │
│  │  │                                                       │  │    │
│  │  │ [Computed]                                            │  │    │
│  │  │   Beamwidth Az: 6.4°    Beamwidth El: 6.4°           │  │    │
│  │  │   Peak Gain:    27.1 dBi                              │  │    │
│  │  │   First sidelobe: -13.3 dB                            │  │    │
│  │  └───────────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │  [Beam Pattern Preview]   ┌─────────────────────┐         │    │
│  │  (실시간 시각화)            │   ╱│╲              │         │    │
│  │                            │  ╱ │ ╲             │         │    │
│  │                            │ ╱  │  ╲            │         │    │
│  │                            └─────────────────────┘         │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ RX Channels ─────────────────────────────────────────────┐    │
│  │ Mode: ( ) Single (Σ only)                                  │    │
│  │       (•) Monopulse 4-channel (Σ, Δaz, Δel, Δ²)             │    │
│  │                                                            │    │
│  │  Channel setup: subarray_partition (auto for planar_array) │    │
│  │  Slope kaz:   [1.4]   Slope kel:   [1.4]                   │    │
│  │  Boresight calibration: [Edit table ...]  (MVP+α)          │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                   │
│         [Cancel]   [Save]   [Save As New]                         │
└───────────────────────────────────────────────────────────────────┘
```

#### 5.3.9c Antenna Type 전환 시 동작

- Parabolic ↔ Planar Array 전환 시 **공통 필드는 보존**, 타입 전용 필드만 교체
- 빔폭·이득 같은 derived 값은 **자동 재계산**
- Beam Pattern Preview도 실시간 갱신

#### 5.3.9d Beam Pattern Preview

작은 polar plot 또는 cartesian plot으로 **실시간 빔 패턴 시각화**:
- Parabolic: sinc² 단일 로브
- Planar Array: array factor (sidelobes 명시)
- 사용자가 파라미터 (예: n_elements 변경) → 즉시 반영

성능: 빔 패턴 계산은 가벼움, 사용자 입력 시점에 재계산 OK.

#### 5.3.9e RX 채널 모드 전환

- **Single SUM**: monopulse 비활성, 단일 빔포밍 가정
- **Monopulse 4-channel**: monopulse 그룹 활성, slope·calibration 입력 필드 표시

채널 모드 전환 시 시뮬 Pipeline의 monopulse 처리 단계도 활성/비활성 (08 § 8.5a.6).

#### 5.3.9f Preset 라이브러리

기본 제공 preset (사용자가 복제 후 수정 권장):

| Preset | Antenna | RX | 용도 |
|---|---|---|---|
| `parabolic_dish_60cm` | Parabolic D=0.6m | Single SUM | 함정 일반 |
| `parabolic_monopulse_60cm` | Parabolic D=0.6m | Monopulse 4ch | 추적 정밀 함정 |
| `planar_16x16_xband` | Planar 16×16, X-band | Monopulse 4ch | 차세대 함정·고정 지상 |
| `planar_32x32_xband` | Planar 32×32, X-band | Monopulse 4ch | 대형 어레이 |

`Save As New`로 preset 복제 가능 (built-in 직접 수정은 거부, 09 § 5.3.8d Save 분기와 동일).

#### 5.3.9g 검증·경고

저장 시 자동 검증:
- spacing > λ/2 → grating lobe 경고
- planar_array에서 n_elements_az × n_elements_el < 4 → "어레이 너무 작음" 경고
- monopulse slope kaz/kel이 0이거나 음수 → 오류
- Pipeline 호환 검증 (예: monopulse 4ch이면 Pipeline에 monopulse stage 활성됐는지)

#### 5.3.9h Run 중에는 Radar Editor 진입 불가

Target RUNNING/PAUSED 중에는 Resource Browser에서 Radar 자원 선택 시 read-only 모드.
편집은 Target Stop 후.

---

## 5.4 Command Registry 설계

### Command 구조

```python
@dataclass(frozen=True)
class Command:
    id: str                             # "scenario.open", "sim.play"
    title: str                          # "Open Scenario..."
    category: str                       # "Scenario" / "Simulation" / "View"
    description: str
    default_shortcut: str | None        # "Ctrl+O"
    enabled_when: Callable[[], bool]    # 현재 활성 여부 판단
    execute: Callable[..., None]        # 실제 동작
    icon: str | None                    # 툴바용
```

### 기본 Command 카탈로그 (MVP 범위)

**Scenario**
- `scenario.open` — 파일 대화상자
- `scenario.close`
- `scenario.reload`
- `scenario.show_in_explorer` — OS 파일 탐색기 열기

**Simulation**
- `sim.play`, `sim.pause`, `sim.stop`
- `sim.step_forward`, `sim.step_backward`
- `sim.seek_to_frame`
- `sim.reset`

**Plugin**
- `plugin.add_from_file`
- `plugin.reload_all`
- `plugin.set_active` — 파라미터: stage, plugin_id
- `plugin.open_in_editor`

**Run**
- `run.execute` — 현재 시나리오+플러그인 조합
- `run.cancel`
- `run.compare_selected`
- `run.reload_as_snapshot`

**View**
- `view.toggle_panel` — 파라미터: panel_id
- `view.reset_layout` — 기본 레이아웃 복원
- `view.toggle_fullscreen`
- `view.save_workspace`, `view.load_workspace`

**Physics**
- `physics.run_validation` — 파라미터: domain (또는 all)
- `physics.update_golden`

**Debug**
- `debug.open_probe_panel`
- `debug.export_trace`
- `debug.replay_run`

### Command Palette UI

Ctrl+Shift+P → 검색 창 + Command 목록:

```
┌─ Command Palette ──────────────────────┐
│ > open scen|                           │
├────────────────────────────────────────┤
│ Scenario: Open...              Ctrl+O  │
│ Scenario: Open Recent                  │
│ Scenario: Reload Current               │
│ Scenario: Show in Explorer             │
└────────────────────────────────────────┘
```

- Fuzzy matching
- Category로 그룹화
- 자주 쓰는 것 상위 (단순 MRU로 시작, 가중치는 후속)

---

## 5.5 툴바 & 단축키

### 5.5.1 MVP 툴바 구성 — 두 레이어 제어 반영 (v0.15)

툴바는 **시뮬 시간 제어**(Layer 1, 바깥)와 **Target 제어**(Layer 2, 안쪽)를 시각적으로 분리.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [Simulation] ◀━━━━━━━━━━━━━━━ 바깥 레이어 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶  │
│ [▶ Sim Start] [⏸ Sim Pause] [⏹ Sim Stop] │ Speed: [×1] ×2 ×4 ×8 │ 📊 actual: 3.7x  │
│                                                                               │
│ [Target Run] ◀━━━━━━━━━━━━━━━━ 안쪽 레이어 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶ │
│ [▶ Target Run] [⏸ Target Pause] [⏹ Target Stop]  │ State: [RUNNING Run #3]    │
│                                                                               │
│ [View] [Scenario] [Plugins] ... (기타)                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

시각적 분리 원칙:
- 두 레이어는 **서로 다른 행** 또는 **구분선으로 분리**해서 혼동 방지
- 각 레이어 앞에 레이블 (`Simulation`, `Target Run`)
- Speed 컨트롤은 Sim 레이어에만 속함
- **상태 표시기** 각 레이어마다 (`STOPPED/RUNNING/PAUSED` vs `IDLE/RUNNING/PAUSED/ENDED`)

### 5.5.2 Speed Multiplier UI

```
Speed:  [×1] [×2] [×4] [×8]         ← 배수 선택 (라디오 버튼)
  └─ actual: 3.7x                   ← 실제 달성 배수 (자동 계산)
```

- 설정 배수는 사용자가 클릭
- `actual` 라벨이 실시간 표시 — 계산 능력이 모자라면 설정보다 낮게 나옴
- actual이 설정의 70% 이하면 노란 경고, 50% 이하면 빨간 경고 (무거운 Plugin 등 원인 파악)

### 5.5.3 단축키 정책

- **Space**: Target Run/Pause 토글 (미디어 플레이어 스타일) — 가장 흔히 쓰는 조작
- **Shift+Space**: Sim Start/Pause 토글
- **Ctrl+Space**: Sim Stop (+ 확인 다이얼로그)
- **Shift+Ctrl+Space**: Target Stop (+ 저장 확인 다이얼로그)
- **M**: 포지셔너 AUTO/MANUAL 토글
- **←/→/↑/↓**: MANUAL 모드일 때 포지셔너 조작
- **Shift+←/→**: 5° 단위 이동 (기본 1°)
- **1/2/3/4**: Speed ×1/×2/×4/×8
- 프레임 스텝 (Sim PAUSED 중): **[/]** (이전/다음 프레임)
- 카메라: **T/L/F/R** (Top/Left/Free/Radar)
- 팔레트: **Ctrl+Shift+P**
- 표준: **Ctrl+O** 열기, **Ctrl+S** 저장

### 5.5.4 시각화 패널 인터랙션 표준 — 휠 줌·팬 (v0.17)

모든 시각화 패널은 **일관된 마우스 조작 규약**을 따른다. 사용자가 "이 순간의 디테일"을
관찰하는 것이 추적 디버깅의 핵심이므로, 줌·팬은 MVP 필수.

#### 5.5.4a 패널별 조작 모델 개요

패널에 따라 **다른 조작 모델**을 쓴다. 2D 데이터 뷰(Google Maps 방식)와 3D 씬 뷰(Unreal 에디터 + DCC 툴 병용)는 본질이 달라 혼용하면 오히려 헷갈림.

| 패널 | 조작 모델 | 비고 |
|---|---|---|
| 3D Scene View (3rd-person) | **Unreal 에디터 + Maya/Blender 병용** | 자유 비행 + Orbit |
| 3D Scene View (Scope POV) | **2D 맵 (Google Maps 방식)** | 빔 축 기준 2D 투영 고정 |
| FFT Spectrum | **2D 맵 (축별 줌)** | 주파수 축 줌 + 시간 팬 |
| Timeline | **2D 맵 (시간 축)** | 시간 축 줌·팬 |
| Stage I/O Panel | **스크롤 + 박스 크기 줌** | 내부 시각화는 해당 패널 규약 상속 |

#### 5.5.4b 3D Scene View (3rd-person) — Unreal + DCC 병용

추적 레이더 시뮬의 공간적 전체 그림을 파악하는 주 도구. 자유도 높은 조작이 필수.

**Unreal 에디터 방식 (게임 엔진 경험자 위주)**

| 조작 | 동작 |
|---|---|
| **우클릭 드래그** | 카메라 회전 (누르고 있는 동안 Look Around) |
| **우클릭 드래그 + WASD** | FPS 스타일 자유 비행 (전/후/좌/우) |
| **우클릭 + Q/E** | 수직 이동 (위/아래) |
| **우클릭 + 휠** | 자유 비행 속도 조절 |
| **중간 버튼 드래그** | 평행 이동 (팬) |
| **휠** | 전/후 이동 (Dolly) |

**Maya/Blender 방식 (DCC 툴 경험자 위주, 같이 사용 가능)**

| 조작 | 동작 |
|---|---|
| **Alt + 좌클릭 드래그** | Tumble (선택 객체 기준 궤도 회전) |
| **Alt + 중간 드래그** | Track (팬) |
| **Alt + 우클릭 드래그** | Dolly (줌) |

두 방식은 **동시에 활성**. 사용자가 익숙한 쪽으로 자연스럽게 쓸 수 있음. 충돌하지 않음 (서로 다른 modifier·클릭 조합).

**F 키 (Focus) — 이 Workbench의 특별 명세**

언리얼 에디터의 "선택 객체 포커스"가 본 프로젝트에서는 **레이더 추적 의미와 결합**된다.

```python
def on_f_key():
    if tracker.is_primary_locked():
        # 상태 1: Primary가 현재 Lock 상태
        # 카메라가 Primary의 현재 추정 위치를 자동 추적 (매 프레임 따라감)
        camera.follow(primary_track.estimated_position)
        ui.show_badge("FOLLOW: Target #1 🎯", color=primary_orange)

    elif last_focused_target.exists():
        # 상태 2: Primary를 놓친 상태. 직전까지 Lock이었던 표적 있음
        # 카메라가 그 표적의 마지막 추정 위치로 포커스 (정지)
        camera.focus_on(last_focused_target.last_known_position)
        ui.show_badge(f"LOST: Target #{last_focused_target.id}",
                      color=warning, badge_detail=f"last lock: {last_focused_target.lock_lost_at_s}s ago")

    else:
        # 상태 3: 아직 Lock된 적이 없음
        # 자함 중심으로 포커스 (fallback)
        camera.focus_on(ownship.position)
        ui.show_badge("FOLLOW: Ownship", color=fg_2)
```

**상태 변수**:
- `last_focused_target`: 가장 최근까지 Lock이었던 표적의 스냅샷
  - `id`, `last_known_position` (last Tracker estimate), `lock_lost_at_s` (Run 내 시간)
  - Tracker가 Lock을 잃은 순간 Run Manager가 기록
  - Primary가 재획득되면 이 스냅샷 갱신 후 상태 1로 복귀

**추가 포커스 단축키**:
- **Shift + F**: 수동 선택 표적 (UI에서 클릭한 Secondary 표적)
- **Alt + F**: 자함 강제 포커스 (전체 구도 리셋)
- **더블 F**: 빠른 토글 — Primary ↔ 자함

**왜 이렇게**: 추적 레이더 디버깅에서 가장 중요한 순간은 **"표적을 놓친 순간"**. 그 순간에 카메라가 자함으로 리셋되면 사용자가 분석을 위해 다시 해당 표적을 찾아 카메라를 돌려야 함 (작업 흐름 단절). "마지막 Lock 위치 유지"는 사용자가 **놓친 상황을 바로 관찰 가능한 상태**로 유지해 추적 실패 원인 분석을 촉진.

**줌 (휠 dolly)**
- 기본 줌: 시나리오 전체가 뷰에 들어오는 거리
- 최소 줌: 표적 1m까지 근접, 최대 줌: 시나리오 전체의 3배 거리
- 줌 중심: F 포커스 대상 (Primary / Lost Target / 자함) 기준

**클릭 선택 (MVP+α)**
- 좌클릭 (Alt 없이): 표적 선택 (Selection). Shift+F의 대상이 됨
- Ctrl + 좌클릭: 클릭한 표적을 Primary로 변경
- 선택된 표적은 3D View에서 외곽선 강조 표시

#### 5.5.4c Scope POV — 2D 맵 방식

레이더 빔이 보는 시야는 본질적으로 **빔 축 기준 2D 투영**. 자유 3D 조작은 오히려 추상화를 흐리므로 의도적으로 제한.

| 조작 | 동작 |
|---|---|
| **휠** | 빔 내부 FOV 줌 (커서 위치 중심) |
| **중간 드래그** | FOV 내 팬 (빔 중심에서 벗어나 옆 영역 관찰 시) |
| **더블 클릭 빈 곳** | 기본 줌 + 빔 중심 복귀 |
| **R 키** | 기본 줌 복귀 (패널 포커스 상태) |

- 기본 줌: 빔 전체 폭 + 약간의 여백 (약 1.5배)
- 최대 줌: 빔폭의 10% 영역까지
- 항상 빔 축과 정렬 — 기울이기 불가

#### 5.5.4d FFT Spectrum / Timeline — 2D 맵 방식

| 조작 | 동작 |
|---|---|
| **휠** | 주/시간 축 줌 (커서 위치 중심) |
| **Shift + 휠** | 축 방향 팬 (줌 레벨 유지) |
| **Ctrl + 휠** | 줌 5배속 (큰 범위 빠르게) |
| **중간 드래그** | 팬 |
| **더블 클릭 / R** | 기본 줌 복귀 |

- FFT: 수직(진폭) 축은 **고정 스케일** — 진폭 비교 일관성 유지
- Timeline: 최소 줌 1 프레임, 최대 줌 Run 전체

#### 5.5.4e Stage I/O Panel

| 조작 | 동작 |
|---|---|
| **휠** | 패널 스크롤 (기본) |
| **Ctrl + 휠** | 스테이지 박스 크기 확대/축소 (한눈에 볼 박스 개수 조절) |
| **박스 내부 시각화** | 해당 패널 규약 상속 (FFTSpectrum 박스는 FFT 규약) |

#### 5.5.4f 줌 상태 표시

각 패널 우하단에 **현재 줌 레벨 UI**:

```
┌─ 3D View ─────────────────────┐
│                               │
│         (scene)               │
│                       [L+Ctrl] ← 좌상단: 현재 활성 modifier 힌트
│                               │
│              FOLLOW: Target#1 ← 우상단: 현재 포커스 대상 (3D 전용)
│                               │
│ Zoom: 1.0× [- +] [R]          │ ← 우하단 컨트롤
└───────────────────────────────┘
```

#### 5.5.4g 구현 지침

- **3D View**: PySide6 네이티브 이벤트 핸들러 커스텀. Qt의 `mouseEvent`/`keyPressEvent` 조합
- **pyqtgraph**: FFT·Timeline·Scope에 기본 지원 최대 활용, 일부 수정
- Trackpad pinch 제스처 → 휠 이벤트로 매핑 (macOS 고려)
- 휠 줌 중에는 **tooltip 자동 숨김** (UX 노이즈 줄이기)
- **Help 오버레이** (Shift+/): 현재 패널의 조작 단축키 전부 표시 — 처음 사용자가 익히는 도움말

---

### 5.5.5 커스터마이저블은 MVP 후

MVP에서는 고정 툴바. 사용자가 드래그로 재구성하는 건 "유용한데 복잡함" — 후속.
단 툴바 자체는 **Command 참조만 담아** 후속 커스터마이징이 쉽도록.

---

## 5.6 테마 & 스타일

### MVP: 단일 다크 테마

이유: 듀얼 테마 유지보수 비용 + MVP는 단순성 우선.

### 스타일 시스템

- PySide6의 QSS (Qt Style Sheet) 사용
- 색상 팔레트는 **중앙 관리** (`ui/theme.py`의 상수)
- 구성: 배경 3단계 / 전경 3단계 / 강조 / 경고 / 오류 / 성공

### 내장 아이콘

- 툴바 아이콘: Qt Material / Phosphor 등 MIT 라이선스 세트
- 라이선스 NOTICE에 명시

---

## 5.7 알림 (Notification) 시스템

### 알림 종류

- **INFO** — "B_Conflict 로드됨 (Primary=Target#1)"
- **WARNING** — "Physics Gate: 클러터 레벨 이상 징후"
- **ERROR** — "Plugin 로드 실패: SyntaxError"
- **SUCCESS** — "Run 완료: Primary 추적 Continuity=0.94, ID Switches=0"

### 표시 방법

- 우상단 **토스트 알림** (5초 후 자동 사라짐)
- 클릭하면 상세 로그 창 열림
- **Notification Center 패널**(도킹 가능)에 전체 이력

### 알림 수준 필터

사용자가 원하는 수준만 보이게:
- 기본: INFO 이상 표시
- "DEBUG도 보기" 토글 (디버깅 모드)

---

## 5.8 워크스페이스 (Workspace) 영속화

### 저장되는 것

- 도킹 상태 (각 패널 위치/크기/표시 여부)
- 열린 시나리오
- 등록된 플러그인 목록
- 카메라 프리셋
- 활성 레이어 토글

### 저장되지 않는 것

- Run 결과 (별도 저장소)
- 시나리오 데이터 원본
- 현재 재생 프레임 (재시작 시 0부터)

### 저장 위치

`~/.workbench/workspaces/default.toml`

여러 워크스페이스 지원은 MVP 후.

---

## 5.9 반응성 / 성능 요구

### 목표

- 시나리오 로드: 500ms 이내 (대형 DEM 제외)
- 프레임 렌더링: 60 FPS 목표, 최저 30 FPS
- Command 실행 피드백: 100ms 이내 (즉각 반응 느낌)
- 재생 정확도: 10 Hz 시나리오 frame rate 유지

### 성능 원칙

- **Sim 스레드와 렌더 스레드 분리** (02 아키텍처)
- **UI 블로킹 작업 금지** — 무거운 건 백그라운드
- **렌더 캐시** — 같은 지형은 한 번만 메시화
- **증분 업데이트** — 매 프레임 전체 재생성 대신 바뀐 것만

---

## 5.10 접근성 / 다국어

### MVP: 한국어 단일

- UI 문자열은 **모두 한 곳**(`ui/strings.py`)에 모음
- 나중에 gettext 등으로 전환 쉽게

### 접근성

- 모든 액션이 키보드만으로 가능해야 함 (Command Palette가 이걸 보장)
- 고대비 모드는 MVP 후
- 스크린 리더는 고려 사항이지만 MVP 범위 밖

---

## 섹션 상태

- 5.1 철학 — ✅
- 5.2 기본 레이아웃 — ✅
- 5.3 패널 — 🟡 (세부 위젯 구현 시 조정)
- 5.4 Command — ✅
- 5.5 툴바/단축키 — 🟡
- 5.6 테마 — ✅
- 5.7 알림 — 🟡
- 5.8 워크스페이스 — ✅
- 5.9 반응성 — 🟡
- 5.10 접근성 — 🟡

---

👉 다음 섹션: [06_topics.md](06_topics.md)
