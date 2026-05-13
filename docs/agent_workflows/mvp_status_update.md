# `mvp_status_update.md` — MVP 매트릭스 자동 갱신 워크플로

`docs/MVP_STATUS.md` 의 Phase 0~9 매트릭스를 sub-step push 후 즉시
반영하기 위한 워크플로. `CLAUDE.md` § 3.6 자동 갱신 규약 + § 9 명령
매핑의 "다음 작업?" / "MVP 상태?" / "남은 작업?" 진입점.

## 트리거

1. **sub-step push 직후** — 매 commit + push 가 끝나면 자동.
2. **사용자 질문** — "다음 작업?", "남은 작업?", "MVP 상태?",
   "phase 상태?" 등.
3. **새 세션 시작** — handoff 정독 후 `docs/MVP_STATUS.md` 도 함께
   참조해서 우선순위 결정.

## 갱신 절차 (sub-step push 직후)

```text
1. push 한 sub-step 이 plan/04 § 4.3 의 어느 phase 항목을 채웠는지
   결정. 모호하면 commit message 의 phase 식별자 (예: "Phase 5.21b",
   "Phase 6 NN Adam") 참조.

2. docs/MVP_STATUS.md 의 해당 행 상태 갱신:
   - ✗ → ✓ (완전 구현 + src/test 검증 + lint/mypy/import-linter pass)
   - ✗ → △ (skeleton 만 추가, 실 데이터 binding / CLI 미완)
   - △ → ✓ (이전 skeleton 을 보강해서 완전 구현)

3. § "한 줄 요약" 줄에 변경 영향 있는지 확인 — Wave 전환 (예: Wave
   1 frame ✓ → Wave 1 ALL ✓) 발생 시 한 줄 갱신.

4. § "미구현 우선순위 리스트" 의 해당 행 갱신 또는 제거. 작은 행
   완료 시 다음 작업 자동 부각.

5. § "변경 이력 footer" 에 한 줄 추가:
   - YYYY-MM-DD <sub-step id> — <항목> ✓ (또는 △).

6. docs/MVP_STATUS.md 변경분을 직전 sub-step commit 에 amend 하지
   말고 별도 follow-up commit 으로:
   ```
   docs: update MVP_STATUS — <항목> ✓ after <sub-step>
   ```
   같은 push 에 묶어 origin/main 으로 보냄.

7. 이미 push 된 sub-step 의 status 만 갱신할 거면 (e.g. 회고적
   업데이트) 동일 패턴 + commit message 에 "retro-update" 표시.
```

## 사용자 질문에 답할 때

```text
1. docs/MVP_STATUS.md 의 § "미구현 우선순위 리스트" 첫 3 행을 먼저
   보고.
2. CLAUDE.md § 1 의 "현재 진행 상황" 줄로 최신 milestone 확인.
3. 사용자 우선순위 (physics_lab > simulator > editor) 와 부합하는
   첫 미구현 행 추천.
4. 추천 행이 큰 단위면 sub-step 분할 제안. 작은 단위 (test-only,
   single-module) 면 바로 진입 가능.
```

## 신뢰성 가드

- 매트릭스의 ✓ / △ / ✗ 가 실제 코드 상태와 어긋나면 신뢰가 깨짐.
  의심 시 `grep` + `Glob` 으로 cross-check 후 정정.
- "큰 작업 시작" 시 매트릭스에서 그 영역 먼저 cross-check (잘못
  표시된 행 있으면 정정 후 진행).
- handoff doc 작성 시에도 MVP_STATUS.md 와 phase 식별자 일치 검증.

## 변경 이력 footer 예시

```
- 2026-05-13 5.21b — ExtendedTarget glint scaling △ → ✓
- 2026-05-13 5.4b — ISA rain monotonicity △ → ✓
- (다음) — Phase 6 Adam optimizer ✗ → ✓
```
