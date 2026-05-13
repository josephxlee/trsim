# Phase 9 cycle — Library Models 동적 채우기 (2026-05-13)

직전 Phase 4 G1-G4 cycle 종료 후 같은 세션에서 이어진 다음 cycle.
사용자 우선순위 (physics_lab > simulator > editor) 의 spirit 따라
Phase 9 § 19.7.5+ 의 "Library Models 동적 채우기" polish 작업.

## 0. 한 줄 요약

- HEAD = `03b22e9` (H2 + MVP_STATUS update).
- 누적 **2468 PASS** local (2434 → 2468, **+34 신규** in this cycle).
- 5 contracts KEPT 매 commit. ruff / mypy --strict / import-linter
  all clean.
- 2 sub-step (H1-H2) 직접 origin/main fast-forward.

## 1. sub-step 표

| sub | commit | new tests | 범위 |
|---|---|---|---|
| H1 | `0773c9d` | +12 | LibraryWidget `set_physics_models(Iterable[PhysicsModelProtocol])` + `physics_model_for(label)` + `physics_model_selected(model)` signal. Empty iterable → legacy 2 placeholder backward-compat. Duplicate name reject. |
| H2 | `03b22e9` | +22 | `app/physics_lab/model_registry.py` 신규 — `builtin_physics_models()` (Gravity + BouncingBall + FreeSpaceLoss) + `register_physics_model(model)` plug-in hook + `default_physics_models()` + `physics_models_from(*, include_builtins, extra)`. PhysicsLabWorkspace `physics_models` kwarg + `set_/refresh_/physics_models()` API. |

## 2. MVP_STATUS 매트릭스 변경

| 행 | before | after |
|---|---|---|
| **plan/19 § 19.7.5+ 확장** (Validation Bench 일반화 / Library Models 동적 채우기 / Plugin discovery via PluginLoader) | △ (후속 candidate) | △ (Library Models 동적 ✓ via H1-H2; Validation Bench 일반화 + PluginLoader discovery 후속) |

## 3. 사용자 우선순위 (변동 없음)

> **physics_lab > simulator > editor**

이 cycle 후 누적 ✓: Phase 9 / Phase 5 후속 / Phase 6 NN 보강 / Phase 5
추가 후속 / Phase 7 DLC CLI / Phase 7 remainder (C7-C8 + F1-F3) /
Phase 3 누락 4 모듈 / Phase 4 dem_import_wizard / Phase 4 domain_
settings + installation_panel / **Phase 9 § 19.7.5+ Library Models
동적 채우기**.

## 4. 운영 학습 (이 cycle 2개)

1. **Edit 의 old_string 매칭 끝까지 안 닿는 위험** (H1) — 큰 method
   끝에 새 method 추가 시 `Edit` 의 `old_string` 이 기존 method
   전체 body 를 포함해야 함. 그러지 않으면 새 코드가 method 본체
   "중간" 에 삽입되어 indentation error. 발견 후 즉시 split edit.
2. **PhysicsModelProtocol runtime_checkable 활용** — register hook
   에서 `isinstance(model, PhysicsModelProtocol)` 한 줄로 gate.
   protocol member 가 모두 property / 0-arg method 라 check 도 빠름.

## 5. 다음 cycle 후보 (자동 모드 계속이면)

`docs/MVP_STATUS.md § "미구현 우선순위 리스트"`:

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | **Phase 4 UI 실 데이터 binding** | 대 | Editor 5 activity / Simulator 8 panel placeholder → 실 데이터. 여러 cycle 분할. G3 의 `set_map_bounds`, G4 의 `set_terrain_altitude` / `set_coverage_stats` API 준비됨 — wiring 만 남음. |
| 2 | **Phase 8 HIL 전체** | 매우 대 | 8.1 MVP → Lock-step → 8.2 L2/L4 → 8.3 L1+AWG. 새 protocol + 새 layer + UI panel + sample mock. |
| 3 | **Phase 9 § 19.7.5+ remainder** | 소-중 | Validation Bench 일반화 (현재 BouncingBall 만) + PluginLoader 가 PhysicsModelProtocol 도 discover. |
| 4 | **Polish**: Floating dock 옵션 B / Theme manager / Stone Soup adapter | 소 | 미루기 가능. |

자동 진행 모드 다음 cycle = 추천 1 (실 데이터 binding) 의 첫 sub-step
부터 — Editor 5 activity 중 하나 (예: Map Editor 가 ResourceLibrary
에서 Map 로드 시 set_map_bounds 자동 호출 wire). 또는 우선순위 3 의
PluginLoader discovery (작음, H2 의 registry 위에 자연).

## 6. UAT 영향

`docs/sessions/user_acceptance_test_2026_05_13.md` 갱신:
- 새 영역 E. Phase 9 Library Models 동적 채우기 추가
  - Physics Lab Library 의 Models 카테고리가 3 row (Gravity Only +
    Bouncing Ball + Free-Space Loss) 로 표시되는지 확인.
  - 각 row 클릭 시 `physics_model_selected` signal 발생 (UI 변화는
    후속 cycle).

## 7. 이 cycle 의 commit (origin/main 시간 순)

```
0773c9d feat(ui): Phase 9 H1 — LibraryWidget set_physics_models dynamic registry
03b22e9 feat(app)+feat(ui): Phase 9 H2 — physics_lab model_registry + workspace wiring
```

(MVP_STATUS doc update + handoff doc 은 마감 commit 에 묶음.)
