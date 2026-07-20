# Contributing to QueHun

Thanks for improving QueHun. Focused fixes, regression tests, calibration improvements,
and documentation corrections are welcome.

## Development setup

QueHun supports Python 3.11 and newer.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Install the optional training stack only when changing `model/`:

```bash
python -m pip install -r requirements-training.txt
```

## Before opening a pull request

```bash
ruff format .
ruff check --fix .
python -m pytest
python -m compileall -q ai capture cv model runtime state tools ui main.py
```

Keep changes scoped and add a regression test for behavior changes. Do not commit virtual
environments, generated debug captures, credentials, private room identifiers, or local editor
configuration.

## Recognition changes

When changing segmentation, classification, or screen-state detection:

1. Record the client resolution and operating system.
2. Add a synthetic or anonymized fixture where practical.
3. Verify read-only analysis first.
4. Keep real clicking disabled until recognition and coordinates are stable.
5. Preserve every guarded-click precondition.

Large image or model additions should include provenance, licensing, and a reason they cannot be
represented by a smaller fixture.

## Commit and pull-request style

Use an imperative Conventional Commit subject where practical, for example:

- `feat: recognize south round marker`
- `fix: reject stale hand before clicking`
- `test: cover scaled river region`
- `docs: clarify macOS permissions`

Pull requests should explain the user-visible effect, verification commands, and any calibration
assumptions. See the pull-request template for the full checklist.
