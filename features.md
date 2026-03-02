# Invoice Generator Feature Log

This document details the major features and architectural improvements made to the Invoice Generator project across its recent versions.

---

## 🚀 Version 0.3.0 (Image Processing & Architecture)

### 1. Image-to-Invoice Pipeline (`src/invoice_generator/image_processor.py`)
* **3-Tier Resilient Architecture:**
  1. **Tier 1 (Primary): LLM Vision.** Sends minimal-processed images to OpenRouter free vision models for maximum accuracy on handwritten documents.
  2. **Tier 2 (Fallback): OCR + LLM Text.** If vision models fail, EasyOCR extracts raw characters (English + Hindi), and the LLM structures them into JSON.
  3. **Tier 3 (Offline): Pure OCR + Heuristics.** If the API fails entirely or no key is present, a custom Python spatial-mapping algorithm (no LLM required) heuristically pulls the challan layout from raw OCR detections.

### 2. Workarounds & Safety Nets
* **Model Cascading & Backoff:** If hitting OpenRouter API rate limits (429) or downtime (502/503), the system gracefully cascades through 5 different free models with automated exponential backoff.
* **LLM JSON Repair Strategies:** Programmatically patches LLM formatting hallucinations (stripping markdown fences, deleting trailing commas, and extracting nested JSON blocks using regex).
* **Validation Alerts:** Issues visible warnings in the console for suspicious extractions (e.g., ₹0 rates, missing quantities, or enormous individual charges > ₹10,00,000) allowing manual verification without crashing.
* **Smart Filtering:** Detects and skips "Totals", "Sum", or "कुल" (Hindi) rows hallucinated by OCR or the LLM. It also deduplicates repeating items via `Challan No. + Date + Material` logic.
* **EXIF Rotation & Binarization:** Images from smartphones are auto-rotated based on EXIF metadata, scaled to fit API bandwidth limitations, denoised to remove physical paper specks, and thresholded for optimal contrast.

### 3. Advanced CLI & Python Module Actions
* **Batch Image Processing:** Supports passing an entire directory of photos using `--batch`. Yields independent invoices per image, counting iteratively upwards from a custom `--start` tag.
* **Combined Invoices:** Added `--combine` behavior, allowing multiple multi-page challan photos to be merged into a single, unified Excel/PDF output.
* **Professional Python Package:** Completely modularized the codebase into a standard `src/invoice_generator` package. Functions like `extract_from_image`, `images_to_invoice`, and the `BatchResult` dataclass are fully importable.

---

## 🛠️ Version 0.2.0 (Core Engine Enhancements)

### 1. Enterprise PDF Generation (`fpdf2`)
* Invoices can now be immediately materialized as structured PDFs reflecting the exact style, borders, and layouts natively designed in the Excel output.

### 2. Complete Configuration Layer (`config.yaml`)
* Sensitive data is fully decoupled from the code. All GSTNs, bank details, headers, company titles, and prefixes are read natively from `.yaml`.
* *(Note: Git history was rewritten to permanently scrub historical instances of sensitive PANs/GSTNs for security compliance).*

### 3. Data & Accounting Polish
* Date parsers natively process diverse inputs and Indian formats (`dd/mm/yyyy` and `dd-mm-yyyy`).
* Built dynamic row limits and calculated Grand Total column spacing, including traditional rounding mechanisms to avoid floating-point errors.
* Correct application of thick visual borders and cell-merges via custom Excel styling functions (`openpyxl`).

### 4. Testing Suite Consolidation (`pytest`)
* Wrote **102 distinct tests** validating the `generator` and `image_processor` systems entirely locally.
* Created programmatic Pillow (`PIL`) image-drawing setups that dynamically build image files inside memory at run-time to mock LLM interactions without storing `.jpg` files in the repository.

### 5. Professional Code Quality Rewrite
* Ripped out original procedural code constraints. Inserted static typing arrays, eliminated "magic numbers", built strict string documentation `"""` standards, and explicitly outlined helper functions to match top-tier enterprise architectures.
