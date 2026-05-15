# debug/backend/ — 백엔드 로직 격리 하니스

domain / app / physics 레이어의 계산·상태·파이프라인 버그를 UI 없이
재현하는 곳. **Qt 불필요, headless, 순수 Python.**

## 패턴

```python
import sys
from pathlib import Path
_SRC = Path(__file__).resolve().parents[3] / "src"   # 깊이에 맞게 조정
sys.path.insert(0, str(_SRC))

# 실제 domain/app/physics 클래스 import → 최소 입력 주입 → print / assert
```

- 실제 클래스를 import 해 의심 함수/파이프라인만 최소 입력으로 호출.
- Qt 이벤트 루프 없음 — 그냥 실행하고 값을 출력/단언.
- headless 라 CI 에서도 돌릴 수 있다. 재현이 안정적이면 그대로
  `tests/` 의 회귀 테스트로 승격하는 것도 고려.

## 프론트엔드 격리와의 경계

- 증상이 **화면/위젯/렌더링**에 보이면 → `debug/frontend/`.
- 증상이 **숫자/상태/예외**(트래커 발산, 파이프라인 NaN, 좌표 변환
  오차 등)면 → 여기.

## 케이스

(아직 없음 — 첫 백엔드 격리 케이스가 생기면 `<case_name>/` 폴더로 추가)
