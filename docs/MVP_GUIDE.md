# TRsim MVP — 테스트 가이드 (2026-05-14 rev11)

`docs/MVP_USAGE.md` 가 "어떻게 쓰나" 라면, 이 가이드는 "어떻게
**확인** 하나" — MVP 가 정상 동작하는지 항목별 명령 + 기대 결과
+ 실패 시 조치. 모든 명령은 repo 루트
(`C:\Workspaces\Claude\Tracking Radar Simulator\trsim`) 에서 PowerShell.

각 섹션 끝의 ☐ 는 직접 체크. 전부 ✓ 면 MVP 본격 완성 확인 OK.

> **rev11 갱신점** (2026-05-12 ~ 2026-05-14):
> - **L1-L6**: Simulator 8 panel 전체가 RunController tick_completed
>   에 묶여 live data binding (Run / FFT / RD / Scene 3D / PluginMgr /
>   StageIO / Properties / ScopePOV)
> - **M1+M2**: Map Editor DEM import → bounds 자동 wire,
>   Composer Installation 의 terrain altitude + coverage stats live
> - **P1-P8**: HIL post-MVP lock / Validation Bench 일반화 /
>   Phase 3 Profile mode toggle / Phase 5 #18+#19 재현성 정량 /
>   arrow-key manual pointing / NN stub lock / Editor preview 3종 /
>   SDK manifest 이동
> - 신규 CLI flags: `--no-3d-viewer`, `--mode {off,explicit,live}`,
>   `--explicit-every N`
> - pytest 1690 → **2790** PASS, 5 contracts KEPT.

---

## 0. 사전 sanity check (1 분)

### 0.0 origin/main 동기화

```powershell
git pull --ff-only
```

**기대**: `Already up to date.` 또는 fast-forward 메시지.

console-script wrapper 재생성이 필요할 때 (entry point 자체가 새로
추가됐을 때) `pip install -e . --no-deps` 도 함께. editable install 의
entry point 가 `workbench.__main__:main` 으로 고정이라 소스 변경만
으로 trsim.exe 가 새 코드를 호출함 — pull 만 해도 대개 충분.

`No module named pip` 에러 (uv venv 등):

```powershell
.\.venv\Scripts\python.exe -m ensurepip --upgrade
# 또는 venv 재생성:
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 0.1 venv + 실행파일 존재

```powershell
Test-Path .venv\Scripts\trsim.exe
Test-Path .venv\Scripts\python.exe
```

**기대**: 둘 다 `True`.

### 0.2 PySide6 + pyqtgraph + pyvista import sanity

```powershell
.\.venv\Scripts\python.exe -c "import PySide6, pyqtgraph, pyvista; print(PySide6.__version__, pyqtgraph.__version__, pyvista.__version__)"
```

**기대**: `6.11.x  0.13.x  0.x` 한 줄. import 에러 없음.

실패 시: `pip install -e ".[dev]"` 다시.

### 0.3 trsim 버전 + 도움말

```powershell
.\.venv\Scripts\trsim.exe --version
.\.venv\Scripts\trsim.exe --help
.\.venv\Scripts\trsim.exe ui --help
.\.venv\Scripts\trsim.exe profile --help
```

**기대**:
- `trsim 0.X.Y`
- `ui --help` 에 **`--workspace`, `--no-dlc`, `--no-3d-viewer`** 3 옵션
- `profile --help` 에 **`--mode {off,explicit,live}`, `--explicit-every N`** 표시

☐ 환경 sanity 통과

---

## 1. 비-UI CLI 검증 (헤드리스 가능, ~ 30 초)

### 1.1 FrameProfiler smoke (default = live mode)

```powershell
.\.venv\Scripts\trsim.exe profile --scenario demo --frames 20
```

**기대**: JSON 한 덩어리 stdout. `mode: "live"`, `frames: 20`,
`recorded_frames: 20`. `reports` 안에 `detector` + `tracker` 두 entry
(`avg_ms`, `p50_ms`, `p95_ms`, `p99_ms` 모두 양수).

### 1.2 Phase 3 Profile mode toggle (P3, plan/03 § 3.5.0c)

```powershell
# off — 측정 비활성, recorded_frames = 0, reports = []
.\.venv\Scripts\trsim.exe profile --scenario demo --frames 10 --mode off

# explicit — 매 5번째 frame 만 기록 → 0/5/10/15 = 4 frames 기록
.\.venv\Scripts\trsim.exe profile --scenario demo --frames 20 --mode explicit --explicit-every 5

# live — 매 frame (default 와 같음)
.\.venv\Scripts\trsim.exe profile --scenario demo --frames 20 --mode live
```

**기대**:
- `--mode off` → `recorded_frames: 0`, `reports: []`
- `--mode explicit --explicit-every 5` → `recorded_frames: 4`
- `--mode live` → `recorded_frames: 20`

### 1.3 Run manifest smoke

```powershell
$tmp = "$env:TEMP\trsim_demo_run"
New-Item -ItemType Directory -Force -Path "$tmp\resources\maps","$tmp\resources\radars","$tmp\resources\targets" | Out-Null
'id = "demo_map"' | Out-File -Encoding utf8 "$tmp\resources\maps\demo_map.toml"
'id = "demo_radar"' | Out-File -Encoding utf8 "$tmp\resources\radars\demo_radar.toml"
'id = "demo_target"' | Out-File -Encoding utf8 "$tmp\resources\targets\demo_target.toml"

.\.venv\Scripts\trsim.exe run --scenario demo --resources "$tmp\resources" `
  --map demo_map --radar demo_radar --target demo_target --out "$tmp\runs\demo"

Get-ChildItem "$tmp\runs\demo"
```

**기대**: stdout 5 줄 (`run_id`, `out_dir`, `map_hash`, `radar`,
`target`). `$tmp\runs\demo\manifest.json` + `traces.npz` 생성.

### 1.4 NN training CLI (A1-b, workbench-train)

```powershell
# Step 1 빌드는 § 5 의 GUI 흐름 끝나야 의미 있음. 여기는 도움말만
.\.venv\Scripts\trsim.exe train --help
```

**기대**: `--job`, `--backend {auto,fake,numpy_mlp,numpy_mlp_adam}`,
`--seed`, `--output` 표시.

### 1.5 SDK CLI (sdk build / test, install / uninstall)

```powershell
.\.venv\Scripts\trsim.exe sdk --help
.\.venv\Scripts\trsim.exe install --help
.\.venv\Scripts\trsim.exe uninstall --help
```

**기대**: 각 subcommand 도움말 정상 표시.

☐ CLI 비-UI 5 항목 통과

---

## 2. 자동 검증 스위트 (~ 40 초)

### 2.1 pytest 전체

```powershell
$env:PYTHONUTF8 = "1"; $env:PYTHONPATH = "$(Get-Location)\src"
.\.venv\Scripts\python.exe -m pytest -q
```

**기대**: `2790 passed in X.Xs` (또는 그 이상). 0 fail, 0 error.

### 2.2 ruff

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
```

**기대**: 둘 다 `All checks passed!` 또는 `XXX files already formatted`.

### 2.3 mypy strict

```powershell
.\.venv\Scripts\python.exe -m mypy --strict src/workbench
```

**기대**: `Success: no issues found in N source files` (현재 212+).

### 2.4 import-linter (5 contracts)

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\lint-imports.exe
```

**기대**: `Contracts: 5 kept, 0 broken.` 5 contracts:
1. Layer dependency stack (UI → App → SDK → Domain → Physics)
2. Editor and Simulator workspaces must not import each other
3. Simulator must not import Editor (역방향)
4. Domain layer must not depend on Qt or visualization
5. SDK must only import Domain (not App, UI)

☐ pytest / ruff / mypy / lint-imports 4 검증 통과

---

## 3. UI 가동 검증 (수동, ~ 5 분)

### 3.1 GUI 띄우기

```powershell
.\.venv\Scripts\trsim.exe ui
```

**기대**: 1280x800 창 열림. 타이틀 `TRsim 0.X.Y`. Editor workspace 가
기본 진입점.

**OpenGL 컨텍스트 없는 환경** (headless CI / 원격 VM):

```powershell
.\.venv\Scripts\trsim.exe ui --no-3d-viewer
```

→ Simulator Scene 3D + Physics Lab 3D viewer 가 lazy QtInteractor
대신 status QLabel 로 fallback.

### 3.2 Workspace 전환 (3-way)

| 행동 | 기대 |
|---|---|
| `Ctrl+Shift+E` | Editor workspace (좌측 vertical activity bar) |
| `Ctrl+Shift+S` | Simulator workspace (8 panel + 6 bottom tabs + DLC) |
| `Ctrl+Shift+L` | Physics Lab workspace (Library / Code / Viz / Parameters / Time controls) |
| 상단 toolbar Editor / Simulator / Physics Lab 라디오 클릭 | 위와 동일 |

### 3.3 Editor 5 activity 전환

Editor workspace 에서:

| 단축키 | 기대 activity |
|---|---|
| `Ctrl+1` | Composer (References / Installation / Composition / Validation) |
| `Ctrl+2` | Map (Tools palette + Layers + **Domain Settings tab**) |
| `Ctrl+3` | Radar (Antenna type / Channel mode 폼 + **Beam Pattern Preview pyqtgraph**) |
| `Ctrl+4` | Targets (Motion kind dropdown 7 종 + **Trajectory Preview pyqtgraph**) |
| `Ctrl+5` | Browser (Resource Browser 풀스크린) |

### 3.4 Resource Browser sidebar

좌측 Activity bar 옆 always-on sidebar:
- `Scenarios (0)` / `Maps (0)` / `Radars (0)` / `Targets (0)` 4 카테고리
- 검색 입력란 + `+ New Resource` 버튼

`~/.trsim/resources/<cat>/<id>.toml` 가 있으면 자동 표시 (§ 4 참조).

### 3.5 Command palette

| 행동 | 기대 |
|---|---|
| `Ctrl+Shift+P` | 검색 가능한 명령 palette 다이얼로그 |
| `editor` 입력 | "Workspace: Editor", "Activity: Composer", ... 항목 검색 |
| Enter | 해당 명령 실행 + 다이얼로그 닫힘 |

### 3.6 종료

`File → Exit` 메뉴 또는 창 X 버튼. 프로세스 정상 종료 (exit code 0).

☐ UI 가동 + workspace / activity / palette 통과

---

## 4. Simulator 8 panel live data binding 검증 (L1-L6 + P5, ~ 4 분)

**rev11 의 핵심 신규**. Simulator workspace 의 8 panel 전체가 매 16 ms
QTimer tick 에 mock generator 로부터 sim_t_s 기반 deterministic 데이터
받아 repaint.

```powershell
.\.venv\Scripts\trsim.exe ui --workspace simulator
```

상단 Sim toolbar 의 **Play** 버튼 클릭 → 모든 panel 이 일제히 live
data 표시 시작.

### 4.1 Run panel (L1) — 좌하 첫 번째 tab

| 확인 | 기대 |
|---|---|
| "Simulation Time" GroupBox 4 readout | `sim_t`, `frame`, `state`, `speed` 4 라벨 |
| Play 클릭 | state=`running`, sim_t 가 16ms 마다 증가, frame 카운터 매 tick +1 |
| Pause | state=`paused`, sim_t / frame 정지 |
| Stop | state=`stopped`, sim_t=0, frame=0 reset |
| Sim toolbar speed (x1 / x2 / x4 / x8) | speed 라벨 갱신, sim_t 증가율 multiplier 적용 |

### 4.2 FFT panel (L2) — 중하 좌

`pg.PlotWidget` + 2 PlotDataItem (up sweep 빨강 / down sweep 파랑) +
2 InfiniteLine peak marker (점선).

| 확인 | 기대 |
|---|---|
| Play 시작 직후 | 빨강 + 파랑 곡선이 동시 표시, peak 가 sinusoidal 로 좌우 이동 |
| 상단 헤더 | `frame: N` + `peaks: 1 up / 1 down` 갱신 |
| Pause | 곡선 정지 (같은 sim_t_s → deterministic 같은 그림) |
| Sweep period 4초 | 매 4 초마다 peak 위치 한 사이클 |

### 4.3 RD (Range-Doppler) panel (L3) — 중하 우

`pg.PlotWidget` + `pg.ImageItem` (viridis LUT) + 2 InfiniteLine
cross-hair (노랑 점선).

| 확인 | 기대 |
|---|---|
| Play | 2-D 색맵 표시, Gaussian blob 이 range × doppler 평면 위를 Lissajous trajectory 로 이동 |
| Axis 라벨 | bottom = doppler (m/s), left = range (m) |
| Cross-hair | 노랑 점선 2개 가 target peak 위치 표시 |
| Pause | 색맵 / cross-hair 정지 |

### 4.4 Scene 3D panel (L4) — 중상

`pyvistaqt.QtInteractor` (lazy mount, OpenGL 필요). `--no-3d-viewer`
면 status QLabel 만.

| 확인 | 기대 |
|---|---|
| Camera preset (T / L / F / R) | 4 라디오 버튼 + 단축키 가능 (T=Top, L=Left, F=Free, R=Radar) |
| Layers 우측 panel | 11 layer checkbox (TERRAIN/SEA/BUILDINGS/SHIPS/TX_BEAM_ACTUAL/...) 8 default on |
| Play | 주황 sphere (radar, 원점 고정) + 빨강 sphere (target, 4km 원궤도 30s 주기) + 회색 plane (terrain placeholder) |
| Pause | actor 위치 정지 |

### 4.5 PluginMgr panel (L5) — 좌상

5 stage QListWidget 각각 default plugin 한 항목 미리 등록.

| 확인 | 기대 |
|---|---|
| Detector 리스트 | `default_cfar` |
| Pairing | `default_pairing` |
| Tracker | `default_ekf` |
| Predictor | `default_cv` |
| Classifier | `default_threshold` |
| `+ Add Plugin` / `Reload All` 버튼 | click 시 signal emit (실 동작은 후속) |

### 4.6 StageIO panel (L5) — 하단 두 번째 tab

6 pipeline stage 각각 IN/OUT 라벨 + Record 토글 + Export 버튼.

| 확인 | 기대 |
|---|---|
| Play | 6 stage (`Transmitter / Environment / Receiver / Detector / Pairing / Tracker`) 가 sim_t 마다 IN/OUT 갱신, 카운트 (reflections / detections / pairs / tracks) 가 sin envelope 으로 변동 |
| `Transmitter` 의 IN 라벨 | `sim_t=X.XXXs` 갱신 |
| 헤더 `frame: N` | tick 마다 +1 |
| **Record 버튼 토글 ON** | 매 tick 마다 frame snapshot 누적 (StageIOController._records) |
| Record OFF → ON 재토글 | 이전 log clear + 새 session 시작 |

### 4.7 Properties panel (L6) — 우

Primary Target 6 행 form: Range / Azimuth / Elevation / RCS / Speed /
Lock.

| 확인 | 기대 |
|---|---|
| 초기 (sim_t=0) | "(nothing selected)" → Play 시 "Primary Target" 으로 |
| Play 직후 | 6 행 모두 숫자 + Lock = `searching` |
| 0.5 초 경과 | Lock = `LOCKED` (lock_after_s 기본 0.5s) |
| Range / Azimuth | sim_t 와 함께 변화 (target orbit) |

### 4.8 ScopePOV panel (L6) — 우상

`pg.PlotWidget` 좌표 [-1, 1] × [-1, 1] + boresight cross-hair (회색
InfiniteLine 2개) + 빨강 ScatterPlotItem target marker.

| 확인 | 기대 |
|---|---|
| Play | 빨강 target marker 가 cross-hair 근처에서 작게 진동 (servo lag) |
| AZ readout (상단) | `AZ actual / cmd / lag: -- / -- / --` → 실 숫자 |
| `(no target — start the simulator)` hint | Play 후 사라짐 |

### 4.9 방향키 manual pointing (P5)

Simulator workspace 가 focus 상태에서:

| 키 | 효과 |
|---|---|
| `Right` | manual AZ +0.5° → ScopePOV cross-hair 가 우측으로 이동 + AZ readout 갱신 |
| `Left` | manual AZ -0.5° |
| `Up` | manual EL +0.5° → cross-hair 가 위로 |
| `Down` | manual EL -0.5° |
| `Home` 또는 `0` | manual offset 둘 다 0 으로 reset |

**Pause 상태에서도 동작** — 화살표가 즉시 cross-hair 를 옮김.

### 4.10 NN-mode 3 tabs (하단 4/5/6번 tab)

bottom_tabs 6번째까지 default — DLC 가 있으면 7번째 이후 추가:

| index | label |
|---|---|
| 0 | Run |
| 1 | Stage I/O |
| 2 | Profiler |
| 3 | NN Step 1 |
| 4 | NN Step 2 |
| 5 | NN Training |
| 6+ | `[DLC] <pkg>: <Class>` (있는 경우) |

NN 흐름 검증은 § 7 (이전 § 5).

### 4.11 하단 tab 떼어내기 (옵션 D)

| 행동 | 기대 |
|---|---|
| 하단 tab 의 tabBar 우클릭 → `Detach tab` | 해당 tab 이 별도 top-level window 로 분리 |
| floating window 의 창 닫기 | tab 이 원래 위치 + 라벨로 자동 복귀 |

☐ Simulator 8 panel + arrow keys + tab detach 통과

---

## 5. Editor 본격 binding (M1+M2 + P7, ~ 3 분)

### 5.1 Map Editor — DEM Import → bounds auto-wire (M1)

```powershell
# 작은 ESRI ASCII DEM 만들기 (3x3 그리드, 500m cell)
$dem = @'
ncols 3
nrows 3
xllcorner 0
yllcorner 0
cellsize 500
NODATA_value -9999
10 12 15
8 11 14
9 10 13
'@
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("$env:TEMP\demo_dem.asc", $dem, $utf8NoBom)
```

GUI 에서:
1. `Ctrl+Shift+E` (Editor) → `Ctrl+2` (Map)
2. 우측 패널의 `Domain` 탭 클릭 → `Map bounds` 라벨이 `(no map loaded)`
3. 하단 action row 의 `Import DEM...` 클릭
4. Wizard:
   - Source: `$env:TEMP\demo_dem.asc`
   - Output: 임의 `.npz` 경로 (예: `$env:TEMP\demo_dem.npz`)
   - Land/Sea: `nodata` 선택
   - Summary 페이지에서 `Import` 클릭
5. Wizard 가 success → close
6. **기대**: Map Editor 의 `Domain` 탭 `Map bounds` 라벨이 자동 갱신:
   `E:[0, 1500] N:[0, 1500] (m)` (3 cols × 500m × 3 rows × 500m)

### 5.2 Composer Installation block — live readouts (M2)

`Ctrl+1` (Composer activity). Installation 블록 안:

| 입력 | 기대 |
|---|---|
| East / North position 변경 (예: 200 / 300) | Altitude 라벨 자동 갱신 (sinusoidal: `+12.34 m (DEM sampled)` 식) |
| Azimuth 변경 (예: 90) | Coverage Stats 의 `Max range`, `Obstructed`, `Blind bearings` 자동 갱신 |
| Elevation 변경 (예: 30 → 0 → -10) | `Max range` 가 elevation 감소시 증가 (cosine), `Obstructed` 가 증가 |

### 5.3 Radar Editor — Beam Pattern Preview (P7)

`Ctrl+3` (Radar). Antenna 블록 하단:

| 확인 | 기대 |
|---|---|
| `BeamPatternPlot` pyqtgraph PlotWidget 표시 | Y 축 `gain (dB)` -40 ~ 0, X 축 `angle off boresight (deg)` |
| 기본 곡선 | sinc² 패턴 (3 dB BW 4 deg) — 빨강, peak 가 boresight 0 deg 에서 0 dB |
| Sidelobe | -13 dB 부근에 첫 sidelobe |

### 5.4 Targets Editor — Trajectory Preview (P7)

`Ctrl+4` (Targets). 하단 Trajectory 블록:

| Motion kind 선택 | 기대 trajectory |
|---|---|
| `FIXED_GROUND` / `FLOATING_STATIC` | 단일 점 (origin 부근) |
| `GROUND_VEHICLE` | 동쪽 1000m 직진 + 좌우 진동 |
| `SURFACE_VESSEL` | 동쪽 800m + 사인 곡선 |
| `AIRCRAFT` | 큰 원 궤도 (서쪽 -2000m 중심) |
| `POWERED_FLIGHT` | 동북 quadratic |
| `BALLISTIC` | parabolic arc (포물선) |

Aspect locked 1:1 + 초록 ScatterPlotItem 시작 marker.

### 5.5 Atmosphere Panel — Rain Attenuation Preview (P7)

Atmosphere 활동 (메뉴에서 직접) 또는 Composer 의 atmosphere 참조에서:

| 확인 | 기대 |
|---|---|
| Atmosphere preview 그룹의 PlotWidget | X 축 `frequency (GHz)` 1~40, Y 축 `rain attenuation (dB/km)` |
| Rain rate 0.0 | 곡선이 거의 0 |
| Rain rate 25.0 (heavy) 입력 후 Tab | 곡선이 즉시 갱신, X-band (~10 GHz) 부근 피크 |

☐ Map / Composer / Radar / Targets / Atmosphere 5 항목 통과

---

## 6. Physics Lab 검증 (rev7~rev11)

`Ctrl+Shift+L` 또는 toolbar 의 "Physics Lab" 라디오 클릭.

### 6.1 레이아웃 + Library 5 카테고리

| 위치 | 위젯 |
|---|---|
| 좌 (Library) | **5 카테고리 QTreeWidget**: Tests / Models (built-in 3 + DLC) / Saved Experiments / Measured Data / Papers |
| 중 상 (Code) | 선택된 simulator 의 step 메서드 소스 |
| 중 하 (Visualization) | pyqtgraph y(t) plot 또는 3D Test Object viewer (lazy) |
| 우 (Parameters) | 자동 생성 슬라이더 (PhysicsParam-driven) |
| 하 (Time controls) | Play / Pause / Stop + Mode combo + Frame slider |

### 6.2 Bouncing Ball — Run 모드

1. Library 의 `Tests > Bouncing Ball Demo` 클릭
2. **Play** 버튼 → 공이 5 m 에서 떨어지며 plot 에 곡선
3. status 라벨 실시간 갱신: `running  t=0.36s  y=4.36m  v=-3.55m/s  bounces=0`
4. 첫 bounce (t ≈ 1 s) → `bounces=1`, 위로 튕김
5. Restitution / Gravity / Drag / Initial height / Initial velocity 5 슬라이더 — Play 중 움직이면 다음 step 부터 즉시 반영
6. **Pause / Stop** 정상

### 6.3 Time Mode (PL-9.1e)

Time controls 의 `Mode` combo:

| 모드 | 기대 |
|---|---|
| `static` | transport (Play/Pause/Stop) disable, Plot 정지 |
| `run` | 일반 dynamic 모드 (위 6.2) |
| `compare` | analytic_peak 곡선 (red marker) overlay — Pause 후 모드 전환해도 history 유지 |
| `sweep` | 4 sibling simulator (restitution 0.3/0.5/0.7/0.9) 동시 실행, 4 overlay curve |

### 6.4 Frame history scrubbing (PL-9.1b)

Time controls 하단 Frame slider + Prev / Next 버튼:

| 행동 | 기대 |
|---|---|
| Play 중 어느 시점 Pause | history 가 보존, slider 가 끝까지 이동 |
| Slider 왼쪽으로 드래그 | plot 이 해당 frame 까지만 표시, status 라벨도 그 frame 의 state |
| Prev / Next 버튼 | 1 frame 단위 |
| Slider mid-history 상태에서 Play | future history truncate + 새 timeline |

### 6.5 Code 패널 — 즉석 수정 + Save & Reload (PL-E)

| 행동 | 기대 |
|---|---|
| **Edit** 토글 | 에디터 read-only 해제 + 자동 scaffold 로 교체 |
| 코드 수정 후 **Save && Reload** | controller 가 ast.parse + exec 검증 → simulator step 교체 → status "applied" |
| syntax error | status 빨강 "SyntaxError: ..." — override 미적용 |
| **Revert** | built-in 소스 복원 |
| Play 중 Save & Reload | 자동 pause → 새 step 설치 → 재시작 |

### 6.6 Auto-completion + Python syntax highlighting (PL-9.1a/9.3a)

Code editor (Edit 모드) 에서:
- Python keyword / builtins / `self` / strings / comments / numbers / decorators / def name / class name 10 색상
- `Ctrl+Space` 또는 자동 → 단어 완성 popup (Python keywords + builtins + Bouncing Ball API: `simulator`, `dt_s`, `state`, `position_m` 등)

### 6.7 Saved Experiments (PL-9.1f)

| 행동 | 기대 |
|---|---|
| 슬라이더 임의 조정 + Library 의 `Save current...` 버튼 클릭 | 이름 prompt → TOML 저장 |
| Library 의 Saved Experiments 카테고리 확장 | 방금 저장한 이름 표시 |
| 해당 row 클릭 | controller 가 simulator reset + 슬라이더 자동 복원 |

### 6.8 Measured Data + Validation Bench (PL-9.2)

GUI 흐름:
1. `~/.trsim/measured/` 디렉토리에 CSV + `.toml` sidecar 만들기 (자세히는 plan/19 § 19.9.2)
2. `PhysicsLabWorkspace(measured_root=...)` 가 필요 — `trsim ui` 가 자동 mount 안하므로 검증은 Python REPL

빠른 검증 (Python REPL):

```powershell
$env:PYTHONUTF8 = "1"; $env:PYTHONPATH = "$(Get-Location)\src"
.\.venv\Scripts\python.exe -c @'
import numpy as np
from workbench.app.physics_lab import (
    BouncingBallModel, GravityOnlyModel, FreeSpaceLossModel,
    ValidationBench, ValidationConfig,
)

# Dynamic — GravityOnly self-check
gen = GravityOnlyModel()
bench = ValidationBench(model=gen)
t = np.linspace(0.01, 4.0, 50)
y = 100.0 - 0.5 * 9.81 * t**2
_, _, metrics = bench.evaluate(
    measured_x=t, measured_y=y,
    params={"gravity_m_s2": 9.81},
    config=ValidationConfig(
        output_field="position_m",
        initial_state={"time_s": 0.0, "position_m": 100.0, "velocity_m_s": 0.0},
        dt_s=0.005,
    ),
)
print(f"GravityOnly self-validation RMSE={metrics.rmse:.4f}m, corr={metrics.pearson_correlation:.4f}")

# Static — FreeSpaceLoss self-check
fsl = FreeSpaceLossModel()
bench = ValidationBench(model=fsl)
import math
freq = 9.4e9; wl = 299_792_458 / freq
r = np.linspace(10, 5000, 20)
loss = 10 * np.log10((4 * math.pi * r / wl) ** 2)
_, _, metrics = bench.evaluate(
    measured_x=r, measured_y=loss,
    params={"freq_hz": freq},
    config=ValidationConfig(
        output_field="loss_db", input_field="range_m", n_samples=64,
    ),
)
print(f"FreeSpaceLoss self-validation RMSE={metrics.rmse:.4f}dB, corr={metrics.pearson_correlation:.4f}")
'@
```

**기대**:
- `GravityOnly self-validation RMSE=0.X m, corr=0.99XX`
- `FreeSpaceLoss self-validation RMSE=0.0XX dB, corr=0.99XX`

### 6.9 9 Test Objects 분석 공식

```powershell
$env:PYTHONUTF8 = "1"; $env:PYTHONPATH = "$(Get-Location)\src"
.\.venv\Scripts\python.exe -c @'
import math
from workbench.domain.physics_lab import default_library
LAMBDA = 299_792_458 / 9.4e9
for obj in default_library():
    sigma = obj.analytic_rcs_m2(LAMBDA)
    if sigma is None:
        print(f"{obj.name:<22} ({obj.visual:<10}) — no analytic RCS")
    else:
        dbsm = 10 * math.log10(sigma) if sigma > 0 else float("-inf")
        print(f"{obj.name:<22} ({obj.visual:<10}) sigma = {sigma:.3e} m^2  ({dbsm:+.1f} dBsm)")
'@
```

**기대 (대략)**:
- `sphere_1m` ~ +5 dBsm (geometric optics π r²)
- `trihedral_0p3m` ~ +15 dBsm (corner reflector)
- `wall_5x3m` ~ +65 dBsm (broadside 큰 plate)

☐ Physics Lab 9 항목 통과

---

## 7. NN 흐름 검증 (GUI 기반, ~ 3 분)

NN-mode 3 tab 이 Simulator bottom_tabs index 3/4/5 에 mount. 모든 단계
GUI 클릭으로 가능.

`trsim ui --workspace simulator` 로 시작.

### 7.1 Step 1 — Single variant 빌드

`NN Step 1` (index 3) tab → panel:

| 입력 | 값 |
|---|---|
| Build mode | `Single variant` |
| Frames (per variant) | `50` |
| Output path | `./datasets/demo_single.h5` |

`Build Dataset` 클릭.

**기대**:
- Status `done: 50/50 samples -> demo_single.h5`
- `./datasets/demo_single.h5` 생성

### 7.2 Step 1 — 4-variant chain 빌드

| 입력 | 값 |
|---|---|
| Build mode | `All 4 variants (A/B/C/D)` |
| Frames (per variant) | `30` |
| Output path | `./datasets/` |

`Build Dataset` → status `done: 4/4 variants -> pairing_variants_manifest.toml`.

```powershell
Get-ChildItem ./datasets/
```

→ `pairing_variant_A.h5` ~ `_D.h5` + `pairing_variants_manifest.toml`.

### 7.3 NN Training — numpy MLP 학습

`NN Training` tab → panel:

| 필드 | 값 |
|---|---|
| Job ID | `pairing_v1` |
| Dataset | `./datasets/pairing_variant_A.h5` |
| Weights | `./weights/v1.npz` |
| Epochs | `20` |
| LR | `0.05` |
| Backend | `numpy_mlp (real gradient descent)` |

`Run Training` → status `done: 20/20 epochs`.

```powershell
.\.venv\Scripts\python.exe -c "import numpy as np; f=np.load('./weights/v1.npz'); print(list(f.files))"
```

**기대 출력**: `['layer_0_W', 'layer_0_b', 'layer_1_W', 'layer_1_b', 'layer_2_W', 'layer_2_b']`

**Backend = `numpy_mlp_adam`** (A1-a, 2026-05-13 추가) 도 가능 — Adam optimizer 사용, weights 파일 키 동일.

### 7.4 NN Training — CLI (workbench-train, A1-b)

```powershell
# Job TOML 만들기 (간단 예)
$job = @'
job_id = "cli_demo"
task = "pairing"
dataset_path = "./datasets/pairing_variant_A.h5"
weights_path = "./weights/cli.npz"
train_fraction = 0.8
val_fraction = 0.2
architecture = "mlp"
layer_sizes = [16, 32, 8]
activation = "relu"
framework = "numpy_only"
optimizer = "sgd"
lr = 0.05
batch_size = 8
epochs = 10
early_stopping = false
metrics_path = "./weights/cli_metrics.json"
'@
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("./demo_job.toml", $job, $utf8NoBom)

.\.venv\Scripts\trsim.exe train --job ./demo_job.toml
```

**기대**: 매 epoch stdout 출력 + 마지막에 JSON summary + `./weights/cli.npz` 생성.

### 7.5 Step 2 — 4-error 평가

`NN Step 2` tab. Plugin combo 기본값 `numpy_pairing_nn`. Dataset combo
는 Step 1 빌드 후 **자동 refresh** (manual refresh = `Refresh datasets`
버튼).

dataset 선택 → `Run Evaluation` → 4-error 표:

| 행 | 기대 |
|---|---|
| Pairing | RMSE 작은 값 (0.0 ~ 0.1), Bias `0.000` |
| Tracker / Predictor / Classifier | `n/a (plugin unsupported)` (P6 stub lock) |

### 7.6 청소

```powershell
Remove-Item -Recurse -Force ./datasets, ./weights, ./demo_job.toml -ErrorAction SilentlyContinue
```

☐ NN 5 항목 통과 (전부 GUI 또는 CLI)

---

## 8. DLC 자동 로드 검증 (~ 3 분)

### 8.1 sample DLC 만들기

> **중요**: PowerShell 5.1 의 `Out-File -Encoding utf8` 은 UTF-8 BOM
> 저장 → tomllib 거부. 아래는 BOM 없는 UTF-8.

```powershell
$pkg = "$env:USERPROFILE\.trsim\packages\demo-panel"
New-Item -ItemType Directory -Force -Path "$pkg\ui" | Out-Null

$manifest = @'
[package]
id = "demo-panel"
name = "Demo Panel DLC"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"

[entry_points]
"trsim.ui.panels" = "ui/diagnostic_panel:DiagnosticPanel"
'@
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("$pkg\manifest.toml", $manifest, $utf8NoBom)

$panel = @'
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

class DiagnosticPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hello from demo-panel DLC"))
'@
[System.IO.File]::WriteAllText("$pkg\ui\diagnostic_panel.py", $panel, $utf8NoBom)
```

### 8.2 UI 재가동 → DLC tab 확인

```powershell
.\.venv\Scripts\trsim.exe ui --workspace simulator
```

**기대**: Simulator bottom_tabs **7 개**:

| index | label |
|---|---|
| 0-5 | Run / Stage I/O / Profiler / NN Step 1 / NN Step 2 / NN Training |
| 6 | **`[DLC] demo-panel: DiagnosticPanel`** |

7번째 (index 6) 탭 클릭 → "Hello from demo-panel DLC" 라벨 표시.

### 8.3 Plugins menu 활용 (F2/F3)

| 메뉴 | 기대 |
|---|---|
| `Plugins → Manage Plugins...` | PackageManagerDialog 열림, `demo-panel` 행 표시 |
| `Plugins → Install Package...` | 파일 picker → `.trsim-pkg` 선택 시 자동 install |

### 8.4 user resource 자동 등장

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.trsim\resources\radars" | Out-Null
$radar = @'
id = "kuband_naval"
carrier_freq_hz = 9.4e9
'@
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText(
    "$env:USERPROFILE\.trsim\resources\radars\kuband_naval.toml",
    $radar,
    $utf8NoBom
)

.\.venv\Scripts\trsim.exe ui
```

**기대**: Editor Resource Browser sidebar 의 `Radars` 카테고리:
- 헤더 `Radars (1)`
- leaf `kuband_naval`
- 더블클릭 → Editor 자동으로 Radar activity (Ctrl+3) 로 전환

### 8.5 --no-dlc 격리

```powershell
.\.venv\Scripts\trsim.exe ui --no-dlc --workspace simulator
```

**기대**:
- Editor sidebar 4 카테고리 모두 `(0)`
- Simulator bottom_tabs **6 개** (DLC tab 없음)
- 종료 코드 0

### 8.6 청소

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.trsim\packages\demo-panel"
Remove-Item -Force "$env:USERPROFILE\.trsim\resources\radars\kuband_naval.toml"
```

☐ DLC 5 항목 통과

---

## 9. 전체 통과 체크리스트

| 섹션 | 항목 | 통과 |
|---|---|---|
| 0 | 환경 sanity + pull + dev install | ☐ |
| 1 | CLI 5 명령 (help / profile + mode toggle / run / train --help / sdk --help) | ☐ |
| 2 | pytest 2790 + ruff + mypy + lint-imports | ☐ |
| 3 | UI 가동 + 3-way workspace + 5 activity + sidebar + palette | ☐ |
| 4 | **Simulator 8 panel live binding** (Run/FFT/RD/Scene3D/PluginMgr/StageIO/Properties/ScopePOV) + arrow keys + tab detach | ☐ |
| 5 | Editor binding (Map DEM → bounds wire + Composer Installation live + 3 preview) | ☐ |
| 6 | Physics Lab (Library 5 cat + Bouncing Ball + Time Mode + Frame scrub + Code edit + autocomplete + Saved + ValidationBench + 9 RCS) | ☐ |
| 7 | NN (Step 1 single + chain + numpy_mlp 학습 + CLI train + 4-error eval) | ☐ |
| 8 | DLC (panel mount + Plugins menu + resource sidebar + --no-dlc) | ☐ |

전부 ✓ 면 MVP 본격 완성. 후속은 [`docs/MVP_STATUS.md`](MVP_STATUS.md)
§ 미구현 우선순위 리스트 — Polish (Floating dock B / Theme manager /
Stone Soup adapter, 미루기 가능) + post-MVP 항목 (HIL / NN per-category
real / Pipeline real binding).

---

## 10. Post-MVP 영역 (의도적 미완)

### Phase 8 HIL

`app/hil/`, `domain/hil/`, `ui/simulator/hil_panel/` 모두 docstring 만
있는 빈 package. `sdk/protocols.py::DUTAdapterProtocol` 은
`@runtime_checkable` shell 만 (멤버 0). 본격 작업은 사용자 신호 후
별도 cycle. 자세히는 `docs/MVP_STATUS.md § "Phase 8 — HIL"`.

### Phase 6 Tracker/Predictor/Classifier real loss + multi-step rollout

`tracker_loss / predictor_loss / classifier_loss / multi_step_rollout_rmse`
는 `NotImplementedError("Phase 6 follow-up")` 발생. Step 2 UI 는 `n/a
(plugin unsupported)` 로 surface. TrackerNNPlugin / PredictorNNPlugin /
ClassifierNNPlugin Protocol 출시 후 본격 구현.

### Phase 4 L-series real Pipeline binding

Simulator 8 panel 의 mock generator (`MockSpectrumGenerator`,
`MockRangeDopplerGenerator`, ...) 는 향후 실 `Pipeline.step()` probe 로
교체. Phase 6+ probe recorder 와 짝.

---

## 11. 실패 모드별 대처

| 증상 | 원인 후보 | 조치 |
|---|---|---|
| `No module named pip` | uv venv 등 pip 없는 venv | § 0.0 의 ensurepip 또는 venv 재생성 |
| `pytest 1690 PASS` (2790 기대) | local main 이 origin/main 뒤쳐짐 | `git pull --ff-only` |
| `trsim ui --help` 에 `--no-3d-viewer` 없음 | trsim.exe 가 옛 entry point | `pip install -e . --no-deps` |
| `trsim profile --help` 에 `--mode` 없음 | rev11 이전 / pull 안됨 | `git pull --ff-only` |
| Simulator 가 process 즉시 종료 (OpenGL fault) | headless / 원격 / Qt platform plugin 누락 | `--no-3d-viewer` 추가 또는 `$env:QT_DEBUG_PLUGINS = "1"` |
| Scene 3D panel 이 status QLabel 만 | `--no-3d-viewer` 켜짐 | 정상 — production 은 `--no-3d-viewer` 빼고 가동 |
| FFT / RD panel 이 정지 (Play 클릭 후도) | Sim toolbar Play 클릭 안함 OR Pause 됨 | Sim toolbar 의 ▶ 버튼 클릭 |
| 방향키가 무반응 | Simulator workspace 의 다른 widget 이 focus | workspace 빈 영역 클릭 후 다시 시도 |
| Map Editor DEM import 후 bounds 안 갱신 | wizard 가 error 로 종료됨 | wizard summary 페이지의 error 메시지 확인, ASC 파일 검사 |
| Composer Position 입력 후 Altitude 변화 없음 | position_changed signal 미발화 — 필드 4 모두 valid float 이어야 함 | East / North / Az / El 4 필드 모두 숫자로 입력 |
| Radar / Targets / Atmosphere preview pyqtgraph 비어있음 | pyqtgraph import 실패 | `pip install -e ".[dev]"` 다시 |
| `package error ... Invalid statement (at line 1, column 1)` | manifest.toml UTF-8 BOM | § 8.1 의 `[System.IO.File]::WriteAllText` + `UTF8Encoding($false)` |
| DLC tab 안 보임 | manifest 잘못 / entry_point typo / `--no-dlc` | manifest 1:1 비교, `--no-dlc` 끄기 |
| pytest 일부 깨짐 | 환경 불일치 | `PYTHONUTF8 / PYTHONPATH` 환경변수 + Python 3.11+ 확인 |
| `lint-imports` UnicodeDecodeError (cp949) | Windows 콘솔 codec | `$env:PYTHONIOENCODING = "utf-8"` 명시 |
| Resource Browser sidebar 비어있음 | `~/.trsim/resources/<cat>/` 디렉토리 없거나 `--no-dlc` | 디렉토리 만들고 `--no-dlc` 끄기 |
| Step 2 dataset combo 비어있음 (Step 1 빌드 전) | `./datasets/` 자체 비어있음 — 정상 | Step 1 빌드 후 자동 refresh 또는 `Refresh datasets` 버튼 |
| Step 2 dataset combo 가 Step 1 빌드 후에도 비어있음 | output path 가 `./datasets/` 가 아닌 다른 디렉토리 | output path parent 가 cwd `./datasets/` 와 일치하는지 확인 |
| `trsim profile --mode explicit` recorded_frames 가 예상보다 다름 | `--explicit-every` 값 확인 (default 10) | `--explicit-every` 명시 |
| ValidationBench `KeyError: 'output_field ... missing'` | `compute()` return dict 에 키 없음 | `ValidationConfig.output_field` 가 모델의 출력 dict 에 실제 있는 key 인지 확인 |

---

## 12. 핵심 신규 기능 빠른 참조 (rev11)

### Phase 4 L1-L6 + M1+M2 (Simulator + Editor binding)

- **L1**: `RunController` (SimulationClock + 16ms QTimer) — sim_t / frame / state / speed live
- **L2**: FFT panel pyqtgraph — `MockSpectrumGenerator` (sinusoidal peak)
- **L3**: RD panel `pg.ImageItem` (viridis LUT) — `MockRangeDopplerGenerator` (Lissajous)
- **L4**: Scene 3D `pyvistaqt.QtInteractor` lazy — `MockSceneGenerator` (radar + target orbit)
- **L5**: PluginMgr default seed + StageIO live + Record toggle log
- **L6**: ScopePOV cross-hair + Properties primary-target — `MockPrimaryTargetGenerator`
- **M1**: DEM Import → MapEditor.set_map_bounds 자동
- **M2**: ComposerInstallationController — position_changed → mock probe → altitude + coverage stats

### P-series (MVP 완성)

- **P1**: HIL post-MVP placeholder lock
- **P2**: `ValidationBench` + `ValidationConfig` — 임의 PhysicsModelProtocol 지원 (dynamic + static)
- **P3**: `trsim profile --mode {off,explicit,live}` + `--explicit-every N`
- **P4**: Phase 5 #18/#19 재현성 정량 test
- **P5**: 방향키 manual pointing
- **P6**: NN per-category stub lock
- **P7**: Editor preview 3종 (Radar beam / Targets trajectory / Atmosphere)
- **P8**: SDK manifest 이동 (`domain/dlc/manifest.py` → `sdk/manifest.py`)

자세히는 [`docs/sessions/mvp_completion_2026_05_14.md`](sessions/mvp_completion_2026_05_14.md).
