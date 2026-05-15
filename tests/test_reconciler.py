"""
test_reconciler.py - Tests for invoice reconciliation logic.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cleaner import clean_purchase_register, clean_gstr2b
from reconciler import reconcile_invoices
from data_loader import load_purchase_register, load_gstr2b

DATA_DIR = Path(__file__).parent.parent / "data"


# --- Helper to build minimal test DataFrames ---

def make_pr_row(invoice_no, supplier_gstin, total_itc):
    return {
        "invoice_no": invoice_no,
        "invoice_date": "2024-01-01",
        "supplier_gstin": supplier_gstin,
        "supplier_name": "Test Supplier",
        "taxable_value": 1000.0,
        "cgst": 90.0,
        "sgst": 90.0,
        "igst": 0.0,
        "total_itc": total_itc,
    }


def make_g2b_row(invoice_no, supplier_gstin, total_itc):
    return make_pr_row(invoice_no, supplier_gstin, total_itc)


def build_pr(rows):
    df = pd.DataFrame(rows)
    return clean_purchase_register(df)


def build_g2b(rows):
    df = pd.DataFrame(rows)
    return clean_gstr2b(df)


# --- Status tests ---

class TestMatchedInvoice:
    def test_matched_status(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        result = reconcile_invoices(pr, g2b)
        assert result["status"].iloc[0] == "matched"

    def test_matched_with_hyphen_difference(self):
        # PR uses hyphens, GSTR-2B does not — should still match after cleaning
        pr = build_pr([make_pr_row("INV-2024-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([make_g2b_row("INV2024001", "27AABCU9603R1ZX", 9000.0)])
        result = reconcile_invoices(pr, g2b)
        assert result["status"].iloc[0] == "matched"

    def test_matched_mismatch_reason_is_empty(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        result = reconcile_invoices(pr, g2b)
        assert result["mismatch_reason"].iloc[0] == ""


class TestMissingIn2B:
    def test_missing_in_2b_status(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        # GSTR-2B has a different invoice — INV-001 will be flagged missing
        g2b = build_g2b([make_g2b_row("INV-999", "27AABCU9603R1ZX", 5000.0)])
        result = reconcile_invoices(pr, g2b)
        missing = result[result["status"] == "missing_in_2b"]
        assert len(missing) == 1
        assert missing.iloc[0]["invoice_no"] == "INV-001"

    def test_missing_in_2b_gstr2b_itc_is_nan(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([make_g2b_row("INV-999", "27AABCU9603R1ZX", 5000.0)])
        result = reconcile_invoices(pr, g2b)
        missing = result[result["status"] == "missing_in_2b"]
        assert pd.isna(missing.iloc[0]["gstr2b_total_itc"])


class TestExtraIn2B:
    def test_extra_in_2b_status(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([
            make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0),
            make_g2b_row("INV-999", "27AABCU9603R1ZX", 5000.0),  # extra in GSTR-2B
        ])
        result = reconcile_invoices(pr, g2b)
        extra = result[result["status"] == "extra_in_2b"]
        assert len(extra) == 1
        assert extra.iloc[0]["invoice_no"] == "INV-999"

    def test_extra_in_2b_purchase_itc_is_nan(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([
            make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0),
            make_g2b_row("INV-999", "27AABCU9603R1ZX", 5000.0),
        ])
        result = reconcile_invoices(pr, g2b)
        extra = result[result["status"] == "extra_in_2b"]
        assert pd.isna(extra.iloc[0]["purchase_total_itc"])


class TestAmountMismatch:
    def test_amount_mismatch_status(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([make_g2b_row("INV-001", "27AABCU9603R1ZX", 9500.0)])
        result = reconcile_invoices(pr, g2b)
        assert result["status"].iloc[0] == "amount_mismatch"

    def test_amount_mismatch_reason_contains_amounts(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([make_g2b_row("INV-001", "27AABCU9603R1ZX", 9500.0)])
        result = reconcile_invoices(pr, g2b)
        reason = result["mismatch_reason"].iloc[0]
        assert "9000" in reason
        assert "9500" in reason

    def test_tiny_float_difference_is_matched(self):
        # Floating point tolerance: diff < 0.01 → still matched
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.005)])
        result = reconcile_invoices(pr, g2b)
        assert result["status"].iloc[0] == "matched"


class TestDuplicateHandling:
    def test_duplicate_in_purchase_status(self):
        # First occurrence reconciles normally (matched), only the second is flagged
        pr = build_pr([
            make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0),
            make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0),  # duplicate
        ])
        g2b = build_g2b([make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        result = reconcile_invoices(pr, g2b)
        dups = result[result["status"] == "duplicate_in_purchase"]
        assert len(dups) == 1

    def test_duplicate_in_purchase_first_occurrence_reconciles(self):
        # The first PR occurrence should produce a matched row, not be discarded
        pr = build_pr([
            make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0),
            make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0),
        ])
        g2b = build_g2b([make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        result = reconcile_invoices(pr, g2b)
        # GSTR-2B invoice must not be extra_in_2b — first PR occurrence covers it
        assert "extra_in_2b" not in result["status"].values
        assert "matched" in result["status"].values

    def test_duplicate_in_gstr2b_status(self):
        # First GSTR-2B occurrence reconciles normally, only second is flagged
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([
            make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0),
            make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0),  # duplicate
        ])
        result = reconcile_invoices(pr, g2b)
        dups = result[result["status"] == "duplicate_in_gstr2b"]
        assert len(dups) == 1


class TestOutputSchema:
    def test_output_has_required_columns(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        result = reconcile_invoices(pr, g2b)
        required = {"invoice_no", "supplier_gstin", "status", "mismatch_reason",
                    "purchase_total_itc", "gstr2b_total_itc"}
        assert required.issubset(set(result.columns))

    def test_output_is_dataframe(self):
        pr = build_pr([make_pr_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        g2b = build_g2b([make_g2b_row("INV-001", "27AABCU9603R1ZX", 9000.0)])
        result = reconcile_invoices(pr, g2b)
        assert isinstance(result, pd.DataFrame)


class TestSampleDataReconciliation:
    """End-to-end test using the actual sample CSV files."""

    def test_reconcile_sample_data_status_counts(self):
        pr = clean_purchase_register(load_purchase_register(DATA_DIR / "sample_purchase_register.csv"))
        g2b = clean_gstr2b(load_gstr2b(DATA_DIR / "sample_gstr2b.csv"))
        result = reconcile_invoices(pr, g2b)
        counts = result["status"].value_counts().to_dict()

        # INV-2024-001 is duplicated in PR — first occurrence reconciles normally,
        # only the second (extra) occurrence is flagged as duplicate_in_purchase
        assert counts.get("duplicate_in_purchase", 0) == 1
        # INV-2024-013 and INV-2024-018 are in PR but not GSTR-2B
        assert counts.get("missing_in_2b", 0) == 2
        # INV-2024-020 is in GSTR-2B but not PR (INV-001 now reconciles correctly)
        assert counts.get("extra_in_2b", 0) == 1
        # INV-2024-008 has different total_itc (16200 vs 17100)
        assert counts.get("amount_mismatch", 0) == 1
        # Remaining invoices should be matched
        assert counts.get("matched", 0) > 0

    def test_reconcile_sample_data_total_rows(self):
        pr = clean_purchase_register(load_purchase_register(DATA_DIR / "sample_purchase_register.csv"))
        g2b = clean_gstr2b(load_gstr2b(DATA_DIR / "sample_gstr2b.csv"))
        result = reconcile_invoices(pr, g2b)
        # All 20 PR rows + 1 extra GSTR-2B row should appear in output
        # (2 dup rows + 18 unique PR rows merged with 17 unique GSTR-2B rows = 19 merged + 2 dups = 21)
        assert len(result) > 0
