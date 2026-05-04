# 10. Workspaces — Editor / Simulator / Physics Lab 구조 분리

**최종 갱신**: 2026-05-02 (v0.40 — Physics Lab Workspace 추가, 두 Workspace → 세 Workspace)

**관련 문서**: [01 vision_scope](01_vision_scope.md), [05 ui_ux](05_ui_ux.md), [09 radar_platforms](09_radar_platforms.md), [19 physics_lab](19_physics_lab.md)

## 10.1 왜 이 문서가 있나

v0.18까지 Workbench는 암묵적으로 **"Simulator" 단일 성격** 으로 설계됐다. 표적·레이더·맵을
포함한 Scenario를 로드해 DSP Plugin의 추적 성능을 검증하는 것이 주 목적이었다.

v0.19에서 **Scenario Editor** 를 추가한다. 맵·레이더·표적 궤적 등 시뮬레이션 입력
자원들을 편집·조립하는 도구다.

**v0.40에서 Physics Lab 추가**. 물리 모델 검증·디버깅·진화 환경 — Bret Victor 스타일 인터랙티브 (3-pane Code | Visualization | Parameters). 19 § 19.5 참조.

세 Workspace 는 **성격이 다른 작업**이다:

| Editor | Simulator | Physics Lab (v0.40) |
|---|---|---|
| 자원 **편집·조립** | 자원 **실행·평가** | 물리 모델 **검증·진화** |
| 시간 진행 없음 | 시뮬 시간 흐름 중심 | 4 시간 모드 (Static/Run/Compare/Sweep) |
| 저장이 주 동작 | Run이 주 동작 | 인터랙티브 슬라이더 + 라이브 갱신 |
| "무엇을 만들 것인가" | "만들어진 걸로 무엇을 관찰할까" | "물리가 정확한가" |

세 Workspace 를 하나의 UI에 평면적으로 펼치면 혼란스럽고, 분리된 세 프로그램으로 만들면
인프라 중복이 크다. **단일 프로그램 + 세 Workspace** 로 이 긴장을 해결한다.

## 10.2 Workspace 정의

### 10.2.1 Workspace란 무엇인가

Workspace는 **특정 작업 성격에 최적화된 UI 구성**이다.

- **DockLayout** (어떤 패널이 어디 배치되는가)
- **ToolBar** (어떤 액션이 상단에 있는가)
- **Command Set** (단축키·팔레트에 어떤 명령이 활성화되는가)
- **열린 파일·상태** (Workspace마다 독립적으로 유지)

VS Code의 Activity Bar 전환(Explorer / Source Control / Run and Debug 등)과 유사한 개념.

### 10.2.2 Workspace와 Mode의 관계

v0.13의 "Mode" (DSP / NN)와 Workspace는 **다른 층위**다:

```
Workbench
├── Editor Workspace
│    └── (내부 모드 없음 — 자원 편집에만 집중)
│
└── Simulator Workspace  ← 기본
     ├── DSP Mode        (추적 성능 검증)
     └── NN Mode         (NN 개발)
          ├── Step 1 (Dataset Extraction)
          └── Step 2 (NN Evaluation)
```

- **Workspace**: 무엇을 하는가 (편집 / 실행)
- **Mode**: Simulator 안에서 어떤 목적인가 (DSP 검증 / NN 개발)

한 번에 **하나의 Workspace, 그 안에서 하나의 Mode**가 활성. 전환은 Workspace 단위 또는 Mode 단위 독립적으로.

### 10.2.3 MVP Workspace 목록

| Workspace | 목적 | 상태 |
|---|---|---|
| **Simulator** | 시뮬 실행·DSP 평가·NN 개발 | v0.1부터 있던 것의 연속 |
| **Editor** | 자원 편집 (Map·Radar·Targets·Scenario 조립) | v0.19 신설 |

미래 후보 (MVP 후):
- **Analysis** — Trace·Run 결과 심화 분석 (현재는 Run Compare 기능이 Simulator 안에 있음)
- **Training** — NN 학습 실행 관리 (현재는 외부 CLI)

## 10.3 두 Workspace 비교

> ⚠️ **v0.27~v0.35 정합**: 아래 패널 목록은 v0.26 시점. 후속 변경 반영 필요 (정식 갱신은 별도 세션):
>
> **Simulator Workspace 추가 패널**:
> - Domain Settings 패널 (v0.29, 11 § 11.11) — Map 밖 OutsideEnvironment 토글
> - Atmosphere Panel (v0.28, 15 § 15.4) — visibility/sky/rain 시각 제어
> - Glint 시각화 레이어 (v0.34, 14 § 14.10) — multi-scatterer 표적의 apparent_position
> - Multipath 디버그 레이어 (v0.34, 08 § 8.5b.1)
>
> **Editor Workspace**:
> - Map Editor 도구 표에 **Flatten Area** 추가 (v0.33, 13 § 13.4 / 12 § 12.11.1)
> - **Plugin Manager 확장** (v0.35) — `[Install Package...]` 버튼, 설치된 `.trsim-pkg` 목록
>   (17 § 17.2.4)

### 10.3.1 Simulator Workspace (기존)

**역할**: 조립된 Scenario를 로드해 레이더 DSP·추적 알고리즘을 실시간 실행·평가.

**주요 패널**:
- Scenario Explorer (조립된 Scenario 선택)
- 3D Scene View (3rd-person + Scope POV)
- FFT Spectrum
- Plugin Manager
- Run Panel
- Stage I/O Panel
- Properties
- (NN Mode) Dataset Builder, Evaluation Panel

**시간 모델**: 두 레이어 (Simulation Clock + Target Run)
**주 동작**: Sim Start → Target Run → 관찰·메트릭

### 10.3.2 Editor Workspace (v0.19 신설)

**역할**: 시뮬레이션에 쓰일 자원(Map·Radar·Targets)을 편집·저장·조립.

**상세 설계**: [13_editor_workspace.md](13_editor_workspace.md) (v0.26 신설).

**주요 패널** (MVP 기준):
- Resource Browser (좌측 상시 사이드바, maps / radars / targets / scenarios)
- Scenario Composer (메인 활동 — References + Installation + Composition + Validation)
- Map Editor (경량 — Land/Sea Brush + Spot Edit + Add Building)
- Radar Editor (Antenna + RX 채널 통합 폼, v0.25)
- Target Trajectory Editor (메타 편집 + 시각화, trajectory 편집은 MVP 후)

**시간 모델**: 없음 — 편집 작업에 시뮬 시간은 무관
**주 동작**: Open → Edit → Save

### 10.3.3 공유 인프라

두 Workspace 모두 다음을 공유:

- **CommandRegistry** (명령 체계)
- **EventBus** (상태 전파)
- **PluginLoader** (Editor에서는 Preset 자원으로, Simulator에서는 DSP 구현체로 쓰임)
- **ConfigManager** (설정)
- **ThemeManager** (다크 테마 등)
- **DockManager** (패널 도킹·상태 저장/복원)
- **Workspace별 독립 DockLayout** (각 Workspace는 자신의 도킹 구성 기억)

## 10.4 Workspace 전환

### 10.4.1 전환 UI

**상단 좌측 Activity Selector** (VS Code Activity Bar와 유사):

```
┌─────────────────────────────────────────────────────────┐
│ [📐 Editor] [▶ Simulator]   ← Workspace 탭               │
│   (active)                                              │
├─────────────────────────────────────────────────────────┤
│  (Workspace별 상단 툴바)                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│              (Workspace별 DockLayout)                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

- Workspace 전환 시 **즉시** DockLayout·Toolbar 교체
- 전환 중 열린 파일·진행 중 작업은 **보존**되어 다시 돌아오면 복구

**단축키**:
- `Ctrl+Shift+E`: Editor Workspace
- `Ctrl+Shift+S`: Simulator Workspace
- `Ctrl+Tab`: Workspace 토글

### 10.4.2 전환 중 상태 처리

#### Simulator에서 Editor로
- **Sim이 RUNNING이면 확인 다이얼로그**: "시뮬레이션 진행 중입니다. Editor로 전환하면 자동 Pause됩니다. 계속?"
- 확인 시 Sim Pause 후 전환
- 진행 중이던 Run도 PAUSED 상태로 보존
- 복귀하면 그 상태에서 재개 가능

#### Editor에서 Simulator로
- **저장 안 된 변경 있으면 확인 다이얼로그**: "저장하지 않은 변경이 있습니다. 저장하시겠어요? (저장 / 저장 안함 / 취소)"
- 보존 후 전환

#### 자원 변경의 반영
- Editor에서 Scenario 저장 후 Simulator로 전환
- Simulator의 Scenario Explorer가 해당 Scenario를 **새로 고침 필요** 표시
- "Reload"로 최신 버전 가져올 수 있음
- Run 중인 경우 자동 반영 안 함 (재현성 보장) — Run 끝난 후 Reload 권장

### 10.4.3 Workspace 간 "이어서 하기" 지원

**일반적 워크플로**:

```
1. Editor에서 Scenario 조립·저장
2. "Open in Simulator" 버튼 클릭
3. Simulator Workspace로 자동 전환 + 해당 Scenario 자동 로드
4. Installation 확인·Run
5. 결과 보고 Editor로 돌아와 수정
```

이 흐름을 매끄럽게 하기 위해 **Context 전달** 메커니즘:
- Editor의 "Test in Simulator" 명령 → Simulator 전환 + 현재 편집 중인 Scenario 자동 로드
- Simulator의 "Back to Editor" 명령 (Run 종료 후 활성화) → Editor 전환 + 방금 실행한 Scenario 열기

## 10.5 Dock Layout 저장 정책

각 Workspace는 **독립된 DockLayout**을 가진다.

```
~/.workbench/
├── layouts/
│   ├── editor.json          ← Editor Workspace 도킹 상태
│   └── simulator.json       ← Simulator Workspace 도킹 상태
```

- 사용자가 각 Workspace에서 패널을 재배치하면 해당 layout에만 저장
- Workspace 간 배치는 간섭 없음
- Workspace마다 "Reset Layout" 명령 제공 (기본 레이아웃 복귀)

## 10.6 아키텍처 영향

### 10.6.1 02 architecture 블록도

UI Layer에 **WorkspaceManager**가 추가된다:

```
UI Layer
├── WorkspaceManager (Editor / Simulator 전환)
│    ├── Editor Workspace
│    │    ├── ResourceBrowser
│    │    ├── MapEditor
│    │    ├── RadarEditor
│    │    ├── TargetEditor
│    │    └── ScenarioComposer
│    └── Simulator Workspace  (기존 Main Window의 역할)
│         ├── ScenarioExplorer
│         ├── 3DSceneView
│         ├── FFT, Plugin, Run, Stage I/O, ...
│         └── Mode Switcher (DSP / NN)
├── ToolBar (Workspace별 교체)
├── CommandPalette (Workspace별 명령 활성화)
├── StatusBar (Workspace 상태 표시)
└── DockManager (Workspace별 독립 layout)
```

### 10.6.2 의존성

- **Editor Workspace → 공유 인프라**: 가능
- **Simulator Workspace → 공유 인프라**: 가능
- **Editor Workspace ↔ Simulator Workspace 직접 참조**: **금지**
  - Workspace 간 통신은 EventBus 또는 WorkspaceManager 경유
  - 한 Workspace가 다른 Workspace의 내부 상태를 알면 안 됨 (교체 가능성 훼손)

### 10.6.3 Command 네임스페이스

- `editor.*`: Editor Workspace 전용 명령 (`editor.new_map`, `editor.save_scenario`, ...)
- `simulator.*` 또는 기존 `sim.*` / `target.*`: Simulator 관련
- `workspace.*`: 전환·공통 (`workspace.switch_to_editor`, `workspace.reset_layout`)
- 공유 명령 (`file.save`, `file.open_recent` 등): 네임스페이스 없이

## 10.7 MVP 구현 우선순위

### MVP 포함
- **Simulator Workspace**: v0.18까지의 모든 설계가 여기 속함
- **Editor Workspace 뼈대**: ResourceBrowser + Scenario Composer만
- **Workspace 전환 UI**: Activity Selector + 단축키
- **Dock Layout 분리 저장**

### MVP 후
- **Map Editor** 풀 기능 (DEM 불러오기, 건물 편집)
- **Radar Editor** 풀 기능 (Platform 파라미터 편집, Preset 관리)
- **Target Trajectory Editor** 그래픽 + 표 병용
- **Analysis Workspace** (Run 심화 분석)

즉 MVP에서는 Editor Workspace가 "자원 선택·조립만 가능"한 최소 형태. 표적 궤적 같은 편집은
여전히 CSV 직접 편집 또는 외부 도구. Editor의 완전한 편집 기능은 **MVP 후**.

## 10.8 이 결정으로 인한 다른 문서 영향

- **01 vision_scope**: "두 Workspace" 프레임 반영
- **02 architecture**: UI Layer에 WorkspaceManager 추가
- **05 ui_ux**: 각 Workspace의 레이아웃·툴바·명령 분리 기술
- **09 radar_platforms**: Installation 화면은 **Editor Workspace의 Scenario Composer** 안에서 활용되는 모듈. Simulator Workspace에서는 Scenario 로드 시 읽기만
- **00_README**: v0.19 이력

## 10.9 자원 저장 구조 — 참조 기반 (v0.20)

> ⚠️ **v0.35 정합**: 본 섹션은 v0.20 시점 자원 라이브러리 모델. v0.35 DLC 시스템과의 통합:
>
> - **ResourceLibrary 확장** (17 § 17.4.3, 02 § 2.2): 3개 출처 우선순위
>   1. **User** (`~/.trsim/resources/`) — 최우선
>   2. **Packages** (`~/.trsim/packages/<id>/resources/`) — DLC 제공
>   3. **Built-in** (TRsim 설치 디렉토리) — 기본
> - ID 충돌 시 우선순위 높은 게 이김. UI에 출처 표시 ("User" / "Package: trsim-busan-port" / "Built-in")
> - DLC 자원도 `[refs]` 시스템으로 동일하게 참조 가능 — 시나리오 작성자는 출처 무관
> - content_hash·재현성 모델은 v0.20 그대로 유효 (DLC 자원도 hash 계산 동일)

### 10.9.1 핵심 원칙

Editor Workspace에서 관리하는 자원은 **참조 기반 구조(C)**로 저장된다. 자원(Map, Radar,
Targets)은 독립된 파일로 라이브러리에 존재하며, Scenario는 이 자원들을 **ID로 참조**한다.

```
~/my_workbench_proj/
├── resources/
│   ├── maps/
│   │   ├── EastCoast_50km/
│   │   │   ├── map.toml          ← 메타데이터 + content hash
│   │   │   ├── terrain.tif       ← DEM
│   │   │   └── buildings.csv     ← 건물 목록 (있으면)
│   │   ├── Harbor_10km/
│   │   └── OpenSea_100km/
│   ├── radars/
│   │   ├── fmcw_corvette/
│   │   │   └── radar.toml
│   │   ├── fmcw_tower/
│   │   └── fmcw_destroyer/
│   └── targets/
│       ├── CrossingShips/
│       │   ├── targets.toml      ← 메타데이터 + hash
│       │   └── trajectories.csv  ← 표적별 waypoint·시간
│       ├── SingleApproach/
│       └── ...
│
├── scenarios/
│   └── B_Conflict_hilltop/
│       └── scenario.toml         ← map_id, radar_id, targets_id + 조합 설정
│
├── plugins/
├── datasets/
└── runs/
```

### 10.9.2 왜 참조 구조

자원 재사용성이 설계의 핵심 요구다:

- 같은 Map에 **다양한 Radar 배치** 실험 → Map 1개, Radar 여러 개
- 같은 Radar로 **다양한 표적 상황** 비교 → Radar 1개, Targets 여러 개
- 같은 표적 궤적을 **다른 Map** 에서 → Targets 1개, Map 여러 개

번들 방식(A)으로 저장하면 같은 Map이 N번 중복되며, DEM이 MB~GB 단위일 경우 치명적.
참조 구조는 자원을 공유하고, 수정은 한 번에 관련 Scenario 모두에 반영된다.

### 10.9.3 자원 식별·참조

각 자원은 **디렉토리 이름 = ID** 로 참조된다:

```toml
# scenarios/B_Conflict_hilltop/scenario.toml

name = "B_Conflict_hilltop"
description = "Crossing ships from hilltop radar"
version = "1.0"

[refs]
map_id = "EastCoast_50km"
map_hash = "sha256:def456..."            # 참조 시점의 hash

radar_id = "fmcw_tower"
radar_hash = "sha256:ghi789..."

targets_id = "CrossingShips"
targets_hash = "sha256:jkl012..."

[composition]
# Scenario 고유 메타 (참조되는 자원에 종속되지 않는 것)
primary_target_id = 1
seed = 42
duration_s = 60
frame_rate_hz = 20

[platform_install]
# v0.18 Installation 정보 — 이 조합에서의 레이더 배치
install_east_m = 1250.0
install_north_m = 3400.0
install_altitude_m = 87.3
initial_az_deg = 180.0
initial_el_deg = 0.0
```

**핵심 필드**:
- `[refs]`: 참조 자원의 ID와 hash (hash는 참조 생성 시점 고정)
- `[composition]`: Scenario 고유 설정
- `[platform_install]`: Installation 정보 (v0.18). 같은 Radar를 다른 위치에 놓는 실험이 가능해짐

### 10.9.4 자원 파일 구조 예시

**Map**:
```toml
# resources/maps/EastCoast_50km/map.toml

name = "EastCoast_50km"
description = "50km stretch of east coastline with harbor"
version = "1.2"
content_hash = "sha256:def456..."       # 자동 계산

[origin]
lat_deg = 37.5665
lon_deg = 126.9780
alt_m = 0.0

[bounds]
east_min_m = -25000.0
east_max_m =  25000.0
north_min_m = -25000.0
north_max_m =  25000.0

[terrain]
source_file = "terrain.tif"            # 같은 폴더 내 DEM 파일
resolution_m = 10.0

[buildings]
source_file = "buildings.csv"          # 있으면
count = 127
```

**Radar**:
```toml
# resources/radars/fmcw_corvette/radar.toml

name = "fmcw_corvette"
description = "FMCW Triangle radar on 500t corvette"
version = "1.0"
content_hash = "sha256:ghi789..."

[platform]
platform_id = "corvette_500t"
category = "maritime"
# ... (v0.18 § 9.5 Platform 필드들)

[radar_model]
model_id = "fmcw_triangle_v1"
# ... (08 § 8.2 Waveform 필드들)

[rx_array]
# ...
```

**Targets**:
```toml
# resources/targets/CrossingShips/targets.toml

name = "CrossingShips"
description = "Two ships crossing paths at ~12km"
version = "1.0"
content_hash = "sha256:jkl012..."

source_file = "trajectories.csv"

[[target]]
id = 1
rcs_model = "simple_aspect"
rcs_params = { peak_dbsm = -5.0 }

[[target]]
id = 2
rcs_model = "simple_aspect"
rcs_params = { peak_dbsm = -8.0 }
```

`trajectories.csv`는 시간 × 위치 데이터 (기존 v0.17 구조 유지).

## 10.10 재현성 보장 — Content Hash + Run Manifest (v0.20)

### 10.10.1 왜 재현성이 중요한가

본 Workbench의 주 목적은 **"DSP 구현 A vs B의 추적 성능 비교"** 다. 자원이 바뀌면 비교가
무의미해진다. 또한 시간이 지난 후 **과거 실험 결과를 다시 실행**해야 할 때가 있다
(논문 재현, 디버깅, 회귀 검증).

v0.14에서 이미 **Plugin에 `source_hash`** 를 도입했다. v0.20에서 이 원칙을 자원 전체로
확장한다.

### 10.10.2 Content Hash 계산 규칙

각 자원 파일(`map.toml`, `radar.toml`, `targets.toml`)의 `content_hash` 필드:

- **자동 계산**: 자원 저장 시 Workbench가 계산해 `content_hash` 필드에 기록
- **제외 대상**: `content_hash` 필드 자체, 주석, 날짜·시간 메타 (변동 요소 제외)
- **포함 대상**: 모든 실제 값 + 참조 파일 (DEM, CSV) 의 해시
- **알고리즘**: SHA-256 (Plugin과 일치)

외부 참조 파일(DEM 등)은 별도 hash 계산 후 메인 파일 hash에 합산:

```python
def compute_map_hash(map_dir: Path) -> str:
    h = hashlib.sha256()
    meta = parse_toml(map_dir / "map.toml")
    # content_hash 필드 제외
    meta_copy = {k: v for k, v in meta.items() if k != "content_hash"}
    h.update(canonical_json(meta_copy).encode())

    # 참조 파일들
    for ref_file in ["terrain.tif", "buildings.csv"]:
        path = map_dir / ref_file
        if path.exists():
            h.update(path.read_bytes())

    return "sha256:" + h.hexdigest()
```

### 10.10.3 Run Manifest 확장

Run 실행 시 **사용된 자원의 hash가 Run Manifest에 기록**된다:

```toml
# ~/.workbench/runs/run_0042/manifest.toml

run_id = "run_0042"
started_at = "2026-04-24T09:30:00Z"
completed_at = "2026-04-24T09:31:12Z"
termination = "COMPLETED"

[scenario]
id = "B_Conflict_hilltop"
hash = "sha256:abc..."              # scenario.toml 전체 hash

[resources]
map_id = "EastCoast_50km"
map_hash = "sha256:def..."          # 실행 시점의 map content hash

radar_id = "fmcw_tower"
radar_hash = "sha256:ghi..."

targets_id = "CrossingShips"
targets_hash = "sha256:jkl..."

[plugins]
detector = { path = "plugins/my_cfar.py", hash = "sha256:mno..." }
pairing = { path = "plugins/my_pair.py", hash = "sha256:pqr..." }

[result]
# ... metrics
```

### 10.10.4 자원 수정 시 동작

사용자가 자원(예: Map)을 수정하면:

1. **자동**: Editor가 `content_hash` 재계산 후 `map.toml`에 저장
2. **Scenario 확인**: 이 Map을 참조하는 Scenario의 `[refs].map_hash`가 옛 값 그대로
   → Scenario Explorer에서 **"자원 업데이트 있음"** 뱃지 표시
3. **사용자 선택** (Scenario를 Load할 때):
   - **(a) 최신 버전 사용** → `scenario.toml`의 `map_hash`를 갱신
   - **(b) 현 상태 유지** → Scenario는 그대로, 다음 Run은 경고 표시

### 10.10.5 과거 Run 재실행 시 동작

사용자가 `runs/run_0042`를 "재실행" 하려 할 때:

```
1. Run Manifest 읽음 → [resources] 섹션의 hash 확인
2. 현재 라이브러리의 자원 hash와 비교:
   - 모두 일치 → 정상 재실행
   - 불일치 → 다이얼로그:
     ┌─ Resource Mismatch ──────────────────────────────┐
     │ 이 Run이 참조하는 자원이 변경되었습니다:           │
     │                                                  │
     │ • EastCoast_50km                                 │
     │   Run 시점: sha256:def456...                      │
     │   현재:    sha256:xyz789...                      │
     │                                                  │
     │ 어떻게 하시겠습니까?                              │
     │                                                  │
     │   ( ) 현재 자원으로 재실행 (다른 결과 나올 수 있음) │
     │   ( ) 취소                                       │
     │   ( ) Resource History에서 원 버전 복원 시도 🔒    │
     │                                                  │
     │             [취소]   [재실행]                     │
     └──────────────────────────────────────────────────┘
```

**Resource History 복원** 옵션은 MVP+α. MVP는 (1) 정상 재실행 / (2) 현재 자원으로 강제
재실행 / (3) 취소 3개만.

### 10.10.6 Resource History (MVP+α)

자원 수정 시 **이전 버전을 hash 키로 자동 보관**:

```
~/my_workbench_proj/.workbench/resource_history/
├── maps/
│   ├── sha256_def456.../          ← 옛 버전 Snapshot
│   │   ├── map.toml
│   │   └── terrain.tif
│   └── sha256_xyz789.../          ← 최신 버전
├── radars/
└── targets/
```

- 정책: 최근 10개 버전 유지 (또는 용량 제한 설정)
- 수동 정리 명령: `workbench-cli prune-history`
- MVP 포함 안 함 — 재현성의 근본 원리만 MVP

## 10.11 Reproducibility Bundle — 다른 PC에서 재현 (v0.20)

### 10.11.1 목적

참조 구조(C)는 같은 PC 내 자원 관리에 최적이지만, **다른 PC로 Scenario/Run을 이관**할 때
참조가 깨진다. 이를 위해 **Bundle export/import** 기능을 제공:

- **Bundle Export**: 하나의 파일로 Scenario(또는 Run) + 참조된 자원 전부 + plugins + manifest
- **Bundle Import**: 받은 Bundle을 자신의 라이브러리에 자동 병합

### 10.11.2 Bundle 종류

#### Scenario Bundle
"이 Scenario를 다른 PC에서 실행 가능하게" — Editor에서 export.

- 내용: `scenario.toml` + 참조된 map/radar/targets 자원 전체 + 메타
- 확장자: `.scnbundle` (실제는 `.tar.gz`)
- 용도: 동료에게 Scenario 전달, 백업

#### Run Bundle (재현 패키지)
"이 Run을 다른 PC에서 똑같이 재실행 가능하게" — Run Panel에서 export.

- 내용: Run Manifest + 참조된 Scenario 번들 + Plugin 코드 + 원본 Trace (선택)
- 확장자: `.runbundle`
- 용도: 논문 재현, 회귀 검증, 버그 리포트

### 10.11.3 Bundle 구조

```
B_Conflict_hilltop.scnbundle  (tar.gz)
├── manifest.toml                      ← Bundle 메타 (생성자, 시간, Workbench 버전)
├── scenario/
│   └── B_Conflict_hilltop/
│       └── scenario.toml
├── resources/
│   ├── maps/EastCoast_50km/
│   │   ├── map.toml
│   │   └── terrain.tif
│   ├── radars/fmcw_tower/
│   │   └── radar.toml
│   └── targets/CrossingShips/
│       ├── targets.toml
│       └── trajectories.csv
└── README.md                          ← 이 Bundle 설명 (자동 생성 + 사용자 편집 가능)
```

`.runbundle`은 여기에 `run/` 폴더와 `plugins/` 폴더 추가.

### 10.11.4 Export 동작

**메뉴**: `File > Export Bundle...` (Editor 또는 Simulator Workspace 모두에서 가능)

```
1. Bundle 대상 선택 다이얼로그:
   - Current Scenario (scenario.toml에 참조된 모든 자원 포함)
   - Specific Run (Run Manifest 기반)

2. 옵션:
   [x] 자원 파일 (DEM 등) 포함
   [ ] 원본 Trace 포함 (Run Bundle만, 용량 큼)
   [x] Plugin 소스 포함
   [x] README 자동 생성 (편집 가능)

3. 저장 위치·파일명 선택
4. 진행 바 → 완성

5. 완성 후 안내:
   "B_Conflict_hilltop.scnbundle (42 MB) 생성됨.
    이 파일을 다른 PC에서 Import하면 동일 환경이 복원됩니다."
```

### 10.11.5 Import 동작

**메뉴**: `File > Import Bundle...`

```
1. Bundle 파일 선택
2. 내용 미리보기:
   ┌─ Import Preview ─────────────────────────────┐
   │ Bundle: B_Conflict_hilltop.scnbundle          │
   │ Created: 2026-04-24 by Alice                 │
   │ Workbench: v0.20 (current: v0.20 — match ✓)  │
   │                                              │
   │ 포함 내용:                                    │
   │ ✓ Scenario: B_Conflict_hilltop               │
   │ ✓ Map: EastCoast_50km (새로 추가)             │
   │ ⚠ Radar: fmcw_tower (로컬과 동일 hash)        │
   │ ⚠ Targets: CrossingShips (로컬 hash 다름!)    │
   │                                              │
   │ 충돌 처리:                                    │
   │   ( ) 로컬 버전 유지 (Bundle 자원 무시)       │
   │   (•) Bundle 버전을 새 이름으로 Import        │
   │       (CrossingShips_imported_2026-04-24)    │
   │   ( ) Bundle 버전으로 덮어쓰기 (로컬 수정분 손실) │
   │                                              │
   │            [취소]  [Import]                   │
   └──────────────────────────────────────────────┘

3. Import 실행:
   - Scenario/자원을 라이브러리의 해당 위치에 복사
   - Hash 일치 확인 (손상 검증)
   - Resource Browser 자동 리프레시

4. 완료 후: "Bundle import 성공. Simulator로 전환해서 실행하시겠어요? [예][아니오]"
```

### 10.11.6 Bundle 버전 호환성

Bundle Manifest에 **Workbench 버전**이 기록되어, 큰 버전 차이 시 Import에 경고:

- **Same major** (0.20 → 0.20.x): 무조건 호환
- **Different minor** (0.20 → 0.21): 경고 후 Import 허용 (대부분 호환)
- **Different major** (0.x → 1.x, 미래): 마이그레이션 스크립트 제안

### 10.11.7 Bundle은 참조 구조를 대체하지 않음

**중요**: Bundle은 **이관 도구**일 뿐, 일상 작업은 여전히 참조 구조(§ 10.9)로 진행한다.
Bundle을 주 저장 형식으로 쓰면 자원 재사용성이 없어진다. Bundle은 **PC 간 이동** 또는 **장기
아카이브** 목적.

## 10.12 Open Questions

MVP 후 또는 실사용 후 결정:

- Editor에서 편집 중 Scenario를 **저장 없이 Simulator에서 시험 실행** 가능 여부 (in-memory handoff)
- Workspace마다 독립된 Command Palette 히스토리 유지?
- Workspace 간 drag-and-drop 자원 전달
- 커스텀 Workspace 정의
- **Resource History** 정책 — 몇 개까지 유지? 용량 관리? (§ 10.10.6)
- **Bundle 서명·검증** — 악의적 Bundle 가드 필요한가? (조직 외부 공유 시)
- **Cloud Resource Registry** — 조직 내 자원 공유 레지스트리 (MVP 후)
- **부분 자원 편집** — Scenario 열린 상태에서 참조된 Map을 수정하면 즉시 반영 vs 저장 시 반영?

## 섹션 상태

- 10.1~10.2 개요 — ✅
- 10.3 두 Workspace 비교 — ✅ (Editor 상세는 후속)
- 10.4 전환 동작 — ✅
- 10.5 Layout 저장 — ✅
- 10.6 아키텍처 영향 — ✅
- 10.7 MVP 범위 — ✅
- 10.8 타 문서 영향 — ✅
- 10.9 자원 저장 구조 (참조 기반) — ✅ (v0.20 신설)
- 10.10 재현성 (Content Hash + Manifest) — ✅ (v0.20 신설). 10.10.6 Resource History는 🟡 MVP+α
- 10.11 Reproducibility Bundle — ✅ (v0.20 신설)
- 10.12 Open Questions — 🟡

---

👉 이전: [09_radar_platforms.md](09_radar_platforms.md)
