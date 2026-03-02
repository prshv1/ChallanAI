import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from invoice_generator.core.config import load_config
from invoice_generator.extractors.llm_client import (
    extract_with_vision,
    extract_with_llm_text,
)
from invoice_generator.extractors.ocr_engine import (
    extract_with_ocr,
    ocr_text_to_dataframe,
)
from invoice_generator.extractors.validator import generate_validation_warnings
from invoice_generator.generation import generate_invoice, generate_pdf

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
)
OCR_CONFIDENCE_THRESHOLD = 0.80


@dataclass
class BatchResult:
    input_path: str
    invoice_number: int
    excel_path: Optional[str] = None
    pdf_path: Optional[str] = None
    extracted_data_path: Optional[str] = None
    record_count: int = 0
    error: Optional[str] = None


def images_to_invoice(
    image_paths: list[Union[str, Path]],
    invoice_number: int,
    output_excel: Union[str, Path],
    generate_pdf_flag: bool = False,
    api_key: Optional[str] = None,
    models: Optional[list[str]] = None,
    force_ocr: bool = False,
    config: Optional[dict] = None,
) -> tuple[pd.DataFrame, Optional[str]]:
    """Process one or more delivery challan images into a single grouped GST invoice."""

    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key and not force_ocr:
        logger.warning(
            "No API key found. Set OPENROUTER_API_KEY in .env or use --api-key. Falling back to OCR-only mode."
        )
        force_ocr = True

    all_frames = []
    failed_images = []

    for image_path in image_paths:
        file_path = Path(image_path)
        if not file_path.exists():
            failed_images.append((str(file_path), "File not found"))
            continue

        logger.info(f"\n📸 Processing: {file_path.name}")
        dataframe = pd.DataFrame()

        try:
            if not force_ocr:
                try:
                    logger.info("  🤖 Attempting direct LLM vision extraction...")
                    dataframe = extract_with_vision(file_path, api_key, models)
                except Exception as llm_vision_error:
                    logger.warning(f"  ⚠️  LLM vision failed: {llm_vision_error}")
                    logger.info("  🔍 Falling back to OCR + LLM text...")

                    ocr_text, confidence = extract_with_ocr(file_path)
                    logger.info(f"  📊 OCR confidence: {confidence:.0%}")

                    try:
                        dataframe = extract_with_llm_text(ocr_text, api_key, models)
                    except Exception as ocr_llm_error:
                        logger.warning(f"  ⚠️  OCR + LLM text failed: {ocr_llm_error}")
                        force_ocr = True

            if force_ocr or dataframe.empty:
                logger.info("  🔍 Falling back to pure OCR (offline mode)...")
                ocr_text, confidence = extract_with_ocr(file_path)
                logger.info(f"  📊 OCR confidence: {confidence:.0%}")

                if confidence < OCR_CONFIDENCE_THRESHOLD:
                    logger.warning(
                        f"  ⚠️  Low OCR confidence ({confidence:.0%} < "
                        f"{OCR_CONFIDENCE_THRESHOLD:.0%}). Results may be unreliable."
                    )

                dataframe = ocr_text_to_dataframe(ocr_text)

            warnings = generate_validation_warnings(dataframe)
            if warnings:
                logger.warning(f"  ⚠️  {len(warnings)} potential data issue(s) found:")
                for warning in warnings:
                    logger.warning(f"      - {warning}")

            all_frames.append(dataframe)

        except Exception as extraction_error:
            failed_images.append((str(file_path), str(extraction_error)))
            logger.error(f"  ❌ {file_path.name}: {extraction_error}")

    if failed_images:
        logger.warning(f"\n⚠️  {len(failed_images)} image(s) failed to process:")
        for path, error_message in failed_images:
            logger.warning(f"     {path}: {error_message}")

    if not all_frames:
        raise ValueError(
            "No records could be extracted from any of the provided images."
        )

    combined_df = pd.concat(all_frames, ignore_index=True)
    combined_df.to_excel(output_excel, index=False, engine="openpyxl")

    pdf_out = None
    if generate_pdf_flag:
        config = config or load_config()
        try:
            workbook = generate_invoice(output_excel, invoice_number, config)
            invoice_excel_path = str(output_excel).replace(
                ".xlsx", f"_Invoice_{invoice_number}.xlsx"
            )
            workbook.save(invoice_excel_path)

            pdf_out = str(output_excel).replace(
                ".xlsx", f"_Invoice_{invoice_number}.pdf"
            )
            generate_pdf(output_excel, invoice_number, pdf_out, config)
        except Exception as e:
            logger.warning(f"Failed to generate final PDFs: {e}")

    return combined_df, pdf_out


def batch_process_images(
    input_dir: Union[str, Path],
    start_num: int,
    output_dir: Optional[Union[str, Path]] = None,
    generate_pdf_flag: bool = False,
    api_key: Optional[str] = None,
    models: Optional[list[str]] = None,
    force_ocr: bool = False,
    config: Optional[dict] = None,
) -> list[BatchResult]:
    """Process a directory of images, generating one invoice per image."""
    input_directory = Path(input_dir)
    output_directory = Path(output_dir) if output_dir else input_directory
    output_directory.mkdir(parents=True, exist_ok=True)

    config = config or load_config()

    image_files = sorted(
        f
        for f in input_directory.iterdir()
        if f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS and not f.name.startswith("~")
    )

    if not image_files:
        logger.warning(f"No images found in {input_directory}")
        return []

    results = []

    for idx, image_path in enumerate(image_files):
        inv_number = start_num + idx
        result = BatchResult(input_path=str(image_path), invoice_number=inv_number)

        excel_output = output_directory / f"Invoice_{inv_number}.xlsx"
        extracted_data_path = output_directory / f"extracted_data_{inv_number}.xlsx"

        try:
            logger.info(
                f"\n📦 Processing {idx + 1}/{len(image_files)}: {image_path.name} (Invoice #{inv_number})"
            )

            dataframe, pdf_path = images_to_invoice(
                image_paths=[image_path],
                invoice_number=inv_number,
                output_excel=extracted_data_path,
                generate_pdf_flag=generate_pdf_flag,
                api_key=api_key,
                models=models,
                force_ocr=force_ocr,
                config=config,
            )

            result.extracted_data_path = str(extracted_data_path)
            result.record_count = len(dataframe)

            workbook = generate_invoice(extracted_data_path, inv_number, config)
            workbook.save(str(excel_output))
            result.excel_path = str(excel_output)

            logger.info(
                f"  ✅ [{inv_number}] {image_path.name} → {excel_output.name} ({result.record_count} records)"
            )

            if generate_pdf_flag:
                pdf_output = output_directory / f"Invoice_{inv_number}.pdf"
                generate_pdf(extracted_data_path, inv_number, pdf_output, config)
                result.pdf_path = str(pdf_output)
                logger.info(f"        📄 {pdf_output.name}")

        except Exception as error:
            result.error = str(error)
            logger.error(f"  ❌ [{inv_number}] {image_path.name}: {error}")

        results.append(result)

    return results
