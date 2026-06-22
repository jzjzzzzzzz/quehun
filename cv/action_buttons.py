from pathlib import Path

import cv2

from cv.game_regions import crop_region


class ActionButtonDetector:
    ACTION_WORDS = {
        "riichi": ("立直", "riichi", "reach"),
        "ron": ("荣和", "榮和", "ron"),
        "tsumo": ("自摸", "tsumo"),
        "kan": ("杠", "槓", "kan", "kong"),
        "pon": ("碰", "pon", "pong"),
        "chi": ("吃", "chi", "chii"),
        "pass": ("跳过", "跳過", "取消", "pass", "skip", "cancel"),
    }

    def __init__(self, templates_dir="templates/actions", threshold=0.72):
        self.templates_dir = Path(templates_dir)
        self.threshold = float(threshold)
        self.templates = self._load_templates()

    def _load_templates(self):
        templates = {}
        if not self.templates_dir.is_dir():
            return templates
        for path in self.templates_dir.iterdir():
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp"}:
                continue
            image = cv2.imread(str(path))
            if image is not None:
                templates[path.stem.lower()] = image
        return templates

    def detect(self, frame, action_region, reference_size=(1920, 1080), ocr=None):
        crop = crop_region(frame, action_region)
        if crop.size == 0:
            return []
        scale_x = frame.shape[1] / max(1, reference_size[0])
        scale_y = frame.shape[0] / max(1, reference_size[1])
        crop_edges = self._edges(crop)
        detected = []

        for action, template in self.templates.items():
            width = max(8, int(round(template.shape[1] * scale_x)))
            height = max(8, int(round(template.shape[0] * scale_y)))
            if width > crop.shape[1] or height > crop.shape[0]:
                continue
            scaled = cv2.resize(template, (width, height), interpolation=cv2.INTER_AREA)
            result = cv2.matchTemplate(
                crop_edges,
                self._edges(scaled),
                cv2.TM_CCOEFF_NORMED,
            )
            _, score, _, location = cv2.minMaxLoc(result)
            if score < self.threshold:
                continue
            left = action_region["left"] + location[0]
            top = action_region["top"] + location[1]
            detected.append({
                "action": action,
                "confidence": float(score),
                "source": "template",
                "region": {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                },
                "center": {
                    "x": left + width // 2,
                    "y": top + height // 2,
                },
            })
        detected.extend(
            self._detect_text_actions(crop, action_region, ocr)
        )
        return self._dedupe_actions(detected)

    def _detect_text_actions(self, crop, action_region, ocr):
        if ocr is None:
            return []
        text = ""
        try:
            text = ocr.read(crop)
        except Exception:
            text = ""
        normalized = " ".join((text or "").lower().split())
        if not normalized:
            return []

        found = []
        actions = [
            action
            for action, words in self.ACTION_WORDS.items()
            if any(word.lower() in normalized for word in words)
        ]
        if not actions:
            return []

        slot_width = max(1, action_region["width"] / len(actions))
        for index, action in enumerate(actions):
            left = int(round(action_region["left"] + slot_width * index))
            width = int(round(slot_width))
            found.append({
                "action": action,
                "confidence": 0.74,
                "source": "ocr",
                "text": text,
                "region": {
                    "left": left,
                    "top": action_region["top"],
                    "width": width,
                    "height": action_region["height"],
                },
                "center": {
                    "x": int(round(left + width / 2)),
                    "y": int(round(action_region["top"] + action_region["height"] / 2)),
                },
            })
        return found

    @staticmethod
    def _dedupe_actions(actions):
        best_by_action = {}
        for item in actions:
            current = best_by_action.get(item["action"])
            if current is None or item["confidence"] > current["confidence"]:
                best_by_action[item["action"]] = item
        return sorted(
            best_by_action.values(),
            key=lambda item: item["confidence"],
            reverse=True,
        )

    @staticmethod
    def _edges(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.Canny(gray, 60, 160)
