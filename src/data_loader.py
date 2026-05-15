"""
data_loader.py - Load GST-related CSV files into pandas DataFrames.

Each function checks that the file exists and is not empty before returning data.
"""

from pathlib import Path
import pandas as pd


def load_csv(file_path):
    """
    Generic CSV loader. Returns a pandas DataFrame.

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError if the file is empty (no rows).
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"File is empty (no rows): {path.name}")

    return df


def load_purchase_register(file_path):
    """
    Load the purchase register CSV.
    Returns a DataFrame with all purchase invoices.
    """
    df = load_csv(file_path)
    return df


def load_gstr2b(file_path):
    """
    Load the GSTR-2B CSV (auto-populated ITC statement from GST portal).
    Returns a DataFrame with supplier-reported invoices.
    """
    df = load_csv(file_path)
    return df


def load_supplier_master(file_path):
    """
    Load the supplier master CSV.
    Returns a DataFrame with supplier GSTIN status and risk notes.
    """
    df = load_csv(file_path)
    return df
