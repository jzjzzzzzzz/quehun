import json
from pathlib import Path
from collections import defaultdict

import cv2
import numpy as np

from ai.tile_set import canonical_tile
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


class PerspectiveTileClassifier:
    """Nearest-template classifier for automatically learned river tiles."""

    def __init__(self, templates_dir="templates/discards", size=(64, 64)):
        self.templates_dir = Path(templates_dir)
        self.size = size
        self.prototypes = {}
        self.reload()

    def _preprocess(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, self.size, interpolation=cv2.INTER_AREA)
        return cv2.equalizeHist(resized).astype(np.float32) / 255.0

    def reload(self):
        grouped = defaultdict(list)
        if self.templates_dir.is_dir():
            for label_dir in self.templates_dir.iterdir():
                label = canonical_tile(label_dir.name)
                if not label or not label_dir.is_dir():
                    continue
                for path in label_dir.iterdir():
                    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp"}:
                        continue
                    image = cv2.imread(str(path))
                    if image is not None:
                        grouped[label].append(self._preprocess(image))
        self.prototypes = dict(grouped)

    def classify(self, image):
        if not self.prototypes:
            return {"tile": None, "confidence": 0.0, "error": None}
        sample = self._preprocess(image)
        ranked = []
        for label, prototypes in self.prototypes.items():
            error = min(float(np.mean((sample - prototype) ** 2)) for prototype in prototypes)
            ranked.append((error, label))
        ranked.sort()
        best_error, best_label = ranked[0]
        second_error = ranked[1][0] if len(ranked) > 1 else best_error + 0.1
        margin = max(0.0, second_error - best_error)
        confidence = min(1.0, max(0.0, 1.0 - best_error * 6.0 + margin * 3.0))
        return {"tile": best_label, "confidence": confidence, "error": best_error}

    def learn(self, label, image):
        label = canonical_tile(label)
        if label is None or image is None or image.size == 0:
            return None
        directory = self.templates_dir / label
        directory.mkdir(parents=True, exist_ok=True)
        existing = sorted(directory.glob("*.png"))
        path = directory / f"{len(existing) + 1:04d}.png"
        if not cv2.imwrite(str(path), image):
            return None
        self.reload()
        return str(path)


class ContourTileParser:
    def __init__(self, classifier=None, min_confidence=0.65):
        self.classifier = classifier or PerspectiveTileClassifier()
        self.min_confidence = float(min_confidence)
        self.last_crops = []

    def parse(self, frame, region):
        crop = crop_region(frame, region)
        rotation = int(region.get("rotation", 0)) % 360
        if crop.size == 0:
            self.last_crops = []
            return [], []
        if rotation == 90:
            crop = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            crop = cv2.rotate(crop, cv2.ROTATE_180)
        elif rotation == 270:
            crop = cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 0, 130), (179, 90, 255))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        crop_area = crop.shape[0] * crop.shape[1]
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = width * height
            aspect = width / max(1, height)
            if area < crop_area * 0.025 or not 0.45 <= aspect <= 1.25:
                continue
            boxes.append((x, y, width, height))
        row_height = max(1, int(np.median([box[3] for box in boxes]))) if boxes else 1
        boxes.sort(key=lambda box: (round(box[1] / row_height), box[0]))

        details = []
        self.last_crops = []
        for index, (x, y, width, height) in enumerate(boxes):
            tile_image = crop[y:y + height, x:x + width]
            self.last_crops.append(tile_image.copy())
            classified = self.classifier.classify(tile_image)
            details.append({
                "index": index,
                "tile": classified["tile"],
                "confidence": classified["confidence"],
                "error": classified["error"],
                "box": (x, y, width, height),
            })
        tiles = [
            item["tile"] for item in details
            if item["tile"] and item["confidence"] >= self.min_confidence
        ]
        return tiles, details


class GameRegionRecognizer:
    def __init__(self, regions_path=DEFAULT_REGIONS_PATH, classifier=None):
        self.regions_path = Path(regions_path)
        self.config = load_regions(self.regions_path)
        self.parser = TileGridParser(classifier=classifier)
        self.discard_parser = ContourTileParser()
        self.dora_parser = ContourTileParser(
            classifier=self.discard_parser.classifier
        )
        self.last_discard_crops = {}
        self.round_templates = self._load_round_templates()
        self.seat_templates = self._load_wind_templates("templates/seat")

    @staticmethod
    def _load_round_templates(directory="templates/round"):
        return GameRegionRecognizer._load_wind_templates(directory)

    @staticmethod
    def _load_wind_templates(directory):
        templates = {}
        path = Path(directory)
        if not path.is_dir():
            return templates
        for image_path in path.iterdir():
            if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp"}:
                continue
            image = cv2.imread(str(image_path))
            if image is not None:
                templates[image_path.stem.lower()] = image
        return templates

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
            tiles, details = self.discard_parser.parse(frame, regions[name])
            discards[player] = tiles
            raw[name] = details
            self.last_discard_crops[player] = [
                image.copy() for image in self.discard_parser.last_crops
            ]

        dora, dora_details = self.dora_parser.parse(
            frame,
            regions["dora_indicators"],
        )
        raw["dora_indicators"] = dora_details
        round_text = ""
        if ocr is not None:
            round_text = ocr.read(crop_region(frame, regions["round_text"]))
        round_wind = self._wind_from_text(round_text)
        round_confidence = 0.0
        if round_wind is None:
            round_wind, round_confidence = self._round_from_templates(
                frame,
                regions["round_text"],
                self.round_templates,
            )
        seat_wind, seat_confidence = self._round_from_templates(
            frame,
            regions["seat_wind"],
            self.seat_templates,
        )
        return {
            "discards": discards,
            "dora_indicators": dora,
            "round_wind": round_wind,
            "round_text": round_text,
            "round_confidence": round_confidence,
            "seat_wind": seat_wind,
            "seat_confidence": seat_confidence,
            "regions": regions,
            "raw": raw,
        }

    def learn_self_discard(self, tile):
        crops = self.last_discard_crops.get("self") or []
        if not crops:
            return None
        return self.discard_parser.classifier.learn(tile, crops[-1])

    def _round_from_templates(self, frame, region, templates):
        crop = crop_region(frame, region)
        if crop.size == 0:
            return None, 0.0
        crop_edges = cv2.Canny(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 60, 160)
        best_wind = None
        best_score = 0.0
        for wind, template in templates.items():
            scale_x = frame.shape[1] / self.config["reference_size"]["width"]
            scale_y = frame.shape[0] / self.config["reference_size"]["height"]
            width = max(8, int(round(template.shape[1] * scale_x)))
            height = max(8, int(round(template.shape[0] * scale_y)))
            if width > crop.shape[1] or height > crop.shape[0]:
                continue
            scaled = cv2.resize(template, (width, height), interpolation=cv2.INTER_AREA)
            edges = cv2.Canny(cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY), 60, 160)
            result = cv2.matchTemplate(crop_edges, edges, cv2.TM_CCOEFF_NORMED)
            _, score, _, _ = cv2.minMaxLoc(result)
            if score > best_score:
                best_wind = wind
                best_score = float(score)
        if best_score < 0.72:
            return None, best_score
        return best_wind, best_score

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
