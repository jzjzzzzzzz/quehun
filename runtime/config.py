import json
import os
from copy import deepcopy


DEFAULT_CONFIG_PATH = "config/autoplay.json"


DEFAULT_CONFIG = {
    "window_title": "雀魂",
    "window_title_fallbacks": ["雀魂麻将", "MahjongSoul", "Mahjong Soul"],
    "window_title_exact": False,
    "region_mode": "window",
    "window_required": False,
    "focus_window": False,
    "focus_delay": 0.2,
    "focus_retries": 2,
    "hand_region": {
        "left": 284,
        "top": 883,
        "width": 1230,
        "height": 137,
    },
    "hand_reference_size": {
        "width": 1920,
        "height": 1080,
    },
    "tile_slots": 14,
    "tile_count": 14,
    "actionable_tile_counts": [14],
    "waiting_tile_counts": [13],
    "stable_frames": 2,
    "click_cooldown": 1.2,
    "analysis": {
        "debug": False,
        "debug_dir": "debug/screenshots",
        "tile_debug_dir": "debug/tiles/latest",
        "max_debug_screenshots": 50,
        "ocr_enabled": True,
        "low_confidence_warning": 0.65,
        "error_backoff": 1.0,
    },
    "click": {
        "enabled": False,
        "min_confidence": 0.82,
        "require_in_game": True,
        "require_foreground": True,
        "y_offset_ratio": 0.5,
        "repeat": 1,
        "repeat_delay": 0.15,
    },
    "discard_confirm": {
        "enabled": False,
        "delay": 0.2,
        "region": None,
    },
    "auto_click_bonus": False,
    "auto_pass": False,
    "action_prompt": {
        "enabled": False,
        "detect_regions": ["chi", "pass"],
        "edge_threshold": 0.05,
        "stable_frames": 1,
        "default_action": "pass",
    },
    "action_policy": {
        "enabled": False,
        "allowed_actions": ["ron", "tsumo", "riichi", "kan", "pon", "chi", "pass"],
        "action_priority": ["ron", "tsumo", "riichi", "kan", "pon", "chi", "pass"],
        "min_confidence": 0.80,
        "stable_frames": 2,
    },
    "action_regions": {
        "chi": {"left": 900, "top": 760, "width": 230, "height": 95},
        "pass": {"left": 1170, "top": 760, "width": 220, "height": 95},
    },
    "min_confidence": 0.25,
    "max_low_confidence_tiles": 0,
    "delay": 1.0,
}


def load_config(path=DEFAULT_CONFIG_PATH):
    if not path or not os.path.exists(path):
        return deepcopy(DEFAULT_CONFIG)

    with open(path, encoding="utf-8") as file:
        config = json.load(file)

    merged = deepcopy(DEFAULT_CONFIG)
    merged.update(config)
    for section in (
        "analysis",
        "click",
        "discard_confirm",
        "action_prompt",
        "action_policy",
        "action_regions",
    ):
        if section in config:
            merged[section] = deepcopy(DEFAULT_CONFIG[section])
            merged[section].update(config[section])
    return merged


def save_config(config, path=DEFAULT_CONFIG_PATH):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)
    return path


def parse_region(value):
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("Region must be left,top,width,height")
    if parts[2] <= 0 or parts[3] <= 0:
        raise ValueError("Region width and height must be positive")
    return {
        "left": parts[0],
        "top": parts[1],
        "width": parts[2],
        "height": parts[3],
    }
