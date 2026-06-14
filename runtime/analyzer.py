import time
from collections import Counter

from ai.advisor import analyze_hand
from ai.tile_set import canonical_hand
from capture.screen import ScreenCapture
from capture.windows_api import find_window, foreground_window
from cv.real_hand_parser import RealHandParser
from cv.game_regions import GameRegionRecognizer
from cv.action_buttons import ActionButtonDetector
from cv.screen_state import QueHunScreenStateDetector, ScreenState
from runtime.clicker import WindowsClicker
from runtime.config import load_config
from state.game_state import GameState
from state.tracker import StateTracker


class AnalysisController:
    """Read the game window, recognize the hand, advise, and optionally discard."""

    def __init__(
        self,
        config_path=None,
        auto_click=False,
        clicker=None,
        screen_capture=None,
        state_detector=None,
    ):
        self.config = load_config(config_path) if config_path else load_config()
        analysis_config = self.config.get("analysis", {})
        self.auto_click = bool(auto_click)
        self.clicker = clicker or WindowsClicker()
        self.capture = screen_capture or ScreenCapture(
            debug=analysis_config.get("debug", False),
            debug_dir=analysis_config.get("debug_dir", "debug/screenshots"),
            max_debug_files=analysis_config.get("max_debug_screenshots", 50),
        )
        self.state_detector = state_detector or QueHunScreenStateDetector()
        self.game_state = GameState()
        self.tracker = StateTracker(self.config.get("stable_frames", 2))
        self.last_click_at = 0.0
        self.last_clicked_hand = None
        self.previous_hand = []
        self.previous_confidence = 0.0
        self.previous_self_discard_count = 0
        self.parser = RealHandParser(
            hand_region=self._frame_hand_region(None),
            tile_count=self.config.get("tile_slots", self.config.get("tile_count", 14)),
        )
        self.region_recognizer = GameRegionRecognizer(
            classifier=self.parser.classifier
        )
        self.action_detector = ActionButtonDetector()
        self.last_action_signature = None
        self.action_stable_count = 0

    def set_debug(self, enabled):
        self.capture.set_debug(enabled)
        self.config.setdefault("analysis", {})["debug"] = bool(enabled)

    def _window_title_candidates(self):
        candidates = [self.config.get("window_title")]
        candidates.extend(self.config.get("window_title_fallbacks", []))
        candidates.extend(["雀魂", "雀魂麻将", "雀魂麻將", "MahjongSoul", "Mahjong Soul"])
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))

    def target_window(self):
        exact = bool(self.config.get("window_title_exact", False))
        for title in self._window_title_candidates():
            window = find_window(title, exact=exact)
            if (
                window
                and window.get("width", 0) >= 500
                and window.get("height", 0) >= 400
                and window.get("left", -32000) > -30000
                and window.get("top", -32000) > -30000
            ):
                return window
        return None

    @staticmethod
    def _window_region(window):
        return {
            "left": window["left"],
            "top": window["top"],
            "width": window["width"],
            "height": window["height"],
        }

    def _frame_hand_region(self, window):
        region = self.config["hand_region"].copy()
        if self.config.get("region_mode") == "window":
            reference = self.config.get("hand_reference_size", {})
            if window and reference:
                scale_x = window["width"] / max(1, reference.get("width", window["width"]))
                scale_y = window["height"] / max(1, reference.get("height", window["height"]))
                region["left"] = int(round(region["left"] * scale_x))
                region["top"] = int(round(region["top"] * scale_y))
                region["width"] = int(round(region["width"] * scale_x))
                region["height"] = int(round(region["height"] * scale_y))
            return region
        if window:
            region["left"] -= window["left"]
            region["top"] -= window["top"]
        return region

    def _absolute_tile_center(self, window, tile_index):
        region = self._frame_hand_region(window)
        tile_count = self.config.get("tile_slots", self.config.get("tile_count", 14))
        x = window["left"] + region["left"] + region["width"] * (tile_index + 0.5) / tile_count
        y_ratio = self.config.get("click", {}).get("y_offset_ratio", 0.5)
        y = window["top"] + region["top"] + region["height"] * y_ratio
        return int(round(x)), int(round(y))

    def _recognized_hand(self, details):
        minimum = float(self.config.get("min_confidence", 0.25))
        return canonical_hand(
            item["tile"] for item in details
            if item.get("confidence", 0.0) >= minimum
        )

    @staticmethod
    def _overall_confidence(details):
        if not details:
            return 0.0
        values = sorted(float(item.get("confidence", 0.0)) for item in details)
        if len(values) > 2:
            values = values[1:-1]
        return max(0.0, min(1.0, sum(values) / max(1, len(values))))

    @staticmethod
    def _foreground_matches(window):
        current = foreground_window()
        return bool(current and current.get("hwnd") == window.get("hwnd"))

    def _click_allowed(self, window, state_result, hand, confidence, stable):
        click_config = self.config.get("click", {})
        if not self.auto_click:
            return False, "automatic clicking disabled"
        if click_config.get("require_in_game", True) and state_result.state != ScreenState.IN_GAME:
            return False, "screen is not confidently in-game"
        if click_config.get("require_foreground", True) and not self._foreground_matches(window):
            return False, "target window is not foreground"
        if confidence < float(click_config.get("min_confidence", 0.82)):
            return False, "recognition confidence below click threshold"
        if len(hand) != 14:
            return False, "hand does not contain 14 recognized tiles"
        if not stable:
            return False, "waiting for stable hand"
        if tuple(hand) == self.last_clicked_hand:
            return False, "this hand was already clicked"
        cooldown = float(self.config.get("click_cooldown", 1.2))
        if time.time() - self.last_click_at < cooldown:
            return False, "click cooldown"
        return True, "all click safety checks passed"

    def _stable_action(self, action):
        signature = action["action"]
        if signature == self.last_action_signature:
            self.action_stable_count += 1
        else:
            self.last_action_signature = signature
            self.action_stable_count = 1
        required = int(
            self.config.get("action_policy", {}).get("stable_frames", 2)
        )
        return self.action_stable_count >= max(1, required)

    def _maybe_click_action(self, window, state_result, actions):
        policy = self.config.get("action_policy", {})
        if not self.auto_click or not policy.get("enabled", False):
            return None, "automatic action responses disabled"
        if state_result.state != ScreenState.IN_GAME:
            return None, "screen is not confidently in-game"
        if self.config.get("click", {}).get("require_foreground", True):
            if not self._foreground_matches(window):
                return None, "target window is not foreground"
        allowed = set(policy.get("allowed_actions", ["pass"]))
        minimum = float(policy.get("min_confidence", 0.80))
        candidate = next(
            (
                action for action in actions
                if action["action"] in allowed and action["confidence"] >= minimum
            ),
            None,
        )
        if candidate is None:
            return None, "no allowed action button detected"
        if not self._stable_action(candidate):
            return None, "waiting for stable action button"
        cooldown = float(self.config.get("click_cooldown", 1.2))
        if time.time() - self.last_click_at < cooldown:
            return None, "click cooldown"
        x = window["left"] + candidate["center"]["x"]
        y = window["top"] + candidate["center"]["y"]
        self.clicker.click(x, y)
        self.last_click_at = time.time()
        return {
            "x": x,
            "y": y,
            "action": candidate["action"],
            "confidence": candidate["confidence"],
        }, "allowed action clicked"

    def step(self, frame=None, window=None):
        window = window or self.target_window()
        if window is None and frame is None:
            return self._warning("window_not_found", "未找到雀魂窗口，等待下一帧")

        if frame is None:
            frame = self.capture.grab(self._window_region(window), label="window")
        elif self.capture.debug:
            self.capture.save_debug(frame, label="provided")

        hand_region = self._frame_hand_region(window)
        self.parser.hand_region = hand_region
        self.parser.tile_count = self.config.get("tile_slots", self.config.get("tile_count", 14))
        state_result = self.state_detector.detect(frame, hand_region=hand_region)
        raw_hand, details = self.parser.parse_with_details(frame)
        region_state = self.region_recognizer.recognize(
            frame,
            ocr=getattr(self.state_detector, "ocr", None),
        )
        visible_actions = self.action_detector.detect(
            frame,
            region_state["regions"]["actions"],
        )
        if self.capture.debug:
            tile_debug_dir = self.config.get("analysis", {}).get(
                "tile_debug_dir",
                "debug/tiles/latest",
            )
            self.parser.save_debug_tiles(frame, tile_debug_dir)
        hand = self._recognized_hand(details)
        confidence = self._overall_confidence(details)
        stable = self.tracker.is_stable(hand) if hand else False
        learned_discard_template = self._learn_discard_transition(
            hand,
            confidence,
            region_state,
        )

        self.game_state.update(
            hand,
            visible_tiles=(
                hand
                + region_state["dora_indicators"]
                + [
                    tile
                    for player_discards in region_state["discards"].values()
                    for tile in player_discards
                ]
            ),
            confidence=confidence,
            drawn_tile=hand[-1] if len(hand) == 14 else None,
            discards=region_state["discards"],
            dora_indicators=region_state["dora_indicators"],
            round_wind=region_state["round_wind"],
            seat_wind=region_state["seat_wind"],
            turn_info="discard" if len(hand) == 14 else "waiting",
            raw_debug_info={
                "screen_state": state_result.state.value,
                "screen_confidence": state_result.confidence,
                "ocr_text": state_result.text,
                "screen_reasons": state_result.reasons,
                "tile_details": details,
                "region_details": region_state["raw"],
                "round_text": region_state["round_text"],
                "round_confidence": region_state["round_confidence"],
                "seat_confidence": region_state["seat_confidence"],
                "visible_actions": visible_actions,
                "learned_discard_template": learned_discard_template,
                "stable": stable,
            },
        )

        advice = analyze_hand(
            hand,
            visible_tiles=self.game_state.get_visible_tiles(),
            discards=self.game_state.discards,
            recognition_confidence=confidence,
            seat_wind=self.game_state.seat_wind,
            round_wind=self.game_state.round_wind,
        )
        action = "analyzed"
        click = None
        click_reason = "no discard recommendation"
        action_click, action_click_reason = self._maybe_click_action(
            window,
            state_result,
            visible_actions,
        )
        if action_click is not None:
            click = action_click
            click_reason = action_click_reason
            action = "action_clicked"
        if advice.recommended_discard:
            allowed, click_reason = self._click_allowed(
                window,
                state_result,
                hand,
                confidence,
                stable,
            )
            if allowed and click is None:
                tile_index = hand.index(advice.recommended_discard)
                x, y = self._absolute_tile_center(window, tile_index)
                self.clicker.click(x, y)
                self.last_click_at = time.time()
                self.last_clicked_hand = tuple(hand)
                click = {"x": x, "y": y, "tile_index": tile_index}
                action = "clicked"

        warning = None
        if state_result.state == ScreenState.UNKNOWN:
            warning = "未知页面状态，将继续等待和识别"
        elif not hand:
            warning = "未识别到手牌，将继续下一帧"
        elif len(hand) not in (13, 14):
            warning = f"手牌数量异常：{len(hand)}"

        return {
            "status": "Analyzing" if hand else "Error Recovering",
            "action": action,
            "warning": warning,
            "window": window,
            "frame": frame,
            "screen_state": state_result.state.value,
            "screen_confidence": state_result.confidence,
            "ocr_text": state_result.text,
            "game_state": self.game_state.to_dict(),
            "hand": hand,
            "raw_hand": raw_hand,
            "details": details,
            "confidence": confidence,
            "stable": stable,
            "advice": advice.to_dict(),
            "discard": advice.recommended_discard,
            "click": click,
            "click_reason": click_reason,
            "visible_actions": visible_actions,
            "learned_discard_template": learned_discard_template,
        }

    def _learn_discard_transition(self, hand, confidence, region_state):
        self_count = len(
            self.region_recognizer.last_discard_crops.get("self") or []
        )
        learned = None
        if (
            len(self.previous_hand) == 14
            and len(hand) == 13
            and self.previous_confidence >= 0.75
            and confidence >= 0.75
            and self_count > self.previous_self_discard_count
        ):
            removed = list((Counter(self.previous_hand) - Counter(hand)).elements())
            if len(removed) == 1:
                learned = self.region_recognizer.learn_self_discard(removed[0])
        if hand:
            self.previous_hand = list(hand)
            self.previous_confidence = confidence
        self.previous_self_discard_count = self_count
        return learned

    @staticmethod
    def _warning(code, message):
        return {
            "status": "Error Recovering",
            "action": "wait",
            "warning": message,
            "error_code": code,
            "frame": None,
            "screen_state": ScreenState.UNKNOWN.value,
            "screen_confidence": 0.0,
            "ocr_text": "",
            "hand": [],
            "confidence": 0.0,
            "stable": False,
            "advice": {
                "recommended_discard": None,
                "top_choices": [],
                "yaku_tendencies": [],
                "confidence": 0.0,
                "warnings": [message],
            },
            "discard": None,
            "click": None,
            "click_reason": message,
        }
