from pathlib import Path

import cv2

from cv.game_regions import crop_region


class ActionButtonDetector:
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

    def detect(self, frame, action_region, reference_size=(1920, 1080)):
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
        return sorted(detected, key=lambda item: item["confidence"], reverse=True)

    @staticmethod
    def _edges(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.Canny(gray, 60, 160)
