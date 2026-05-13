# User Acceptance Test — 2026-05-13

이 문서는 2026-05-13 cycle (Phase 4 DEM Import Wizard) 에서 추가된
UI 동작을 사용자가 직접 확인할 수 있게 step-by-step 으로 정리한다.
새 cycle 의 검수 시 이 파일에 그 cycle 의 항목을 **append** 한다
(섹션 별로 분리).

## 환경 준비 (한 번만)

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

# 1. Smoke: 전체 test 통과 (2327 PASS 예상)
& $PY -m pytest -q

# 2. lint-imports 5 KEPT 확인
& ".\.venv\Scripts\lint-imports.exe"

# 3. UI 가동
& $PY -m workbench
```

---

## Section A — Phase 4 DEM Import Wizard (2026-05-13)

### A.1 샘플 ESRI ASCII grid 만들기

PowerShell 로 한 줄로 작성. 출력 파일은 BOM 없는 UTF-8 권장.

```powershell
$body = @'
ncols        4
nrows        3
xllcorner    1000.0
yllcorner    2000.0
cellsize     10.0
NODATA_value -9999
70.0 80.0 90.0 100.0
40.0 50.0 60.0 -9999
10.0 20.0 30.0 -9999
'@
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText("$env:USERPROFILE\Desktop\sample_dem.asc", $body, $utf8)
```

세 row × 네 column DEM. row 0 (top) = 70..100m (north 쪽 산),
row 2 (bottom) = 10..30m (south 쪽 평지). 우측 두 셀에 NODATA.

### A.2 Wizard 띄우기

1. UI 가동 후 좌측 toolbar 의 **Editor** workspace 선택 (또는
   Ctrl+Shift+E).
2. Editor 사이드바에서 **Map** activity 선택 (Ctrl+2). Map Editor
   widget 가 중앙에 표시되면 OK.
3. 우측 하단 action row 의 **Import DEM...** 버튼 클릭.
4. "Import DEM" 제목의 QWizard 다이얼로그가 modal 로 열리면 OK.

### A.3 7-step 일주

| Step | 페이지 | 액션 | 확인 |
|---|---|---|---|
| 1 | Source DEM file | "Browse..." → A.1 에서 만든 `sample_dem.asc` 선택 | path 가 QLineEdit 에 표시되면 Next 활성 |
| 2 | Vertical reference | 기본 "EGM96 geoid (recommended)" 선택된 상태 그대로 Next | — |
| 3 | Region | "Full extent" 선택된 상태 그대로 Next ("Custom crop" 켜면 4 개 spinbox 노출) | crop group 이 Full 선택 시 disable, Custom 선택 시 enable |
| 4 | Land/Sea | "Auto threshold" 선택된 상태 + threshold=0.5 그대로 Next | "External coastline file (deferred)" radio 가 회색으로 비활성 |
| 5 | CRS conversion | "No conversion is performed in the MVP" 안내 Next | — |
| 6 | Grid interpolation | "Bilinear (default)" 그대로 Next | combo 가 3 항목 표시 |
| 7 | Save | "Browse..." → 데스크탑/저장하고 싶은 곳에 `sample_terrain.npz` 저장 위치 지정 + **Finish** | wizard 가 닫힘, Map Editor 의 Edit History list 에 `Imported DEM -> ...sample_terrain.npz` 한 줄 등장 |

### A.4 검증 (terrain.npz 파일 확인)

```powershell
$PY = ".\.venv\Scripts\python.exe"
& $PY -c @'
import numpy as np
from pathlib import Path
p = Path(r"$env:USERPROFILE\Desktop\sample_terrain.npz")
data = np.load(p)
print("elevation shape:", data["elevation"].shape)
print("south row (row 0):", data["elevation"][0])
print("land_mask south row:", data["land_mask"][0])
print("cell_size_m:", data["cell_size_m"])
'@
```

기대 출력:

```
elevation shape: (3, 4)
south row (row 0): [10. 20. 30. nan]
land_mask south row: [ True  True  True False]
cell_size_m: 10.0
```

- ESRI flip 이 적용돼서 row 0 = south = "10 20 30 -9999" line.
- NODATA -9999 → NaN, AUTO_THRESHOLD(>0.5) → False.
- cell_size_m 10m 그대로 보존.

### A.5 실패 케이스

#### A.5.a 빈 source path 로 Finish

1. Import DEM 띄움.
2. Source page 에서 path 입력 없이 (혹은 Save page 도 path 입력
   없이) **Next** 만 7번 누르고 **Finish**.
3. 확인: wizard 가 안 닫히고, Map Editor 의 Edit History list 에
   `Import failed: DEM source path is empty` 한 줄 등장.

#### A.5.b 존재하지 않는 source 파일

1. Source page 의 LineEdit 에 직접 `C:\nonexistent.asc` 타이핑 +
   Save page 도 임의 path 입력 + Finish.
2. 확인: Edit History 에 `Import failed: DEM file not found: ...`
   한 줄.

#### A.5.c 두 번째 import 시 history append

1. A.3 따라 한 번 성공.
2. **Import DEM...** 다시 클릭, 다시 한 번 일주, 다른 출력
   filename (`sample_terrain_2.npz`).
3. 확인: Edit History 가 **2 줄**, 가장 최근 (sample_terrain_2)
   이 맨 위.

### A.6 라이브 코드 health 체크

```powershell
& $PY -m pytest -q tests/unit/app/test_dem_wizard.py tests/unit/ui/editor/test_dem_import_wizard.py tests/unit/ui/editor/test_map_editor_page_wizard.py
# 47 PASS 예상
```

---

## 추후 cycle 항목 ↓ (다음 cycle 가 append)
