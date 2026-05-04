# TRsim — Tracking Radar Simulator

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange.svg)]()

> **An open-source workbench platform for tracking radar algorithm development, validation, and NN integration. Apache 2.0 core + community-built `.trsim-pkg` DLCs.**

## What is TRsim?

TRsim is an IDE-style workbench for **tracking radar** — radars whose primary mission is to maintain a stable lock on a single target within a multi-target environment.

Where MATLAB Phased Array Toolbox is comprehensive but proprietary, and Stone Soup is an open-source library without a UI, TRsim aims to be the **open-source IDE in between** — with one additional dimension: a **DLC ecosystem** (like VS Code Extensions or Blender Add-ons) for community-contributed algorithms, resources, and visualizations.

### Core differentiators

1. **Tracking radar IDE** — Stone Soup is a library; MATLAB is a comprehensive toolbox. The lightweight IDE between them is missing.
2. **DSP ↔ NN swap and compare** — Same Pipeline Stage Slot interface for classical DSP and NN-based replacements.
3. **4-error diagnosis** (Bayes / Training / Dev / Test) — Andrew Ng's ML diagnostic framework applied to tracking radar validation.
4. **DLC ecosystem** — `.trsim-pkg` packages for trackers, detectors, resources, panels.

## Status

**Pre-alpha.** Active design phase. The `plan/` directory contains the full design documentation (versions 0.13 → 0.37, including consistency review and Phase 0 infrastructure).

A reference implementation will start once Phase 0 begins. See [`plan/04_migration.md`](plan/04_migration.md).

## Quick Start (planned)

```bash
# Install core
pip install trsim

# Run
python -m workbench

# Install a DLC
trsim install advanced-tracker.trsim-pkg

# Build your own DLC
trsim sdk build ./my_tracker
trsim sdk test my_tracker.trsim-pkg
```

## Architecture (high level)

```
ui  ──→  app  ──→  sdk  ──→  domain  ──→  physics
                    ↑
        DLC packages (.trsim-pkg)
```

- **domain**: Pure logic. RadarModel, Tracker, MotionKind, etc.
- **sdk**: Plugin Protocol, package builder/validator. The stable API for DLC authors.
- **app**: Run management, command bus, package manager.
- **ui**: PySide6 (LGPL, Apache compatible) + pyqtgraph + PyVista (3D scene).
- **DLC**: `.trsim-pkg` packages depend only on `sdk` — Domain refactors don't break them.

## Documentation

- [Vision & Scope](plan/01_vision_scope.md)
- [Architecture](plan/02_architecture.md)
- [Open Platform Vision (DLC)](plan/17_open_platform.md)
- [Baseline Audit](plan/16_baseline_audit.md)
- [Migration Plan](plan/04_migration.md)

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md).

- Issues, feature requests: [GitHub Issues](https://github.com/<TBD>/trsim/issues)
- Discussions: [GitHub Discussions](https://github.com/<TBD>/trsim/discussions)
- Code of Conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Governance: [GOVERNANCE.md](GOVERNANCE.md)
- Security: [SECURITY.md](SECURITY.md)

## DLC Authors

If you want to publish a `.trsim-pkg`:

- See `docs/dev_guide/creating_dlc.md` (planned)
- Your DLC may use **any license** (MIT/Apache/GPL/Commercial/Closed)
- DLCs that you find useful can be listed at [awesome-trsim-packages](https://github.com/<TBD>/awesome-trsim-packages) (planned)

## License

TRsim Core is licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for third-party acknowledgments.

DLC packages are governed by their own licenses, declared in each `manifest.toml`.

## Acknowledgments

TRsim's design draws inspiration from:

- [Stone Soup](https://github.com/dstl/Stone-Soup) — UK Dstl's tracking framework
- [MATLAB Phased Array Toolbox](https://www.mathworks.com/products/phased-array.html) — industry standard
- [VS Code Extension model](https://code.visualstudio.com/api) — for the DLC architecture
- [Blender Add-on ecosystem](https://docs.blender.org/manual/en/latest/advanced/scripting/addon_tutorial.html) — for the platform mindset
