# Todo list for Python Module & Features

## Python Module Improvements
- Add `__main__.py` to `src/invoice_generator/` to support clean execution via `python -m invoice_generator` (doing `python -c "from invoice_generator.cli import main_generator"` is too verbose for users).
- Explicitly expose the `extract_from_image` function in `__init__.py` and abstract it so power users can run OCR/LLMs individually, beyond just running `images_to_invoice`.
- Add mapping to `pyproject.toml` or `setup.py` so the module installs a native CLI bin like `invoice-gen`.

## CI & Testing
- We temporarily deleted our tests directory! We need to recreate `tests/test_generation.py` (with the 250 test suite logic we built), `tests/test_image_processor.py`, and `tests/test_invoices.py` so the CI/CD pipeline remains green.
- Add GitHub Actions workflows to auto-build and run the tests on pushes to `main`.

## Upcoming Features (from README Roadmap)
- [ ] Web interface — browser-based upload & download
- [ ] Email integration — auto-send invoices to buyers
- [ ] IGST support — inter-state invoice detection
