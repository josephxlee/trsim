# Simple Pairing Demo — Reference TRsim DLC

A minimal `.trsim-pkg` source layout that ships with the TRsim repo
so new DLC authors have a working `trsim sdk build` target without
needing to invent a manifest from scratch.

## Contents

```
simple_pairing_demo/
├── manifest.toml          ← package metadata (plan/17 § 17.2.4)
├── README.md              ← this file
├── resources/maps/
│   └── demo_map.toml      ← sample Map resource
└── ui/
    └── demo_panel.py      ← sample UI panel (placeholder)
```

## Build + install

From the repository root:

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m workbench sdk build `
    --source examples/dlc/simple_pairing_demo `
    --output dist/simple_pairing_demo.trsim-pkg

& $PY -m workbench sdk test `
    --package dist/simple_pairing_demo.trsim-pkg

& $PY -m workbench install `
    --package dist/simple_pairing_demo.trsim-pkg
```

After the install, launch the workbench (`& $PY -m workbench ui`) — the
DemoPanel appears in the Simulator workspace bottom-tab list as
`[DLC] simple-pairing-demo: DemoPanel`, and `demo_map` appears in
the Resource Browser under `Maps`.

## See also

- [`docs/dev_guide/creating_dlc.md`](../../../docs/dev_guide/creating_dlc.md)
  — tutorial that explains every section of the manifest and the
  `entry_points` mapping.
- `plan/17_open_platform.md` § 17.2.4 — formal `.trsim-pkg` spec.
