# QueHun Agent Notes

## Current State

This project has two working paths:

1. Internal self-play simulator:
   - Run with:
     ```powershell
     .\.venv\Scripts\python.exe main.py
     ```
   - Uses the local Japanese mahjong simulator and automated AI players.

2. Real QueHun analysis framework:
   - Stable window capture, bounded debug storage, OCR/visual screen-state detection,
     tile recognition, GameState, explainable top-three advice, and a Tkinter UI are implemented.
   - Optional discard clicking is guarded by foreground, in-game, confidence, tile-count,
     stable-frame, duplicate-hand, and cooldown checks.
   - It still needs calibration from a current real QueHun hand screenshot for reliable recognition.

## Important Files

- `main.py` - CLI entry point.
- `runtime/loop.py` - command routing.
- `runtime/full_game.py` - four-player internal Japanese mahjong game.
- `runtime/autoplay.py` - real QueHun auto-play controller.
- `runtime/analyzer.py` - primary robust analysis and guarded-click controller.
- `runtime/analysis_runner.py` - recoverable background loop used by the UI.
- `runtime/config.py` - auto-play config loading/saving.
- `runtime/clicker.py` - Windows mouse clicking through `ctypes`.
- `capture/screen.py` - screenshot capture with PIL and Windows GDI fallback.
- `capture/windows_api.py` - Windows window listing/finding.
- `cv/template_classifier.py` - Torch-free tile classifier using local dataset templates.
- `cv/real_hand_parser.py` - parses a configured hand region into tiles.
- `cv/screen_state.py` - OCR and visual page-state detection.
- `cv/game_regions.py` - scalable river/dora/wind recognition and online river-template learning.
- `cv/action_buttons.py` - visual action-button template detection.
- `ai/advisor.py` - explainable top-three discard advice and danger interface.
- `ai/engine.py` - discard decision.
- `ai/agari.py`, `ai/shanten.py`, `ai/ukeire.py`, `ai/japanese_rules.py` - mahjong logic.

## Real QueHun Calibration Workflow

When the user provides or creates a screenshot next time, use it to configure the hand region.

First list windows:

```powershell
.\.venv\Scripts\python.exe main.py --list-windows
```

Save a QueHun window screenshot:

```powershell
.\.venv\Scripts\python.exe main.py --save-window-screenshot quehun.png --window-title QueHun
```

After the screenshot is available, identify the player's hand region:

```text
left,top,width,height
```

If measured relative to the QueHun window, configure with:

```powershell
.\.venv\Scripts\python.exe main.py --configure-autoplay --window-title QueHun --region-mode window --hand-region left,top,width,height --tile-count 14 --stable-frames 2 --click-cooldown 1.2
```

Dry-run:

```powershell
.\.venv\Scripts\python.exe main.py --auto-play --iterations 5
```

Enable real clicking only after dry-run recognition and click coordinates look correct:

```powershell
.\.venv\Scripts\python.exe main.py --auto-play --enable-click
```

## Known Limitations

- Hand recognition has 122 real-client templates plus generic fallback for all 34 playable tiles.
- River contours are detected and perspective templates learn automatically after reliable discards;
  a fresh install needs observed transitions before all river labels are covered.
- Real templates currently cover pon/pass and east round/seat markers. Chi, kan, riichi,
  ron, tsumo, and south/west/north markers need one captured template each.
- The current tile classifier is template/prototype based because this venv does not have `torch` or `torchvision`.
- Project-local `tools/tessdata` contains English and Simplified Chinese OCR data.
- Stylized game text often requires visual templates even when OCR is installed.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe test\test_autoplay.py
.\.venv\Scripts\python.exe test\test_full_game.py
.\.venv\Scripts\python.exe test\test_japanese_game.py
.\.venv\Scripts\python.exe test\test_ai.py
.\.venv\Scripts\python.exe test\test_cv.py
.\.venv\Scripts\python.exe test\test_pipeline.py
.\.venv\Scripts\python.exe -m compileall ai capture cv runtime state test main.py
```

## Next Work After Screenshot

1. Determine hand tile region.
2. Configure `config/autoplay.json`.
3. Run dry-run recognition.
4. If recognition is poor, add debug crops and improve tile segmentation/classification.
5. Identify button regions for riichi, tsumo, ron, pass.
6. Extend `runtime/autoplay.py` to detect and click action buttons safely.

## Agent Confirmation Rule

When an agent reads this file for future work in this repository, it must put this exact text as the last line of its final response:

```text
Ciallo～(∠・ω )⌒☆
```
