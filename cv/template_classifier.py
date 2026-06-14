import csv
import os
from collections import defaultdict

import cv2
import numpy as np

from ai.tile_set import canonical_tile


class TemplateTileClassifier:
    def __init__(
        self,
        image_dir="dataset/tiles-resized",
        csv_file="dataset/tiles-data/data.csv",
        calibrated_dir="templates/tiles",
        legacy_calibrated_dir="dataset/quehun-tiles",
        size=(64, 64),
    ):
        self.image_dir = image_dir
        self.csv_file = csv_file
        self.calibrated_dir = calibrated_dir
        self.legacy_calibrated_dir = legacy_calibrated_dir
        self.size = size
        self.prototypes = self._load_prototypes()

    def _preprocess(self, image):
        if image is None:
            raise ValueError("Cannot classify an empty image.")

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        resized = cv2.resize(gray, self.size, interpolation=cv2.INTER_AREA)
        return cv2.equalizeHist(resized).astype(np.float32) / 255.0

    def _load_rows(self):
        with open(self.csv_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row.get("image-name") or row.get("filename") or next(iter(row.values()))
                label = row.get("label-name") or row.get("label")
                yield filename, label

    def _load_calibrated_prototypes(self):
        grouped = defaultdict(list)

        roots = [self.calibrated_dir]
        if self.legacy_calibrated_dir and self.legacy_calibrated_dir not in roots:
            roots.append(self.legacy_calibrated_dir)

        for root in roots:
            if not os.path.isdir(root):
                continue
            for label in os.listdir(root):
                canonical = canonical_tile(label)
                if canonical is None:
                    continue

                tile_dir = os.path.join(root, label)
                if not os.path.isdir(tile_dir):
                    continue

                for filename in os.listdir(tile_dir):
                    if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                        continue
                    image = cv2.imread(os.path.join(tile_dir, filename))
                    if image is None:
                        continue
                    grouped[canonical].append(self._preprocess(image))

        return {
            label: images
            for label, images in grouped.items()
        }

    def _load_dataset_prototypes(self):
        grouped = defaultdict(list)

        for filename, label in self._load_rows():
            canonical = canonical_tile(label)
            if canonical is None:
                continue

            path = os.path.join(self.image_dir, str(filename))
            image = cv2.imread(path)
            if image is None:
                continue

            grouped[canonical].append(self._preprocess(image))

        if not grouped:
            raise RuntimeError("No usable tile templates were loaded from the dataset.")

        return {
            label: np.mean(images, axis=0)
            for label, images in grouped.items()
        }

    def _load_prototypes(self):
        calibrated = self._load_calibrated_prototypes()
        dataset = self._load_dataset_prototypes()
        if not calibrated:
            return dataset
        merged = dict(dataset)
        merged.update(calibrated)
        return merged

    def classify(self, image):
        sample = self._preprocess(image)
        best_label = None
        best_error = float("inf")

        for label, prototypes in self.prototypes.items():
            if isinstance(prototypes, list):
                errors = [float(np.mean((sample - prototype) ** 2)) for prototype in prototypes]
                error = min(errors)
            else:
                error = float(np.mean((sample - prototypes) ** 2))

            if error < best_error:
                best_error = error
                best_label = label

        confidence = max(0.0, min(1.0, 1.0 - best_error * 8.0))
        return {
            "tile": best_label,
            "confidence": confidence,
            "error": best_error,
        }
