import logging
import pandas as pd

logger = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "Date",
    "Challan No.",
    "Vehicle No.",
    "Site",
    "Material",
    "Quantity",
    "Rate",
    "Per",
]


def convert_records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    """
    Convert a list of raw dictionaries into a normalized Pandas DataFrame.
    Filters out 'Total' or 'Summary' rows implicitly derived by LLMs.
    """
    if not records:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = pd.DataFrame(records)

    string_cols = df.select_dtypes(include="object").columns

    # Filter out summary/total rows
    mask = pd.Series([False] * len(df), index=df.index)
    for index, row in df.iterrows():
        row_str = " ".join(
            str(val).lower() for col, val in row.items() if col in string_cols
        )
        if any(keyword in row_str for keyword in ("total", "कुल")):
            mask[index] = True

    df = df[~mask].copy()
    df = df.reset_index(drop=True)

    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    return df


def generate_validation_warnings(dataframe: pd.DataFrame) -> list[str]:
    """Inspects the given delivery records DataFrame for data issues like missing limits and generates warnings."""
    warnings = []

    column_mapping = {}
    for expected_column in OUTPUT_COLUMNS:
        for actual_column in dataframe.columns:
            if (
                str(actual_column).lower().replace("_", " ").strip()
                == expected_column.lower()
            ):
                column_mapping[actual_column] = expected_column

    df = dataframe.rename(columns=column_mapping)

    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype=float if col in ("Quantity", "Rate") else object)

    missing_qty = int(df["Quantity"].isna().sum())
    missing_rate = int(df["Rate"].isna().sum())

    if missing_qty > 0:
        warnings.append(f"{missing_qty} row(s) have missing Quantity")
    if missing_rate > 0:
        warnings.append(f"{missing_rate} row(s) have missing Rate")

    zero_qty = int((df["Quantity"] == 0).sum())
    zero_rate = int((df["Rate"] == 0).sum())

    if zero_qty > 0:
        warnings.append(f"{zero_qty} row(s) have Quantity = 0")
    if zero_rate > 0:
        warnings.append(f"{zero_rate} row(s) have Rate = 0")

    line_amounts = df["Quantity"].fillna(0) * df["Rate"].fillna(0)
    large_amounts = line_amounts[line_amounts > 1_000_000]
    if len(large_amounts) > 0:
        warnings.append(
            f"{len(large_amounts)} row(s) have Amount > ₹10,00,000 — verify these are correct"
        )

    empty_sites = int((df["Site"].astype(str).str.strip() == "").sum())
    empty_materials = int((df["Material"].astype(str).str.strip() == "").sum())

    if empty_sites > 0:
        warnings.append(f"{empty_sites} row(s) have empty Site")
    if empty_materials > 0:
        warnings.append(f"{empty_materials} row(s) have empty Material")

    return warnings
