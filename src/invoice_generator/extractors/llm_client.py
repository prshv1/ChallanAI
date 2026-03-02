import logging
import time
from pathlib import Path
from typing import Optional, Union

import pandas as pd
import requests

from invoice_generator.core.image_utils import encode_image_for_llm
from invoice_generator.extractors.json_parser import repair_json
from invoice_generator.extractors.validator import convert_records_to_dataframe

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODELS = [
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.2-90b-vision-instruct:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
]

API_TIMEOUT_SECONDS = 45
MAX_RETRIES_PER_MODEL = 3


def _call_openrouter(messages: list[dict], model: str, api_key: str) -> str:
    """Make a single chat completion call to the OpenRouter API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Invoice Generator",
    }

    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }

    response = requests.post(
        OPENROUTER_URL, headers=headers, json=payload, timeout=API_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    data = response.json()

    if "choices" not in data or not data["choices"]:
        raise ValueError("API response contained no choices.")

    return data["choices"][0]["message"]["content"]


def _call_with_cascade(
    messages: list[dict],
    api_key: str,
    models: Optional[list[str]] = None,
    on_json_error_suffix: str = "",
) -> list[dict]:
    """Execute LLM calls cascading through models with exponential backoff on retries."""
    models_to_try = models if models else DEFAULT_MODELS

    for model in models_to_try:
        current_messages = list(messages)

        for attempt in range(MAX_RETRIES_PER_MODEL):
            try:
                raw_response = _call_openrouter(current_messages, model, api_key)
                try:
                    return repair_json(raw_response)
                except ValueError as parse_error:
                    logger.warning(f"  ⚠️  JSON parse error on {model}: {parse_error}")
                    if attempt < MAX_RETRIES_PER_MODEL - 1:
                        current_messages.append(
                            {"role": "assistant", "content": raw_response}
                        )
                        current_messages.append(
                            {
                                "role": "user",
                                "content": f"You returned invalid JSON: {parse_error}{on_json_error_suffix}",
                            }
                        )
                    continue

            except requests.Timeout:
                logger.warning(f"  ⏰ Timeout on {model}, retrying...")
            except Exception as api_error:
                logger.warning(f"  ⚠️  API Error on {model}: {api_error}")
                break

            time.sleep(1.5**attempt)

    raise RuntimeError(
        "All models failed after returning invalid or timout API formats."
    )


VISION_EXTRACTION_PROMPT = """You are an expert at reading Indian delivery challans, bills, and handwritten records.

Extract ALL delivery records from this image into a JSON array.
Each record MUST have these exact fields:
{
  "Date": "dd/mm/yyyy",
  "Challan No.": number_or_null,
  "Vehicle No.": number_or_null,
  "Site": "location name",
  "Material": "material type (e.g. 10 mm, 20 mm, C. Sand, Cement)",
  "Quantity": decimal_number,
  "Rate": decimal_number,
  "Per": "unit (usually Tonne)"
}

Rules:
- Use dd/mm/yyyy format for dates
- Do NOT include total/summary rows
- Return ONLY the raw JSON array
"""


def extract_with_vision(
    image_path: Union[str, Path], api_key: str, models: Optional[list[str]] = None
) -> pd.DataFrame:
    base64_image = encode_image_for_llm(image_path)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": VISION_EXTRACTION_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        }
    ]
    records = _call_with_cascade(
        messages,
        api_key,
        models,
        on_json_error_suffix="\n\nIMPORTANT: Return ONLY valid JSON.",
    )
    return convert_records_to_dataframe(records)


TEXT_STRUCTURING_PROMPT = """You are an expert at formatting OCR text from delivery challans.

The following text was extracted by OCR. Group the unstructured words into a tabular structure.
Return a JSON array of records with these exact fields:
{
  "Date": "dd/mm/yyyy",
  "Challan No.": number_or_null,
  "Vehicle No.": number_or_null,
  "Site": "location name",
  "Material": "material type",
  "Quantity": decimal_number,
  "Rate": decimal_number,
  "Per": "unit (usually Tonne)"
}

Rules:
- Use dd/mm/yyyy format for dates
- Do NOT include total/summary rows
- Return ONLY the raw JSON array

OCR Text:
"""


def extract_with_llm_text(
    ocr_text: str, api_key: str, models: Optional[list[str]] = None
) -> pd.DataFrame:
    messages = [{"role": "user", "content": TEXT_STRUCTURING_PROMPT + ocr_text}]
    records = _call_with_cascade(messages, api_key, models)
    return convert_records_to_dataframe(records)
