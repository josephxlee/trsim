# MVP hand-test in progress — handoff (2026-05-15)

사용자가 CLI 단에서 기본 골격 안정성 확인하는 동안의 대기-기간
인계 문서. 새 세션 또는 이 세션이 재개 시 이 파일이 첫 진입점.
다음 세션의 작업은 hand-test 결과 (1.F.1 ~ 1.F.11) 받아서
`docs/MVP_VERIFICATION_TREE.md` 의 ☐ → ✓ / △ / ✗ in-place 갱신 + 새
✗ 가 § 4 표에 추가.

## 0. 한 줄 요약

- main HEAD = `2488774` (직전 cycle 의 design docs scaffold commit).
- 누적 **2807 PASS** local (P5b/P5d 가산 후). 5 contracts KEPT.
- 사용자 = CLI 단 hand-test 진행 중. 한국어 반말 / 간결 톤.
- 이 세션이 push 한 origin/main commit 2 개 (`84eadf8`, `2488774`).

## 1. 이번 cycle 누적 변경 (3 commit, 시간순)

| commit | 종류 | 내용 |
|---|---|---|
| `a8c75c6` | fix(ui) | Scene3D `QtInteractor.setFocusPolicy(StrongFocus)` + `setMouseTracking(True)` (마우스 휠/드래그 안 먹던 거 fix). 함께 Simulator workspace splitter stretch ratio 정정 — top_row `1:3:1:1` (이전 `0:1:0:0`) + outer `3:1` (이전 `1:0`). maximize 시 panel 비율 정상 확장. |
| `84eadf8` | docs | `docs/MVP_VERIFICATION_TREE.md` 신규 (393 lines). Simulation 워크스페이스를 Front / Wire / Back 3 layer 로 분해, leaf 마다 ☐ marker. § 4 잔여 이슈 표 (6 entries). § 5 isolation API reference. |
| `2488774` | docs | `docs/design/` 폴더 scaffold + `simulator/scene_3d_panel.md` 본격 다이어그램 (9 절). plan/ (plan-of-record) 와 분리된 as-built design docs. mermaid + ASCII art 혼용. |

### 직전 cycle 잔재 (MVP 완성, `mvp_completion_2026_05_14.md`)

P1~P8 8 sub-step 다 ✓. HIL post-MVP. 누적 2790 PASS. 그 위에
P5b (Properties fast path) + P5d (run_controller idempotent) 추가
push 까지 2807 PASS. P5c (resize paint suppression) 는 ✗ — revert
(`5c3be82`).

## 2. 진행 중 — Simulation Front hand-test (plan 승인됨)

`~/.claude/plans/mvp-abstract-bear.md` 의 4-step chunking. 위치 = Step 1.

```
Step 1  Workspace shell + toolbar         ← 사용자 입력 대기
        (1.F.1, 3 leaf)
Step 2  8 panel widget mount + layout
        (1.F.2 ~ 1.F.10, 9 leaf)
Step 3  Resize / window behavior
        (1.F.11, 3 leaf — 일부 ✗ 이미 표시)
Step 4  결과 보고 + 트리 갱신 + commit/push
```

다음 세션의 첫 행동: 사용자가 보고한 1.F.1 결과 받아서
`docs/MVP_VERIFICATION_TREE.md` 의 해당 leaf 3 개를 `Edit` 으로 in-place
마크. 새 ✗ 가 § 4 표에 추가.

## 3. 알려진 ✗ (Simulation Front) — fix 후보 정리

`MVP_VERIFICATION_TREE.md § 4` 의 6 entries 중 active 2 개:

### 3.1 Run 중 resize 시 panel paint conflict (1.F.11 2번째 leaf)

- P5c (`c09cc88`) tick_completed suppression 시도 → 더 이상해져서
  revert (`5c3be82`).
- 후속 fix path 후보 (한 줄로):
  - `widget.setUpdatesEnabled(False)` 를 splitterMoved 전후로
  - tick rate 를 resize 동안 한시 감속
  - Qt 의 `WA_OpaquePaintEvent` flag 활용

### 3.2 창 maximize 시 FFT / RD 그래프 잔상 (1.F.11 마지막 leaf)

- VTK QtInteractor (native OpenGL surface) + pyqtgraph (alien Qt) 의
  BitBlt 잔재 가설. `docs/design/simulator/scene_3d_panel.md § 8.1`
  에 fix path A / B / C 후보 명시:
  - **A**: `Scene3DPanel.resizeEvent` override → `self.update()` +
    `self._interactor.render()` 강제
  - **B**: `SimulatorWorkspace.resizeEvent` 에서 child 들에
    broadcast `update()`
  - **C**: QtInteractor 의 `WA_DontCreateNativeAncestors` 해제

3.1 fix 가 3.2 도 자연 해결할 가능성 (둘 다 paint conflict).

## 4. 다음 세션 진입 절차

### 4.1 사용자가 hand-test 결과 보고했을 때

1. `docs/MVP_VERIFICATION_TREE.md` 를 Read (큰 파일이라
   offset/limit 활용 — 1.F 영역만).
2. 해당 leaf 의 `☐` 를 `Edit` 으로 `✓` / `△` / `✗` 마크.
3. 새 `✗` 면 § 4 잔여 이슈 표에 한 줄 추가 (leaf 위치 + 짧은
   원인 + "후속 cycle").
4. commit + push (worktree branch → origin/main ff).
5. 다음 Step 안내 (현재 Step 1 → Step 2 → 3 → 4).

### 4.2 사용자가 새 fix 요청했을 때

§ 3 의 fix path 중 사용자가 지정한 path 로 시도. 시도 후 결과 안
좋으면 **즉시 revert** (P5c 처럼). MVP 단계라 "더 이상해지는 fix"
는 무가치.

### 4.3 사용자가 다음 cycle 진입 신호 줬을 때

`docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 첫 행 참조. 현재
active 후보:
- Simulation Wire (1.W) hand-test
- Simulation Back (1.B) verification
- Front 잔여 ✗ 2 개 fix cycle
- Physics Lab + Editor 트리 작성 (지금 § 2 / § 3 placeholder)

## 5. 환경 / 도구 메모

- worktree: `.claude/worktrees/suspicious-bhabha-818f39/`
- branch: `claude/suspicious-bhabha-818f39`
- 직전 작업 직후 stale worktree 10 개 + stale branch 11 개 정리 →
  메인 + 현재 세션 2 worktree / 1 branch 만 남음.
- 사용자 PC = Windows + PowerShell. 명령 제시 시 PowerShell 우선
  (`.\.venv\Scripts\trsim.exe ui --workspace simulator`).
- pytest 환경 = `.venv` Python 3.13 + PySide6 6.11 + pyqtgraph 0.14
  + pyvista 0.48 + pyvistaqt.
- CI 결과 추측 금지 (CLAUDE.md § 7.1) — push 후 `_ci_log.md` 한
  줄 추가 흐름.

## 6. 정합성 체크 (이 핸드오프 작성 시 점검)

방금 push 한 design docs 가 코드와 어긋나면 다음 세션이 신뢰 못 함.
재확인:

| 항목 | 위치 | 매치 |
|---|---|---|
| plan/05 § 5.3.2 | `plan/05_ui_ux.md:152` | ✓ |
| plan/05 § 5.5.4b | `plan/05_ui_ux.md:919` | ✓ |
| MVP_VERIFICATION_TREE § 4 | `docs/MVP_VERIFICATION_TREE.md:311` | ✓ |
| `Scene3DPanel` 클래스 | `src/workbench/ui/simulator/panels/scene_3d_panel.py:108` | ✓ |
| `SimulatorSceneController` | `src/workbench/ui/simulator/scene_controller.py:25` | ✓ |
| `MockSceneGenerator` | `src/workbench/app/simulator/mock_scene.py:51` | ✓ |
| `SceneLayer` 11 값 | enum value 표 매치 | ✓ |
| `_DEFAULT_ON` 8 종 | TERRAIN/SEA/BUILDINGS/SHIPS/TX_BEAM_ACTUAL/GT_TARGETS/TRACKS/PRIMARY_HIGHLIGHT | ✓ |
| `CameraPreset` 4 값 + 라벨/단축 | TOP=T / LEFT=L / FREE=F / RADAR=R | ✓ |
| `_RADAR_MARKER_RADIUS_M=80` / `_TARGET_MARKER_RADIUS_M=60` | scene_3d_panel.py 상수 | ✓ |
| Mock orbit default | radius=4000m / period=30s / alt=500m / terrain halfspan=8000m | ✓ |
| `enable_3d_viewer` lazy 패턴 | scene_3d_panel.py:182~200 | ✓ |
| `setFocusPolicy(StrongFocus)` + `setMouseTracking(True)` | scene_3d_panel.py:196~197 | ✓ |
| `pyvistaqt.*` mypy override | pyproject.toml:200~209 | ✓ |
| design 문서 § 8.1 cross-link | `MVP_VERIFICATION_TREE.md § 4` 와 동일 이슈 | ✓ |

15 항목 all ✓. 다음 세션이 이 문서를 첫 참조점으로 써도 OK.

## 7. 사용자 톤 / 우선순위 (변동 없음)

- 한국어 반말, 간결.
- "추천대로" / "그렇게 가자" = full GO. 다시 묻지 말기.
- 누적 결정 ~100 개 이미 끝남. 블로커 0.
- **physics_lab > simulator > editor** 우선순위. 현재 simulator
  Front hand-test 마무리 단계.

## 8. 이 cycle commit (origin/main)

```
2488774 docs: design docs scaffold + Scene3DPanel diagram
84eadf8 docs: MVP verification tree (Simulation only) — layered to-do single-source
a8c75c6 fix(ui): Scene3D mouse focus + Simulator splitter stretch ratios
```

세 commit 모두 ff push 완료. 직전 mvp_completion (`mvp_completion_
2026_05_14.md`) 핸드오프와의 차이 = 위 3 commit + MVP_VERIFICATION_
TREE.md 의 Simulation 트리 + design docs scaffold.

---

다음 세션은 이 파일 + `MVP_VERIFICATION_TREE.md § 1.F` + 사용자 보고만
보면 즉시 작업 재개 가능. 고생하세요.
