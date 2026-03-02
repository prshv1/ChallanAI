import calendar
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd
from invoice_generator.core.config import load_config

logger = logging.getLogger(__name__)

# ─── Dates and Numbers ───


def get_fiscal_year(date: datetime) -> str:
    """Return the Indian fiscal year (e.g., '23-24') for a given date."""
    year = date.year
    if date.month <= 3:
        return f"{str(year - 1)[-2:]}-{str(year)[-2:]}"
    return f"{str(year)[-2:]}-{str(year + 1)[-2:]}"


def get_invoice_date(data_date: datetime) -> datetime:
    """Return the last day of the month for the given delivery date."""
    last_day = calendar.monthrange(data_date.year, data_date.month)[1]
    return datetime(data_date.year, data_date.month, last_day)


def format_date_short(date: Any) -> str:
    """Format a pandas timestamp to 'DD/MM' safely."""
    if pd.isna(date):
        return ""
    if isinstance(date, str):
        try:
            date = pd.to_datetime(date, dayfirst=True)
        except ValueError:
            return date
    return date.strftime("%d/%m")


def parse_dates(date_series: pd.Series) -> pd.Series:
    """Parse a pandas Series of dates, handling multiple formats robustly."""
    try:
        return pd.to_datetime(date_series, format="%d/%m/%Y", errors="coerce")
    except Exception:
        pass
    try:
        return pd.to_datetime(date_series, dayfirst=True, errors="coerce")
    except Exception:
        pass
    return pd.to_datetime(date_series, errors="coerce")


def round_conventional(value: float) -> int:
    """Round to the nearest integer. .5 rounds up (Python's round() rounds to even)."""
    return math.floor(value + 0.5)


class DataProcessor:
    """Processor responsible for sanitizing and grouping flat delivery records."""

    def __init__(
        self, input_file: Union[str, Path], inv_num: int, config: Optional[dict] = None
    ):
        self.input_file = Path(input_file)
        self.inv_num = inv_num
        self.config = config or load_config()

    def process(self) -> dict[str, Any]:
        """Read, validate, structure, and compute raw delivery data."""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")

        try:
            df = pd.read_excel(self.input_file, engine="openpyxl")
        except Exception as read_error:
            raise ValueError(
                f"Failed to read Excel file '{self.input_file.name}': {read_error}"
            )

        expected_columns = {"Date", "Site", "Material", "Quantity", "Rate"}
        actual_columns = set(df.columns)
        missing_columns = expected_columns - actual_columns
        if missing_columns:
            raise ValueError(
                f"Input file is missing required columns: {', '.join(missing_columns)}"
            )

        df["Date"] = parse_dates(df["Date"])
        df = df.dropna(subset=["Date", "Site", "Material"])

        if df.empty:
            raise ValueError("No valid data rows found after filtering empty records.")

        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
        df["Rate"] = pd.to_numeric(df["Rate"], errors="coerce")
        df = df.dropna(subset=["Quantity", "Rate"])

        if df.empty:
            raise ValueError("No valid numeric data found for Quantity / Rate.")

        materials = df["Material"].dropna().unique().tolist()
        sites_data = []

        total_amount = 0.0

        for site, site_group in df.groupby("Site"):
            min_date = site_group["Date"].min()
            max_date = site_group["Date"].max()
            date_range_label = (
                f"DT: {format_date_short(min_date)} TO {format_date_short(max_date)}"
            )

            site_info = {
                "site_name": str(site).strip(),
                "date_range_label": date_range_label,
                "material_data": {},
            }

            for material in materials:
                material_group = site_group[site_group["Material"] == material]
                if not material_group.empty:
                    qty = material_group["Quantity"].sum()
                    rate = material_group["Rate"].iloc[0]
                    site_info["material_data"][material] = {"qty": qty, "rate": rate}
                    total_amount += qty * rate

            sites_data.append(site_info)

        cgst_amount = round(total_amount * self.config["gst"]["cgst_rate"], 2)
        sgst_amount = round(total_amount * self.config["gst"]["sgst_rate"], 2)

        exact_grand_total = total_amount + cgst_amount + sgst_amount
        grand_total = round_conventional(exact_grand_total)
        round_off = round(grand_total - exact_grand_total, 2)

        baseline_date = df["Date"].max()
        if pd.isna(baseline_date):
            baseline_date = datetime.now()

        return {
            "df": df,
            "sites_data": sites_data,
            "materials": materials,
            "total_amount": total_amount,
            "cgst_amount": cgst_amount,
            "sgst_amount": sgst_amount,
            "grand_total": grand_total,
            "round_off": round_off,
            "invoice_date": get_invoice_date(baseline_date),
            "fiscal_year": get_fiscal_year(baseline_date),
            "inv_num": self.inv_num,
            "config": self.config,
            "unit": self.config.get("unit", "Tonne"),
        }
