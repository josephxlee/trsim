# debug/ — 격리 디버깅 작업 공간

`trsim ui` 또는 백엔드에서 문제가 생기면, **전체 앱에서 떼어내 가장 작은
독립 하니스로 재현**해 원인을 이분할(bisect)하는 공간이다.

- 테스트 스위트도, 배포 패키지(`src/workbench/`)도 아니다 — 개발자 전용
  scratch 영역.
- 하니스는 항상 **실제 클래스를 import** 한다 (소스 복사 금지 — 복사본은
  버그가 아니라 복사본을 테스트하게 됨).

## 구조

```
debug/
├── frontend/   UI 격리 — Qt / VTK / pyqtgraph / 렌더링. 디스플레이 필요.
└── backend/    로직 격리 — domain / app / physics. headless, Qt 없음.
```

각 케이스는 `<frontend|backend>/<case_name>/` 폴더 하나로:

```
frontend/scene3d_resize_ghost/
├── README.md            케이스 writeup (증상→조사→근본원인→수정→교훈)
└── panel_isolation.py   재현 하니스
```

## 새 케이스 추가 절차

1. frontend(화면 필요) / backend(headless) 판별 → 해당 폴더 밑에
   `<case_name>/` 생성.
2. 하니스 스크립트 작성 — `sys.path`에 `src/` 추가 후 실제 클래스 import,
   문제 컴포넌트만 최소 셸에 마운트.
3. 해결되면 `README.md`에 writeup 작성 — 특히 **막다른 길**과 **교훈**을
   남겨 다음 사람이 같은 헛수고를 반복하지 않게 한다.

## 해결된 케이스

| 케이스 | 영역 | 요약 |
|---|---|---|
| [scene3d_resize_ghost](frontend/scene3d_resize_ghost/README.md) | frontend | 리사이즈 후 VTK 3D 뷰가 stale — 네이티브 윈도우 페인트 문제 |
