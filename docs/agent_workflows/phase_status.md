# phase_status — 진행 상황 조회 + dashboard 갱신

호출 trigger: "phase 상태", "진행 상황", "dashboard 갱신", "/phase-status"

## 단계

### 1. 핵심 파일 읽기

```
docs/sessions/phase_2_progress.md
CLAUDE.md  (§ 1 한 줄)
docs/sessions/_ci_log.md  (있으면)
```

```bash
git log --oneline -5
```

### 2. 누적 test count 검증

```bash
cd "$(git rev-parse --show-toplevel)"
grep -rh "^def test_" tests/ | wc -l
```

또는:

```bash
pytest --collect-only -q 2>&1 | tail -3
```

phase_2_progress.md 표시값과 차이 1 이상이면 한 줄 비고.

### 3. 다음 sub-phase 결정

phase_2_progress.md 의 "다음 sub-phase 후보" 우선순위 1번 추출.

### 4. dashboard 갱신 (변화 있을 때만)

진행률 / test count / 마지막 push / CI 상태 중 하나라도 변했으면:

1. `outputs/trsim_dashboard.html` 새로 작성 (디자인 유지, 데이터만 교체).
2. `mcp__cowork__update_artifact` id=`trsim-phase-dashboard`.
3. update_summary 에 "Phase X.Y 완료 / +N test" 짧게.

변화 없으면 갱신 생략.

### 5. 사용자 보고 (한국어 반말, 짧게)

```
Phase 2.3c 완료 (push 대기)
누적 test: 258 (+16 this sub)
CI 마지막: 2.3b PASS 6/6 (2026-05-07)
다음: 2.3d Target (의존 2.3a, dataclass-only)
```

dashboard 갱신했으면 "dashboard 갱신함" 한 줄 추가.

## Args 변형

- 없음: 위 1~5 그대로
- "verbose": 모든 sub-phase test count + 의존 그래프
- "<phase_id>" (예: "2.5"): 특정 phase 의 의존 / 모듈 / 예상 test count

## 금지

- 결정 재논의 — DECISIONS.md 가 권위
- 사용자에게 다음 phase 진행 여부 묻기 — 보고 후 응답 대기
