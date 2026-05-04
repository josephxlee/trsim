#!/bin/bash
# Phase 0.3 + 0.4 commit 스크립트
#
# 사용법: Git Bash 에서 trsim/ 폴더 안에서:
#   $ bash setup_phase0_4.sh
# 그 후:
#   $ git push

set -e

echo "=== Phase 0.3 + 0.4 commit ==="
echo ""
echo "추가된 파일:"
echo "  - src/workbench/ 디렉토리 트리 (40 __init__.py + py.typed)"
echo "  - src/workbench/__main__.py (CLI 진입점)"
echo "  - src/workbench/domain/types.py (PositionENU/VelocityENU/Time)"
echo "  - src/workbench/sdk/protocols.py (11 Plugin Protocol)"
echo "  - src/workbench/sdk/__init__.py (Protocol re-export)"
echo "  - tests/ 디렉토리 + conftest.py + test_types.py (5 unit test)"
echo "  - .importlinter 단순화 (Phase 0 호환)"
echo ""

git add .
git status --short
echo ""

git commit -s -m "Phase 0.3 + 0.4: directory tree + first dataclasses + protocols + tests

Phase 0.3 — directory structure:
- src/workbench/{domain,physics,sdk,app,ui,cli,io,plugins_builtin}/
- subpackages: domain/{dynamics,timing,hil,physics_lab}, physics/{propagation,reflection,
  dynamics,atmosphere,antenna,_testbench}, app/{commands,nn,hil,timing,physics_lab},
  ui/{editor,simulator/{scene_3d,nn_mode,hil_panel,profiler_panel},physics_lab,welcome,
  nn_training,plugin_manager}
- tests/{unit/{domain,sdk},integration,physics}/
- All __init__.py with module-level docstrings
- py.typed marker for PEP 561

Phase 0.4 — first code:
- src/workbench/__init__.py: __version__ = '0.1.0a0'
- src/workbench/__main__.py: minimal CLI entry (python -m workbench)
- src/workbench/domain/types.py: PositionENU, VelocityENU, Time (frozen, slots)
- src/workbench/sdk/protocols.py: 11 Plugin Protocol stubs (DetectorProtocol ~
  PhysicsModelProtocol, all @runtime_checkable)
- src/workbench/sdk/__init__.py: re-exports all 11 protocols as public API
- tests/conftest.py: sample_position fixture
- tests/unit/domain/test_types.py: 5 unit tests (creation, immutability, speed,
  zero-velocity, time advance)

.importlinter:
- Active: layer-stack, workspace-isolation (both directions), domain-purity,
  sdk-dependency
- Disabled (commented): pyvista-isolation (Phase 4), nn-isolation (Phase 6) —
  source modules don't exist yet

Refs: plan/02 § 2.3 (디렉토리), plan/03 § 3.2 (dataclass), plan/04 § 4.3 Phase 0~2,
plan/17 § 17.4.1 (11 Protocol), plan/19 § 19.8 (PhysicsModelProtocol)."

echo ""
echo "=== commit 완료 ==="
git log --oneline -5
echo ""
echo "다음: git push"
