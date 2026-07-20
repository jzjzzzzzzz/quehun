# Architecture

QueHun separates pure mahjong logic from platform integration and screen recognition. This keeps
the decision engine testable without a live client.

## Data flow

```text
window capture
    -> screen-state and region recognition
    -> hand segmentation and tile classification
    -> GameState / StateTracker
    -> shanten, ukeire, danger, and yaku analysis
    -> explainable top-three advice
    -> UI or guarded click controller
```

## Modules

| Area | Responsibility |
| --- | --- |
| `capture/` | Cross-platform window discovery, screen capture, and coordinate sources |
| `cv/` | Screen state, regions, hand segmentation, templates, OCR, and calibration |
| `state/` | Current game state, frame synchronization, and transition tracking |
| `ai/` | Canonical tiles, notation, agari, shanten, ukeire, yaku, danger, and advice |
| `runtime/` | CLI routing, simulation, analysis loop, autoplay, and guarded clicking |
| `ui/` | Tkinter configuration, status, calibration, and advice presentation |
| `model/` | Optional Torch training path; not required by template-based runtime recognition |
| `test/` | Unit, regression, platform-boundary, and pipeline tests |

## Safety boundary for clicks

Recognition and advice are read-only by default. A discard click is permitted only when all
configured checks pass: correct foreground window, in-game screen state, sufficient recognition
confidence, expected tile count, stable frames, a new hand signature, valid coordinates, and an
elapsed cooldown. Action-button clicks have their own confidence and policy gates.

Platform code belongs behind `capture/` or `runtime/clicker.py`; mahjong logic must not depend on
window handles, images, or GUI state.

## Runtime and training dependencies

The default runtime uses OpenCV template/prototype recognition and does not import Torch. The
training stack is isolated in `model/` and installed through `requirements-training.txt`.
