"""
validator.py - Validate that loaded DataFrames contain the expected columns.

Raises clear ValueError messages so the user knows exactly what is missing,
instead of getting a confusing pandas KeyError.
"""

import pandas as pd

# Required columns for each CSV file type
PURCHASE_REQUIRED_COLUMNS = [
    "invoice_no",
    "invoice_date",
    "supplier_gstin",
    "supplier_name",
    "taxable_value",
    "cgst",
    "sgst",
    "igst",
    "total_itc",
]

GSTR2B_REQUIRED_COLUMNS = [
    "invoice_no",
    "invoice_date",
    "supplier_gstin",
    "supplier_name",
    "taxable_value",
    "cgst",
    "sgst",
    "igst",
    "total_itc",
]

SUPPLIER_REQUIRED_COLUMNS = [
    "supplier_gstin",
    "supplier_name",
    "gstin_status",
    "return_filing_status",
    "risk_note",
]


def validate_required_columns(df, required_columns, file_label):
    """
    Check that all required columns exist in the DataFrame.

    Args:
        df: pandas DataFrame to check.
        required_columns: list of column names that must be present.
        file_label: a human-readable name for the file (used in error messages).

    Returns:
        True if all columns are present.

    Raises:
        ValueError: lists every missing column so the user can fix them all at once.
    """
    actual_columns = set(df.columns.tolist())
    required_set = set(required_columns)
    missing = required_set - actual_columns

    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Missing columns in {file_label}: {missing_list}")

    return True


def validate_purchase_register(df):
    """Validate the purchase register DataFrame."""
    return validate_required_columns(df, PURCHASE_REQUIRED_COLUMNS, "purchase_register.csv")


def validate_gstr2b(df):
    """Validate the GSTR-2B DataFrame."""
    return validate_required_columns(df, GSTR2B_REQUIRED_COLUMNS, "gstr2b.csv")


def validate_supplier_master(df):
    """Validate the supplier master DataFrame."""
    return validate_required_columns(df, SUPPLIER_REQUIRED_COLUMNS, "supplier_master.csv")
