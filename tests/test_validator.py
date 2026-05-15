"""
test_validator.py - Tests for column validation functions.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_loader import load_purchase_register, load_gstr2b, load_supplier_master
from validator import (
    validate_required_columns,
    validate_purchase_register,
    validate_gstr2b,
    validate_supplier_master,
    PURCHASE_REQUIRED_COLUMNS,
    GSTR2B_REQUIRED_COLUMNS,
    SUPPLIER_REQUIRED_COLUMNS,
)

DATA_DIR = Path(__file__).parent.parent / "data"


class TestValidateRequiredColumns:
    def test_passes_when_all_columns_present(self):
        df = pd.DataFrame(columns=["col_a", "col_b", "col_c"])
        result = validate_required_columns(df, ["col_a", "col_b"], "test.csv")
        assert result is True

    def test_raises_value_error_when_column_missing(self):
        df = pd.DataFrame(columns=["col_a"])
        with pytest.raises(ValueError, match="Missing columns in test.csv"):
            validate_required_columns(df, ["col_a", "col_b"], "test.csv")

    def test_error_message_names_missing_column(self):
        df = pd.DataFrame(columns=["invoice_no"])
        with pytest.raises(ValueError, match="supplier_gstin"):
            validate_required_columns(df, ["invoice_no", "supplier_gstin"], "test.csv")

    def test_error_message_includes_file_label(self):
        df = pd.DataFrame(columns=[])
        with pytest.raises(ValueError, match="my_file.csv"):
            validate_required_columns(df, ["invoice_no"], "my_file.csv")


class TestValidatePurchaseRegister:
    def test_valid_purchase_register_passes(self):
        df = load_purchase_register(DATA_DIR / "sample_purchase_register.csv")
        assert validate_purchase_register(df) is True

    def test_purchase_register_missing_column_raises(self):
        # Build a DataFrame that is missing 'total_itc'
        df = pd.DataFrame(columns=[c for c in PURCHASE_REQUIRED_COLUMNS if c != "total_itc"])
        with pytest.raises(ValueError, match="total_itc"):
            validate_purchase_register(df)

    def test_purchase_register_missing_gstin_raises(self):
        df = pd.DataFrame(columns=[c for c in PURCHASE_REQUIRED_COLUMNS if c != "supplier_gstin"])
        with pytest.raises(ValueError, match="supplier_gstin"):
            validate_purchase_register(df)


class TestValidateGstr2b:
    def test_valid_gstr2b_passes(self):
        df = load_gstr2b(DATA_DIR / "sample_gstr2b.csv")
        assert validate_gstr2b(df) is True

    def test_gstr2b_missing_column_raises(self):
        df = pd.DataFrame(columns=[c for c in GSTR2B_REQUIRED_COLUMNS if c != "igst"])
        with pytest.raises(ValueError, match="igst"):
            validate_gstr2b(df)


class TestValidateSupplierMaster:
    def test_valid_supplier_master_passes(self):
        df = load_supplier_master(DATA_DIR / "sample_supplier_master.csv")
        assert validate_supplier_master(df) is True

    def test_supplier_master_missing_column_raises(self):
        df = pd.DataFrame(columns=[c for c in SUPPLIER_REQUIRED_COLUMNS if c != "gstin_status"])
        with pytest.raises(ValueError, match="gstin_status"):
            validate_supplier_master(df)

    def test_supplier_master_missing_risk_note_raises(self):
        df = pd.DataFrame(columns=[c for c in SUPPLIER_REQUIRED_COLUMNS if c != "risk_note"])
        with pytest.raises(ValueError, match="risk_note"):
            validate_supplier_master(df)
