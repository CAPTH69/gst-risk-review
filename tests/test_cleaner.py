"""
test_cleaner.py - Tests for data cleaning functions.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cleaner import (
    clean_invoice_no,
    clean_gstin,
    clean_amount,
    clean_purchase_register,
    clean_gstr2b,
)

DATA_DIR = Path(__file__).parent.parent / "data"


class TestCleanInvoiceNo:
    def test_strips_hyphens(self):
        assert clean_invoice_no("INV-2024-001") == "INV2024001"

    def test_uppercases(self):
        assert clean_invoice_no("inv2024001") == "INV2024001"

    def test_strips_leading_trailing_spaces(self):
        assert clean_invoice_no("  INV2024001  ") == "INV2024001"

    def test_removes_internal_spaces(self):
        assert clean_invoice_no(" inv 001 ") == "INV001"

    def test_strips_slashes(self):
        assert clean_invoice_no("INV/2024/001") == "INV2024001"

    def test_handles_none(self):
        assert clean_invoice_no(None) == ""

    def test_handles_nan(self):
        assert clean_invoice_no(float("nan")) == ""

    def test_handles_pd_na(self):
        assert clean_invoice_no(pd.NA) == ""

    def test_plain_string_unchanged_after_upper(self):
        assert clean_invoice_no("ABC123") == "ABC123"


class TestCleanGstin:
    def test_uppercases(self):
        assert clean_gstin("27aabcu9603r1zx") == "27AABCU9603R1ZX"

    def test_strips_whitespace(self):
        assert clean_gstin("  27AABCU9603R1ZX  ") == "27AABCU9603R1ZX"

    def test_handles_none(self):
        assert clean_gstin(None) == ""

    def test_handles_nan(self):
        assert clean_gstin(float("nan")) == ""

    def test_already_clean_unchanged(self):
        assert clean_gstin("29AADCS5739H1ZK") == "29AADCS5739H1ZK"


class TestCleanAmount:
    def test_removes_commas(self):
        assert clean_amount("1,00,000") == 100000.0

    def test_handles_none(self):
        assert clean_amount(None) == 0.0

    def test_handles_blank_string(self):
        assert clean_amount("") == 0.0

    def test_handles_nan(self):
        assert clean_amount(float("nan")) == 0.0

    def test_handles_integer(self):
        assert clean_amount(9000) == 9000.0

    def test_handles_float_string(self):
        assert clean_amount("4500.50") == 4500.50

    def test_handles_zero_string(self):
        assert clean_amount("0") == 0.0


class TestCleanPurchaseRegister:
    def test_adds_clean_invoice_no_column(self):
        df = pd.read_csv(DATA_DIR / "sample_purchase_register.csv")
        cleaned = clean_purchase_register(df)
        assert "clean_invoice_no" in cleaned.columns

    def test_adds_clean_supplier_gstin_column(self):
        df = pd.read_csv(DATA_DIR / "sample_purchase_register.csv")
        cleaned = clean_purchase_register(df)
        assert "clean_supplier_gstin" in cleaned.columns

    def test_does_not_modify_original_df(self):
        df = pd.read_csv(DATA_DIR / "sample_purchase_register.csv")
        original_cols = list(df.columns)
        clean_purchase_register(df)
        assert list(df.columns) == original_cols

    def test_total_itc_is_float(self):
        df = pd.read_csv(DATA_DIR / "sample_purchase_register.csv")
        cleaned = clean_purchase_register(df)
        assert cleaned["total_itc"].dtype == float

    def test_invoice_no_normalized(self):
        df = pd.read_csv(DATA_DIR / "sample_purchase_register.csv")
        cleaned = clean_purchase_register(df)
        # INV-2024-001 → INV2024001
        assert cleaned["clean_invoice_no"].iloc[0] == "INV2024001"


class TestCleanGstr2b:
    def test_adds_clean_columns(self):
        df = pd.read_csv(DATA_DIR / "sample_gstr2b.csv")
        cleaned = clean_gstr2b(df)
        assert "clean_invoice_no" in cleaned.columns
        assert "clean_supplier_gstin" in cleaned.columns

    def test_total_itc_is_float(self):
        df = pd.read_csv(DATA_DIR / "sample_gstr2b.csv")
        cleaned = clean_gstr2b(df)
        assert cleaned["total_itc"].dtype == float
