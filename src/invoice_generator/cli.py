import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from invoice_generator.core.config import load_config
from invoice_generator.extraction import batch_process_images, images_to_invoice
from invoice_generator.generation import batch_process, generate_invoice, generate_pdf

logger = logging.getLogger(__name__)

load_dotenv()


def main_generator() -> None:
    """Command-line interface entry point for generating Excel invoices from Data."""
    parser = argparse.ArgumentParser(
        description="Invoice Generator — GST Tax Invoice from Raw Delivery Data"
    )
    parser.add_argument("-i", "--invoice", type=int, help="Invoice number")
    parser.add_argument(
        "--input",
        type=str,
        default="Example Data/Raw_Data.xlsx",
        help="Input Excel file",
    )
    parser.add_argument(
        "--output", type=str, default="Final_Output.xlsx", help="Output Excel file"
    )
    parser.add_argument("--pdf", action="store_true", help="Also generate PDF output")
    parser.add_argument(
        "--batch", type=str, help="Batch process all Excel files in a directory"
    )
    parser.add_argument(
        "--start", type=int, default=1, help="Starting invoice number for batch mode"
    )
    parser.add_argument(
        "--output-dir", type=str, help="Output directory for batch mode"
    )
    parser.add_argument("--config", type=str, help="Path to config YAML file")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.batch:
        batch_dir = Path(args.batch)
        if not batch_dir.is_dir():
            logger.error(f"Error: {args.batch} is not a directory.")
            sys.exit(1)

        results = batch_process(
            batch_dir, args.start, args.output_dir, args.pdf, config
        )
        succeeded = sum(1 for r in results if r["error"] is None)
        failed = len(results) - succeeded
        logger.info(f"\n✅ {succeeded} succeeded, ❌ {failed} failed")
        sys.exit(1 if failed > 0 else 0)

    invoice_number = args.invoice
    if invoice_number is None:
        try:
            invoice_number = int(input("Enter invoice number: "))
        except ValueError:
            logger.error("Error: Please enter a valid integer.")
            sys.exit(1)

    try:
        workbook = generate_invoice(args.input, invoice_number, config)
        workbook.save(args.output)
        logger.info(f"✅ Excel: {args.output}")

        if args.pdf:
            pdf_path = Path(args.output).with_suffix(".pdf")
            generate_pdf(args.input, invoice_number, pdf_path, config)
            logger.info(f"📄 PDF:   {pdf_path}")

    except Exception as error:
        logger.error(f"Error: {error}")
        sys.exit(1)


def main_processor() -> None:
    """Command-line interface entry point for Vision Image Extractions."""
    parser = argparse.ArgumentParser(
        description="Image Processor — Extract delivery data from challan images."
    )
    parser.add_argument("images", nargs="*", help="Path to one or more image files")
    parser.add_argument(
        "-b", "--batch", type=str, help="Batch process folder of images"
    )
    parser.add_argument(
        "-c", "--combine", type=str, nargs="+", help="Combine images into invoice"
    )
    parser.add_argument("-i", "--invoice", type=int, default=1, help="Invoice number")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="extracted_data.xlsx",
        help="Output Excel file path",
    )
    parser.add_argument("--start", type=int, default=1, help="Starting invoice number")
    parser.add_argument("--api-key", type=str, help="OpenRouter API key")
    parser.add_argument(
        "--model", type=str, action="append", help="override model cascade"
    )
    parser.add_argument("--ocr", action="store_true", help="Force OCR fallback mode")
    parser.add_argument("--pdf", action="store_true", help="Generate PDF invoices")

    args = parser.parse_args()
    config = load_config()
    api_key = args.api_key or os.getenv("OPENROUTER_API_KEY")

    if args.batch:
        batch_dir = Path(args.batch)
        if not batch_dir.is_dir():
            logger.error(f"Error: {args.batch} is not a directory.")
            sys.exit(1)

        results = batch_process_images(
            batch_dir,
            args.start,
            "output",
            args.pdf,
            api_key,
            args.model,
            args.ocr,
            config,
        )
        succeeded = sum(1 for r in results if r.error is None)
        failed = len(results) - succeeded
        total_records = sum(r.record_count for r in results)
        logger.info(
            f"\n✅ {succeeded} succeeded, ❌ {failed} failed ({total_records} records extraction)"
        )
        sys.exit(1 if failed > 0 else 0)

    images_to_process = args.combine or args.images

    if not images_to_process:
        parser.print_help()
        sys.exit(1)

    invoice_number = args.invoice

    if args.combine:
        try:
            invoice_number = int(input("Enter invoice number: "))
        except ValueError:
            logger.warning("Error: Invoice number required for combine mode.")
            sys.exit(1)

    try:
        df, pdf_out = images_to_invoice(
            image_paths=images_to_process,
            invoice_number=invoice_number,
            output_excel=args.output,
            generate_pdf_flag=args.pdf,
            api_key=api_key,
            models=args.model,
            force_ocr=args.ocr,
            config=config,
        )
        logger.info(f"✅ Excel: {args.output} (Extracted {len(df)} Records)")
        if pdf_out:
            logger.info(f"📄 PDF: {pdf_out}")

    except Exception as error:
        logger.error(f"Error: {error}")
        sys.exit(1)
