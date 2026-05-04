# Contributing to TRsim

Thank you for your interest. TRsim is an open-source platform for tracking radar algorithm development, and we welcome contributions of all kinds — bug fixes, features, documentation, examples, and DLC packages.

## Quick links

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Governance](GOVERNANCE.md)
- [Security policy](SECURITY.md)
- [Architecture overview](plan/02_architecture.md)

## Ways to contribute

### 1. Report bugs / Request features

- Use [GitHub Issues](https://github.com/<TBD>/trsim/issues)
- Templates available for bugs, features, questions
- Search existing issues first to avoid duplicates

### 2. Submit a pull request

For code contributions, please:

1. **Open an issue first** for non-trivial changes — to align on scope before coding
2. Fork the repo, create a feature branch
3. Follow the [coding guidelines](#coding-guidelines)
4. Write tests (we use `pytest`)
5. Sign off your commits (DCO — see below)
6. Open a PR against `main`

### 3. Improve documentation

Doc PRs are always welcome. The `plan/` directory holds design documents; the `docs/` directory holds user-facing guides.

### 4. Build a DLC package

If your contribution is best expressed as a `.trsim-pkg` (a Tracker, Detector, custom Map, etc.), publish it as your own repo and (optionally) submit it to the [awesome-trsim-packages](https://github.com/<TBD>/awesome-trsim-packages) list.

DLCs are independent of TRsim Core — you choose your own license, release schedule, and dependencies.

## Developer Certificate of Origin (DCO)

We use the [Developer Certificate of Origin](https://developercertificate.org/) (DCO) instead of a CLA. Every commit must include a `Signed-off-by` line:

```
Signed-off-by: Your Name <your.email@example.com>
```

The easiest way is `git commit -s` (the `-s` flag adds the line automatically).

By signing off, you certify that you wrote the code (or have the right to submit it under the project's license). See [DCO](https://developercertificate.org/) for the full text.

We do **not** require a separate Contributor License Agreement.

## Coding guidelines

### Python style
- Python 3.11+
- `ruff` for linting and formatting (config in `pyproject.toml`)
- Type hints on all public APIs
- Dataclasses with `frozen=True` for value objects (see [03 data_model](plan/03_data_model.md))

### Architecture rules
The dependency direction is strictly enforced (see [02 § 2.5](plan/02_architecture.md)):

```
ui → app → sdk → domain → physics
```

DLC packages depend only on `sdk`. Reverse imports are blocked by `import-linter` in CI.

### Testing
- Unit tests in `tests/unit/`
- Physics regression tests in `tests/physics/` with golden datasets
- Aim for new code to come with tests; bug fixes should include a regression test
- Run locally: `pytest`

### Commit messages
- Subject line < 72 chars, present tense ("Add UKF tracker", not "Added")
- Body explains *why*, not *what* (the diff already shows what)
- Reference issues: `Fixes #123` / `Refs #123`
- Sign off (`-s`)

## Pull request review

- A maintainer will review within ~1 week (best effort, this is volunteer work)
- Expect feedback and iteration — don't take review comments personally
- We squash-merge by default; preserve a clean commit history if you prefer rebase-merge (note in PR)

## Coding scope guidance

Some areas are **stable** (don't change without prior discussion in an issue):
- `domain/` core types (RigidBodyState, RadarModel, etc.)
- Coordinate system conventions (see [11 coordinate_systems](plan/11_coordinate_systems.md))
- Pipeline Stage Slot Protocol
- Data model TOML schemas

Some areas are **welcoming new contributions**:
- New tracker / detector / pairing implementations
- New visualization panels
- Bug fixes everywhere
- Documentation, examples, tutorials
- Tests (especially physics regression)

## Questions?

- [GitHub Discussions](https://github.com/<TBD>/trsim/discussions) for design / architecture questions
- [Issues](https://github.com/<TBD>/trsim/issues) for bugs and concrete requests
- Be patient — this project is maintained by volunteers
