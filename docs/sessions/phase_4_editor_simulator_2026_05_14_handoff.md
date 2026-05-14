# Phase 9 / Phase 4 / Phase 3 wrap — 2026-05-13~14 자동 모드 (26 commit)

이 핸드오프는 PR #1 (`claude/check-progress-status-KpNpy`) 의 누적
26 commit 을 정리한다. 직전 핸드오프 `phase_9_validation_simulator
_polish_2026_05_13.md` (commit `da70f65`, 14 commit 시점) 의 후속.

세션 옮길 때 새 클라이언트가 이 문서 + `docs/MVP_STATUS.md` § "미구현
우선순위 리스트" + `CLAUDE.md` 만 봐도 정확한 컨텍스트 복원 가능.

---

## 1. 현재 상태

| | |
|---|---|
| 브랜치 | `claude/check-progress-status-KpNpy` |
| HEAD | `b3012b9` feat(editor): Atmosphere Activity |
| 누적 commit (43c2759 ~ b3012b9) | **26** |
| 누적 신규 tests | **+130** (2518 → **2648 PASS**) |
| 4-gate 로컬 | ruff / format / mypy --strict / lint-imports 전부 green |
| 최근 CI 결과 | `9c6c980` (직전) 8/8 green 확인. `6e757f2` / `ebf03e6` / `b3012b9` 결과 webhook 알림 대기 |

---

## 2. Phase 진행률 (HIL 제외 9-phase 평균 **96%**)

| Phase | 진행률 | 변화 (이 세션) |
|---|---:|---|
| 0 Repo + OSS | 100% | — |
| 1 Primitives | 100% | — |
| 2 Domain | 100% | — |
| **3 Application** | **100%** | ↑ 95% → 100% (Profile gate 마감) |
| **4 UI** | **~80%** | ↑ 50% → 80% (Simulator L1-L6 + Editor 5 controller + Atmosphere Activity) |
| 5 물리 검증 | 100% | reproducibility tests 추가 (#7) |
| 6 NN MVP | 85% | — (Tracker/Predictor/Classifier NN plug-in 출시 의존) |
| **7 DLC** | **98%** | ↑ SDK manifest 이동 (#9) |
| 8 HIL | (MVP 외) | shell only — 사용자 결정 |
| **9 Physics Lab** | **100%** | ↑ M1+M2+M3 Validation Bench 일반화 종결 |

종합: **96%** (HIL 제외) / **86%** (HIL 포함).

---

## 3. 카테고리별 누적 (43c2759 ~ b3012b9)

| 카테고리 | commit 수 | tests | 핵심 commit |
|---|---:|---:|---|
| HIL 우선순위 제외 + Phase 9 Validation Bench 일반화 | 4 | +27 | `43c2759` `b733608` `afc52a2` `3fdd9ff` |
| Phase 4 Simulator L1~L6 (Run + PluginMgr + frame fan-out + Properties + StageIO + FFT peaks) | 6 | +32 | `e504df1` `bda4d51` `d715c68` `66960b9` `9c6c980` (L1 별도) |
| Phase 5 #7 / Phase 7 #9 / Phase 3 #6 sidequest | 3 | +25 | `d833889` `cf0f57e` `5ce10d2` |
| Editor 5 controller cluster | 6 | +28 | `3b0f30a` (Composer dropdown) `56ca1d4` (Composer validate) `73171a4` (Targets) `9f1e107` (Radar) `e05b019` (Atmosphere propagator) `8d80803` (Map) |
| CI fix bundle (PR #1 첫 fail 대응) + macOS pyvistaqt skip | 2 | 0 | `5ffcb73` `26d0e8b` |
| Profile mode runtime gating + Atmosphere Activity 마운트 | 3 | +8 | `6e757f2` `ebf03e6` `b3012b9` |
| docs / handoff | 2 | 0 | `da70f65` `d38be16` `63f047d` |
| **합계** | **26 commit** | **+130 tests** | |

---

## 4. 사용자 우선순위별 결과

### #1 physics_lab (1순위) — **100% 종결**

- **M1** `b733608` — `app/physics_lab/validation_runner.py` (3 함수 +
  ValidationRun dataclass), 17 tests
- **M2** `afc52a2` — BouncingBallController.run_validation_from_dataset
  → M1 layer 위임, 1 parity test
- **M3** `3fdd9ff` — 임의 PhysicsModelProtocol UI dispatch
  (`default_validation_fields` registry + workspace 분기), 9 tests

→ plan/19 § 19.7.5+ "Validation Bench 일반화" closed.

### #2 simulator (2순위) — **~78% (L1-L6 + PluginMgr baseline 완료)**

- **L1** Run panel sim_t/frame_id (직전 cycle, 25db1ae)
- **L2** PluginManager baseline (`e504df1`)
- **L3** FFT/RD/StageIO frame_label fan-out (`bda4d51`)
- **L4** Properties live snapshot + selection pin (`d715c68`)
- **L5** StageIO 6-box placeholder text (`66960b9`)
- **L6** FFT peak counts deterministic pattern (`9c6c980`)

남은 잔여 = FFT spectrum array / RD heatmap matrix / Scene3D PyVista.

### #3 editor (3순위) — **~55% (5 controller + Atmosphere Activity 마운트)**

- **Composer** dropdown (`3b0f30a`) + validate controller (`56ca1d4`)
- **Map** validate controller + auto-stale (`8d80803`)
- **Radar** live computed values (`9f1e107`)
- **Targets** validate controller (`73171a4`)
- **Atmosphere** propagator (`e05b019`) + 6번째 Activity 마운트
  (`b3012b9`, Ctrl+5 단축키, Browser → Ctrl+6)

남은 잔여 = Save round-trip (ScenarioService 의존), Map canvas
pyqtgraph mount.

### 사이드 quest

- **#7** Phase 5 #18/#19 reproducibility tests (`d833889`)
- **#9** SDK manifest.py 이동 (`cf0f57e`) — `domain/dlc` 패키지 삭제
- **#6** Phase 3 Profile mode toggle (`5ce10d2`) + runtime gate
  (`6e757f2`) — **Phase 3 → 100%**

---

## 5. PR #1 CI 이력 + 트랩 정리

| 시도 | 결과 | 비고 |
|---|---|---|
| `9f1e107` (1차) | 7 fail | mypy + lint-imports + circular import + Protocol __test__ 누적 |
| `5ffcb73` (2차) | 7/8 pass | Linux/Windows green, macOS fail (pyvistaqt segfault) |
| `26d0e8b` (3차) | 8/8 pass | macOS skipif 추가 |
| `9c6c980` 등 (4-6차) | 추가 cycle 후 마지막 검증 = 8/8 green | `b3012b9` 결과 webhook 대기 |

**알려진 트랩** (다음 세션 도움):
- `pyvistaqt.QtInteractor.__init__` macOS GitHub Actions runner 에서
  segfault (offscreen 모드여도) — `test_test_object_view.py::test_
  panel_construction_succeeds` 가 darwin skip.
- `TestObjectProtocol.__test__ = False` post-class assignment 가
  Python 3.11 의 `_get_protocol_attrs` 에서 leak — 제거.
- `workbench.sdk.manifest` import 가 `workbench.io.package_io` 통해
  순환 발생 — `sdk/package_builder.py` + `sdk/test_harness.py` 에서
  lazy import 로 회피.
- mypy `[unused-ignore]` 가 stale `# type: ignore` 잡음.
- pytest-qt 가 controller 인스턴스를 GC 함 — 테스트 fixture 에서
  꼭 변수에 assign 해서 참조 유지.

---

## 6. 남은 잔여 (다음 세션 후보)

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | **FFT 실 spectrum array binding** | 중-대 | `numpy.fft.rfft` 합성 chirp + FFTPanel canvas 에 pyqtgraph PlotWidget mount. 3-4 cycle 분량. |
| 2 | **RD 실 heatmap matrix binding** | 중-대 | 동일 chirp 로 2D RD matrix → pyqtgraph ImageView. 2-3 cycle. |
| 3 | **Scene3D PyVista 실 mount** | 중 | PhysicsLab 패턴 적용 (enable_3d_viewer kwarg). 기존 SimulatorWorkspace test 대량 영향 — 신중. 1-2 cycle + test 갱신. |
| 4 | **Map canvas pyqtgraph mount + Save round-trip** | 중 | 실 brush 페인팅 시작점. plan/13 § 13.4. |
| 5 | **RadarEditor / TargetsEditor Save action** | 중 | ScenarioService 필요. |
| 6 | Phase 6 Step 2 per-category dispatch (Tracker / Predictor / Classifier) | 큼 | NN plug-in 외부 출시 후. A1-c stub → real. |
| 7 | Phase 6 multi-step rollout RMSE | 큼 | Sequence dataset spec 후. A1-d stub → real. |

추천 다음 cycle: **#1 FFT 실 spectrum array** — 가장 큰 visible value
(사용자 우선순위 simulator) + Pipeline.step 까지 안 가도 합성 chirp 만
으로 충분.

---

## 7. 사용자 PC 검증 (PowerShell)

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

# pytest (예상 2648 PASS)
& $PY -m pytest -q

# mypy --strict (예상 0 issues, 208 source files)
& $PY -m mypy src/

# import-linter (5 contracts kept)
& $PY -m lint_imports

# ruff
& $PY -m ruff check .
& $PY -m ruff format --check .
```

---

## 8. 한 줄 인계

> PR #1 (`claude/check-progress-status-KpNpy`, 26 commit, 2648 PASS,
> 96% MVP) 의 CI 모두 green. 다음 세션 = **FFT 실 spectrum array
> binding** (#1 후보) 부터 시작 또는 **PR merge 결정** 부터.

---

## 9. 핵심 파일 참조

- `docs/MVP_STATUS.md` — 매트릭스 (행 단위로 ✓/△/✗)
- `CLAUDE.md` § 1 — 현재 진행 상황 (한 줄)
- `docs/sessions/phase_9_validation_simulator_polish_2026_05_13.md` —
  직전 핸드오프 (14 commit 시점)
- `docs/agent_workflows/mvp_status_update.md` — 매 sub-step push 후
  doc 갱신 절차

Branch `claude/check-progress-status-KpNpy` 가 권위; main 은 아직
구버전 `fafd03c`.
