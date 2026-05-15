"""
test_report_writer.py - Tests for Excel exception report generation.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from report_writer import (
    calculate_itc_at_risk,
    filter_exception_rows,
    get_suggested_ca_action,
    prepare_exception_report,
    generate_report_filename,
    write_exception_report,
)
from data_loader import load_purchase_register, load_gstr2b, load_supplier_master
from cleaner import clean_purchase_register, clean_gstr2b
from reconciler import reconcile_invoices
from risk_scorer import add_supplier_risk

DATA_DIR = Path(__file__).parent.parent / "data"


# --- Helper ---

def make_row(status="matched", risk_level="Low", pr_itc=9000.0, g2b_itc=9000.0):
    return {
        "invoice_no": "INV-001",
        "supplier_gstin": "27AABCU9603R1ZX",
        "supplier_name": "Test Supplier",
        "status": status,
        "mismatch_reason": "",
        "gstin_status": "Active",
        "return_filing_status": "Regular Filer",
        "supplier_risk_score": 0,
        "supplier_risk_level": risk_level,
        "supplier_risk_reasons": "No major supplier risk detected",
        "purchase_total_itc": pr_itc,
        "gstr2b_total_itc": g2b_itc,
    }


def make_df(*rows):
    return pd.DataFrame(rows)


def full_pipeline_df():
    """Build the enriched DataFrame from the sample CSVs."""
    pr = clean_purchase_register(load_purchase_register(DATA_DIR / "sample_purchase_register.csv"))
    g2b = clean_gstr2b(load_gstr2b(DATA_DIR / "sample_gstr2b.csv"))
    sm = load_supplier_master(DATA_DIR / "sample_supplier_master.csv")
    return add_supplier_risk(reconcile_invoices(pr, g2b), sm)


# --- ITC at risk tests ---

class TestCalculateItcAtRisk:
    def test_missing_in_2b(self):
        row = make_row(status="missing_in_2b", pr_itc=9000.0)
        assert calculate_itc_at_risk(row) == 9000.0

    def test_amount_mismatch(self):
        row = make_row(status="amount_mismatch", pr_itc=9000.0, g2b_itc=9500.0)
        assert calculate_itc_at_risk(row) == 500.0

    def test_amount_mismatch_reverse_order(self):
        # abs() — direction doesn't matter
        row = make_row(status="amount_mismatch", pr_itc=9500.0, g2b_itc=9000.0)
        assert calculate_itc_at_risk(row) == 500.0

    def test_duplicate_in_purchase(self):
        row = make_row(status="duplicate_in_purchase", pr_itc=9000.0)
        assert calculate_itc_at_risk(row) == 9000.0

    def test_extra_in_2b_is_zero(self):
        row = make_row(status="extra_in_2b", pr_itc=9000.0, g2b_itc=9000.0)
        assert calculate_itc_at_risk(row) == 0.0

    def test_matched_low_risk_is_zero(self):
        row = make_row(status="matched", risk_level="Low", pr_itc=9000.0)
        assert calculate_itc_at_risk(row) == 0.0

    def test_matched_high_risk_has_itc_at_risk(self):
        row = make_row(status="matched", risk_level="High", pr_itc=9000.0)
        assert calculate_itc_at_risk(row) == 9000.0

    def test_matched_medium_risk_has_itc_at_risk(self):
        row = make_row(status="matched", risk_level="Medium", pr_itc=9000.0)
        assert calculate_itc_at_risk(row) == 9000.0

    def test_nan_purchase_itc_handled(self):
        row = make_row(status="missing_in_2b", pr_itc=float("nan"))
        assert calculate_itc_at_risk(row) == 0.0

    def test_nan_both_amount_mismatch_handled(self):
        row = make_row(status="amount_mismatch", pr_itc=float("nan"), g2b_itc=float("nan"))
        assert calculate_itc_at_risk(row) == 0.0


# --- Filter tests ---

class TestFilterExceptionRows:
    def test_excludes_matched_low(self):
        df = make_df(make_row(status="matched", risk_level="Low"))
        result = filter_exception_rows(df)
        assert len(result) == 0

    def test_includes_matched_high(self):
        df = make_df(make_row(status="matched", risk_level="High"))
        result = filter_exception_rows(df)
        assert len(result) == 1

    def test_includes_matched_medium(self):
        df = make_df(make_row(status="matched", risk_level="Medium"))
        result = filter_exception_rows(df)
        assert len(result) == 1

    def test_includes_missing_in_2b(self):
        df = make_df(make_row(status="missing_in_2b", risk_level="Low"))
        result = filter_exception_rows(df)
        assert len(result) == 1

    def test_includes_extra_in_2b(self):
        df = make_df(make_row(status="extra_in_2b", risk_level="Low"))
        result = filter_exception_rows(df)
        assert len(result) == 1

    def test_does_not_modify_original(self):
        df = make_df(
            make_row(status="matched", risk_level="Low"),
            make_row(status="missing_in_2b", risk_level="High"),
        )
        original_len = len(df)
        filter_exception_rows(df)
        assert len(df) == original_len

    def test_mixed_returns_only_exceptions(self):
        df = make_df(
            make_row(status="matched", risk_level="Low"),   # excluded
            make_row(status="matched", risk_level="High"),  # included
            make_row(status="missing_in_2b", risk_level="Low"),  # included
        )
        result = filter_exception_rows(df)
        assert len(result) == 2


# --- Suggested CA action tests ---

class TestGetSuggestedCaAction:
    def test_extra_in_2b_action(self):
        row = make_row(status="extra_in_2b", risk_level="Low")
        assert get_suggested_ca_action(row) == "Check whether invoice is missing from books"

    def test_high_risk_action(self):
        row = make_row(status="matched", risk_level="High")
        assert get_suggested_ca_action(row) == "Review before filing"

    def test_medium_risk_action(self):
        row = make_row(status="matched", risk_level="Medium")
        assert get_suggested_ca_action(row) == "Verify supporting documents"

    def test_unmatched_other_status(self):
        # missing_in_2b with Low risk — falls through to reconciliation check
        row = make_row(status="missing_in_2b", risk_level="Low")
        assert get_suggested_ca_action(row) == "Check reconciliation difference"

    def test_matched_low_no_action(self):
        row = make_row(status="matched", risk_level="Low")
        assert get_suggested_ca_action(row) == "No action required"

    def test_extra_in_2b_takes_priority_over_high_risk(self):
        # extra_in_2b should win even when supplier risk is High
        row = make_row(status="extra_in_2b", risk_level="High")
        assert get_suggested_ca_action(row) == "Check whether invoice is missing from books"


# --- Report preparation tests ---

class TestPrepareExceptionReport:
    CA_COLUMNS = [
        "Invoice No", "Supplier GSTIN", "Supplier Name",
        "Reconciliation Status", "Mismatch Reason",
        "Supplier Risk Level", "Supplier Risk Score", "Supplier Risk Reasons",
        "Purchase ITC", "GSTR-2B ITC", "ITC At Risk", "Suggested CA Action",
        "CA Review Status", "CA Remarks",
    ]

    def test_has_ca_column_names(self):
        df = make_df(make_row(status="missing_in_2b", risk_level="High"))
        report = prepare_exception_report(df)
        assert list(report.columns) == self.CA_COLUMNS

    def test_only_exceptions_in_report(self):
        df = make_df(
            make_row(status="matched", risk_level="Low"),
            make_row(status="missing_in_2b", risk_level="High"),
        )
        report = prepare_exception_report(df)
        assert len(report) == 1

    def test_does_not_modify_input(self):
        df = make_df(make_row(status="missing_in_2b"))
        original_cols = list(df.columns)
        prepare_exception_report(df)
        assert list(df.columns) == original_cols

    def test_empty_when_no_exceptions(self):
        df = make_df(make_row(status="matched", risk_level="Low"))
        report = prepare_exception_report(df)
        assert len(report) == 0
        assert list(report.columns) == self.CA_COLUMNS

    def test_itc_at_risk_column_exists(self):
        df = make_df(make_row(status="missing_in_2b"))
        report = prepare_exception_report(df)
        assert "ITC At Risk" in report.columns

    def test_suggested_ca_action_column_exists(self):
        df = make_df(make_row(status="missing_in_2b"))
        report = prepare_exception_report(df)
        assert "Suggested CA Action" in report.columns


# --- File writing tests ---

class TestWriteExceptionReport:
    def _sample_report_df(self):
        return prepare_exception_report(make_df(
            make_row(status="missing_in_2b", risk_level="High", pr_itc=9000.0),
            make_row(status="matched", risk_level="Medium", pr_itc=5000.0),
        ))

    def test_write_creates_excel_file(self, tmp_path):
        output = tmp_path / "report.xlsx"
        write_exception_report(self._sample_report_df(), output)
        assert output.exists()

    def test_write_file_not_empty(self, tmp_path):
        output = tmp_path / "report.xlsx"
        write_exception_report(self._sample_report_df(), output)
        assert output.stat().st_size > 0

    def test_write_creates_parent_dir(self, tmp_path):
        # Directory does not exist yet — write_exception_report should create it
        output = tmp_path / "new_subdir" / "report.xlsx"
        assert not output.parent.exists()
        write_exception_report(self._sample_report_df(), output)
        assert output.exists()

    def test_empty_exception_report_still_creates_excel(self, tmp_path):
        # No exception rows — must write a header-only file without crashing
        empty_df = prepare_exception_report(
            make_df(make_row(status="matched", risk_level="Low"))
        )
        assert len(empty_df) == 0
        output = tmp_path / "empty_report.xlsx"
        write_exception_report(empty_df, output)
        assert output.exists()
        assert output.stat().st_size > 0

    def test_write_sample_data(self, tmp_path):
        enriched = full_pipeline_df()
        report = prepare_exception_report(enriched)
        output = tmp_path / "sample_report.xlsx"
        write_exception_report(report, output)
        assert output.exists()
        assert output.stat().st_size > 0


# --- CA review column tests ---

class TestCaReviewColumns:
    def test_ca_review_status_column_present(self):
        df = make_df(make_row(status="missing_in_2b", risk_level="High"))
        report = prepare_exception_report(df)
        assert "CA Review Status" in report.columns

    def test_ca_remarks_column_present(self):
        df = make_df(make_row(status="missing_in_2b", risk_level="High"))
        report = prepare_exception_report(df)
        assert "CA Remarks" in report.columns

    def test_default_ca_review_status_is_pending(self):
        df = make_df(make_row(status="missing_in_2b", risk_level="High"))
        report = prepare_exception_report(df)
        assert (report["CA Review Status"] == "Pending").all()

    def test_default_ca_remarks_is_blank(self):
        df = make_df(make_row(status="missing_in_2b", risk_level="High"))
        report = prepare_exception_report(df)
        assert (report["CA Remarks"] == "").all()


# --- Filename tests ---

class TestGenerateReportFilename:
    def test_filename_starts_with_exception_report(self):
        name = generate_report_filename()
        assert name.startswith("exception_report_")

    def test_filename_ends_with_xlsx(self):
        name = generate_report_filename()
        assert name.endswith(".xlsx")

    def test_filename_contains_date(self):
        import datetime
        today = datetime.date.today().strftime("%Y%m%d")
        name = generate_report_filename()
        assert today in name
