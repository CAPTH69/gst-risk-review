"""
cleaner.py - Normalize raw GST data before matching.

Raw CSV data from clients and the GST portal often has inconsistent formatting:
whitespace, different cases, hyphens vs no hyphens, commas in numbers, etc.
These functions normalize everything to a standard form before reconciliation.
"""

import pandas as pd


def clean_invoice_no(value):
    """
    Normalize an invoice number for reliable matching.

    Converts to uppercase, removes whitespace, hyphens, and slashes.
    Example: "inv-2024-001 " → "INV2024001"
    Returns "" for null/missing values.
    """
    if pd.isna(value):
        return ""
    return str(value).strip().upper().replace(" ", "").replace("-", "").replace("/", "")


def clean_gstin(value):
    """
    Normalize a GSTIN (supplier tax ID) for reliable matching.

    GSTINs are 15-character alphanumeric codes. Uppercase and strip whitespace.
    Example: " 27aabcu9603r1zx" → "27AABCU9603R1ZX"
    Returns "" for null/missing values.
    """
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def clean_amount(value):
    """
    Convert a numeric value to float, handling commas and null values.

    Example: "1,00,000" → 100000.0
    Returns 0.0 for null, blank, or unparseable values.
    """
    if pd.isna(value):
        return 0.0
    cleaned = str(value).strip().replace(",", "")
    if cleaned == "" or cleaned.lower() == "nan":
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# Columns that contain tax/amount data in purchase register and GSTR-2B
AMOUNT_COLUMNS = ["taxable_value", "cgst", "sgst", "igst", "total_itc"]


def clean_purchase_register(df):
    """
    Return a cleaned copy of the purchase register DataFrame.

    Adds:
      - clean_invoice_no: normalized invoice number
      - clean_supplier_gstin: normalized GSTIN

    Also normalizes all amount columns to float.
    """
    df = df.copy()
    df["clean_invoice_no"] = df["invoice_no"].apply(clean_invoice_no)
    df["clean_supplier_gstin"] = df["supplier_gstin"].apply(clean_gstin)
    for col in AMOUNT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(clean_amount)
    return df


def clean_gstr2b(df):
    """
    Return a cleaned copy of the GSTR-2B DataFrame.

    Same cleaning logic as clean_purchase_register.
    """
    df = df.copy()
    df["clean_invoice_no"] = df["invoice_no"].apply(clean_invoice_no)
    df["clean_supplier_gstin"] = df["supplier_gstin"].apply(clean_gstin)
    for col in AMOUNT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(clean_amount)
    return df
