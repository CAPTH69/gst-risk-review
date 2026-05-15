"""
test_data_loader.py - Tests for data loading functions.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

# Allow importing from src/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_loader import load_csv, load_purchase_register, load_gstr2b, load_supplier_master

# Paths to sample data
DATA_DIR = Path(__file__).parent.parent / "data"


class TestLoadCsv:
    def test_load_csv_returns_dataframe(self):
        df = load_csv(DATA_DIR / "sample_purchase_register.csv")
        assert isinstance(df, pd.DataFrame)

    def test_load_csv_has_rows(self):
        df = load_csv(DATA_DIR / "sample_purchase_register.csv")
        assert len(df) > 0

    def test_load_csv_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_csv(tmp_path / "does_not_exist.csv")

    def test_load_csv_empty_file_raises_value_error(self, tmp_path):
        # Create a CSV with only a header and no data rows
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("invoice_no,supplier_gstin\n")
        with pytest.raises(ValueError, match="empty"):
            load_csv(empty_csv)


class TestLoadPurchaseRegister:
    def test_load_purchase_register_returns_dataframe(self):
        df = load_purchase_register(DATA_DIR / "sample_purchase_register.csv")
        assert isinstance(df, pd.DataFrame)

    def test_load_purchase_register_row_count(self):
        df = load_purchase_register(DATA_DIR / "sample_purchase_register.csv")
        # Sample file has 20 rows (including 1 duplicate)
        assert len(df) == 20

    def test_load_purchase_register_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_purchase_register(tmp_path / "missing.csv")


class TestLoadGstr2b:
    def test_load_gstr2b_returns_dataframe(self):
        df = load_gstr2b(DATA_DIR / "sample_gstr2b.csv")
        assert isinstance(df, pd.DataFrame)

    def test_load_gstr2b_row_count(self):
        df = load_gstr2b(DATA_DIR / "sample_gstr2b.csv")
        # Sample GSTR-2B has 18 rows
        assert len(df) == 18

    def test_load_gstr2b_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_gstr2b(tmp_path / "missing.csv")


class TestLoadSupplierMaster:
    def test_load_supplier_master_returns_dataframe(self):
        df = load_supplier_master(DATA_DIR / "sample_supplier_master.csv")
        assert isinstance(df, pd.DataFrame)

    def test_load_supplier_master_row_count(self):
        df = load_supplier_master(DATA_DIR / "sample_supplier_master.csv")
        # Sample supplier master has 10 rows
        assert len(df) == 10

    def test_load_supplier_master_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_supplier_master(tmp_path / "missing.csv")
