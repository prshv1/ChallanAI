import logging
import re
from pathlib import Path
from typing import Optional, Union

import yaml

logger = logging.getLogger(__name__)

# ─── File Paths ───
INPUT_FILE = Path("Example Data/Raw_Data.xlsx")
OUTPUT_EXCEL = Path("Final_Output.xlsx")
CONFIG_FILE = Path("config.yaml")

# ─── Regex & Constants ───
_INVALID_SHEET_CHARS = re.compile(r"[\\/*?\[\]:]")
_MAX_SHEET_NAME_LENGTH = 31

DEFAULT_CONFIG = {
    "company": {
        "name": "YOUR COMPANY NAME",
        "subtitle": "(BUSINESS TYPE)",
        "address": "Your Address Here",
        "contact": "0000000000",
        "gstn": "00XXXXX0000X0XX",
        "pan": "XXXXX0000X",
    },
    "buyer": {
        "name": "BUYER NAME",
        "address": "Buyer Address",
        "gstn": "00XXXXX0000X0XX",
    },
    "bank": {
        "account_name": "YOUR COMPANY NAME",
        "bank_name": "BANK NAME",
        "account_no": "000000000000",
        "branch": "BRANCH",
        "ifsc": "XXXX0000000",
    },
    "gst": {
        "cgst_rate": 0.09,
        "sgst_rate": 0.09,
        "hsn_code": 996511,
    },
    "unit": "Tonne",
}


def load_config(config_path: Optional[Union[str, Path]] = None) -> dict:
    """
    Load business configuration from a YAML file.
    User provided values are merged on top of sensible defaults.
    """
    path = Path(config_path) if config_path else CONFIG_FILE

    if not path.exists():
        logger.warning(f"Config file not found at {path}, using defaults.")
        return DEFAULT_CONFIG.copy()

    with open(path, "r", encoding="utf-8") as file:
        user_config = yaml.safe_load(file) or {}

    merged = {}
    for section_name, default_values in DEFAULT_CONFIG.items():
        if isinstance(default_values, dict):
            merged[section_name] = {
                **default_values,
                **user_config.get(section_name, {}),
            }
        else:
            merged[section_name] = user_config.get(section_name, default_values)

    return merged


def sanitize_sheet_name(name: str) -> str:
    """Make a string safe for use as an Excel sheet name."""
    cleaned = _INVALID_SHEET_CHARS.sub("_", str(name))
    return cleaned[:_MAX_SHEET_NAME_LENGTH]
