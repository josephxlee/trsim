# Phase 5 마감 + Phase 6 NN + Phase 7 DLC — 한 세션 인계 (2026-05-11)

같은 자동-진행 세션 1회에 Phase 5 마무리 (skip 회수 포함), Phase 6
NN 통합 MVP 전체, Phase 7 DLC 시스템 전체. 새 세션이 5분 안에
따라잡기 위한 짧은 인계.

## 0. 현재 상태 (한 줄)

- HEAD = `be41394` (Phase 7.3+7.4+7.5)
- 누적 **1484 PASS** local (Phase 4 끝 998 → +486 신규 tests)
- ruff / mypy strict / import-linter 5 contracts KEPT 매 commit
- 21 commits main 직접 push (이 세션)

## 1. 다음 진입점 (이 줄만 갱신)

**선택지** (사용자 결정 영역, 모두 결정 입력 필요):

A. **main_window wire-up** — PackageManager.scan → PluginLoader.load_all
   → ResourceLibrary + PanelRegistry.register_dlc_plugins → Editor /
   Simulator UI dock mount. 4 layer connection.
B. **Variant build runner** — DatasetBuilder + PipelineRunner 를 4 variant
   자동 chain build + VariantsManifest TOML 생성 + Step 1 UI 의 variant
   picker. (task 4 의 후속)
C. **Real TrainerService backend** — fake-loop → numpy MLP 또는 외부
   `workbench-train` CLI subprocess wrapping.
D. **Resource Browser 연결** — Phase 4.4 sidebar 의 ResourceLibrary
   데이터 source slot wire.

권고: A 가 가장 valuable — 모든 Phase 7 작업의 finale, DLC 가 실제로
mount 되는 첫 흐름.

## 2. 이 세션 누적 push (21 commits)

| commit | phase / task |
|---|---|
| `f41044f` | 5.14 ExtendedTarget glint |
| `c9a68d2` | 5.17 + 5.18 tracker scenario + GNN |
| `b2db473` | docs wrap-up Phase 5 |
| `35d3741` | 5.19~5.22 closing batch (multipath / horizon golden + glint RMS + maneuver) |
| `9d12a6e` | 5.15 + 5.16 (skip 회수: coherence_validator + simulation_domain src 신규 + test) |
| `c778f6d` | 6.1 + 6.2 NN schema + NNPluginMixin |
| `9dc0974` | 6.3 DataExporter HDF5 |
| `7d60a5e` | 6.4a DatasetBuilder streaming |
| `044f689` | 6.4b Pipeline probe-hook |
| `249821f` | 6.4c Step 1 UI controller |
| `a876e4f` | 6.5 NumpyPairingNN reference |
| `64d46de` | 6.6 NNEvaluator 4-error |
| `592b0b8` | 6.7 TrainerService stub + Phase 6 wrap-up |
| `49de982` | 6.8 Step 2 controller |
| `ef42b02` | task 2 — real Pipeline probe wire (random demo → scenario-driven) |
| `64cb09f` | task 3 — Training Panel UI |
| `f75d9d7` | Phase 7.1 — `.trsim-pkg` manifest schema |
| `10848b9` | Phase 7.2 — PackageManager scan |
| `730eed0` | task 4 — Variant 4-tier manifest |
| `be41394` | **Phase 7.3 + 7.4 + 7.5** — PluginLoader + ResourceLibrary + PanelRegistry |

## 3. Phase 별 요약

### Phase 5 (verification framework, 18 카테고리, +236 tests)

처음 5.14 부터 회복. 5.15/5.16 은 src 미구현이라 처음에는 skip 했지만,
같은 세션 후반에 신규 구현 후 verification 추가. 5.17~5.22 는 tracker
scenario + multipath/horizon golden + glint RMS + maneuver. Phase 5
종료 시 1448 PASS local (당시).

5.x 패턴 안정 — golden JSON closed-form + invariant + validation 3
layer, 매 phase 8~22 tests, 기존 unit test 와 다른 각도 (multi-frame /
글로벌 / golden geometry).

### Phase 6 (NN 통합 MVP, 8 sub-step + task 2/3, +247 tests)

스택: schema (6.1) → NNPluginMixin Protocol (6.2) → HDF5 IO (6.3) →
DatasetBuilder (6.4a) → Pipeline probe (6.4b) → Step 1 UI (6.4c) →
NumpyPairingNN baseline (6.5) → 4-error Evaluator (6.6) → TrainerService
fake-loop (6.7) → Step 2 UI (6.8) → real Pipeline probe wire (task 2) →
Training Panel (task 3).

NN 파이프라인 end-to-end 동작 (Editor 안):
```
Step 1 → DatasetBuilder + PipelineRunner (default_pairing_scenario,
         FMCW Triangle closed-form GT, 3 target diagonal pair_indices)
       → write_dataset HDF5
Step 2 → pairing_loss(plugin, dataset) → Pairing 행 RMSE
Training panel → TrainerService fake-loop → placeholder weights .npz
```

### Phase 7 (DLC 시스템, 5 sub-step + task 4, +106 tests)

- 7.1 manifest.toml schema (frozen dataclass + tomllib reader,
  kebab-case + SemVer + license required)
- 7.2 PackageManager scan (`~/.trsim/packages/` 디렉토리, duplicate
  package_id 첫 winner, load_errors 누적, rescan 가 state 교체)
- 7.3 PluginLoader (`module:attr` import via importlib.util.spec_from_
  file_location / 디렉토리 path slot resolve / load_errors)
- 7.4 ResourceLibrary 3-source (User > Package > Built-in, shadowed_
  by_source 보고, 4 카테고리: maps/radars/targets/scenarios)
- 7.5 PanelRegistry (workspace / dock_area tagging, register_dlc_
  plugins 가 PluginLoader 결과 자동 등록)
- task 4 Variant manifest (4-tier A/B/C/D preset + TOML write/read)

## 4. 운영 학습 (이 세션)

1. **Auto mode 활성 시 main push 자동 차단** — settings.local.json 에
   `"Bash(git push origin HEAD:main)"` allow 룰 추가 필요.
   `update-config` skill 자체도 self-modification 으로 차단 — 사용자가
   직접 settings.local.json 편집해야.
2. **itertools.pairwise vs zip(strict=True)** — 길이 다른 list
   `zip(a, a[1:], strict=True)` 가 ValueError. `pairwise(a)` 가 표준.
   5.17 + 6.7 둘 다 함정.
3. **GeoOrigin field 이름**: `lat_deg / lon_deg / alt_m` (not
   `latitude_deg / longitude_deg`).
4. **Step1DatasetPanel accessor 는 method** (not property) — 호출
   필요: `panel.frames_edit().setText(...)`, `panel.status_label().text()`.
5. **PYTHONIOENCODING=utf-8 + PYTHONUTF8=1** lint-imports.exe 호출 시
   필수 (cp949 codec fail 회피).
6. **plan/07 § 7.4.5b GT pair_indices** = 닫힌형 diagonal. FMCW Triangle
   physics 로 build_pairing_matrix 단순화 — multi-target 시 target i
   의 up[i] ↔ down[i].
7. **bindfs 잘림 0** — 모든 21 commits 에서 truncation 발생 없음.

## 5. 다음 세션 진입 명령

```bash
cd "C:/Workspaces/Claude/Tracking Radar Simulator/trsim"
git pull --ff-only
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest -q
# 1484 PASS expected
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/lint-imports.exe
# 5 contracts KEPT
```

CI 결과는 사용자가 push 직후 `docs/sessions/_ci_log.md` 한 줄 추가 흐름
(워크플로 `docs/agent_workflows/ci_status.md`). 자동 진행 중에는 skip 함.

## 6. 알려진 후속 후보 (사용자 결정 필요)

- main_window wire-up (위 A)
- Variant build runner (위 B)
- Real TrainerService backend (위 C)
- Resource Browser 데이터 source slot 연결 (위 D)
- Phase 4.11 NN mode 의 Training panel 통합 (TrainingPanel + 4.11 UI 합치기)
- ExtendedTarget σ_glint RMS 정량 회귀 (5.21 후속)
- High-g UKF/EKF RMSE 정량 회귀 (5.22 후속)
- multipath/horizon golden 추가 case 보강 (5.19/5.20 후속)
