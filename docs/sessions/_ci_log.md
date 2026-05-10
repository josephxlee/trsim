# TRsim CI 실행 로그

자동 스케줄 태스크 `trsim-ci-status` 가 GitHub Actions 의 최신 run 을 조회해 한 줄씩 추가한다.

| 시각 (KST) | sha | branch | conclusion | 6env | commit message |
|---|---|---|---|---|---|
| 2026-05-08 17:13 | 39efe38 | main | success | 6/6 | Phase 2.3c: domain/building.py — BuildingEntity + Anchor / MeshOrigin |
| 2026-05-08 17:43 | 2931923 | main | **failure** | ?/6 | Phase 2.3d: domain/target.py — TargetEntity + TargetWaypoint |
| 2026-05-08 17:43 | 3a92bb5 | main | **failure** | ?/6 | Phase 2.5: physics/atmosphere.py — ISA + ITU-R P.838 rain attenuation |
| 2026-05-08 17:43 | f13e6d4 | main | **failure** | ?/6 | Phase 2.6: physics/antenna.py — Parabolic dish + sinc^2 pattern |
| 2026-05-08 18:41 | 7c4b115 | main | (in_progress) | ?/6 | Phase 2.6 fixup: physics 단일파일 vs placeholder dir 충돌 해소 |
| 2026-05-10 (회수) | f530cee | main | success | 6/6 | Phase 4.1: ui/main_window.py + WorkspaceSelector + Editor/Simulator stub |
| 2026-05-10 (회수) | d32a3ba | main | success | 6/6 | docs: CLAUDE.md § 1 — Phase 4.1 DONE 갱신 |

> **메모 (Cowork→Claude Code 전환 시점):** 2.3d/2.5/2.6 3 run 의 fail
> 원인은 `physics/{antenna,atmosphere}/__init__.py` placeholder 디렉토리가
> 단일파일 (`physics/antenna.py` / `physics/atmosphere.py`) 와 import
> 충돌. 새 PC fresh `.venv` 에서 처음 발견 (Cowork 단계에서 .pyc 캐시로
> 마스킹). fixup `7c4b115` 가 placeholder 두 디렉토리 제거. 2.3d 도 같은
> 충돌의 collateral fail (전체 collection 단계에서 cascade). gh 인증 후
> 정확한 6env 비율 / fail step 은 `gh run view` 로 사후 회수.
