"""
ChallanAI
=================

Convert photos of handwritten or printed delivery challans into structured
Excel data and GST PDF invoices leveraging OpenRouter's multimodal LLMs.
"""

from challanai.core.config import load_config
from challanai.core.image_utils import preprocess_image, encode_image_for_llm
from challanai.extraction import (
    BatchResult,
    images_to_invoice,
    batch_process_images,
)
from challanai.generation import generate_invoice, generate_pdf, batch_process

__all__ = [
    "load_config",
    "preprocess_image",
    "encode_image_for_llm",
    "BatchResult",
    "images_to_invoice",
    "batch_process_images",
    "generate_invoice",
    "generate_pdf",
    "batch_process",
]

__version__ = "0.3.0"
