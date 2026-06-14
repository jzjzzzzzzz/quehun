import cv2

from ai.tile_set import canonical_hand
from cv.template_classifier import TemplateTileClassifier


class RealHandParser:
    def __init__(self, hand_region, tile_count=14, classifier=None):
        self.hand_region = hand_region
        self.tile_count = tile_count
        self.classifier = classifier or TemplateTileClassifier()

    def crop_hand(self, frame):
        frame_height, frame_width = frame.shape[:2]
        left = max(0, int(self.hand_region["left"]))
        top = max(0, int(self.hand_region["top"]))
        right = min(frame_width, left + int(self.hand_region["width"]))
        bottom = min(frame_height, top + int(self.hand_region["height"]))
        return frame[top:bottom, left:right]

    def split_tiles(self, hand_image):
        height, width = hand_image.shape[:2]
        tile_width = width / self.tile_count
        tiles = []

        for idx in range(self.tile_count):
            x1 = int(round(idx * tile_width))
            x2 = int(round((idx + 1) * tile_width))
            tile = hand_image[0:height, x1:x2]
            if tile.size:
                tiles.append((idx, tile))

        return tiles

    def detect_tile_boxes(self, hand_image):
        """Return calibrated slot boxes with a lightweight occupancy score."""
        boxes = []
        height, width = hand_image.shape[:2]
        if height <= 0 or width <= 0:
            return boxes
        tile_width = width / self.tile_count
        for idx in range(self.tile_count):
            x1 = int(round(idx * tile_width))
            x2 = int(round((idx + 1) * tile_width))
            tile = hand_image[:, x1:x2]
            if tile.size == 0:
                continue
            gray = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            occupancy = min(
                1.0,
                float((gray > 80).mean()) * 0.6 + float((edges > 0).mean()) * 2.5,
            )
            boxes.append({
                "index": idx,
                "box": (x1, 0, x2 - x1, height),
                "occupancy": occupancy,
                "image": tile,
            })
        return boxes

    def parse_with_details(self, frame):
        hand_image = self.crop_hand(frame)
        results = []

        for box in self.detect_tile_boxes(hand_image):
            idx = box["index"]
            tile_image = box["image"]
            classified = self.classifier.classify(tile_image)
            results.append({
                "index": idx,
                "tile": classified["tile"],
                "confidence": classified["confidence"] * box["occupancy"],
                "error": classified["error"],
                "occupancy": box["occupancy"],
                "box": box["box"],
            })

        hand = canonical_hand([result["tile"] for result in results])
        return hand, results

    def parse(self, frame):
        hand, _ = self.parse_with_details(frame)
        return hand

    def debug_image(self, frame, output_path):
        hand_image = self.crop_hand(frame)
        if hand_image.size == 0:
            return None
        for idx, _ in self.split_tiles(hand_image):
            height, width = hand_image.shape[:2]
            x = int(round(idx * width / self.tile_count))
            cv2.line(hand_image, (x, 0), (x, height), (0, 255, 0), 1)
        cv2.imwrite(output_path, hand_image)
        return output_path

    def save_debug_tiles(self, frame, output_dir):
        import json
        import os

        os.makedirs(output_dir, exist_ok=True)
        for filename in os.listdir(output_dir):
            if (
                filename == "hand.png"
                or filename == "classification.json"
                or filename.startswith("tile-")
            ):
                os.remove(os.path.join(output_dir, filename))

        hand_image = self.crop_hand(frame)
        if hand_image.size == 0:
            debug_path = os.path.join(output_dir, "classification.json")
            with open(debug_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            return debug_path

        cv2.imwrite(os.path.join(output_dir, "hand.png"), hand_image)

        details = []
        for idx, tile_image in self.split_tiles(hand_image):
            classified = self.classifier.classify(tile_image)
            details.append({
                "index": idx,
                "tile": classified["tile"],
                "confidence": classified["confidence"],
                "error": classified["error"],
            })
            safe_tile = str(classified["tile"]).replace("/", "-")
            path = os.path.join(output_dir, f"tile-{idx:02d}-{safe_tile}.png")
            cv2.imwrite(path, tile_image)

        debug_path = os.path.join(output_dir, "classification.json")
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(details, f, indent=2)

        return debug_path
