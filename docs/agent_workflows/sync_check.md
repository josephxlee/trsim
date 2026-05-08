# sync_check — bindfs 잘림 + lint 빠른 검사

호출 trigger: "sync 체크", "잘림 확인", "/sync-check", 모듈 Write 직후
(Cowork 자동 호출 권장).

## 단계

### Args

- 단일 파일: `sync_check <file_path>`
- staged: `sync_check staged`
- recent: `sync_check recent` (find -mmin -5)
- 없음: staged 와 동일

### A. py_compile (truncation 1차)

```bash
python -m py_compile "$file" 2>&1
```

실패:
- `tail -5 "$file"` 출력
- `wc -l "$file"` 줄 수
- 결론: "bindfs sync 잘림 의심. Write 재실행."

### B. ruff check

```bash
cd "$(git rev-parse --show-toplevel)"
ruff check --quiet "$file"
```

실패: 위반 규칙명 + 첫 5 줄.

### C. ruff format --check

```bash
ruff format --check --quiet "$file"
```

실패: "format 미적용. 'ruff format <file>' 후 재 add."

### D. 끝줄 sanity

```bash
tail -3 "$file"
```

마지막 줄이 partial identifier (예: `def make_def`) 면 경고.

## 보고 형식

성공:
```
sync_check OK — src/workbench/domain/building.py (165 lines)
```

실패:
```
sync_check FAIL — src/workbench/domain/building.py
[A] py_compile: SyntaxError line 158
tail:
  159    return BuildingEntity(
  160        placement=Plac
```

## 호출 시점

1. Cowork 모듈 Write 직후 (자동, 권장)
2. Edit 여러 번 후 sanity
3. 사용자 phase commit 직전 (pre-commit hook 과 중복이지만 안전)

## 금지

- 자동 수정 — 사용자/Cowork 가 다음 행동 결정
- 통과 시 긴 설명 — "OK + 줄수" 만
