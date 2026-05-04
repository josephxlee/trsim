#!/bin/bash
# Phase 0.1 Git 셋업 스크립트
#
# 사용법: Git Bash 에서 trsim/ 폴더 열고 실행
#   $ cd "C:/Workspaces/Claude/Tracking Radar Simulator/trsim"
#   $ bash setup_phase0.sh
#
# 또는 명령 하나씩 복사·붙여넣기 가능.

set -e  # 에러 시 중단

echo "=== Phase 0.1 Git 셋업 — TRsim repo 초기화 ==="
echo ""

# 1. 깨진 .git/ 정리 (Cowork sandbox 가 만든 partial init)
if [ -d ".git" ]; then
  echo "[1/6] 기존 .git/ 정리..."
  rm -rf .git
  echo "  완료."
fi

# 2. git init + main branch
echo "[2/6] git init (main branch)..."
git init -b main

# 3. user 설정 (commit 시 사용)
echo "[3/6] git config (user.name + user.email)..."
git config user.name "joseph"
git config user.email "huvluv14@gmail.com"

# 4. remote 등록
echo "[4/6] git remote add origin..."
git remote add origin https://github.com/josephxlee/trsim.git

# 5. 모두 stage
echo "[5/6] git add ..."
git add .

# 6. 첫 commit (DCO sign-off)
echo "[6/6] git commit (DCO sign-off)..."
git commit -s -m "Initial commit: design v0.41 + open-source infrastructure

- v0.16~v0.40 누적 설계: 19 plan + 부록 2 (14,000+ 줄)
- UI mockup 9 영역 (HTML + SPEC.md 한 쌍)
- 차별점 5+1: Tracking IDE / DSP↔NN / 4-error / HIL / Physics Lab + DLC
- 세 Workspace: Editor (teal) / Simulator (회청+빨강) / Physics Lab (보라)
- 6 계층 아키텍처: UI → App → SDK → Domain → Physics → Primitives
- 11 Plugin Protocol (DetectorProtocol ~ PhysicsModelProtocol)
- 7 MotionKind (FIXED_GROUND ~ BALLISTIC, v0.27)
- 9 Test Objects (Sphere/Cube/Plate/Cylinder/Cone/Point/Plane/Wall/Trihedral, v0.40)
- 결정 ~100개 closed, 블로커 0
- Apache 2.0 + DCO + BDFL → Core team 거버넌스
- pyproject.toml + .importlinter (6 의존 계약)
- .github/ (PR/Issue 템플릿 + CI workflow)"

echo ""
echo "=== 완료 ==="
echo ""
git log --oneline -1
echo ""
echo "다음 단계: GitHub 에 push"
echo "  $ git push -u origin main"
