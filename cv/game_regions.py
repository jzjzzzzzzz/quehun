import json
from pathlib import Path

import cv2

from cv.template_classifier import TemplateTileClassifier


DEFAULT_REGIONS_PATH = "config/screen_regions.json"


def load_regions(path=DEFAULT_REGIONS_PATH):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def save_regions(config, path=DEFAULT_REGIONS_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)
    return str(path)


def update_region(name, region, frame_size, path=DEFAULT_REGIONS_PATH):
    config = load_regions(path)
    reference = config["reference_size"]
    frame_width, frame_height = frame_size
    scale_x = reference["width"] / max(1, frame_width)
    scale_y = reference["height"] / max(1, frame_height)
    current = dict(config["regions"].get(name, {}))
    current.update({
        "left": int(round(region["left"] * scale_x)),
        "top": int(round(region["top"] * scale_y)),
        "width": int(round(region["width"] * scale_x)),
        "height": int(round(region["height"] * scale_y)),
    })
    config["regions"][name] = current
    save_regions(config, path)
    return current


def scaled_region(region, frame_shape, reference_size):
    frame_height, frame_width = frame_shape[:2]
    scale_x = frame_width / max(1, reference_size["width"])
    scale_y = frame_height / max(1, reference_size["height"])
    result = dict(region)
    for key, scale in (
        ("left", scale_x),
        ("width", scale_x),
        ("top", scale_y),
        ("height", scale_y),
    ):
        result[key] = int(round(float(region.get(key, 0)) * scale))
    return result


def crop_region(frame, region):
    height, width = frame.shape[:2]
    left = max(0, int(region["left"]))
    top = max(0, int(region["top"]))
    right = min(width, left + max(0, int(region["width"])))
    bottom = min(height, top + max(0, int(region["height"])))
    return frame[top:bottom, left:right]


class TileGridParser:
    def __init__(self, classifier=None, min_confidence=0.55, min_occupancy=0.30):
        self.classifier = classifier or TemplateTileClassifier()
        self.min_confidence = float(min_confidence)
        self.min_occupancy = float(min_occupancy)

    def parse(self, frame, region):
        crop = crop_region(frame, region)
        if crop.size == 0:
            return [], []
        rows = max(1, int(region.get("rows", 1)))
        columns = max(1, int(region.get("columns", 1)))
        rotation = int(region.get("rotation", 0)) % 360
        height, width = crop.shape[:2]
        details = []

        for row in range(rows):
            for column in range(columns):
                x1 = int(round(column * width / columns))
                x2 = int(round((column + 1) * width / columns))
                y1 = int(round(row * height / rows))
                y2 = int(round((row + 1) * height / rows))
                tile_image = crop[y1:y2, x1:x2]
                if tile_image.size == 0:
                    continue
                if rotation == 90:
                    tile_image = cv2.rotate(tile_image, cv2.ROTATE_90_CLOCKWISE)
                elif rotation == 180:
                    tile_image = cv2.rotate(tile_image, cv2.ROTATE_180)
                elif rotation == 270:
                    tile_image = cv2.rotate(tile_image, cv2.ROTATE_90_COUNTERCLOCKWISE)

                tile_image, tile_area_ratio = self._tight_tile_crop(tile_image)
                gray = cv2.cvtColor(tile_image, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                occupancy = min(
                    1.0,
                    tile_area_ratio * 1.5
                    + float((gray > 90).mean()) * 0.25
                    + float((edges > 0).mean()) * 1.2,
                )
                classified = self.classifier.classify(tile_image)
                confidence = classified["confidence"] * occupancy
                details.append({
                    "row": row,
                    "column": column,
                    "tile": classified["tile"],
                    "confidence": confidence,
                    "occupancy": occupancy,
                    "box": (x1, y1, x2 - x1, y2 - y1),
                })

        tiles = [
            item["tile"] for item in details
            if (
                item["confidence"] >= self.min_confidence
                and item["occupancy"] >= self.min_occupancy
            )
        ]
        return tiles, details

    @staticmethod
    def _tight_tile_crop(image):
        original_height, original_width = image.shape[:2]
        if original_height <= 0 or original_width <= 0:
            return image, 0.0
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 0, 105), (179, 150, 255))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return image, 0.0
        contour = max(contours, key=cv2.contourArea)
        x, y, width, height = cv2.boundingRect(contour)
        area_ratio = (width * height) / max(1, original_width * original_height)
        if area_ratio < 0.12 or width < 8 or height < 10:
            return image, area_ratio
        padding_x = max(1, int(width * 0.04))
        padding_y = max(1, int(height * 0.04))
        x1 = max(0, x - padding_x)
        y1 = max(0, y - padding_y)
        x2 = min(original_width, x + width + padding_x)
        y2 = min(original_height, y + height + padding_y)
        return image[y1:y2, x1:x2], area_ratio


class GameRegionRecognizer:
    def __init__(self, regions_path=DEFAULT_REGIONS_PATH, classifier=None):
        self.regions_path = Path(regions_path)
        self.config = load_regions(self.regions_path)
        self.parser = TileGridParser(classifier=classifier)

    def regions_for_frame(self, frame):
        reference = self.config["reference_size"]
        return {
            name: scaled_region(region, frame.shape, reference)
            for name, region in self.config["regions"].items()
        }

    def recognize(self, frame, ocr=None):
        regions = self.regions_for_frame(frame)
        discards = {}
        raw = {}
        for player in ("self", "right", "opposite", "left"):
            name = f"discards_{player}"
            tiles, details = self.parser.parse(frame, regions[name])
            discards[player] = tiles
            raw[name] = details

        dora, dora_details = self.parser.parse(frame, regions["dora_indicators"])
        raw["dora_indicators"] = dora_details
        round_text = ""
        if ocr is not None:
            round_text = ocr.read(crop_region(frame, regions["round_text"]))
        round_wind = self._wind_from_text(round_text)
        return {
            "discards": discards,
            "dora_indicators": dora,
            "round_wind": round_wind,
            "round_text": round_text,
            "regions": regions,
            "raw": raw,
        }

    @staticmethod
    def _wind_from_text(text):
        normalized = (text or "").lower()
        for word, wind in (
            ("东", "east"), ("東", "east"), ("east", "east"),
            ("南", "south"), ("south", "south"),
            ("西", "west"), ("west", "west"),
            ("北", "north"), ("north", "north"),
        ):
            if word in normalized:
                return wind
        return None
