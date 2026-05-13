# Phase 9 cycle — PluginLoader Physics-Model Discovery (2026-05-13)

직전 Phase 9 H1-H2 cycle (Library Models 동적 채우기) 와 같은 세션의
이어진 cycle. plan/19 § 19.7.5+ remainder 의 "Plugin discovery via
PluginLoader" 작업.

## 0. 한 줄 요약

- HEAD = `eed2640` (I2 + MVP_STATUS update).
- 누적 **2486 PASS** local (2468 → 2486, **+18 신규** in this cycle).
- 5 contracts KEPT 매 commit. ruff / mypy --strict / import-linter
  all clean.
- 2 sub-step (I1-I2) 직접 origin/main fast-forward.

## 1. sub-step 표

| sub | commit | new tests | 범위 |
|---|---|---|---|
| I1 | `0e9a01f` | +4 | PluginLoader 의 `_PYTHON_IMPORT_EXACT_SLOTS` frozenset 신설. SDK `KNOWN_ENTRY_POINT_SLOTS` 의 9 singleton 슬롯 (`trsim.physics_model` / `trsim.tracker` / `trsim.pairing` / `trsim.predictor` / `trsim.classifier` / `trsim.data_associator` / `trsim.angle_estimator` / `trsim.detector` / `trsim.dut_adapter`) 가 Python-import 으로 dispatch. error message 의 hint 도 갱신. |
| I2 | `eed2640` | +14 | `app/physics_lab/discovery.py` 신규 — `DiscoveryError` / `DiscoveryResult` frozen dataclass + `physics_models_from_loaded_plugins(loaded)` pure transform (None attr / ctor raise / protocol 미충족 모두 errors[] 로) + `register_discovered_physics_models(loaded)` side-effect helper (built-in name collision silent skip, registered_count 만 반영). |

## 2. MVP_STATUS 매트릭스 변경

| 행 | before | after |
|---|---|---|
| **plan/19 § 19.7.5+ 확장** | △ (H1-H2 Library Models 동적 ✓; PluginLoader discovery 후속) | △ (H1-H2 + I1-I2 Plugin discovery via PluginLoader ✓; Validation Bench 일반화 후속) |

## 3. 사용자 우선순위 (변동 없음)

> **physics_lab > simulator > editor**

이 cycle 후 누적 ✓: Phase 9 / Phase 5 후속 / Phase 6 NN 보강 / Phase 5
추가 후속 / Phase 7 DLC CLI / Phase 7 remainder / Phase 3 누락 4 모듈 /
Phase 4 dem_import_wizard / Phase 4 domain_settings + installation_panel /
Phase 9 § 19.7.5+ Library Models 동적 / **Phase 9 § 19.7.5+ PluginLoader
discovery**.

## 4. 운영 학습 (이 cycle 2개)

1. **SDK validator ↔ PluginLoader 불일치 회피** (I1) — SDK
   `package_validator.KNOWN_ENTRY_POINT_SLOTS` 에 9 singleton 슬롯
   listing 됐지만 plugin_loader 가 prefix match (`trsim.plugins.` /
   `trsim.ui.` / `trsim.resources.`) 만 했어서 실제 install 시 unknown
   slot error. 양쪽 set 동기화 + plugin_loader 의 dispatch 가 exact-set
   first, prefix second 로 변경. 두 set 가 어긋날 가능성 줄이려면
   미래에 동일 module 에 정의.
2. **runtime_checkable Protocol 의 instance check 가 cheap** (I2) —
   PhysicsModelProtocol member 가 모두 property + 0-arg method 라
   `isinstance(instance, PhysicsModelProtocol)` 가 호출 비용 적음.
   discovery 의 protocol gate 가 한 줄로 가능.

## 5. 다음 cycle 후보

`docs/MVP_STATUS.md § "미구현 우선순위 리스트"`:

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | **Phase 4 UI 실 데이터 binding** | 대 | Editor 5 activity / Simulator 8 panel placeholder → 실 데이터. 여러 cycle 분할. |
| 2 | **Phase 8 HIL 전체** | 매우 대 | 8.1 MVP → Lock-step → 8.2 L2/L4 → 8.3 L1+AWG. |
| 3 | **MainWindow → DLC physics-model auto-register** | 소 | I2 의 `register_discovered_physics_models(plugin_loader.plugins)` 호출 wiring. PhysicsLabWorkspace 가 import 직후 자동으로 DLC 의 physics model 사용 가능. |
| 4 | **Phase 9 § 19.7.5+ Validation Bench 일반화** | 소-중 | 현재 BouncingBall 만 — 임의 PhysicsModelProtocol 에 대해 일반화. |

자동 모드 다음 cycle = 추천 3 (MainWindow wiring) — 작고 self-contained,
직전 2 cycle 의 H+I 결과를 사용자에게 처음으로 visible 하게 만듦.

## 6. 이 cycle 의 commit (origin/main 시간 순)

```
0e9a01f feat(app): Phase 9 I1 — PluginLoader trsim.physics_model singleton slot
eed2640 feat(app): Phase 9 I2 — physics_lab discovery (LoadedPlugin → registry)
```

(MVP_STATUS + CLAUDE.md + handoff doc 은 마감 commit 에 묶음.)
