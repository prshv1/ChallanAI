from pathlib import Path
from typing import Optional, Union

from openpyxl import Workbook
import logging

from invoice_generator.core.config import load_config
from invoice_generator.core.data_processing import DataProcessor
from invoice_generator.renderers.excel import InvoiceExcelRenderer
from invoice_generator.renderers.pdf import InvoicePDFRenderer

logger = logging.getLogger(__name__)


def generate_invoice(
    input_file: Union[str, Path],
    inv_num: int,
    config: Optional[dict] = None,
) -> Workbook:
    """Generate a GST tax invoice as an Excel workbook."""
    processor = DataProcessor(input_file, inv_num, config)
    data = processor.process()

    workbook = Workbook()
    renderer = InvoiceExcelRenderer(data)
    renderer.render(workbook)

    return workbook


def generate_pdf(
    input_file: Union[str, Path],
    inv_num: int,
    output_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
) -> Union[bytes, Path]:
    """Generate a GST tax invoice as a PDF."""
    processor = DataProcessor(input_file, inv_num, config)
    data = processor.process()

    renderer = InvoicePDFRenderer(data)
    pdf = renderer.render()

    if output_path:
        pdf.output(str(output_path))
        return Path(output_path)

    return pdf.output()


def batch_process(
    input_dir: Union[str, Path],
    start_num: int,
    output_dir: Optional[Union[str, Path]] = None,
    pdf: bool = False,
    config: Optional[dict] = None,
) -> list[dict]:
    """Batch process folder of flat datastores into GST Invoices."""
    input_directory = Path(input_dir)
    output_directory = Path(output_dir) if output_dir else input_directory
    output_directory.mkdir(parents=True, exist_ok=True)

    config = config or load_config()

    excel_files = sorted(
        f
        for f in input_directory.iterdir()
        if f.suffix.lower() in (".xlsx", ".xls") and not f.name.startswith("~")
    )

    if not excel_files:
        logger.warning(f"No Excel files found in {input_directory}")
        return []

    results = []

    for idx, file_path in enumerate(excel_files):
        inv_number = start_num + idx
        result = {
            "input": str(file_path),
            "invoice_num": inv_number,
            "excel": None,
            "pdf": None,
            "error": None,
        }

        try:
            workbook = generate_invoice(file_path, inv_number, config)
            excel_out = output_directory / f"Invoice_{inv_number}.xlsx"
            workbook.save(str(excel_out))
            result["excel"] = str(excel_out)
            logger.info(f"  ✅ [{inv_number}] {file_path.name} → {excel_out.name}")

            if pdf:
                pdf_out = output_directory / f"Invoice_{inv_number}.pdf"
                generate_pdf(file_path, inv_number, pdf_out, config)
                result["pdf"] = str(pdf_out)
                logger.info(f"        📄 {pdf_out.name}")

        except Exception as error:
            result["error"] = str(error)
            logger.warning(f"  ❌ [{inv_number}] {file_path.name}: {error}")

        results.append(result)

    return results
