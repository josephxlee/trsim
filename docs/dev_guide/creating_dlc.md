# Creating a TRsim DLC (`.trsim-pkg`)

This tutorial walks you through building, testing, and installing a
TRsim DLC package using the `trsim sdk` CLI introduced in Phase 7.
Reference implementation:
[`examples/dlc/simple_pairing_demo/`](../../examples/dlc/simple_pairing_demo/).

## 1. Why DLC?

TRsim's Core ships with the FMCW-triangle pipeline, single-target
EKF/UKF tracker, and the standard 9 Test Objects. A **DLC** lets you
add your own:

- **Algorithms** — Pairing / Tracker / Predictor / Classifier /
  DataAssociator NN plugins (see [`plan/07_nn_integration.md`](../../plan/07_nn_integration.md)).
- **Resources** — Map / Radar / Targets `.toml` definitions.
- **UI panels** — Custom pyqtgraph / pyvista widgets shown in the
  Simulator workspace bottom-tab.
- **Physics models** — `PhysicsModelProtocol` implementations
  (plan/19 § 19.8) consumed by the Physics Lab.

A DLC is a single `.trsim-pkg` zip archive that the Core can install,
load, and uninstall without touching the Core source. See
[`plan/17_open_platform.md`](../../plan/17_open_platform.md) for the
full design.

## 2. Source layout

```
my_tracker_src/
├── manifest.toml          ← package metadata (REQUIRED at zip root)
├── README.md
├── resources/
│   ├── maps/<id>.toml
│   ├── radars/<id>.toml
│   └── targets/<id>.toml
├── plugins/
│   └── my_tracker.py      ← Python module implementing TrackerProtocol
└── ui/
    └── my_panel.py        ← QWidget subclass
```

Every file under `manifest.toml`'s parent directory is included in
the zip. Symlinks and special files are skipped silently.

## 3. `manifest.toml` schema

Minimum required keys (plan/17 § 17.2.4):

```toml
[package]
id = "my-tracker"                        # kebab-case, globally unique
name = "My Cool Tracker"                 # human label
version = "0.1.0"                        # SemVer
author = "Your Name <you@example.com>"
description = "Stealth target tracker (CNN + Kalman)"
license = "Apache-2.0"
homepage = "https://github.com/you/my-tracker"

[compatibility]
trsim_min_version = "0.40.0"             # SemVer of the Core you tested against
trsim_max_version = ""                   # optional, "" = unbounded

[python]
extra_requires = []                       # extra pip deps your plugin needs

[entry_points]
# slot = "<path-inside-zip>:<attribute>"
"trsim.tracker" = "plugins/my_tracker.py:MyTracker"
"trsim.ui.panels" = "ui/my_panel.py:MyPanel"
# Resource directories are *path* slots — no `:attribute`.
"trsim.resources.maps" = "resources/maps/"
"trsim.resources.radars" = "resources/radars/"
"trsim.resources.targets" = "resources/targets/"
```

### Slot reference

| Slot | Target shape | Loaded by |
|---|---|---|
| `trsim.tracker` | Class implementing `TrackerProtocol` | `app/dlc/plugin_loader.py` |
| `trsim.pairing` | Class implementing `PairingProtocol` | `app/dlc/plugin_loader.py` |
| `trsim.predictor` / `trsim.classifier` / `trsim.data_associator` | matching Protocol | `app/dlc/plugin_loader.py` |
| `trsim.ui.panels` | `QWidget` subclass | `ui/panel_registry.py` |
| `trsim.resources.{maps,radars,targets,scenarios}` | Directory path | `app/resources/library.py` |

See [`src/workbench/sdk/protocols.py`](../../src/workbench/sdk/protocols.py)
for every Protocol's required surface.

## 4. Build + test + install

From the repository root (PowerShell):

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

# 1. Pack the source directory into a .trsim-pkg.
& $PY -m workbench sdk build `
    --source examples/dlc/simple_pairing_demo `
    --output dist/simple_pairing_demo.trsim-pkg

# 2. Sanity-check the manifest before publishing.
& $PY -m workbench sdk test `
    --package dist/simple_pairing_demo.trsim-pkg

# 3. Install into ~/.trsim/packages/.
& $PY -m workbench install `
    --package dist/simple_pairing_demo.trsim-pkg
```

Bash variant:

```bash
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m workbench sdk build \
    --source examples/dlc/simple_pairing_demo \
    --output dist/simple_pairing_demo.trsim-pkg
```

## 5. CLI exit codes

| Code | Meaning |
|---|---|
| 0 | Success. Soft issues (empty description / author) print but don't fail. |
| 2 | Hard failure: missing file, invalid manifest, wrong file suffix, zip-slip, existing install dir without `--force`. |

`trsim install` writes to `<packages-root>/<package_id>/`, defaults
to `~/.trsim/packages/`. Override with `--packages-root <dir>`.

`--force` removes an existing install of the same `package_id`
before extracting — same UX as `pip install --force-reinstall` for
a single package.

## 6. Python API (alternative to CLI)

```python
from pathlib import Path
import workbench.sdk as sdk

# Build
pkg = sdk.build_package(
    source=Path("my_tracker_src/"),
    output=Path("dist/my_tracker.trsim-pkg"),
)

# Test
result = sdk.test_package(pkg)
print(result.package_id, result.package_version)
for issue in result.issues:
    print(f"  soft: {issue}")
```

`trsim install` does not currently have a Python API — call the CLI
or use `workbench.io.package_io.unpack_package(pkg, target_dir)`
directly.

## 7. Common pitfalls

- **`manifest.toml` is not at the zip root**. Build / test rejects this
  with `missing root manifest.toml`. Make sure your `--source` argument
  points at the directory *containing* `manifest.toml`, not its
  parent.
- **PowerShell 5.1 BOM**. `Out-File -Encoding utf8` writes a UTF-8
  BOM that `tomllib` can't read. The loader strips it now, but
  prefer `[System.IO.File]::WriteAllText(...,
  [System.Text.UTF8Encoding]::new($false))` for clean files.
- **`entry_points` typo**. Slot names must match exactly — `trsim.tracker`
  (singular) not `trsim.trackers`. Wrong slot names land in
  `PluginLoader.load_errors` and the package fails to surface in the UI.
- **Zip slip**. An entry named `../escape.txt` is rejected during
  unpack (CVE-2018-1002201 defence). Don't try to install files
  outside the package's own directory.

## 8. Reference DLC

[`examples/dlc/simple_pairing_demo/`](../../examples/dlc/simple_pairing_demo/)
ships in-tree and round-trips through the entire workflow. Use it as
a working starting point.
