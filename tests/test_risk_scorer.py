"""
test_risk_scorer.py - Tests for supplier risk scoring functions.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from risk_scorer import (
    clean_supplier_status,
    clean_return_filing_status,
    calculate_supplier_risk_score,
    get_risk_level,
    build_risk_reasons,
    add_supplier_risk,
)
from cleaner import clean_purchase_register, clean_gstr2b
from reconciler import reconcile_invoices
from data_loader import load_purchase_register, load_gstr2b, load_supplier_master

DATA_DIR = Path(__file__).parent.parent / "data"


# --- Helpers ---

def score(gstin_status="ACTIVE", filing_status="REGULAR FILER",
          recon_status="matched", found=True):
    """Shorthand to call calculate_supplier_risk_score."""
    return calculate_supplier_risk_score(gstin_status, filing_status, recon_status, found)


def level(gstin_status="ACTIVE", filing_status="REGULAR FILER",
          recon_status="matched", found=True):
    """Shorthand to get risk level directly."""
    return get_risk_level(score(gstin_status, filing_status, recon_status, found))


# --- Cleaner tests ---

class TestCleanSupplierStatus:
    def test_uppercases(self):
        assert clean_supplier_status("active") == "ACTIVE"

    def test_strips_whitespace(self):
        assert clean_supplier_status("  Inactive  ") == "INACTIVE"

    def test_handles_none(self):
        assert clean_supplier_status(None) == ""

    def test_handles_nan(self):
        assert clean_supplier_status(float("nan")) == ""


class TestCleanReturnFilingStatus:
    def test_uppercases(self):
        assert clean_return_filing_status("Regular Filer") == "REGULAR FILER"

    def test_strips_whitespace(self):
        assert clean_return_filing_status("  Non-Filer  ") == "NON-FILER"

    def test_handles_none(self):
        assert clean_return_filing_status(None) == ""


# --- Score calculation tests ---

class TestCalculateSupplierRiskScore:
    def test_active_regular_matched_is_zero(self):
        assert score() == 0

    def test_inactive_gstin_alone_is_75(self):
        assert score(gstin_status="INACTIVE") == 75

    def test_inactive_gstin_alone_is_high(self):
        assert level(gstin_status="INACTIVE") == "High"

    def test_suspended_gstin_alone_is_75(self):
        assert score(gstin_status="SUSPENDED") == 75

    def test_suspended_gstin_alone_is_high(self):
        assert level(gstin_status="SUSPENDED") == "High"

    def test_non_filer_alone_is_75(self):
        assert score(filing_status="NON-FILER") == 75

    def test_non_filer_alone_is_high(self):
        assert level(filing_status="NON-FILER") == "High"

    def test_non_filer_variant_with_space(self):
        # "NON FILER" (no hyphen) should also trigger
        assert score(filing_status="NON FILER") == 75

    def test_irregular_filer_alone_is_40(self):
        assert score(filing_status="IRREGULAR FILER") == 40

    def test_irregular_filer_alone_is_medium(self):
        assert level(filing_status="IRREGULAR FILER") == "Medium"

    def test_missing_in_2b_alone_is_40(self):
        assert score(recon_status="missing_in_2b") == 40

    def test_missing_in_2b_alone_is_medium(self):
        assert level(recon_status="missing_in_2b") == "Medium"

    def test_amount_mismatch_alone_is_35(self):
        assert score(recon_status="amount_mismatch") == 35

    def test_amount_mismatch_alone_is_medium(self):
        assert level(recon_status="amount_mismatch") == "Medium"

    def test_duplicate_in_purchase_alone_is_75(self):
        assert score(recon_status="duplicate_in_purchase") == 75

    def test_duplicate_in_purchase_alone_is_high(self):
        assert level(recon_status="duplicate_in_purchase") == "High"

    def test_extra_in_2b_alone_is_10(self):
        assert score(recon_status="extra_in_2b") == 10

    def test_extra_in_2b_alone_is_low(self):
        assert level(recon_status="extra_in_2b") == "Low"

    def test_unknown_supplier_alone_is_35(self):
        assert score(found=False) == 35

    def test_unknown_supplier_alone_is_medium(self):
        assert level(found=False) == "Medium"

    def test_score_capped_at_100(self):
        # inactive(75) + non-filer(75) + missing(40) = 190 → capped at 100
        s = score(gstin_status="INACTIVE", filing_status="NON-FILER",
                  recon_status="missing_in_2b")
        assert s == 100

    def test_inactive_non_filer_missing_is_high(self):
        assert level(gstin_status="INACTIVE", filing_status="NON-FILER",
                     recon_status="missing_in_2b") == "High"

    def test_irregular_filer_missing_in_2b_is_high(self):
        # 40 (irregular) + 40 (missing) = 80 → High
        assert level(filing_status="IRREGULAR FILER", recon_status="missing_in_2b") == "High"

    def test_non_filer_does_not_also_trigger_irregular(self):
        # A Non-Filer should NOT also add Irregular points (elif guards this)
        s = score(filing_status="NON-FILER")
        assert s == 75  # not 75+40


# --- Risk level tests ---

class TestGetRiskLevel:
    def test_score_0_is_low(self):
        assert get_risk_level(0) == "Low"

    def test_score_30_is_low(self):
        assert get_risk_level(30) == "Low"

    def test_score_31_is_medium(self):
        assert get_risk_level(31) == "Medium"

    def test_score_70_is_medium(self):
        assert get_risk_level(70) == "Medium"

    def test_score_71_is_high(self):
        assert get_risk_level(71) == "High"

    def test_score_100_is_high(self):
        assert get_risk_level(100) == "High"


# --- Reason string tests ---

class TestBuildRiskReasons:
    def test_no_risk_returns_default_message(self):
        result = build_risk_reasons("ACTIVE", "REGULAR FILER", "matched", True)
        assert result == "No major supplier risk detected"

    def test_inactive_gstin_reason(self):
        result = build_risk_reasons("INACTIVE", "REGULAR FILER", "matched", True)
        assert "Inactive GSTIN" in result

    def test_suspended_gstin_reason(self):
        result = build_risk_reasons("SUSPENDED", "REGULAR FILER", "matched", True)
        assert "Suspended GSTIN" in result

    def test_non_filer_reason(self):
        result = build_risk_reasons("ACTIVE", "NON-FILER", "matched", True)
        assert "Non-filer supplier" in result

    def test_irregular_filer_reason(self):
        result = build_risk_reasons("ACTIVE", "IRREGULAR FILER", "matched", True)
        assert "Irregular filer" in result

    def test_missing_in_2b_reason(self):
        result = build_risk_reasons("ACTIVE", "REGULAR FILER", "missing_in_2b", True)
        assert "Invoice missing in GSTR-2B" in result

    def test_amount_mismatch_reason(self):
        result = build_risk_reasons("ACTIVE", "REGULAR FILER", "amount_mismatch", True)
        assert "Amount mismatch" in result

    def test_duplicate_reason(self):
        result = build_risk_reasons("ACTIVE", "REGULAR FILER", "duplicate_in_purchase", True)
        assert "Duplicate invoice in purchase register" in result

    def test_extra_in_2b_reason(self):
        result = build_risk_reasons("ACTIVE", "REGULAR FILER", "extra_in_2b", True)
        assert "Invoice only in GSTR-2B" in result

    def test_unknown_supplier_reason(self):
        result = build_risk_reasons("", "", "matched", False)
        assert "Supplier not found in master" in result

    def test_multiple_reasons_combined(self):
        result = build_risk_reasons("INACTIVE", "NON-FILER", "missing_in_2b", True)
        assert "Inactive GSTIN" in result
        assert "Non-filer supplier" in result
        assert "Invoice missing in GSTR-2B" in result

    def test_multiple_reasons_separated_by_semicolon(self):
        result = build_risk_reasons("INACTIVE", "NON-FILER", "matched", True)
        assert ";" in result


# --- Integration tests ---

class TestAddSupplierRisk:
    def _make_recon_row(self, invoice_no, supplier_gstin, status="matched"):
        return {
            "invoice_no": invoice_no,
            "supplier_gstin": supplier_gstin,
            "status": status,
            "mismatch_reason": "",
            "purchase_total_itc": 9000.0,
            "gstr2b_total_itc": 9000.0,
        }

    def _make_supplier_row(self, gstin, gstin_status="Active", filing_status="Regular Filer"):
        return {
            "supplier_gstin": gstin,
            "supplier_name": "Test Supplier",
            "gstin_status": gstin_status,
            "return_filing_status": filing_status,
            "risk_note": "",
        }

    def test_no_rows_dropped(self):
        recon = pd.DataFrame([
            self._make_recon_row("INV-001", "27AABCU9603R1ZX"),
            self._make_recon_row("INV-002", "29AADCS5739H1ZK"),
        ])
        sm = pd.DataFrame([self._make_supplier_row("27AABCU9603R1ZX")])
        result = add_supplier_risk(recon, sm)
        assert len(result) == 2

    def test_has_risk_score_column(self):
        recon = pd.DataFrame([self._make_recon_row("INV-001", "27AABCU9603R1ZX")])
        sm = pd.DataFrame([self._make_supplier_row("27AABCU9603R1ZX")])
        result = add_supplier_risk(recon, sm)
        assert "supplier_risk_score" in result.columns

    def test_has_risk_level_column(self):
        recon = pd.DataFrame([self._make_recon_row("INV-001", "27AABCU9603R1ZX")])
        sm = pd.DataFrame([self._make_supplier_row("27AABCU9603R1ZX")])
        result = add_supplier_risk(recon, sm)
        assert "supplier_risk_level" in result.columns

    def test_unknown_supplier_no_crash(self):
        # Supplier GSTIN not in master — should still produce a valid row
        recon = pd.DataFrame([self._make_recon_row("INV-001", "UNKNOWN999")])
        sm = pd.DataFrame([self._make_supplier_row("27AABCU9603R1ZX")])
        result = add_supplier_risk(recon, sm)
        assert len(result) == 1
        assert result.iloc[0]["supplier_name"] == "Unknown Supplier"

    def test_unknown_supplier_is_medium(self):
        recon = pd.DataFrame([self._make_recon_row("INV-001", "UNKNOWN999")])
        sm = pd.DataFrame([self._make_supplier_row("27AABCU9603R1ZX")])
        result = add_supplier_risk(recon, sm)
        assert result.iloc[0]["supplier_risk_level"] == "Medium"

    def test_inactive_supplier_is_high(self):
        recon = pd.DataFrame([self._make_recon_row("INV-001", "27AABCU9603R1ZX")])
        sm = pd.DataFrame([self._make_supplier_row("27AABCU9603R1ZX",
                                                    gstin_status="Inactive",
                                                    filing_status="Non-Filer")])
        result = add_supplier_risk(recon, sm)
        assert result.iloc[0]["supplier_risk_level"] == "High"

    def test_case_insensitive_join(self):
        # Supplier master GSTIN is lowercase — join should still work after cleaning
        recon = pd.DataFrame([self._make_recon_row("INV-001", "27AABCU9603R1ZX")])
        sm = pd.DataFrame([self._make_supplier_row("27aabcu9603r1zx")])
        result = add_supplier_risk(recon, sm)
        assert result.iloc[0]["supplier_name"] == "Test Supplier"

    def test_sample_data_no_rows_dropped(self):
        pr = clean_purchase_register(load_purchase_register(DATA_DIR / "sample_purchase_register.csv"))
        g2b = clean_gstr2b(load_gstr2b(DATA_DIR / "sample_gstr2b.csv"))
        sm = load_supplier_master(DATA_DIR / "sample_supplier_master.csv")
        recon = reconcile_invoices(pr, g2b)
        result = add_supplier_risk(recon, sm)
        assert len(result) == len(recon)

    def test_sample_data_high_risk_invoices_exist(self):
        pr = clean_purchase_register(load_purchase_register(DATA_DIR / "sample_purchase_register.csv"))
        g2b = clean_gstr2b(load_gstr2b(DATA_DIR / "sample_gstr2b.csv"))
        sm = load_supplier_master(DATA_DIR / "sample_supplier_master.csv")
        recon = reconcile_invoices(pr, g2b)
        result = add_supplier_risk(recon, sm)
        assert (result["supplier_risk_level"] == "High").sum() > 0

    def test_sample_data_required_columns_present(self):
        pr = clean_purchase_register(load_purchase_register(DATA_DIR / "sample_purchase_register.csv"))
        g2b = clean_gstr2b(load_gstr2b(DATA_DIR / "sample_gstr2b.csv"))
        sm = load_supplier_master(DATA_DIR / "sample_supplier_master.csv")
        recon = reconcile_invoices(pr, g2b)
        result = add_supplier_risk(recon, sm)
        for col in ["supplier_risk_score", "supplier_risk_level", "supplier_risk_reasons", "supplier_name"]:
            assert col in result.columns
