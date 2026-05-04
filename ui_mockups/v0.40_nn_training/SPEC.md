# UI Mockup Spec — NN Training Workflow (v0.40)

**최종 갱신**: 2026-05-04
**대상 plan**: 07 nn_integration, 17 § 17.4.1 (TrackerProtocol NN plugin), 19 § 19.9 형태 2 (NN 대체)
**대상 Phase**: Phase 6 (NN 통합 MVP+α Wave 1)

---

## 0. 의도

**TRsim 차별점 2 (DSP↔NN 동일 인터페이스) 의 NN 측 작업 흐름**.
Simulator 의 SIM-2 가 "NN 사용" 측이라면, NN Training 은 "NN 만들기" 측.

핵심 사용자 흐름:
```
[1] NN Training 열기 (메뉴 또는 SIM-2 의 "Train new NN" 버튼)
[2] Dataset 선택 — Run history (.h5) / 외부 (CSV/HDF5) / 합성
[3] Trainer Config — Plugin dropdown (architecture) + Hyperparameter 슬라이더
[4] Train 시작 — 학습 진행 시각화 (loss curve, gradient stat 등)
[5] Evaluate — 4-error + 학습 영역 vs 외삽 영역 시각
[6] Deploy — Wizard 로 .trsim-pkg packaging → Plugin Manager 등록
```

**5 단계** (Q-NN-1=b): Dataset → Trainer Config → Train → Evaluate → Deploy

---

## 1. Screen NN-1 — Main Workflow

**Dataset / Trainer Config / Deploy 흐름.** Train / Evaluate 는 별도 화면.
**파일**: `ui/nn_training/nn_training_workspace.py`

### 1.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ NN Training Workflow · TRsim                                       [×]  │
├─────────────────────────────────────────────────────────────────────────┤
│ Workflow steps: ⦿ Dataset  ━━ ⦿ Trainer Config  ━━ ○ Train  ━━ ○ Eval  ━━ ○ Deploy │
├──────────────────┬──────────────────────────────────────────────────────┤
│                  │                                                       │
│ Project          │  ── Step 1: Dataset ────────────────────────────────  │
│ ─────            │                                                       │
│ Tracker NN v0.5  │  Source: ⦿ Run history  ○ External file  ○ Synthetic │
│ Maritime base    │                                                       │
│                  │  ┌────────────────────────────────────────────────┐  │
│                  │  │ Selected runs (drag to add):                   │  │
│                  │  │  ✓ #042 Maritime Missile (DSP, 1500 frames)    │  │
│                  │  │  ✓ #041 Maritime Missile (DSP, 1500 frames)    │  │
│                  │  │  ✓ #040 Maritime Missile (DSP, 1500 frames)    │  │
│                  │  │  ✓ #036 Fixed Aircraft (DSP, 2200 frames)      │  │
│                  │  │  ─────────────────────                          │  │
│                  │  │  Total: 6700 trajectory samples                 │  │
│                  │  │  [+ Add Run]  [Filter]                          │  │
│                  │  └────────────────────────────────────────────────┘  │
│                  │                                                       │
│                  │  Split:                                                │
│                  │   Training [▆▆▆▆▆▆▆▆▆▆▆░░░░] 70%  4690 samples       │
│                  │   Dev      [▆▆▆░░░░░░░░░░░░] 20%  1340 samples       │
│                  │   Test     [▆▆░░░░░░░░░░░░░] 10%   670 samples       │
│                  │                                                       │
│                  │  Stratify: ☑ Sea state  ☑ Target type  ☐ Range       │
│                  │                                                       │
│                  │  ── Step 2: Trainer Config ───────────────────────── │
│                  │                                                       │
│                  │  Plugin (architecture):                                │
│                  │  [ torch_lstm_v0.4 ▾ ] ⓘ [View source] [↗ External]  │
│                  │                                                       │
│                  │  Hyperparameter:                                       │
│                  │  Learning rate: [▆▆▆░░░░] 1e-3  (log)                 │
│                  │  Batch size:    [▆▆▆▆▆░░] 64    (linear)              │
│                  │  Epochs:        [▆▆▆▆░░░] 50                           │
│                  │  Optimizer:     [ AdamW ▾ ]                            │
│                  │  Loss function: [ MSE ▾ ]                              │
│                  │  Val split:     [▆▆░░░░░] 15%                         │
│                  │  Early stopping ☑  patience: [10 ]                    │
│                  │  Augmentation:  ☑ Time jitter  ☑ Noise  ☐ Mixup       │
│                  │                                                       │
│                  │                                                       │
│                  │           [Save Config]   [▶ Start Training]          │
│                  │                                                       │
└──────────────────┴──────────────────────────────────────────────────────┘
```

### 1.2 단계 표시 (top progress bar)

5 단계 가로 흐름:
- ⦿ active (현재 작업 중)
- ✓ completed
- ○ pending

각 단계 클릭 가능 (이미 완료한 단계는 다시 보기).

### 1.3 Step 1 — Dataset (Q-NN-3=d)

**3 출처**:
- ⦿ **Run history** — Simulator 의 trace_*.h5 (가장 자연)
- ○ **External file** — CSV / HDF5 / .npz 업로드
- ○ **Synthetic** — 실시간 시뮬 진행하면서 데이터 생성 (Phase 6.2)

**Stratified split**:
- Training / Dev / Test 비율 슬라이더
- Stratify by: Sea state / Target type / Range — 균등 분포 보장

### 1.4 Step 2 — Trainer Config (Q-NN-4 권고)

#### Plugin (architecture) dropdown
설치된 NN plugin 목록 (Plugin Manager 의 TrackerProtocol + NN tag):
- torch_lstm_v0.4
- transformer-tracker (beta)
- 사용자 정의 plugin (Local Install 한 것)

옆 버튼:
- ⓘ Plugin info — name / author / params count / 입력 출력 spec
- **[View source]** — Read-only Pygments 코드 표시 (디버깅·학습)
- **[↗ External IDE]** — VS Code 또는 시스템 default editor 로 plugin 디렉토리 열기

→ **In-app live edit X** (NN 코드 위험성·학습 시간·라이선스 책임)

#### Hyperparameter (Q-NN-4=b)
- **Learning rate** [log scale] — slider + 숫자 입력
- **Batch size** [linear, integer] — 16 / 32 / 64 / 128 / 256
- **Epochs** — 정수
- **Optimizer** dropdown — Adam / AdamW / SGD / RMSprop
- **Loss function** dropdown — MSE / MAE / Huber / Custom (plugin)
- **Validation split** — 학습 안의 val 비율
- **Early stopping** ☑ + patience 정수
- **Augmentation** ☑ — Time jitter / Noise / Mixup

### 1.5 좌측 sidebar

- **Project** 이름 + base info
- 4 단계 상태 (다음 단계 가능 여부)
- 옵션: Recent training runs (다른 사용자 작업)

### 1.6 색·시각

NN 영역 전체 **보라 accent** (Physics Lab 통일, 학술 느낌). Q-NN-7=(a).

---

## 2. Screen NN-2 — Training in Progress

**학습 진행 시각화.** [▶ Start Training] 클릭 → 이 화면.
**파일**: `ui/nn_training/training_progress.py`

### 2.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Training in Progress · Tracker NN v0.5                              [×] │
├─────────────────────────────────────────────────────────────────────────┤
│ Workflow steps: ✓ Dataset  ━━ ✓ Trainer Config  ━━ ⦿ Train  ━━ ○ Eval ─⛔ Deploy │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ Status: ▶ Training  · Epoch 23 / 50  · ETA 18 min  · GPU 0 (RTX 4090)   │
│ Progress: [▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆░░░░░░░░░░░░] 46%                              │
│                                                                          │
├──────────────────────────────────┬──────────────────────────────────────┤
│                                   │                                       │
│  Loss curve                       │  Gradient statistics                 │
│  ─────────                        │  ─────────                           │
│   loss                            │   norm                               │
│   3.0 ┤                           │   2.0 ┤  ╱╲                          │
│   2.5 ┤╲                          │   1.5 ┤ ╱  ╲╱╲   ╱╲                  │
│   2.0 ┤ ╲                         │   1.0 ┤╱       ╲╱  ╲╱╲╱             │
│   1.5 ┤  ╲╲                       │   0.5 ┤                              │
│   1.0 ┤    ╲╲╲                    │   0.0 └──────────────────            │
│   0.5 ┤       ╲╲╲╲                │        epoch                         │
│   0.0 ┤───────────────────         │                                      │
│        0  10  20  30  40  50 epoch│  Layer-wise (current epoch):         │
│   ── train  ── val                 │   lstm.0  ▆▆▆▆▆▆░░░░ 0.42           │
│                                    │   lstm.1  ▆▆▆░░░░░░░ 0.21           │
│  Current: train 0.082, val 0.094  │   fc.out  ▆▆▆▆▆▆▆▆▆░ 0.78           │
│                                    │                                      │
├──────────────────────────────────┼──────────────────────────────────────┤
│                                   │                                       │
│  Validation metric (RMSE [m])     │  Resource usage                      │
│  ─────────                        │  ─────────                           │
│   2.0 ┤                           │  GPU mem  [▆▆▆▆▆▆▆▆░░] 18.4 / 24 GB │
│   1.5 ┤╲                          │  GPU util [▆▆▆▆▆▆▆▆▆▆] 96%          │
│   1.0 ┤ ╲                         │  CPU util [▆▆▆░░░░░░░] 28%          │
│   0.7 ┤  ╲╲                       │  RAM      [▆▆▆▆▆░░░░░] 12.8 / 32 GB │
│   0.5 ┤   ╲╲╲                     │                                      │
│   0.4 ┤      ╲╲╲                  │  Throughput: 124 samples/sec        │
│   0.3 ┤────────────────             │  Time/epoch: ~38 sec                 │
│        0  10  20  30  40  50 epoch│                                      │
│                                    │  [📋 Export logs]                    │
│  Best so far: 0.42 m (epoch 19)   │  [⏸ Pause]  [⏹ Stop]                │
│                                    │                                      │
└──────────────────────────────────┴──────────────────────────────────────┘
```

### 2.2 4 패널

#### A. Loss curve (좌-상)
- Train loss + Val loss overlay
- 시간축: epoch
- 자동 update (epoch 끝날 때마다)

#### B. Gradient statistics (우-상)
- Gradient norm 시계열
- Layer-wise gradient (current epoch) 막대
- Vanishing / exploding gradient 진단

#### C. Validation metric (좌-하)
- RMSE 시계열 (Validation 세트)
- Best so far 표시
- Early stopping trigger 시각

#### D. Resource usage (우-하)
- GPU memory / utilization
- CPU / RAM
- Throughput (samples/sec)
- Time/epoch
- [Export logs] / [Pause] / [Stop]

### 2.3 학습 진행 인터랙션

- **Pause / Resume** — 체크포인트 저장 후 재개
- **Stop** — 현재까지 결과 보존 + Evaluate 진행 가능
- **Live tweaking 제한** — 학습 중 hyperparameter 변경은 새 Run (안전)

---

## 3. Screen NN-3 — Evaluate (4-error + 학습 영역)

**학습 완료 후 평가.** Q-NN-6=b — SIM-3 베이스 + 학습 영역 표시.
**파일**: `ui/nn_training/evaluate_panel.py`

### 3.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Evaluate · Tracker NN v0.5                                          [×] │
├─────────────────────────────────────────────────────────────────────────┤
│ Workflow steps: ✓ Dataset  ━━ ✓ Trainer Config  ━━ ✓ Train  ━━ ⦿ Eval  ━━ ○ Deploy │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ Result summary:                                                          │
│  Final RMSE — Train 0.38 m · Dev 0.51 m · Test 0.73 m                   │
│  Best epoch: 47 / 50  ·  Total training time: 31 min 14 sec              │
│                                                                          │
├──────────────────────────────────────┬──────────────────────────────────┤
│                                       │                                   │
│ 4-error Diagnostic                    │ 학습 영역 vs 외삽 영역            │
│ ─────────                             │ ─────────                        │
│                                       │                                   │
│ Bayes      ▆▆░░░░░░░░ 0.30 m          │  Aspect angle [deg]              │
│            ━ avoid bias 0.08 (small ✓)│   ┌─────────────────────────┐    │
│ Training   ▆▆▆░░░░░░░ 0.38 m          │   │░░░░░░░░░░░░░░░░░░░░░░░░│    │
│            ━ variance 0.13            │   │░░ ⚠ 외삽 영역  ░░░░░░░│    │
│ Dev        ▆▆▆▆▆░░░░░ 0.51 m          │   │░░░░ 빨강 ─ verify ░░░░│    │
│            ━ dist shift 0.22 ⚠        │   │░░ ┌─────────────────┐ ░░│    │
│ Test       ▆▆▆▆▆▆▆░░░ 0.73 m          │   │░░ │  학습 영역      │ ░░│    │
│                                       │   │░░ │ 녹색 reliable  │ ░░│    │
│ Auto-diagnosis:                       │   │░░ │   ●  ●  ●  ●   │ ░░│    │
│ ⚠ Distribution shift 0.22m            │   │░░ │  ●  ●  ●  ●  ● │ ░░│    │
│   Test 분포가 학습과 다름             │   │░░ │   ●  ●  ●  ●   │ ░░│    │
│   → Test 시 sea state 5+ 비율 ↑       │   │░░ │  data points    │ ░░│    │
│                                       │   │░░ └─────────────────┘ ░░│    │
│ → Suggestion:                         │   │░░░░░░░░░░░░░░░░░░░░░░░░│    │
│   학습 데이터에 sea state 5+ 추가     │   └─────────────────────────┘    │
│   (현재 cover: 1~4)                   │       Range [m]                  │
│                                       │                                   │
│ [📊 SIM-3 Drill]                      │   Coverage: 64% of operational   │
│                                       │   range. 36% extrapolation risk. │
│                                       │                                   │
├──────────────────────────────────────┴──────────────────────────────────┤
│                                                                          │
│ Compare with baseline DSP:                                               │
│  Tracker NN v0.5  RMSE 0.73 m · Latency 4.2 ms                           │
│  Default DSP      RMSE 1.20 m · Latency 1.8 ms                           │
│  Δ                -0.47 m (-39%) · +2.4 ms (+133%)                       │
│                                                                          │
│  Trade-off: 정확도 vs 지연. 운용 환경 latency 제약 있는 경우 DSP, off-line  │
│  분석에서는 NN. SIM-6 (Multi-Run Compare) 에서 직접 비교.                  │
│                                                                          │
│              [↶ Re-train]   [→ Deploy as Plugin]                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 4-error (좌)

SIM-3 의 베이스 패턴 재사용:
- Bayes / Training / Dev / Test 막대
- gap 시각화 (avoidable bias / variance / distribution shift)
- 자동 진단 + suggestion
- "SIM-3 Drill" 버튼 → Simulator 의 4-error 화면

### 3.3 학습 영역 vs 외삽 영역 (우, Q-PL8 패턴)

**Physics Lab Q-PL8 의 패턴**을 NN 평가에도:
- 2D plot (e.g., Range × Aspect angle)
- 녹색 영역: 학습 데이터 cover (NN reliable)
- 빨강 반투명: 외삽 영역 (verify carefully)
- Coverage % 표시 (학습 cover 비율)

이게 NN 의 **신뢰 경계** 시각화. 외삽 시 위험 명시.

### 3.4 Compare with baseline DSP

- 현재 NN vs Default DSP 직접 비교
- RMSE / Latency
- Trade-off 인식
- → SIM-6 Multi-Run Compare 로 깊이

### 3.5 Action

- **Re-train** — Step 2 로 돌아가서 hyperparameter 조정
- **Deploy as Plugin** — Step 5 로 진행 (Q-NN-5=b Wizard)

---

## 4. Deploy Wizard (Step 5, Q-NN-5=b)

**학습한 NN 을 .trsim-pkg 로 packaging**. NN-3 의 [Deploy] → 모달 wizard.

```
┌────────────────────────────────────────────────────────────────┐
│ Deploy NN Model as Plugin · Step 1/4                      [×]  │
├────────────────────────────────────────────────────────────────┤
│ Step 1: Plugin metadata                                          │
│                                                                  │
│  Plugin name:  [ torch_lstm_v0.5_maritime__________ ]            │
│  Display name: [ LSTM Tracker for Maritime _________ ]           │
│  Version:      [ 0.5.0 ]                                         │
│  Description:  [_______________________________________ ]        │
│                                                                  │
│  Author:       [ user-local _________________ ]                  │
│  License:      [ Apache 2.0 ▾ ]                                  │
│                                                                  │
│  Tags:         [maritime] [lstm] [tracker] [+]                   │
│                                                                  │
│                              [Cancel]   [Next →]                 │
└────────────────────────────────────────────────────────────────┘

Step 2: Training info
  - Dataset summary (4 runs, 6700 samples)
  - Hyperparameters (learning rate, batch, epochs, etc.)
  - Final metrics (RMSE Train/Dev/Test, latency)
  - 학습 영역 coverage % + 외삽 경계 spec

Step 3: Files to include
  ☑ model.pt (12.4 MB)
  ☑ config.toml (1 KB)
  ☑ training_history.json (340 KB)
  ☑ README.md (auto-generated)
  ☐ raw dataset (X — privacy 또는 license)

Step 4: Validation & Publish
  - Plugin Manager 등록 위치 (~/.trsim/packages/)
  - 또는 Marketplace 제출 옵션 (awesome-trsim PR)
  - 자동 회귀 테스트 (Validation Bench 실행)
  - ✓ packaging 완료 → Plugin Manager 의 Browse 에서 보임
```

---

## 5. 화면 간 흐름

```
[Welcome 또는 SIM-2 의 "Train new NN"]
       │
       ▼
[NN-1 Main: Dataset + Trainer Config]
       │
       │ [▶ Start Training]
       ▼
[NN-2 Training Progress]
       │
       │ Training 완료 또는 [Stop]
       ▼
[NN-3 Evaluate: 4-error + 학습 영역]
       │
       ├─ [↶ Re-train] → NN-1 으로
       │
       └─ [→ Deploy] → Wizard 모달 (4 단계) → Plugin Manager 등록
```

---

## 6. CLI 대응

```bash
# Training 시작
trsim nn train --config training.toml

# Training resume
trsim nn resume --checkpoint last

# Evaluate
trsim nn evaluate --model torch_lstm_v0.5

# Deploy
trsim nn deploy torch_lstm_v0.5 --output torch_lstm_v0.5.trsim-pkg
```

---

## 7. 영향 받는 plan 영역

| 영역 | 변경 |
|---|---|
| 07 nn_integration | UI 측 보강 |
| 04 Phase 6 | NN 통합 체크리스트 |
| 17 § 17.4.1 | TrackerProtocol + NN tag |
| 19 § 19.9 형태 2 | NN 대체 학습 흐름 (Phase 9.3 결합) |

---

## 8. 미결정 (UI 측)

- **NN-U1**: GPU 자동 감지 vs 수동 선택
- **NN-U2**: Distributed training (multi-GPU) — 미래
- **NN-U3**: Pre-trained checkpoint loading 흐름
- **NN-U4**: Hyperparameter sweep (Optuna 같은) 통합

---

## 9. Phase 위치

- **Phase 6.1 (MVP NN)**: NN-1 + NN-2 + NN-3 (Run history dataset)
- **Phase 6.2**: External + Synthetic data
- **Phase 6.3**: Deploy Wizard + Plugin Manager 통합
- **Phase 9.3 (Physics Lab 결합)**: 형태 2 NN 대체 — Physics Lab 안에서 같은 흐름 재사용

---

## 10. NN 코드 직접 수정 — 명시 제외

Physics Lab Code Pane (PL-7) 와 다른 결정:

| Physics Lab | NN Trainer |
|---|---|
| Read-only default + ⚠ Edit toggle | View source + External IDE link |
| 함수 단위 짧음 | 코드 큼 (수십~수백 줄) |
| 즉시 시각 (ms) | 학습 시간 (분~시간) |
| Validation Bench 안전망 | 약한 안전망 (학습 영역 시각만) |

**NN architecture 수정은 외부 IDE (VS Code) 가 자연**. TRsim 안에서는 hyperparameter + dataset + evaluate 에 집중.

---

👉 HTML artifact 동행 (3 화면 + Deploy Wizard 모달)
