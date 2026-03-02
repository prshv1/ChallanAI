<div align="center">

# ChallanAI

**Turn handwritten challans into GST invoices instantly.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.3.0-6366f1?style=for-the-badge)]()

---

*Small businesses in India can't afford big SaaS invoicing software.*
*Upload raw delivery data or photos of handwritten challans → get a digitized, GST-compliant tax invoice instantly.*

</div>

---

## Architecture

```
ChallanAI/
├── src/challanai/              ← Core Python module (generation, extraction, OCR)
├── server/                     ← FastAPI REST API + Docker + Cloud Run deploy
├── challanai_web/              ← Single-file web UI (deploy to Vercel)
├── Example Data/               ← Sample .xlsx input files
├── config.yaml                 ← Business configuration (company, buyer, bank, GST)
└── requirements.txt            ← Python dependencies (core module)
```

**Three deployment targets:**

| Component | Stack | Deploy |
|-----------|-------|--------|
| **Core module** | Python package | `pip install -r requirements.txt` |
| **API server** | FastAPI + Docker | GCP Cloud Run |
| **Web UI** | Single HTML file | Vercel (drag & drop) |

---

## Features

- **Excel & Image Input** — Upload Excel data or photos of handwritten/printed challans
- **PDF Export** — Generate print-ready PDF invoices alongside Excel
- **Batch Processing** — Process entire folders with auto-incrementing invoice numbers
- **Config File** — Customize company, buyer, bank, GST via `config.yaml`
- **GST Compliant** — Auto-calculates CGST + SGST with HSN codes
- **AI/OCR Pipeline** — 3-tier fallback: Vision LLM → OCR + LLM → Pure OCR + heuristics
- **REST API** — Stateless FastAPI server, ready for Cloud Run
- **Web UI** — Dark-themed single-page app, zero dependencies

---

## Quick Start

### CLI Usage

```bash
git clone https://github.com/prshv1/ChallanAI.git
cd ChallanAI
pip install -r requirements.txt

# Generate from Excel data
python3 -c "from challanai.cli import main_generator; main_generator()" -i 178 --pdf

# Batch process
python3 -c "from challanai.cli import main_generator; main_generator()" --batch ./data/ --start 178
```

### Python API

```python
from challanai import generate_invoice, generate_pdf, batch_process

wb = generate_invoice("data.xlsx", inv_num=178)
wb.save("Invoice_178.xlsx")

generate_pdf("data.xlsx", inv_num=178, output_path="Invoice_178.pdf")
```

### API Server

```bash
cd server
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

See [server/README.md](server/README.md) for Cloud Run deployment.

### Web UI

Drag the `challanai_web/` folder into [vercel.com/new](https://vercel.com/new). Set `BASE_URL` to your API endpoint.

See [challanai_web/README.md](challanai_web/README.md).

---

## API Endpoints

| Method | Path | Input | Output |
|--------|------|-------|--------|
| `GET` | `/health` | — | Health check |
| `POST` | `/generate` | `.xlsx` + `inv_num` | `.xlsx` invoice |
| `POST` | `/generate-pdf` | `.xlsx` + `inv_num` | PDF invoice |
| `POST` | `/generate-from-image` | Image + `inv_num` | `.xlsx` invoice |
| `POST` | `/generate-from-image-pdf` | Image + `inv_num` | PDF invoice |
| `POST` | `/batch` | `.zip` + `start_num` | `.zip` of invoices |

---

## Configuration

Customize `config.yaml` for your business:

```yaml
company:
  name: "YOUR COMPANY NAME"
  subtitle: "(BUSINESS TYPE)"
  address: "Your Address"
  contact: "9876543210"
  gstn: "00XXXXX0000X0XX"
  pan: "XXXXX0000X"

buyer:
  name: "BUYER NAME"
  address: "Buyer Address"
  gstn: "00XXXXX0000X0XX"

bank:
  account_name: "YOUR COMPANY"
  bank_name: "BANK NAME"
  account_no: "000000000000"
  branch: "BRANCH"
  ifsc: "XXXX0000000"

gst:
  cgst_rate: 0.09
  sgst_rate: 0.09
  hsn_code: 996511

unit: "Tonne"
```

---

## Project Structure

```
ChallanAI/
├── src/challanai/
│   ├── core/
│   │   ├── config.py              # YAML config loader & defaults
│   │   ├── data_processing.py     # Data processing & GST calculations
│   │   └── image_utils.py         # Image preprocessing & base64 encoding
│   ├── extractors/
│   │   ├── json_parser.py         # JSON repair & parsing from LLM output
│   │   ├── llm_client.py          # OpenRouter LLM API client
│   │   ├── ocr_engine.py          # EasyOCR extraction engine
│   │   └── validator.py           # Data validation & syncing
│   ├── renderers/
│   │   ├── excel.py               # Excel invoice rendering engine
│   │   └── pdf.py                 # PDF invoice rendering
│   ├── __init__.py                # Public module API & exports
│   ├── cli.py                     # CLI argument parsing
│   ├── extraction.py              # Image-to-Invoice pipeline
│   └── generation.py              # Excel-to-Invoice pipeline
├── server/
│   ├── api.py                     # FastAPI REST server
│   ├── Dockerfile                 # Production Docker image
│   ├── cloudbuild.yaml            # GCP Cloud Build config
│   ├── requirements.txt           # Server dependencies
│   └── .dockerignore
├── challanai_web/
│   ├── index.html                 # Single-file web UI
│   └── vercel.json                # Vercel routing config
├── Example Data/                   # Sample .xlsx input files
├── config.yaml                     # Business configuration
├── requirements.txt                # Core Python dependencies
└── README.md
```

---

## License

MIT — free to use, modify, and distribute.

---

<div align="center">

**Made with care for India's small businesses**

</div>
