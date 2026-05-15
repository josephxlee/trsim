# 세션 핸드오프 2026-05-15 — Scene3D polish + 격리 디버깅 인프라

## 0. 한 줄 요약

MVP 완성(P1~P8) 후 polish 세션. Scene3D 리사이즈 잔상 수정 + 카메라
단축키 / 프리셋 실동작 + actor lifecycle 리팩터 + `debug/` 격리 디버깅
폴더 신설. 누적 **2804 → 2814 PASS** (+10). 5 contracts KEPT. ruff /
mypy --strict / import-linter all clean. CLAUDE.md 정리(1310 → 197줄).

## 1. 작업 내역

| # | 내용 |
|---|---|
| 1 | **CLAUDE.md 정리** — § 1 의 sub-step 누적 로그(1310줄)를 `SESSION_SUMMARY.md` + `docs/sessions/` 로 위임, 현재 상태 한 단락만 유지 → 197줄. § 3.4b PySide6 트랩 신설. |
| 2 | **handoff 리뷰** — `mvp_completion_2026_05_14.md` § 1 표 검증, P7 행 `+16` → `+11` 수정 (커밋별 실측 `def test_` 수와 불일치, footer +83 이 정답). |
| 3 | **Scene3D 리사이즈 잔상 수정** — `scene_3d_panel.py`: `resizeEvent` 가 단일샷 `QTimer`(`_RESIZE_RENDER_DEBOUNCE_MS=50`)를 (재)시작 → `_render_interactor` 가 레이아웃 정착 후 `interactor.render()` 1회. 즉시 inline render(너무 이름)에서 디바운스 정착 렌더로. |
| 4 | **Scene3D actor lifecycle 리팩터** — `set_scene_frame` 이 매 프레임 radar/target sphere 를 `remove_actor`+`add_mesh` 재생성하던 것을 `_ensure_marker` 로 1회 생성 + `.position` transform 갱신. `interactor_factory` 주입점 추가(headless 테스트 검증용 fake interactor). |
| 5 | **카메라 단축키** — T/L/F/R `QShortcut` (`WidgetWithChildrenShortcut` 스코프 — VTK 캔버스 포커스 시에도 동작). 기존엔 버튼 라벨에 글자만 있고 미연결. |
| 6 | **카메라 프리셋 실동작** — `_apply_camera_preset` 신규: TOP `view_xy` / LEFT `view_yz` / FREE `view_isometric` / RADAR `camera_position`. 기존엔 `camera_preset_chosen` emit 만 하고 소비처가 없어 화면이 안 바뀜. |
| 7 | **`debug/` 격리 디버깅 폴더** — `frontend/` (UI, 디스플레이 필요) / `backend/` (로직, headless) 분리 구조. `frontend/scene3d_resize_ghost/` 에 케이스 writeup + `panel_isolation.py` 하니스. |

## 2. 테스트

- 2804 → 2814 PASS (+10: 리사이즈/actor 5, 카메라 단축키 2, 카메라 적용 2,
  나머지 회귀). `.venv` Python 3.13.3, pytest-qt 4.5.0.
- ruff / mypy --strict / import-linter 5 contracts all clean.

## 3. Scene3D 리사이즈 잔상 — 근본 원인

상세 디버깅 기록: `debug/frontend/scene3d_resize_ghost/README.md`.

요약: pyvistaqt `QtInteractor` 는 `WA_PaintOnScreen` 네이티브 윈도우 —
Qt 백킹스토어 없이 VTK 가 OS 윈도우에 직접 렌더. 리사이즈 후 render
window 는 올바르게 `SetSize` 되지만(크기는 항상 정상이었음, 크기 프로브로
확정) 새 프레임이 화면에 자동으로 안 올라옴. 정착 후 명시적 render 트리거
필요 → 디바운스 정착 렌더가 수정. `QVTKRWIBase="QOpenGLWidget"` 은
pyvistaqt `rwi.py` 가 네이티브 페인트를 하드코딩해 불가(막다른 길).

## 4. 잔여 / 다음

- **커밋 안 됨** — 세션 변경(`scene_3d_panel.py`, scene 테스트 3종,
  `CLAUDE.md`, `mvp_completion_2026_05_14.md`, `debug/`, 이 문서)이
  uncommitted. 사용자 확인 후 커밋.
- 향후 `trsim ui` 문제는 `debug/` 격리 워크플로로 — `debug/README.md`
  의 절차 참조. UI 증상은 `frontend/`, 로직 증상은 `backend/`.
- Post-MVP punch list (변동 없음): Phase 8 HIL / Pipeline real binding /
  NN per-category real loss.

## 5. 학습 / 트랩

- **blind 패치 금지** — Scene3D 리사이즈를 증상 가정만으로 2번 잘못
  패치. 격리 하니스 + 크기 프로브로 데이터를 확보하고서야 진짜 원인
  판명. UI 버그는 측정 먼저.
- **VTK-in-Qt** — 임베드 interactor 는 네이티브 윈도우. 리사이즈/페인트
  아티팩트는 VTK 렌더링이 아니라 네이티브-윈도우 페인트 모델에서 옴.
- **수정 후 재시작** — `trsim ui` 수정 검증 시 완전 재시작 후 확인.
  떠 있던 옛 인스턴스가 false "아직 안 됨" 보고를 유발.
