from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import shutil

import cv2
import numpy as np


class ScreenState(str, Enum):
    ROOM_CREATION = "room_creation"
    IN_GAME = "in_game"
    LOADING = "loading"
    UNKNOWN = "unknown"


@dataclass
class ScreenStateResult:
    state: ScreenState
    confidence: float
    text: str = ""
    reasons: list[str] = field(default_factory=list)
    ocr_available: bool = False


class OCRReader:
    def __init__(self, data_dir=None):
        self.available = False
        self.languages = []
        self._pytesseract = None
        default_data_dir = Path(__file__).resolve().parent.parent / "tools" / "tessdata"
        self.data_dir = Path(data_dir) if data_dir else default_data_dir
        self.tesseract_config = ""
        if self.data_dir.is_dir():
            self.tesseract_config = f'--tessdata-dir "{self.data_dir}"'
        try:
            import pytesseract

            self._pytesseract = pytesseract
            executable = shutil.which("tesseract")
            if not executable:
                default_executable = Path(
                    "C:/Program Files/Tesseract-OCR/tesseract.exe"
                )
                if default_executable.is_file():
                    executable = str(default_executable)
            if executable:
                pytesseract.pytesseract.tesseract_cmd = executable
            self.languages = pytesseract.get_languages(config=self.tesseract_config)
            self.available = True
        except Exception:
            self.available = False

    @property
    def language(self):
        if "chi_sim" in self.languages and "eng" in self.languages:
            return "chi_sim+eng"
        if "eng" in self.languages:
            return "eng"
        return self.languages[0] if self.languages else None

    def read(self, frame):
        if not self.available or not self.language or frame is None or frame.size == 0:
            return ""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scale = min(2.0, max(1.0, 1400.0 / max(1, gray.shape[1])))
        if scale != 1.0:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        normalized = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        try:
            return self._pytesseract.image_to_string(
                normalized,
                lang=self.language,
                config=f"{self.tesseract_config} --psm 11".strip(),
            ).strip()
        except Exception:
            return ""


class QueHunScreenStateDetector:
    ROOM_WORDS = (
        "create room", "room settings", "friend", "friendly", "创建房间", "友人场",
        "四人麻将", "人机",
    )
    GAME_WORDS = (
        "east", "south", "west", "north", "riichi", "ron", "tsumo",
        "东", "南", "西", "北", "立直", "荣和", "自摸",
    )
    LOADING_WORDS = ("loading", "connecting", "加载", "连接中")

    def __init__(self, ocr=None, templates_dir="templates/screens"):
        self.ocr = ocr or OCRReader()
        self.templates = self._load_templates(templates_dir)

    def detect(self, frame, hand_region=None):
        if frame is None or not hasattr(frame, "shape") or frame.size == 0:
            return ScreenStateResult(
                state=ScreenState.UNKNOWN,
                confidence=0.0,
                reasons=["empty frame"],
                ocr_available=self.ocr.available,
            )

        text = self.ocr.read(frame)
        normalized = " ".join(text.lower().split())
        scores = {
            ScreenState.ROOM_CREATION: self._keyword_score(normalized, self.ROOM_WORDS),
            ScreenState.IN_GAME: self._keyword_score(normalized, self.GAME_WORDS),
            ScreenState.LOADING: self._keyword_score(normalized, self.LOADING_WORDS),
        }
        reasons = []
        template_state, template_score = self._template_state(frame)
        if template_state is not None:
            scores[template_state] += template_score * 0.75
            reasons.append(
                f"screen template {template_state.value} {template_score:.2f}"
            )

        edge_density = self._edge_density(frame)
        color_variance = float(np.std(cv2.resize(frame, (64, 36)))) / 128.0
        center_dark = self._center_dark_ratio(frame)
        hand_score = self._hand_region_score(frame, hand_region)

        if hand_score > 0.30:
            scores[ScreenState.IN_GAME] += 0.55
            reasons.append(f"hand-region visual score {hand_score:.2f}")
        if center_dark > 0.65 and edge_density < 0.06:
            scores[ScreenState.LOADING] += 0.35
            reasons.append("mostly dark low-detail frame")
        if edge_density > 0.08 and color_variance > 0.35 and hand_score < 0.20:
            scores[ScreenState.ROOM_CREATION] += 0.12

        best_state = max(scores, key=scores.get)
        best_score = min(1.0, scores[best_state])
        if best_score < 0.22:
            best_state = ScreenState.UNKNOWN
            best_score = max(0.05, min(0.35, edge_density + color_variance * 0.1))
            reasons.append("no reliable state signal")
        elif normalized:
            reasons.append("OCR keyword match")

        return ScreenStateResult(
            state=best_state,
            confidence=round(best_score, 3),
            text=text,
            reasons=reasons,
            ocr_available=self.ocr.available,
        )

    @staticmethod
    def _load_templates(directory):
        templates = {}
        path = Path(directory)
        if not path.is_dir():
            return templates
        mapping = {
            "room_creation": ScreenState.ROOM_CREATION,
            "in_game": ScreenState.IN_GAME,
            "loading": ScreenState.LOADING,
        }
        for image_path in path.iterdir():
            state = mapping.get(image_path.stem.lower())
            if state is None:
                continue
            image = cv2.imread(str(image_path))
            if image is not None:
                templates[state] = image
        return templates

    def _template_state(self, frame):
        if not self.templates:
            return None, 0.0
        sample = self._screen_feature(frame)
        best_state = None
        best_score = 0.0
        for state, template in self.templates.items():
            feature = self._screen_feature(template)
            score = float(cv2.compareHist(sample, feature, cv2.HISTCMP_CORREL))
            score = max(0.0, min(1.0, score))
            if score > best_score:
                best_state = state
                best_score = score
        if best_score < 0.55:
            return None, best_score
        return best_state, best_score

    @staticmethod
    def _screen_feature(frame):
        resized = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        histogram = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
        return cv2.normalize(histogram, histogram).flatten().astype(np.float32)

    @staticmethod
    def _keyword_score(text, words):
        if not text:
            return 0.0
        matches = sum(1 for word in words if word.lower() in text)
        return min(0.9, matches * 0.35)

    @staticmethod
    def _edge_density(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
        edges = cv2.Canny(gray, 60, 160)
        return float((edges > 0).mean())

    @staticmethod
    def _center_dark_ratio(frame):
        height, width = frame.shape[:2]
        crop = frame[height // 4: height * 3 // 4, width // 4: width * 3 // 4]
        if crop.size == 0:
            return 0.0
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return float((gray < 45).mean())

    @staticmethod
    def _hand_region_score(frame, region):
        if not region:
            return 0.0
        height, width = frame.shape[:2]
        left = max(0, int(region.get("left", 0)))
        top = max(0, int(region.get("top", 0)))
        right = min(width, left + int(region.get("width", 0)))
        bottom = min(height, top + int(region.get("height", 0)))
        crop = frame[top:bottom, left:right]
        if crop.size == 0:
            return 0.0
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        bright = float((hsv[:, :, 2] > 150).mean())
        edges = cv2.Canny(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 50, 150)
        edge_density = float((edges > 0).mean())
        return min(1.0, bright * 0.55 + edge_density * 2.5)
