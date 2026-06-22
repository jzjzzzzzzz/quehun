import time

import cv2

from ai.engine import decide
from ai.tile_set import canonical_hand
from capture.screen import capture_screen
from capture.windows_api import find_window, focus_window, foreground_window
from cv.real_hand_parser import RealHandParser
from cv.game_regions import GameRegionRecognizer
from cv.action_buttons import ActionButtonDetector
from cv.screen_state import QueHunScreenStateDetector, ScreenState
from runtime.clicker import LazyWindowsClicker, NoOpClicker
from runtime.config import load_config


class AutoPlayController:
    def __init__(self, config_path=None, dry_run=True, clicker=None, debug_dir=None):
        self.config = load_config(config_path) if config_path else load_config()
        self.dry_run = dry_run
        self.clicker = clicker or (NoOpClicker() if dry_run else LazyWindowsClicker())
        self.debug_dir = debug_dir
        self.last_hand = None
        self.stable_count = 0
        self.last_action = None
        self.action_stable_count = 0
        self.last_click_at = 0.0
        self.parser = RealHandParser(
            hand_region=self._absolute_hand_region(),
            tile_count=self.config.get("tile_slots", self.config.get("tile_count", 14)),
        )
        self.region_recognizer = GameRegionRecognizer(
            classifier=self.parser.classifier
        )
        self.action_detector = ActionButtonDetector()
        self.state_detector = QueHunScreenStateDetector()

    def _window_title_candidates(self):
        candidates = []
        title = self.config.get("window_title")
        if title:
            candidates.append(title)
        candidates.extend(self.config.get("window_title_fallbacks", []))
        candidates.extend(["雀魂", "雀魂麻將", "MahjongSoul", "Mahjong Soul"])

        result = []
        for candidate in candidates:
            if candidate and candidate not in result:
                result.append(candidate)
        return result

    def _target_window(self):
        exact = bool(self.config.get("window_title_exact", False))
        for title in self._window_title_candidates():
            window = find_window(title, exact=exact)
            if window is not None:
                return window
        return None

    def focus_target_window(self):
        window = self._target_window()
        if window is None:
            return None

        foreground = foreground_window()
        if foreground is not None and foreground.get("hwnd") == window.get("hwnd"):
            return window

        focused = None
        exact = bool(self.config.get("window_title_exact", False))
        for title in self._window_title_candidates():
            focused = focus_window(title, exact=exact)
            if focused is not None:
                break
        return focused or window

    def _target_is_foreground(self):
        window = self._target_window()
        foreground = foreground_window()
        return (
            window is not None
            and foreground is not None
            and foreground.get("hwnd") == window.get("hwnd")
        )

    def _focus_and_wait(self):
        focused = self.focus_target_window()
        if focused is None:
            return False

        focus_delay = float(self.config.get("focus_delay", 0.1))
        if focus_delay > 0:
            time.sleep(focus_delay)

        retries = max(0, int(self.config.get("focus_retries", 1)))
        for _ in range(retries):
            if self._target_is_foreground():
                return True
            self.focus_target_window()
            if focus_delay > 0:
                time.sleep(focus_delay)
        return self._target_is_foreground()

    def _absolute_hand_region(self):
        region = self.config["hand_region"].copy()
        if self.config.get("region_mode") != "window":
            return region

        window = self._target_window()
        if window is None:
            if not self.config.get("window_required", False):
                return region
            raise RuntimeError(
                f"Could not find window containing title: {self.config.get('window_title')!r}"
            )

        region["left"] += window["left"]
        region["top"] += window["top"]
        return region

    def _refresh_parser_region(self):
        self.parser.hand_region = self._absolute_hand_region()
        self.parser.tile_count = self.config.get("tile_slots", self.config.get("tile_count", 14))

    def _tile_center(self, tile_index):
        region = self._absolute_hand_region()
        tile_count = self.config.get("tile_slots", self.config.get("tile_count", 14))
        tile_width = region["width"] / tile_count
        x = region["left"] + tile_width * (tile_index + 0.5)
        y_ratio = self.config.get("click", {}).get("y_offset_ratio", 0.5)
        y = region["top"] + region["height"] * y_ratio
        return int(round(x)), int(round(y))

    def _absolute_region(self, region):
        absolute = region.copy()
        if self.config.get("region_mode") != "window":
            return absolute

        window = self._target_window()
        if window is None:
            return absolute

        absolute["left"] += window["left"]
        absolute["top"] += window["top"]
        return absolute

    def _region_center(self, region):
        absolute = self._absolute_region(region)
        x = absolute["left"] + absolute["width"] / 2
        y = absolute["top"] + absolute["height"] / 2
        return int(round(x)), int(round(y))

    def _select_tile_index(self, hand, discard):
        for idx, tile in enumerate(hand):
            if tile == discard:
                return idx
        return None

    def _is_stable_hand(self, hand):
        current = tuple(hand)
        if current == self.last_hand:
            self.stable_count += 1
        else:
            self.last_hand = current
            self.stable_count = 1
        return self.stable_count >= self.config.get("stable_frames", 2)

    def _is_stable_action(self, action):
        if action == self.last_action:
            self.action_stable_count += 1
        else:
            self.last_action = action
            self.action_stable_count = 1
        return self.action_stable_count >= self.config.get("stable_frames", 2)

    def _cooldown_ready(self):
        return (time.time() - self.last_click_at) >= self.config.get("click_cooldown", 1.2)

    def _prepare_click(self):
        if self.config.get("focus_window", True):
            return self._focus_and_wait()
        return True

    def _click_tile(self, x, y):
        if not self._prepare_click():
            return False

        click_config = self.config.get("click", {})
        repeat = max(1, int(click_config.get("repeat", 1)))
        repeat_delay = float(click_config.get("repeat_delay", 0.15))

        for idx in range(repeat):
            self.clicker.click(x, y)
            if idx + 1 < repeat:
                time.sleep(repeat_delay)
        return True

    def _click_region(self, region):
        if not self._prepare_click():
            return None
        x, y = self._region_center(region)
        self.clicker.click(x, y)
        return {"x": x, "y": y}

    def _discard_confirm_region(self):
        discard_config = self.config.get("discard_confirm", {})
        if not discard_config.get("enabled", False):
            return None

        region = discard_config.get("region")
        if region:
            return region

        return self.config.get("action_regions", {}).get("discard")

    def _click_discard_confirm(self):
        region = self._discard_confirm_region()
        if not region:
            return None

        discard_config = self.config.get("discard_confirm", {})
        delay = float(discard_config.get("delay", 0.2))
        if delay > 0:
            time.sleep(delay)
        return self._click_region(region)

    def _action_region(self, action):
        return self.config.get("action_regions", {}).get(action)

    def _click_action(self, action):
        region = self._action_region(action)
        if not region:
            return None
        return self._click_region(region)

    def _region_crop(self, frame, region):
        absolute = self._absolute_region(region)
        left = max(0, int(absolute["left"]))
        top = max(0, int(absolute["top"]))
        right = max(left, int(absolute["left"] + absolute["width"]))
        bottom = max(top, int(absolute["top"] + absolute["height"]))
        return frame[top:bottom, left:right]

    def _region_edge_score(self, frame, region):
        crop = self._region_crop(frame, region)
        if crop.size == 0:
            return 0.0
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return float((edges > 0).mean())

    def _visible_action_prompts(self, frame):
        prompt_config = self.config.get("action_prompt", {})
        if not prompt_config.get("enabled", True):
            return []

        threshold = float(prompt_config.get("edge_threshold", 0.05))
        actions = []
        for action in prompt_config.get("detect_regions", ["chi", "pass"]):
            region = self._action_region(action)
            if not region:
                continue
            score = self._region_edge_score(frame, region)
            if score >= threshold:
                actions.append({"action": action, "score": score})
        return actions

    def _scene_state(self, frame):
        try:
            hand_region = self.parser.hand_region
            screen = self.state_detector.detect(frame, hand_region=hand_region)
            regions = self.region_recognizer.recognize(
                frame,
                ocr=getattr(self.state_detector, "ocr", None),
            )
            actions = self.action_detector.detect(
                frame,
                regions["regions"]["actions"],
                reference_size=(
                    self.region_recognizer.config["reference_size"]["width"],
                    self.region_recognizer.config["reference_size"]["height"],
                ),
                ocr=getattr(self.state_detector, "ocr", None),
            )
            visible_tiles = [
                tile
                for player_discards in regions["discards"].values()
                for tile in player_discards
            ] + list(regions["dora_indicators"])
            return {
                "screen_state": screen.state.value,
                "screen_confidence": screen.confidence,
                "ocr_text": screen.text,
                "discards": regions["discards"],
                "dora_indicators": regions["dora_indicators"],
                "round_wind": regions["round_wind"],
                "seat_wind": regions["seat_wind"],
                "visible_actions": actions,
                "visible_tiles": visible_tiles,
                "region_details": regions["raw"],
            }
        except Exception as exc:
            return {
                "screen_state": ScreenState.UNKNOWN.value,
                "screen_confidence": 0.0,
                "ocr_text": "",
                "discards": {"self": [], "right": [], "opposite": [], "left": []},
                "dora_indicators": [],
                "round_wind": None,
                "seat_wind": None,
                "visible_actions": [],
                "visible_tiles": [],
                "region_details": {},
                "scene_error": str(exc),
            }

    def _template_action_prompt(self, scene):
        policy = self.config.get("action_policy", {})
        if not policy.get("enabled", False):
            return None

        allowed = set(policy.get("allowed_actions", ["pass"]))
        minimum = float(policy.get("min_confidence", 0.80))
        priority = policy.get(
            "action_priority",
            ["ron", "tsumo", "riichi", "kan", "pon", "chi", "pass"],
        )
        candidates = [
            action for action in scene.get("visible_actions", [])
            if action["action"] in allowed and action["confidence"] >= minimum
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda action: (
                priority.index(action["action"])
                if action["action"] in priority
                else len(priority),
                -float(action["confidence"]),
            )
        )
        return candidates[0]

    def _handle_template_action_prompt(self, scene):
        action = self._template_action_prompt(scene)
        if action is None:
            return None

        stable_required = int(
            self.config.get("action_policy", {}).get(
                "stable_frames",
                self.config.get("stable_frames", 2),
            )
        )
        signature = (
            "detected-action",
            action["action"],
            action.get("source"),
            action.get("center", {}).get("x"),
            action.get("center", {}).get("y"),
        )
        if stable_required > 1 and not self._is_stable_action(signature):
            return {
                "action": "wait",
                "reason": f"waiting for stable {action['action']} button",
                "detected_action": action,
                "low_confidence_count": None,
                **scene,
            }
        if not self._cooldown_ready():
            return {
                "action": "wait",
                "reason": "click cooldown",
                "detected_action": action,
                "low_confidence_count": None,
                **scene,
            }

        click = {"x": action["center"]["x"], "y": action["center"]["y"]}
        if not self.dry_run:
            if not self._prepare_click():
                return {
                    "action": "skip",
                    "reason": "target window is not foreground",
                    "detected_action": action,
                    "low_confidence_count": None,
                    **scene,
                }
            self.clicker.click(click["x"], click["y"])
            self.last_click_at = time.time()

        return {
            "action": (
                f"{action['action']}_dry_run"
                if self.dry_run
                else f"{action['action']}_click"
            ),
            "reason": "action button detected",
            "detected_action": action,
            "click": click,
            "low_confidence_count": None,
            **scene,
        }

    def _decide_prompt_action(self, prompts):
        default_action = self.config.get("action_prompt", {}).get("default_action", "pass")
        if any(prompt["action"] == default_action for prompt in prompts):
            return default_action
        if self._action_region(default_action):
            return default_action
        return prompts[0]["action"] if prompts else None

    def _handle_action_prompt(self, frame):
        prompts = self._visible_action_prompts(frame)
        if not prompts:
            return None

        action = self._decide_prompt_action(prompts)
        if not action:
            return None

        stable_required = int(
            self.config.get("action_prompt", {}).get(
                "stable_frames",
                self.config.get("stable_frames", 2),
            )
        )
        if stable_required > 1 and not self._is_stable_action(("prompt", action)):
            return {
                "action": "wait",
                "reason": f"waiting for stable {action} prompt",
                "prompts": prompts,
                "low_confidence_count": None,
            }

        if not self._cooldown_ready():
            return {
                "action": "wait",
                "reason": "click cooldown",
                "prompts": prompts,
                "low_confidence_count": None,
            }

        click = None
        if not self.dry_run:
            click = self._click_action(action)
            if click is None:
                return {
                    "action": "skip",
                    "reason": f"{action} region is not configured or target window is not foreground",
                    "prompts": prompts,
                    "low_confidence_count": None,
                }
            self.last_click_at = time.time()

        return {
            "action": f"{action}_dry_run" if self.dry_run else f"{action}_click",
            "reason": "action prompt visible",
            "prompts": prompts,
            "click": click or {"region": action},
            "low_confidence_count": None,
        }

    def _confidence_failures(self, details):
        minimum = self.config.get("min_confidence", 0.25)
        return [item for item in details if item["confidence"] < minimum]

    def _confident_hand(self, details):
        minimum = self.config.get("min_confidence", 0.25)
        return canonical_hand(
            item["tile"] for item in details
            if item["confidence"] >= minimum
        )

    def _confident_bonus_indices(self, details):
        minimum = self.config.get("min_confidence", 0.25)
        return [
            item["index"] for item in details
            if (
                item["confidence"] >= minimum
                and str(item["tile"]).startswith("bonus-")
            )
        ]

    def _count_state(self, hand):
        hand_count = len(hand)
        actionable = set(self.config.get("actionable_tile_counts", [self.config.get("tile_count", 14)]))
        waiting = set(self.config.get("waiting_tile_counts", []))

        if hand_count in actionable:
            return "action"
        if hand_count in waiting:
            return "wait"
        return "skip"

    def step(self, frame=None):
        self._refresh_parser_region()
        if frame is None and self.config.get("focus_window", True):
            if not self._focus_and_wait():
                return {
                    "action": "skip",
                    "reason": "target window is not foreground",
                    "details": [],
                    "low_confidence_count": None,
                }
        frame = frame if frame is not None else capture_screen()
        scene = self._scene_state(frame)
        template_prompt_result = self._handle_template_action_prompt(scene)
        if template_prompt_result is not None:
            return template_prompt_result
        prompt_result = self._handle_action_prompt(frame)
        if prompt_result is not None:
            prompt_result.update(scene)
            return prompt_result

        raw_hand, details = self.parser.parse_with_details(frame)
        hand = self._confident_hand(details)
        if self.debug_dir:
            self.parser.save_debug_tiles(frame, self.debug_dir)

        if not hand:
            bonus_indices = self._confident_bonus_indices(details)
            if not bonus_indices:
                return {
                    "action": "skip",
                    "reason": "no tiles recognized",
                    "raw_hand": raw_hand,
                    "details": details,
                    **scene,
                }

        bonus_indices = self._confident_bonus_indices(details)
        if self.config.get("auto_click_bonus", True) and bonus_indices:
            tile_index = bonus_indices[0]
            if not self._is_stable_action(("bonus", tile_index)):
                return {
                    "action": "wait",
                    "reason": "waiting for stable bonus tile",
                    "hand": hand,
                    "raw_hand": raw_hand,
                    "details": details,
                    "tile_index": tile_index,
                    "stable_count": self.action_stable_count,
                    "low_confidence_count": len(self._confidence_failures(details)),
                    **scene,
                }

            if not self._cooldown_ready():
                return {
                    "action": "wait",
                    "reason": "click cooldown",
                    "hand": hand,
                    "raw_hand": raw_hand,
                    "details": details,
                    "low_confidence_count": len(self._confidence_failures(details)),
                    **scene,
                }

            x, y = self._tile_center(tile_index)
            result = {
                "action": "bonus_dry_run" if self.dry_run else "bonus_click",
                "reason": "bonus tile recognized",
                "hand": hand,
                "raw_hand": raw_hand,
                "details": details,
                "tile_index": tile_index,
                "click": {"x": x, "y": y},
                "low_confidence_count": len(self._confidence_failures(details)),
                **scene,
            }
            if not self.dry_run:
                self._click_tile(x, y)
                self.last_click_at = time.time()
            return result

        count_state = self._count_state(hand)
        if count_state == "wait":
            if self.config.get("auto_pass", False) and self._cooldown_ready():
                if not self._is_stable_action(("pass", tuple(hand))):
                    return {
                        "action": "wait",
                        "reason": "waiting for stable pass prompt",
                        "hand": hand,
                        "raw_hand": raw_hand,
                        "details": details,
                        "stable_count": self.action_stable_count,
                        "low_confidence_count": len(self._confidence_failures(details)),
                        **scene,
                    }

                click = None
                if not self.dry_run:
                    click = self._click_action("pass")
                    if click is None:
                        return {
                            "action": "skip",
                            "reason": "pass region is not configured or target window is not foreground",
                            "hand": hand,
                            "raw_hand": raw_hand,
                            "details": details,
                            "low_confidence_count": len(self._confidence_failures(details)),
                            **scene,
                        }
                    self.last_click_at = time.time()

                return {
                    "action": "pass_dry_run" if self.dry_run else "pass_click",
                    "reason": "recognized waiting hand; clicking pass",
                    "hand": hand,
                    "raw_hand": raw_hand,
                    "details": details,
                    "click": click or {"region": "pass"},
                    "low_confidence_count": len(self._confidence_failures(details)),
                    **scene,
                }

            return {
                "action": "wait",
                "reason": f"recognized {len(hand)} tiles; waiting for draw",
                "hand": hand,
                "raw_hand": raw_hand,
                "details": details,
                "low_confidence_count": len(self._confidence_failures(details)),
                **scene,
            }
        if count_state == "skip":
            return {
                "action": "skip",
                "reason": f"recognized unexpected tile count: {len(hand)}",
                "hand": hand,
                "raw_hand": raw_hand,
                "details": details,
                "low_confidence_count": len(self._confidence_failures(details)),
                **scene,
            }

        low_confidence = self._confidence_failures(details)
        max_low_confidence = self.config.get("max_low_confidence_tiles", 0)
        if low_confidence and not self.dry_run and len(low_confidence) > max_low_confidence:
            return {
                "action": "skip",
                "reason": f"{len(low_confidence)} tile recognitions below confidence threshold",
                "hand": hand,
                "raw_hand": raw_hand,
                "details": details,
                "low_confidence_count": len(low_confidence),
                **scene,
            }

        if not self._is_stable_hand(hand):
            return {
                "action": "wait",
                "reason": "waiting for stable hand",
                "hand": hand,
                "stable_count": self.stable_count,
                "details": details,
                **scene,
            }

        if not self._cooldown_ready():
            return {
                "action": "wait",
                "reason": "click cooldown",
                "hand": hand,
                "details": details,
                **scene,
            }

        decision = decide(hand, visible_tiles=hand + scene.get("visible_tiles", []))
        discard = decision["discard"]
        tile_index = self._select_tile_index(hand, discard)

        if discard is None or tile_index is None:
            return {
                "action": "skip",
                "reason": "AI did not select a clickable tile",
                "hand": hand,
                "details": details,
                "decision": decision,
                **scene,
            }

        x, y = self._tile_center(tile_index)
        result = {
            "action": "dry_run" if self.dry_run else "click",
            "hand": hand,
            "details": details,
            "decision": decision,
            "discard": discard,
            "tile_index": tile_index,
            "click": {"x": x, "y": y},
            "confirm_click": None,
            "low_confidence_count": len(low_confidence),
            **scene,
        }

        if not self.dry_run:
            clicked = self._click_tile(x, y)
            if not clicked:
                result["action"] = "skip"
                result["reason"] = "target window is not foreground"
                return result
            result["confirm_click"] = self._click_discard_confirm()
            self.last_click_at = time.time()

        return result

    def run(self, iterations=None, image_path=None, startup_delay=0.0):
        count = 0
        delay = self.config.get("delay", 1.0)
        image = cv2.imread(image_path) if image_path else None
        if image_path and image is None:
            raise RuntimeError(f"Could not read image: {image_path}")

        if image is None and self.config.get("focus_window", True):
            self.focus_target_window()

        if startup_delay > 0:
            print(f"Starting auto-play capture in {startup_delay:.1f}s...")
            time.sleep(startup_delay)

        while iterations is None or count < iterations:
            result = self.step(frame=image)
            hand_text = ",".join(result.get("hand") or [])
            print(
                f"{result['action']}: discard={result.get('discard')} "
                f"index={result.get('tile_index')} click={result.get('click')} "
                f"confirm={result.get('confirm_click')} "
                f"low_conf={result.get('low_confidence_count')} "
                f"reason={result.get('reason')} hand=[{hand_text}]",
                flush=True,
            )
            count += 1
            time.sleep(delay)
