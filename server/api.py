import io
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from challanai.core.config import load_config
from challanai.generation import generate_invoice, generate_pdf
from challanai.extraction import images_to_invoice

app = FastAPI(title="ChallanAI API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _save_upload(upload: UploadFile, suffix: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="/tmp")
    tmp.write(upload.file.read())
    tmp.close()
    return Path(tmp.name)


def _config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    if config_path.exists():
        return load_config(config_path)
    return load_config()


@app.get("/health")
def health():
    return {"status": "ok", "service": "challanai"}


@app.post("/generate")
async def generate(file: UploadFile = File(...), inv_num: int = Form(1)):
    """Accept .xlsx upload, return generated .xlsx invoice."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="File must be .xlsx or .xls")

    input_path = _save_upload(file, ".xlsx")
    output_path = Path(f"/tmp/Invoice_{inv_num}.xlsx")

    try:
        config = _config()
        workbook = generate_invoice(input_path, inv_num, config)
        workbook.save(str(output_path))

        return StreamingResponse(
            open(output_path, "rb"),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=Invoice_{inv_num}.xlsx"},
        )
    finally:
        input_path.unlink(missing_ok=True)


@app.post("/generate-pdf")
async def generate_pdf_endpoint(file: UploadFile = File(...), inv_num: int = Form(1)):
    """Accept .xlsx upload, return PDF invoice."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="File must be .xlsx or .xls")

    input_path = _save_upload(file, ".xlsx")
    output_path = Path(f"/tmp/Invoice_{inv_num}.pdf")

    try:
        config = _config()
        generate_pdf(input_path, inv_num, output_path, config)

        return StreamingResponse(
            open(output_path, "rb"),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Invoice_{inv_num}.pdf"},
        )
    finally:
        input_path.unlink(missing_ok=True)


@app.post("/generate-from-image")
async def generate_from_image(file: UploadFile = File(...), inv_num: int = Form(1)):
    """Accept image upload, extract data via AI/OCR, return .xlsx invoice."""
    input_path = _save_upload(file, Path(file.filename).suffix)
    output_excel = Path(f"/tmp/extracted_{inv_num}.xlsx")

    try:
        config = _config()
        df, _ = images_to_invoice(
            image_paths=[input_path],
            invoice_number=inv_num,
            output_excel=output_excel,
            generate_pdf_flag=False,
            config=config,
        )

        invoice_path = Path(f"/tmp/Invoice_{inv_num}.xlsx")
        workbook = generate_invoice(output_excel, inv_num, config)
        workbook.save(str(invoice_path))

        return StreamingResponse(
            open(invoice_path, "rb"),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=Invoice_{inv_num}.xlsx"},
        )
    finally:
        input_path.unlink(missing_ok=True)
        output_excel.unlink(missing_ok=True)


@app.post("/generate-from-image-pdf")
async def generate_from_image_pdf(file: UploadFile = File(...), inv_num: int = Form(1)):
    """Accept image upload, extract data via AI/OCR, return PDF invoice."""
    input_path = _save_upload(file, Path(file.filename).suffix)
    output_excel = Path(f"/tmp/extracted_{inv_num}.xlsx")

    try:
        config = _config()
        df, _ = images_to_invoice(
            image_paths=[input_path],
            invoice_number=inv_num,
            output_excel=output_excel,
            generate_pdf_flag=False,
            config=config,
        )

        pdf_path = Path(f"/tmp/Invoice_{inv_num}.pdf")
        generate_pdf(output_excel, inv_num, pdf_path, config)

        return StreamingResponse(
            open(pdf_path, "rb"),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Invoice_{inv_num}.pdf"},
        )
    finally:
        input_path.unlink(missing_ok=True)
        output_excel.unlink(missing_ok=True)


@app.post("/batch")
async def batch_endpoint(file: UploadFile = File(...), start_num: int = Form(1)):
    """Accept zip of .xlsx files, return zip of generated invoices."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")

    zip_path = _save_upload(file, ".zip")
    work_dir = Path(tempfile.mkdtemp(dir="/tmp"))
    output_dir = Path(tempfile.mkdtemp(dir="/tmp"))

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(work_dir)

        config = _config()
        input_files = sorted(
            f for f in work_dir.rglob("*")
            if f.suffix.lower() in (".xlsx", ".xls") and not f.name.startswith("~")
        )

        if not input_files:
            raise HTTPException(status_code=400, detail="No .xlsx files found in zip")

        for idx, input_file in enumerate(input_files):
            inv_num = start_num + idx
            workbook = generate_invoice(input_file, inv_num, config)
            workbook.save(str(output_dir / f"Invoice_{inv_num}.xlsx"))

        result_buffer = io.BytesIO()
        with zipfile.ZipFile(result_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for output_file in sorted(output_dir.iterdir()):
                zf.write(output_file, output_file.name)
        result_buffer.seek(0)

        return StreamingResponse(
            result_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=invoices.zip"},
        )
    finally:
        zip_path.unlink(missing_ok=True)
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)
