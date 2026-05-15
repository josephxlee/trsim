# Scene3D 리사이즈 잔상 — 디버깅 케이스

- **날짜**: 2026-05-15
- **상태**: 해결됨
- **영역**: frontend (VTK / pyvistaqt)
- **수정 위치**: `src/workbench/ui/simulator/panels/scene_3d_panel.py`

## 증상

`trsim ui --workspace simulator` 에서 창을 리사이즈(특히 최대화)하면
Scene3D 패널의 3D 렌더링이 옛 프레임 그대로 남는다("잔상"). 윈도우와
위젯은 커지는데 3D 내용만 갱신되지 않음.

## 환경

Windows 11, PySide6 6.11, pyvista / pyvistaqt 0.11+, VTK 9,
디스플레이 150% HiDPI 스케일.

## 조사 타임라인

1. **가설 1 — 렌더 타이밍**: `Scene3DPanel.resizeEvent` 에서 즉시
   `interactor.render()` 호출. → 실패.
2. **가설 2 — 렌더가 너무 이름**: Qt 레이아웃 reflow 전에 render 하면
   interactor 가 옛 geometry 상태. 50 ms 디바운스 타이머로 정착 후 render.
   → 부분 개선했으나 잔상 잔존 보고.
3. **격리 하니스 제작** (`panel_isolation.py`): Scene3D / FFT / RD 를
   SimulatorWorkspace · MainWindow 없이 단독 마운트. 실제 클래스 import.
4. **크기 프로브 추가** → 결정적 데이터:

   |        | panel     | interactor | render_window |
   |--------|-----------|------------|---------------|
   | 기본   | 1100x750  | 916x704    | 1374x1056     |
   | 최대화 | 1707x996  | 1523x950   | 2285x1425     |

   panel · interactor 위젯 · VTK render window 가 **전부 정확히 비례
   리사이즈**됨 (render window = interactor × 1.5 = HiDPI 스케일).
   → **sizing 은 원래부터 정상이었다.** 가설 1·2 의 blind 패치는 잘못된
   증상을 쫓고 있었음.
5. **가설 3 — `QVTKRWIBase = "QOpenGLWidget"`** (Qt 합성 GL 위젯으로
   전환): → 실패. `vtkWin32OpenGLRenderWindow: failed to get valid pixel
   format`. 원인은 아래 "막다른 길" 참조.
6. **수동 프로브 버튼** 추가 (render / SetSize+Render / nudge ±1px):
   셋 다 stale 을 해제. → VTK 는 올바르게 그릴 수 있고, 정착 후 render
   트리거만 있으면 된다는 게 확정됨.

## 근본 원인

pyvistaqt `QtInteractor` 는 `WA_PaintOnScreen` **네이티브 윈도우**다 —
Qt 백킹스토어 없이 VTK 가 OS 윈도우에 직접 OpenGL 렌더링한다. 리사이즈
후 VTK 렌더 윈도우는 올바르게 `SetSize` 되지만, 새 프레임이 화면에
자동으로 올라오지 않는다. 리사이즈가 최종 geometry 로 정착한 뒤
명시적 render 트리거가 필요하다.

## 수정

`src/workbench/ui/simulator/panels/scene_3d_panel.py` — 디바운스 정착
렌더:

- `_RESIZE_RENDER_DEBOUNCE_MS = 50` 모듈 상수.
- `__init__`: 단일샷 `QTimer` (`_resize_render_timer`).
- `resizeEvent`: `super().resizeEvent()` 후 타이머 (재)시작 — 리사이즈
  burst 를 디바운스.
- `_render_interactor` (타이머 콜백): 레이아웃이 최종 geometry 로
  정착한 뒤 `interactor.render()` 를 1회 호출.

## 막다른 길 (다시 시도하지 말 것)

- **`resizeEvent` 인라인 즉시 render** — Qt 레이아웃 reflow 전이라
  interactor 가 옛 크기. 너무 이름.
- **`QVTKRWIBase = "QOpenGLWidget"`** — pyvistaqt 의 vendored
  `rwi.py` (`__init__` 의 `setAttribute(WA_PaintOnScreen)` + VTK 의
  `SetWindowInfo(WId)`) 가 베이스 클래스와 무관하게 네이티브 페인트를
  하드코딩한다. `QOpenGLWidget` 이 자체 GL 컨텍스트를 만들면 VTK 가 같은
  HWND 에 또 만들려다 충돌 → 픽셀 포맷 에러. 이 pyvistaqt 버전에선
  `QVTKRWIBase` 전환으로 Qt 합성 동작을 얻을 수 없다.

## 교훈

- **패치 전에 측정하라.** blind 패치를 2번 한 뒤에야 크기 프로브가
  "sizing 은 정상"임을 증명하며 방향을 바로잡았다. 증상 가정만으로
  고치지 말 것.
- **VTK-in-Qt**: 임베드된 interactor 는 네이티브 윈도우다. 리사이즈 /
  페인트 아티팩트는 VTK 렌더링 자체가 아니라 네이티브-윈도우 페인트
  모델에서 온다.
- **격리가 이분할을 가능케 한다**: 실제 클래스를 최소 셸에 단독
  마운트하면 "패널 자체 문제냐 / workspace 중첩 문제냐"를 가를 수 있다.
- pyvistaqt `rwi.py` 는 vendored 사본이며 `WA_PaintOnScreen` 을
  하드코딩한다 — 베이스 클래스 전환으로 우회 불가.
- **수정 후엔 `trsim ui` 를 완전히 재시작하고 재확인**할 것. 떠 있던 옛
  인스턴스가 false "아직도 안 됨" 보고를 유발할 수 있다.

## 재현 하니스

`panel_isolation.py` (이 폴더). 사용법은 파일 docstring 참조:

```powershell
$PY = ".\.venv\Scripts\python.exe"
$H = "debug\frontend\scene3d_resize_ghost\panel_isolation.py"
& $PY $H --panel scene3d     # Scene3D 단독
& $PY $H --panel center      # 3패널 함께 (실제 레이아웃)
```

크기 프로브가 1초마다 `[size]` 줄을 출력하고, 상단 툴바의 버튼 3개로
stale 해제 동작을 수동 검증할 수 있다.
