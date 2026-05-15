# debug/frontend/ — UI 격리 하니스

Qt 위젯 / VTK(pyvistaqt) / pyqtgraph / 렌더링 / 레이아웃 관련 버그를
`MainWindow` + workspace 중첩에서 떼어내 단독으로 재현하는 곳.

## 패턴

```python
import sys
from pathlib import Path
_SRC = Path(__file__).resolve().parents[3] / "src"   # 깊이에 맞게 조정
sys.path.insert(0, str(_SRC))

# ↑ 이후에 PySide6 / workbench import (ruff E402 는 noqa)
```

- 실제 패널/컨트롤러 클래스를 import 해 최소 `QMainWindow`에 마운트.
- 문제를 이분할할 수 있게 CLI 옵션(`--panel scene3d` 등)으로 마운트 대상을
  고를 수 있게 한다 — "패널 단독 / 조합 / workspace 중첩" 비교가 핵심.
- 필요하면 진단 프로브(크기 출력, 강제 새로고침 버튼)를 붙인다.

## 실행 환경 주의

- **VTK / pyvistaqt(3D)** 는 실제 디스플레이 + OpenGL 필요 — headless
  CI / offscreen 에서 못 띄운다. 데스크톱에서 직접 실행.
- **pyqtgraph** 패널은 `QT_QPA_PLATFORM=offscreen` 으로 headless 구동 가능
  (스모크 테스트용).
- 컨트롤러/타이머는 QObject parent 가 없으면 GC 되니, 이벤트 루프가 끝날
  때까지 Python 참조를 살려둘 것.

## 케이스

| 케이스 | 요약 |
|---|---|
| [scene3d_resize_ghost](scene3d_resize_ghost/README.md) | 리사이즈 후 VTK 3D 뷰 stale |
