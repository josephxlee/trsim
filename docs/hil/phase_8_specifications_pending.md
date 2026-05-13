# Phase 8 (HIL) — 진입 전 구체화 필요 항목 리스트

**작성**: 2026-05-13
**상태**: Phase 8 (HIL 통합) 진입 결정 전 명확화 필요한 12 항목.
**관련 plan 문서**: [plan/18 hil_integration](../../plan/18_hil_integration.md),
[plan/04 § 4.3 Phase 8](../../plan/04_migration.md), [plan/02 § 2.6 architecture](../../plan/02_architecture.md).

---

## 0. 이 문서의 목적

`plan/18` 의 § 18.7 (DUTAdapter Protocol) / § 18.9 (3-way 비교) / § 18.16.4
(Lock-step Handshake) 등이 **추상 수준에서** HIL 의 설계를 정의하지만,
실 코드를 작성하기 직전에 결정해야 할 구체적 wire-format / 매칭 알고리즘
/ run-loop 통합 정책이 모호한 영역이 남아있다.

`plan/18 § 18.14` 의 Open Questions (Q-HIL1~7 + Q-RT1~8) 가 일부 다루지만,
**Phase 8.1 (MVP HIL) K1~K6 sub-step 진입 전에 결정해야 할** 항목들을 다시
정리한다.

각 항목별:
- **모호점**: 무엇이 명시되지 않았나
- **결정 필요 시점**: 어느 sub-step 에 영향
- **현 plan 가정**: plan/18 의 implicit assumption (있다면)
- **권장 결정 옵션**: 작성자가 보는 합리적 default + 근거
- **영향 / 위험**: 잘못 가정하면 어떤 cycle 가 다시 작성되는가

---

## A. Protocol / Data Model 명세 (K1-K2 진입 직전 필수)

K1 = 데이터모델 (domain/hil/), K2 = DUTAdapterProtocol 본체. 두 sub-step
모두 SDK 표면 결정 — 후속 plug-in 작성자가 모두 따라야 하므로
이 시점에 잘못 가정하면 ABI break.

### A1. `DUTAdapter.receive_results()` 의 element 타입

**모호점**: plan/18 § 18.7 의 `receive_results(self) -> Iterator[DUTResult]`
에서 `DUTResult` 의 정확한 타입이 명시 안 됨. L1~L5 5종 dataclass 가
있는데, Iterator 가 union 인지 / base class 인지 / Generic 인지 결정 필요.

**결정 필요 시점**: K1 (5 dataclass 작성 시) + K2 (Protocol 본체 작성 시).

**현 plan 가정**: docstring 의 "DUT → TRsim 결과 수신 (streaming)" 만 명시.
union 도 base class 도 직접 언급 X.

**권장 결정 옵션**:
- (a) **Union `DUTResult = DUTRawIQ | DUTSpectrum | DUTDetection | DUTPairedDetection | DUTTrack`** — 타입 알리아스. 호출자가 `match`/`isinstance` 로 dispatch.
  - 장: typed Python, mypy strict OK
  - 단: 새 L 추가 시 union 갱신 필요 (그러나 그건 L 추가 자체가 의도된 변경)
- (b) **base class `DUTResult` + 5 subclass** — OO 상속. 공통 필드 (`timestamp_ns`, `sweep_id`) 를 base 에.
  - 장: 공통 필드 DRY
  - 단: dataclass + 상속이 frozen 과 충돌 (slots + 상속 mypy 까다로움)
- (c) **Generic protocol `DUTAdapter[ResultT]`** — Generic Protocol.
  - 장: type-safe at adapter 작성 시점
  - 단: Phase 8.1 에서 over-engineering

**작성자 default**: (a) Union 타입 alias. `from typing import TypeAlias`. 새 L 추가가 dramatic event 라 union 갱신이 의도된 marker 가 된다.

**영향**: K1 의 5 dataclass 와 K2 의 Protocol body 가 동시 변경. K3 evaluator
도 dispatch 흐름 영향. 잘못 가정하면 3 cycle 재작성.

---

### A2. `DUTAdapter.send_signal()` 의 signal 타입

**모호점**: plan/18 § 18.7 의 `send_signal(self, signal: TXSignal)` —
`TXSignal` 이 union (`TXSignalDigital | TXSignalAnalog`) 인지 별도 메소드
(`send_digital()` / `send_analog()`) 인지 명시 안 됨.

**결정 필요 시점**: K2 (Protocol 본체 작성 시).

**현 plan 가정**: plan/18 § 18.6 의 두 dataclass (TXSignalDigital MVP,
TXSignalAnalog MVP+α). Protocol 본체에선 `TXSignal` 만 적힘.

**권장 결정 옵션**:
- (a) **Union `TXSignal = TXSignalDigital | TXSignalAnalog`** — A1 와 동일 패턴.
- (b) **별도 메소드**: `send_digital(signal: TXSignalDigital)` + `send_analog(signal: TXSignalAnalog)`.
  - 장: protocol 자체가 어댑터의 능력 선언 (TXSignalAnalog 미지원 어댑터 면 send_analog 미구현)
  - 단: protocol 폭이 늘어남

**작성자 default**: (a) Union — `supported_levels` 와 대칭. 어댑터가
지원 안 하는 TX 타입을 받으면 `NotImplementedError` 가 표준.

**영향**: K2 + K5 (TCP/JSON adapter) — adapter 가 union dispatch.

---

### A3. `DUTAdapter.connect(config: dict)` 의 config schema

**모호점**: plan/18 § 18.7 의 `connect(self, config: dict) -> None` 에서
`config: dict` 가 너무 느슨. 어댑터 specific (host, port 등) 필드를 어떻게
선언 / 검증?

**결정 필요 시점**: K2 (Protocol) + K5 (TCPJsonDUTAdapter).

**현 plan 가정**: docstring "config는 어댑터 specific" 만 — schema 없음.

**권장 결정 옵션**:
- (a) **dict 유지 + 어댑터 별 TypedDict** — `class TCPJsonConfig(TypedDict): host: str; port: int`. Protocol 는 dict 그대로 받고, adapter 가 내부에서 cast + validate.
- (b) **Pydantic / dataclass per adapter** — 강한 검증, 그러나 sdk 가 pydantic 의존 추가.
- (c) **Scenario `[hil.adapter]` 섹션에 raw TOML dict 직접 전달** — TOML → dict 변환 후 그대로.

**작성자 default**: (a). SDK 는 dict 유지 (가벼움), adapter 마다 TypedDict
class + `__post_validate__` 권고 패턴 + 가이드 doc.

**영향**: K2 시그니처 + K5 의 adapter 구현 + Scenario TOML schema (E1).

---

### A4. Lock-step Handshake 의 wire format

**모호점**: plan/18 § 18.16.4 의 `sync_frame_start(frame_id: int)` /
`sync_frame_end(frame_id: int, timeout_ms: float) -> bool` 가 Protocol
시그니처만 정의 — TCP 위에서 어떻게 인코딩? frame_start 가 OOB 신호인지
일반 message 인지? frame_end 의 ack payload 가 결과 데이터 포함인지?

**결정 필요 시점**: K2 (Protocol 시그니처) + K5 (TCP/JSON 의 첫 wire 정의).

**현 plan 가정**: plan/18 § 18.16.4 의 "frame_id (uint64) + ack_required +
timeout 표준" + Q-RT2 의 "표준" 만 — 그러나 message 자체 format 미명시.

**권장 결정 옵션**:
- (a) **JSON-line 표준 message envelope**:
  ```json
  {"type": "frame_start", "frame_id": 42, "timestamp_ns": 1000000}
  {"type": "frame_end", "frame_id": 42, "result": {...DUTTrack...}}
  ```
  - 장: 펌웨어 측 sprintf 가능, debug 친화
  - 단: parse overhead
- (b) **binary header (8-byte type + 8-byte frame_id) + payload** — 고성능.
- (c) **frame_start 가 RPC call (request-response), frame_end 도 RPC** — Protocol 의 abstraction 그대로.

**작성자 default**: (a) JSON-line + message envelope (`type` field) — TCP/JSON
adapter 의 의도와 일치. K5 의 mock DUT + 실 펌웨어 가이드 둘 다 단순.

**영향**: K2 + K5 + F1 (펌웨어 가이드). 잘못 가정하면 펌웨어 사용자가
재작성.

---

### A5. DUT `track_id` ↔ GT `target_id` 매칭 (가장 위험)

**모호점**: plan/18 § 18.5 의 `DUTTrack.track_id` (DUT 내부 namespace) ↔
시뮬 의 `Target.target_id` (GT namespace) 가 다른 공간. `HILComparisonResult`
의 `target_id` 필드는 어느 쪽?

**결정 필요 시점**: K1 (HILComparisonResult dataclass 정의) + K3 (evaluator
의 매칭 알고리즘) — **B1/B2/B3 와 strongly coupled**.

**현 plan 가정**: plan/18 § 18.9 의 HILComparisonResult dataclass 에 `target_id`
하나만 — 어떤 namespace 인지 명시 X.

**권장 결정 옵션**:
- (a) **GT target_id 가 권위**, SIL/HIL 의 track_id 는 evaluator 가 매칭 (위치 기반 GNN association 한 번 더).
  - 장: 시뮬 차원에서 GT 가 truth — 자연
  - 단: evaluator 가 SIL-GT + HIL-GT 각각 GNN association
- (b) **TXSignal metadata 에 GT target_id echo** — DUT 측이 결과에 그대로 echo. 사실상 cheat 이지만 mock DUT / firmware sample 시 명시 가능.
  - 장: matching trivial
  - 단: 실 DUT 가 모를 가능성 (자기 detection 으로 track 만들었으니)
- (c) **양 namespace 모두 저장**: HILComparisonResult 가 `gt_target_id`, `sil_track_id`, `hil_track_id` 3 필드.
  - 장: 명시적 + 후속 분석 가능
  - 단: 매칭 알고리즘은 여전히 필요 (어떻게 셋이 한 row 가 되나)

**작성자 default**: (c) — 3 필드 명시 + (a) 매칭 알고리즘 = evaluator 가
GT 위치 기반 GNN association 으로 SIL-GT + HIL-GT 각각 매칭 후 row 빌드.
mock DUT 는 편의상 sweep_id metadata 에 GT 힌트 줄 수 있음 (시뮬-only convention).

**영향**: K1 (HILComparisonResult schema) + K3 (evaluator core) — **가장 위험.
잘못 가정하면 K1+K3 모두 재작성**.

---

## B. 매칭 / 평가 로직 (K3 evaluator 직전 필수)

### B1. HILComparisonResult 의 매칭 키

**모ho점**: "한 시점·한 표적" 단위 (plan/18 § 18.9) — 어떻게 한 row 가 만들어지나?
sweep_id 일치? timestamp_ns 일치? target_id ↔ track_id 매칭?

**결정 필요 시점**: K3 (evaluator).

**현 plan 가정**: 없음. dataclass 만 정의됨.

**권장 결정 옵션**:
- (a) **(sweep_id, gt_target_id) tuple** — TXSignal 보낼 때 sweep_id 부여 → DUT 가 echo (`DUTTrack.sweep_id` 필드 추가 권장). evaluator 가 매 sweep_id 마다 GT 표적 list ↔ SIL track list ↔ HIL track list 를 GNN association.
  - 장: 명시적, 회귀 가능
  - 단: DUT 가 sweep_id echo 가정 (firmware contract)
- (b) **timestamp_ns 일치 (~tolerance)** — 정확한 시간 매칭 어려움 (latency 변동).
- (c) **frame_id (Lock-step) + GT target_id 위치 매칭** — Reference Timing 활성화 시 frame_id 가 자연스러운 키.

**작성자 default**: (a) — DUTTrack 에 `sweep_id: int` 필드 추가 (plan/18 § 18.5
의 L5 dataclass 보강). frame_id 도 활용 가능하지만 sweep_id 가 더 일반적
(Reference Timing 비활성화 시도 작동).

**영향**: K1 (DUTTrack 에 sweep_id 추가) + K3 (matching algorithm).

---

### B2. DUT 처리 latency 시 GT 매칭 시점

**모ho점**: TXSignal 발송 시 시뮬 시간 t0 vs HIL 결과 도착 시 시뮬 시간 t1.
GT 의 어느 시점 위치를 비교?

**결정 필요 시점**: K3.

**현 plan 가정**: HILComparisonResult.timestamp_ns 만 — 어느 시점인지 명시 X.

**권장 결정 옵션**:
- (a) **DUTTrack.timestamp_ns 가 시뮬 발송 시점 t0** — DUT 가 받은 timestamp 그대로 echo. GT 는 t0 시점 표적 위치.
  - 장: 회귀 가능, 명확
  - 단: DUT 가 timestamp echo 정직 가정
- (b) **시뮬이 발송 시 GT snapshot 저장, 도착 시 그 snapshot 사용** — evaluator 가 sweep_id 기준 GT history 보관.
  - 장: DUT 정직성 가정 안 함
  - 단: evaluator memory ↑

**작성자 default**: (b) — `HILEvaluator` 가 sweep_id → GT snapshot history
보관. DUT 의 timestamp_ns 는 cross-check 용. plan/18 § 18.4 의 데이터흐름 그대로 (GT 가 시뮬 측 인 것 처럼).

**영향**: K3 evaluator 의 state 설계.

---

### B3. SIL track 매칭

**모ho점**: SIL pipeline 의 `TrackState.track_id` 도 자체 namespace. evaluator
가 SIL-GT 매칭 + HIL-GT 매칭 + SIL-HIL 매칭 — 셋 다 별도 association?

**결정 필요 시점**: K3.

**현 plan 가정**: 없음.

**권장 결정 옵션**:
- (a) **SIL-GT 매칭은 시뮬이 직접** (Phase 5 회귀 시나리오 패턴) — Pipeline 출력 시 GT 표적 ID 와 연결 (Phase 6 evaluator 패턴과 동일).
- (b) **evaluator 가 모든 association 책임** — SIL/HIL 각각 GT 위치 기반 GNN association.

**작성자 default**: (b) — `HILEvaluator` 가 일관된 association 알고리즘 (GNN
Hungarian + chi² gate, plan/05 의 Tracker 와 동일) 으로 GT-SIL + GT-HIL +
SIL-HIL 매칭. 매칭 결과는 row 별 (gt_target_id, sil_track_id_or_None,
hil_track_id_or_None) tuple.

**영향**: K3 의 핵심 알고리즘.

---

### B4. HIL 회귀 시 tolerance 정책

**모ho점**: SIL 은 deterministic (같은 seed → 같은 결과). HIL 은 외부 hardware
— clock drift / temperature / 비결정성. 같은 Scenario 두 번 run 시 HIL
결과 tolerance 는?

**결정 필요 시점**: K3 + HIL-A 검증 시나리오 작성 시.

**현 plan 가정**: plan/18 § 18.9 의 metrics (sil_error_range_m, hil_error_range_m,
dut_bias_range_m) 만 정의 — 회귀 합격 기준 없음.

**권장 결정 옵션**:
- (a) **절대값 tolerance**: `|hil_value - expected| < tol` per 메트릭. tol 은 Scenario 명시.
- (b) **상대값 tolerance**: `|hil - sil| / |sil| < pct`.
- (c) **통계 (n-run mean ± k-σ)**: 같은 Scenario n 번 run 의 mean + variance 로 합격 판정.
- (d) **Mahalanobis (cov 행렬)**: track state 의 covariance 이용.

**작성자 default**: (a) 절대값 + Scenario 명시. (c) 는 HIL-E (회귀) 시
운영자 옵션.

**영향**: K3 의 합격/실패 판정 + Scenario `[hil]` 섹션 (E1).

---

## C. Run-loop 통합 (K4 time_synchronizer 진입 직전 필수)

### C1. SignalSink 추상화의 현 상태

**모ho점**: plan/02 § 2.6 가 "SignalSink → SignalSink + DUTAdapter" 갱신
언급. 그러나 현 `domain/pipeline.py` 의 `step()` 가 직접 sample 받아 처리
— `SignalSink` 라는 class 가 코드에 없음.

**결정 필요 시점**: K4 (분기점 추가) — 또는 Phase 8 전체 진입 전.

**현 plan 가정**: SignalSink 가 존재 가정.

**권장 결정 옵션**:
- (a) **K4 안에 mini-리팩터로 SignalSink 도입** — `domain/pipeline.py` 에
  `SignalSink(Protocol)` 추가 + `SILSink` (Pipeline 호출) + `HILSink`
  (DUTAdapter 호출). Pipeline `step()` 가 SILSink 의 한 구현체로 둠.
- (b) **별도 cycle (K0) 으로 SignalSink 만 추출** — 코어 변경이라 안전.

**작성자 default**: (b) — Phase 8 진입 전 별도 cycle (K0 = SignalSink 추출
+ SIL pipeline 가 SILSink 로 wire). 1 cycle 안 됨. Phase 8 본격 진입 후
mini-리팩터 위험 회피.

**영향**: domain/pipeline.py + 모든 호출자 (commands, run_manager 등) + 회귀
test 영향. K0 가 K1 보다 먼저 들어가야.

---

### C2. SIL pipeline 과 HIL DUT 동시 실행 모델

**모ho점**: 한 frame 안에서 SIL = 동기 (Python 즉시), HIL = async (외부
DUT 응답 대기). sim_time 모드 시 둘 다 완료 후 다음 frame? SIL 만 진행
+ HIL catch-up?

**결정 필요 시점**: K4 (time_synchronizer).

**현 plan 가정**: plan/18 § 18.8 모드 1 "DUT 응답 기다림" — sim_time 모드는
HIL 완료까지 wait. 그러나 SIL 측의 lifecycle 미명시.

**권장 결정 옵션**:
- (a) **순차 (SIL → HIL)**: SIL 먼저 처리 + 결과 buffer, 그 다음 HIL sync_frame_start → DUT 처리 wait → sync_frame_end → 결과 buffer, frame 끝에 둘 다 evaluator.
- (b) **병렬 (asyncio)**: SIL 작업 + HIL 전송을 동시 시작, 둘 다 await.
- (c) **TXSignal 발송 동시 + 결과 수집 frame 끝**: 둘 다 한 분기점에서 시작, 결과는 frame 끝에 모음.

**작성자 default**: (c) — plan/18 § 18.4 의 SignalSink 분기점 의도와 일치.
SIL Sink 가 즉시 Python 처리 (동기), HIL Sink 가 DUT 비동기 호출 (sync_frame_end
에서 wait). frame 끝에서 둘 다 collected.

**영향**: K4 + K3 (evaluator 호출 시점).

---

### C3. HIL Lock-step + Reference Timing 결합

**모ho점**: PerformanceClock 의 sleep (target_latency - measured) vs
DUTAdapter.sync_frame_end timeout — 두 timer 의 순서?

**결정 필요 시점**: K4.

**현 plan 가정**: plan/18 § 18.16.4 의 "PC ↔ DUT desync detection" 만 —
순서 미명시.

**권장 결정 옵션**:
- (a) **sleep 먼저 → sync 마지막**: PerformanceClock 이 sleep 으로 sim_time
  target 까지 보정 → DUTAdapter.sync_frame_end 호출 (이미 DUT 끝났을
  가능성 ↑).
- (b) **sync 먼저 → sleep 마지막**: DUT 완료 대기 후 남은 시간 sleep.
- (c) **`wait_ns = max(target_ns - measured_ns, dut_remaining_ns)`** — 둘
  중 큰 쪽 기다리고 다른 건 그 안에서 처리.

**작성자 default**: (c) — 두 차원 결합. PerformanceClock 측에 `wait_for(target_ns,
event)` 메소드 추가, DUTAdapter.sync_frame_end 가 `threading.Event` 도
지원 (또는 future).

**영향**: K4 + Reference Timing 측 PerformanceClock 시그니처 (이미 ✓
인 SIL 측 코드 약간 변경 필요).

---

### C4. timeout 시 graceful degradation

**모ho점**: `sync_frame_end(N, timeout=100ms)` False 반환 시 — sample loss?
frame skip? abort?

**결정 필요 시점**: K4 (dut_session_manager).

**현 plan 가정**: plan/18 § 18.14 의 Q-HIL7 "warning + skip, sample loss
통계 기록" — real_time 모드 한정.

**권장 결정 옵션**:
- (a) **sim_time 모드 = abort + error** — 사용자 명시 모드면 timeout 은 fatal.
- (b) **sim_time 모드 = warn + frame skip + 통계** — graceful, 실험적 fault tolerance.
- (c) **Scenario 명시 (`timeout_policy = "abort" | "skip"`)**.

**작성자 default**: (c) — Scenario `[hil].timeout_policy` 기본 "abort", 사용자
명시 시 "skip" + `sample_loss_count` metric.

**영향**: K4 + Scenario schema (E1).

---

## D. Mock DUT 행동 명세 (K5 진입 직전 필수)

### D1. Mock DUT 의 정확도

**모ho점**: Mock 이 자체 처리 (FMCW beat → CFAR → tracker) 흉내? GT echo +
noise (cheat)? plan 미명시.

**결정 필요 시점**: K5.

**현 plan 가정**: plan/18 § 18.11 의 "Mock DUT (Python sample — 펌웨어 흉내)"
만.

**권장 결정 옵션**:
- (a) **GT echo + Gaussian noise** (cheat) — 회귀 가능, 단순.
- (b) **SIL pipeline 재사용** (Python DSP 그대로) — SIL 과 mock-HIL 동등 → dut_bias_range_m = 0 회귀.
- (c) **간소 자체 DSP** (단순 FFT + peak pick) — 부분 cheat.

**작성자 default**: (b) — mock DUT 가 SIL pipeline 의 deterministic wrapper.
HIL evaluator 의 sanity test 가 dut_bias_range_m ≈ 0 invariant 로 회귀.

**영향**: K5 + HIL-A 검증 시나리오.

---

### D2. Mock DUT 의 latency 모델

**모ho점**: 고정? Gaussian? plan 미명시.

**결정 필요 시점**: K5.

**현 plan 가정**: 없음.

**권장 결정 옵션**:
- (a) **고정 latency** (e.g. `dut_latency_ms = 50.0` config).
- (b) **Gaussian (mean, std) config**.
- (c) **0 (synchronous)** — mock 이 즉시 응답.

**작성자 default**: (a) — `MockDUTConfig(dut_latency_ms: float = 0.0)` 기본
0 (synchronous), 사용자 설정 시 `time.sleep(0.05)` per frame. Reference
Timing 검증 시 (a) 가 결정성 ✓.

**영향**: K5 + Reference Timing 회귀 시나리오.

---

### D3. Mock DUT 와 실 DUT 의 인터페이스 동일성

**모ho점**: wire format 이 mock 의 implementation detail 인지 표준 schema
인지?

**결정 필요 시점**: K5 + F1 (펌웨어 가이드).

**현 plan 가정**: TCP/JSON 의 wire format 표준화 의도 (A4 결정).

**권장 결정 옵션**:
- (a) **wire format = standardised in `docs/hil/wire_format.md`**, mock 과 실 DUT 모두 따름.
- (b) **mock 이 reference implementation**, doc 은 mock 의 동작 설명만.

**작성자 default**: (a) — standardised wire format doc + mock 이 그 doc 의
첫 reference 구현. 실 펌웨어 작성자가 mock 코드 + doc 둘 다 참조.

**영향**: K5 + F1 + 실 펌웨어 사용자 경험.

---

## E. Scenario / Config (K6 진입 직전 필수)

### E1. Scenario `[hil]` 섹션 schema

**모ho점**: plan/18 § 18.8 의 예시 (sync_mode, dut_timeout_ms,
expected_dut_latency_ms) 외 adapter 선택 + adapter-specific config 어디?

**결정 필요 시점**: K6 (Scenario `[hil]` 섹션 + UI panel).

**현 plan 가정**: 부분 예시만 (plan/18 § 18.8).

**권장 결정 옵션**:
- (a) **`[hil]` 본체 + `[hil.adapter]` sub-section**:
  ```toml
  [hil]
  enabled = true
  sync_mode = "sim_time"
  dut_timeout_ms = 100
  timeout_policy = "abort"
  expected_levels = ["L5"]

  [hil.adapter]
  type = "tcp_json"  # plug-in slot lookup key
  host = "127.0.0.1"
  port = 5555
  ```
- (b) **`[hil]` 본체 + `[hil.adapter.<name>]` per adapter** (e.g. `[hil.adapter.tcp_json]`).
- (c) **별도 `dut_adapter_manifest.toml` 파일** (plan/03 § 3.2.1m 언급).

**작성자 default**: (a) — 단순 + adapter 한 종류만 활성 시점 직관.

**영향**: K6 + 사용자 가이드.

---

### E2. supported_levels 의 mismatch 정책

**모ho점**: DUT 가 `supported_levels = {"L5"}` 인데 Scenario 가 `expected_levels
= ["L2", "L5"]` 일 때 — reject? warn?

**결정 필요 시점**: K6.

**현 plan 가정**: 없음.

**권장 결정 옵션**:
- (a) **reject** (`HILConfigError`) — 명시적 사용자 의도면 mismatch 는 fatal.
- (b) **warn + adjust** (adjust expected_levels = intersection).

**작성자 default**: (a) — 명시적 contract 충돌 fatal.

**영향**: K6 + Scenario validation.

---

## F. 후속 / 가이드 (MVP 후, 그러나 Phase 8.1 끝나기 전 doc draft 권장)

### F1. DUT 측 펌웨어 sample / 가이드

**모ho점**: plan/04 § 4.3 의 "DUT 측 핸드쉐이크 구현 가이드 (펌웨어 sample,
README)" — MVP 포함? mock DUT 만으로 갈음?

**결정 필요 시점**: Phase 8.1 끝 후 또는 사용자 첫 펌웨어 작성 시점.

**현 plan 가정**: gap.

**권장 결정 옵션**:
- (a) **`docs/hil/dut_firmware_guide.md` + `docs/hil/wire_format.md` doc 두 개** — MVP 포함, mock DUT 가 reference 구현.
- (b) **mock DUT 코드만** — doc 후속.

**작성자 default**: (a) — D3 결정 그대로. wire format doc 은 mock 작성 시점에
같이 쓰는 게 자연.

**영향**: F1 + 외부 펌웨어 사용자.

---

### F2. frame_id 표준 외 ack_payload 의 결과 포함 여부

**모ho점**: Q-RT2 의 "frame_id (uint64) + ack_required + timeout 표준" —
ack 가 단순 boolean 인지 결과 data 포함인지?

**결정 필요 시점**: K2 + K5.

**현 plan 가정**: ack only — 결과는 별도 stream.

**권장 결정 옵션**:
- (a) **frame_end ack = 결과 포함** (DUTTrack 데이터를 ack 의 payload):
  ```json
  {"type": "frame_end", "frame_id": 42, "result": {...DUTTrack...}}
  ```
  - 장: 한 message → 한 frame 의 결과 모음
  - 단: 한 frame 에 여러 result 발생 시 부적합 (multi-target 트랙)
- (b) **frame_end ack 는 boolean, 결과는 frame_start ↔ frame_end 사이의 별도 message stream**:
  ```json
  {"type": "frame_start", "frame_id": 42}
  {"type": "track_result", "frame_id": 42, ...DUTTrack...}  # 여러 개 가능
  {"type": "frame_end", "frame_id": 42}
  ```

**작성자 default**: (b) — multi-target 자연 (한 frame 에 여러 track). frame_end
는 단순 barrier.

**영향**: A4 + K2 + K5 + F1.

---

## 결정 권장 순서 (Phase 8.1 진입 시)

| 단계 | 결정 항목 | sub-step 영향 |
|---|---|---|
| 1 | A1, A2 (DUTResult / TXSignal union) | K1, K2 |
| 2 | A4, F2 (wire format envelope) | K2, K5 |
| 3 | A3 (config schema) | K2, K5 |
| 4 | **A5, B1, B2, B3** (매칭 / association) — **가장 위험** | K1, K3 |
| 5 | B4 (tolerance 정책) | K3 |
| 6 | **C1 (SignalSink 추출)** — **K0 별도 cycle 권고** | K0 (Phase 8 진입 전) |
| 7 | C2, C3, C4 (run-loop + Lock-step + timeout) | K4 |
| 8 | D1, D2, D3 (mock DUT) | K5 |
| 9 | E1, E2 (Scenario schema) | K6 |
| 10 | F1 (가이드) | Phase 8.1 끝 후 |

---

## 결정 doc 작성 권고

이 문서는 **모호점 식별**. 다음 cycle 진입 시 별도 doc `phase_8_decisions_accepted.md`
에 위 권고 default 가 사용자 의도와 일치하는지 사용자 검토 + 합의 후
"accepted" 항목별로 한 줄 (날짜 + commit hash + 합의 결정) 기록.

plan/18 § 18.14 의 Q-HIL/Q-RT 패턴과 동일.

---

## 변경 이력

- 2026-05-13 초기 작성 — Phase 8 진입 결정 전 모호점 12 항목 (A1-F2) 식별.
