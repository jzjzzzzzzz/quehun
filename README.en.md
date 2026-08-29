# QueHun

[![CI](https://github.com/jzjzzzzzzz/quehun/actions/workflows/ci.yml/badge.svg)](https://github.com/jzjzzzzzzz/quehun/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

<p align="center">
  <a href="README.md">简体中文</a> · <strong>English</strong>
</p>

A Mahjong Soul screen-recognition, Japanese mahjong tile-efficiency analysis, and optional
safety-guarded clicking tool. The project also includes a four-player self-play simulator that
does not require the game client, plus a read-only live analysis workbench for Windows and macOS.

## Features

- Cross-platform window enumeration, screenshots, and foreground-state detection;
- Hand segmentation, template classification, OCR/visual page-state detection, and scalable
  region recognition;
- Recognition for discard rivers, dora indicators, round/seat winds, and action buttons;
- Shanten, ukeire, winning-hand, yaku, danger, and explainable top-three discard analysis;
- Compact notation, Unicode mahjong tiles, dora rotation, and hand-validation utilities;
- Tkinter calibration and analysis interface;
- Optional clicking controller that is disabled by default and protected by multiple
  preconditions;
- Reproducible Japanese mahjong self-play and a comprehensive regression test suite.

> The live-client classifier currently relies mainly on local templates and prototypes rather
> than Torch. Hand and action regions must be recalibrated for different client versions,
> resolutions, and display scaling settings.

## Requirements

- Python 3.11 or later;
- Windows 10/11 or macOS; Linux supports the pure mahjong logic and tests;
- Optional Tesseract OCR. English and Simplified Chinese language data are included, but the
  Tesseract executable is still required;
- Live analysis on macOS requires Screen Recording permission. Clicking additionally requires
  Accessibility permission.

## Installation

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

To train the Torch models under `model/`, install the training dependencies instead:

```bash
python -m pip install -r requirements-training.txt
```

## Quick start

Launch the graphical workbench:

```bash
python main.py --gui
```

Running without arguments also launches the UI. On macOS, you can double-click
`run_quehun_mac.command`. Before the first live session, run:

```bash
python tools/macos_permissions.py
```

Common commands:

| Purpose | Command |
| --- | --- |
| Read-only analysis loop | `python main.py --analyze` |
| Debug analysis | `python main.py --analyze --debug` |
| Single-table simulation | `python main.py --simulate --seed 1` |
| Full four-player game | `python main.py --full-game --rounds 4` |
| List windows | `python main.py --list-windows` |
| Save a window screenshot | `python main.py --save-window-screenshot quehun.png --window-title QueHun` |
| Auto-discard dry run | `python main.py --auto-play --iterations 5` |

At most 50 full-window debug screenshots are retained in `debug/screenshots`. The latest hand
crops are stored in `debug/tiles/latest`.

## Live-client calibration

Open a Mahjong Soul friendly or AI room, then use **Select screenshot region** in the UI to draw a
tight box around all of your hand slots. Alternatively, save a window screenshot from the CLI,
measure `left,top,width,height`, and write the region to the configuration.

See [`docs/calibration.md`](docs/calibration.md) for the complete workflow and Windows/macOS
examples. See [`templates/tiles/README.md`](templates/tiles/README.md) for template labels and the
directory layout.

## Click safeguards

Read-only analysis is the default. A discard click is allowed only when all of the following are
true:

- The detector reports an active game and the target window is in the foreground;
- The hand is stable across consecutive frames and its tile count matches the action phase;
- Overall and per-tile confidence meet their thresholds;
- The target coordinate is inside the calibrated region;
- The hand has not already been processed;
- The click cooldown has elapsed.

Action buttons have separate template-confidence, stable-frame, and allow-list requirements.
When changing recognition or clicking logic, preserve these preconditions and validate the change
in dry-run mode first.

## Development

```bash
python -m pip install -r requirements-dev.txt
ruff format --check .
ruff check .
python -m pytest
python -m compileall -q ai capture cv model runtime state tools ui main.py
```

The same CI suite runs on Python 3.11 and 3.13. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the
contribution workflow, recognition-test requirements, and commit conventions.

## Documentation

- [Architecture and module boundaries](docs/architecture.md)
- [Live-client calibration](docs/calibration.md)
- [Mahjong notation and validation API](docs/mahjong_notation.md)
- [Changelog](CHANGELOG.md)
- [Security reporting](SECURITY.md)

## Data and licensing

The project source code is licensed under the [Apache License 2.0](LICENSE). Mahjong tile data in
`dataset/` retains its separate [MIT License](dataset/LICENSE) and source attribution. Record the
source and license whenever adding images, templates, or models.
