import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import pandas as pd
from invoice_generator.core.image_utils import preprocess_image
from invoice_generator.extractors.validator import OUTPUT_COLUMNS

logger = logging.getLogger(__name__)

Y_TOLERANCE_PX = 15
HEADER_KEYWORDS = (
    "date",
    "challan",
    "vehicle",
    "site",
    "material",
    "quantity",
    "rate",
    "amount",
)


@dataclass
class OCRDetection:
    """A single word detected by OCR, with its position and confidence."""

    bounding_box: list[list[int]]
    text: str
    confidence: float

    @property
    def center_x(self) -> int:
        return int((self.bounding_box[0][0] + self.bounding_box[1][0]) / 2)

    @property
    def center_y(self) -> int:
        return int((self.bounding_box[0][1] + self.bounding_box[2][1]) / 2)


_ocr_reader_cache = None


def _get_ocr_reader():
    """Get the EasyOCR reader instance, caching it after first load."""
    global _ocr_reader_cache
    if _ocr_reader_cache is None:
        import easyocr

        logger.info("  📦 Loading OCR model (first run downloads ~500MB)...")
        _ocr_reader_cache = easyocr.Reader(["en", "hi"], verbose=False)
    return _ocr_reader_cache


def extract_with_ocr(image_path: Union[str, Path]) -> tuple[str, float]:
    """Extract text from an image with spatial layout preservation into pipe-separated rows."""
    import cv2
    import numpy as np

    reader = _get_ocr_reader()
    preprocessed_bytes = preprocess_image(image_path)

    image_array = np.frombuffer(preprocessed_bytes, np.uint8)
    grayscale_image = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)

    raw_detections = reader.readtext(grayscale_image, detail=1)
    if not raw_detections:
        return "", 0.0

    detections = [
        OCRDetection(bounding_box=bbox, text=text, confidence=conf)
        for bbox, text, conf in raw_detections
    ]
    median_confidence = float(np.median([d.confidence for d in detections]))

    # Group into lines
    detections.sort(key=lambda d: d.center_y)
    lines: list[list[OCRDetection]] = [[detections[0]]]

    for detection in detections[1:]:
        previous = lines[-1][-1]
        if abs(detection.center_y - previous.center_y) <= Y_TOLERANCE_PX:
            lines[-1].append(detection)
        else:
            lines.append([detection])

    for line in lines:
        line.sort(key=lambda d: d.center_x)

    structured_text = "\n".join(
        " | ".join(detection.text for detection in line) for line in lines
    )
    return structured_text, median_confidence


def ocr_text_to_dataframe(ocr_text: str) -> pd.DataFrame:
    """Parse structured OCR text into a DataFrame using heuristic rules."""
    text_lines = [line.strip() for line in ocr_text.strip().split("\n") if line.strip()]

    date_pattern = re.compile(r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}")
    pure_number_pattern = re.compile(r"^\d+\.?\d*$")

    records = []

    for line in text_lines:
        fields = [field.strip() for field in re.split(r"[|\t]", line) if field.strip()]

        line_lower = " ".join(fields).lower()
        if any(keyword in line_lower for keyword in HEADER_KEYWORDS):
            continue

        if len(fields) < 4:
            continue

        detected_date = next(
            (date_pattern.search(f).group() for f in fields if date_pattern.search(f)),
            None,
        )
        if detected_date is None:
            continue

        numeric_values = []
        text_values = []
        for field in fields:
            if field == detected_date:
                continue
            cleaned = field.replace(",", "").strip()
            if pure_number_pattern.match(cleaned):
                numeric_values.append(float(cleaned))
            else:
                text_values.append(field)

        qty = (
            numeric_values[-2]
            if len(numeric_values) > 3
            else (numeric_values[2] if len(numeric_values) > 2 else 0.0)
        )
        rate = (
            numeric_values[-1]
            if len(numeric_values) > 3
            else (numeric_values[3] if len(numeric_values) > 3 else 0.0)
        )

        record = {
            "Date": detected_date,
            "Challan No.": numeric_values[0] if len(numeric_values) > 0 else None,
            "Vehicle No.": numeric_values[1] if len(numeric_values) > 1 else None,
            "Site": text_values[0] if len(text_values) > 0 else "",
            "Material": text_values[1] if len(text_values) > 1 else "",
            "Quantity": qty,
            "Rate": rate,
            "Per": text_values[2] if len(text_values) > 2 else "",
        }
        records.append(record)

    if not records:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    return pd.DataFrame(records, columns=OUTPUT_COLUMNS)
