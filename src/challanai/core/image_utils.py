import base64
import io
import logging
from pathlib import Path
from typing import Union

import cv2
import numpy as np
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)

MAX_IMAGE_WIDTH_PX = 1200
JPEG_COMPRESSION_QUALITY = 85


def _fix_exif_rotation(pil_image: Image.Image) -> Image.Image:
    """Auto-rotate image based on EXIF."""
    try:
        if not hasattr(pil_image, "_getexif"):
            return pil_image
        exif = pil_image._getexif()
        if not exif:
            return pil_image

        orientation_key = next(
            (k for k, v in ExifTags.TAGS.items() if v == "Orientation"), None
        )
        if orientation_key and orientation_key in exif:
            orientation = exif[orientation_key]
            if orientation == 3:
                pil_image = pil_image.rotate(180, expand=True)
            elif orientation == 6:
                pil_image = pil_image.rotate(270, expand=True)
            elif orientation == 8:
                pil_image = pil_image.rotate(90, expand=True)
    except Exception as exif_err:
        logger.warning(f"  ⚠️  Could not read EXIF data: {exif_err}")

    return pil_image


def _resize_if_needed(
    pil_image: Image.Image, max_width: int = MAX_IMAGE_WIDTH_PX
) -> tuple[Image.Image, float]:
    """Resize image proportionally if it exceeds max_width."""
    width, height = pil_image.size
    if width <= max_width:
        return pil_image, 1.0

    scale_factor = max_width / width
    new_dims = (max_width, int(height * scale_factor))
    return pil_image.resize(new_dims, Image.LANCZOS), scale_factor


def preprocess_image(image_path: Union[str, Path]) -> bytes:
    """Load, preprocess, and return an image as JPEG bytes optimized for OCR."""
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    pil_image = Image.open(image_path)
    pil_image = _fix_exif_rotation(pil_image)

    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    pil_image, _scale = _resize_if_needed(pil_image)

    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.fastNlMeansDenoising(enhanced, h=30)
    adjusted = cv2.convertScaleAbs(denoised, alpha=1.2, beta=0)
    _, binary = cv2.threshold(adjusted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    final_pil = Image.fromarray(binary)
    if pil_image.mode != "L":
        final_pil = final_pil.convert("L")

    buffer = io.BytesIO()
    final_pil.save(buffer, format="JPEG", quality=JPEG_COMPRESSION_QUALITY)
    return buffer.getvalue()


def encode_image_for_llm(image_path: Union[str, Path]) -> str:
    """Encode an image as base64 JPEG for the LLM vision API."""
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    pil_image = Image.open(image_path)
    pil_image = _fix_exif_rotation(pil_image)

    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    pil_image, _scale = _resize_if_needed(pil_image)

    buffer = io.BytesIO()
    pil_image.save(buffer, format="JPEG", quality=JPEG_COMPRESSION_QUALITY)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
