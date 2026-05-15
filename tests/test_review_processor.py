"""
test_review_processor.py - Tests for CA review workflow processing.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from review_processor import (
    load_reviewed_report,
    validate_review_columns,
    normalize_review_status,
    validate_review_statuses,
    calculate_review_summary,
    get_filing_recommendation,
    print_review_summary,
    process_reviewed_report,
    ALLOWED_REVIEW_STATUSES,
)


# --- Helpers ---

def make_reviewed_df(statuses, itc_values):
    """Build a minimal reviewed DataFrame with the columns review_processor expects."""
    return pd.DataFrame({
        "Invoice No": [f"INV-{i:03d}" for i in range(len(statuses))],
        "Supplier GSTIN": ["27AABCU9603R1ZX"] * len(statuses),
        "ITC At Risk": itc_values,
        "CA Review Status": statuses,
        "CA Remarks": [""] * len(statuses),
    })


def write_reviewed_excel(df, path):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Exception Report", index=False)


# --- load_reviewed_report tests ---

class TestLoadReviewedReport:
    def test_load_reviewed_report_returns_dataframe(self, tmp_path):
        df = make_reviewed_df(["Accepted"], [5000.0])
        path = tmp_path / "reviewed.xlsx"
        write_reviewed_excel(df, path)
        result = load_reviewed_report(path)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_missing_file_raises_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_reviewed_report(tmp_path / "nonexistent.xlsx")

    def test_missing_file_error_message_contains_path(self, tmp_path):
        path = tmp_path / "nonexistent.xlsx"
        with pytest.raises(FileNotFoundError, match=str(path)):
            load_reviewed_report(path)


# --- validate_review_columns tests ---

class TestValidateReviewColumns:
    def test_validate_passes_when_all_columns_present(self):
        df = make_reviewed_df(["Pending"], [0.0])
        assert validate_review_columns(df) is True

    def test_validate_raises_when_column_missing(self):
        df = make_reviewed_df(["Pending"], [0.0]).drop(columns=["CA Review Status"])
        with pytest.raises(ValueError):
            validate_review_columns(df)

    def test_error_names_missing_column(self):
        df = make_reviewed_df(["Pending"], [0.0]).drop(columns=["ITC At Risk"])
        with pytest.raises(ValueError, match="ITC At Risk"):
            validate_review_columns(df)


# --- normalize_review_status tests ---

class TestNormalizeReviewStatus:
    def test_normalize_accepted_lowercase(self):
        assert normalize_review_status("accepted") == "Accepted"

    def test_normalize_accepted_uppercase(self):
        assert normalize_review_status("ACCEPTED") == "Accepted"

    def test_normalize_strips_whitespace(self):
        assert normalize_review_status("  Accepted  ") == "Accepted"

    def test_normalize_blank_becomes_pending(self):
        assert normalize_review_status("") == "Pending"

    def test_normalize_whitespace_only_becomes_pending(self):
        assert normalize_review_status("   ") == "Pending"

    def test_normalize_none_becomes_pending(self):
        assert normalize_review_status(None) == "Pending"

    def test_normalize_nan_becomes_pending(self):
        assert normalize_review_status(float("nan")) == "Pending"

    def test_normalize_escalated(self):
        assert normalize_review_status("escalated") == "Escalated"

    def test_normalize_pending(self):
        assert normalize_review_status("PENDING") == "Pending"

    def test_normalize_hold_itc(self):
        assert normalize_review_status("hold itc") == "Hold ITC"

    def test_normalize_hold_itc_uppercase(self):
        assert normalize_review_status("HOLD ITC") == "Hold ITC"

    def test_normalize_reverse_itc(self):
        assert normalize_review_status("reverse itc") == "Reverse ITC"

    def test_normalize_reverse_itc_mixed_case(self):
        assert normalize_review_status("Reverse ITC") == "Reverse ITC"

    def test_normalize_unknown_returns_cleaned_string(self):
        assert normalize_review_status("  SomeOtherValue  ") == "SomeOtherValue"


# --- validate_review_statuses tests ---

class TestValidateReviewStatuses:
    def test_all_allowed_statuses_pass(self):
        df = make_reviewed_df(list(ALLOWED_REVIEW_STATUSES), [100.0] * len(ALLOWED_REVIEW_STATUSES))
        result = validate_review_statuses(df)
        assert isinstance(result, pd.DataFrame)

    def test_returns_normalized_copy(self):
        df = make_reviewed_df(["accepted"], [0.0])
        result = validate_review_statuses(df)
        assert result["CA Review Status"].iloc[0] == "Accepted"

    def test_does_not_modify_original(self):
        df = make_reviewed_df(["accepted"], [0.0])
        validate_review_statuses(df)
        assert df["CA Review Status"].iloc[0] == "accepted"

    def test_invalid_status_raises_value_error(self):
        df = make_reviewed_df(["Approved"], [0.0])
        with pytest.raises(ValueError):
            validate_review_statuses(df)

    def test_error_message_includes_invalid_value(self):
        df = make_reviewed_df(["Approved"], [0.0])
        with pytest.raises(ValueError, match="Approved"):
            validate_review_statuses(df)


# --- calculate_review_summary tests ---

class TestCalculateReviewSummary:
    def test_counts_accepted(self):
        df = make_reviewed_df(["Accepted", "Accepted"], [1000.0, 2000.0])
        s = calculate_review_summary(df)
        assert s["accepted_count"] == 2

    def test_counts_escalated(self):
        df = make_reviewed_df(["Escalated"], [500.0])
        s = calculate_review_summary(df)
        assert s["escalated_count"] == 1

    def test_counts_pending(self):
        df = make_reviewed_df(["Pending", "Pending", "Pending"], [0.0, 0.0, 0.0])
        s = calculate_review_summary(df)
        assert s["pending_count"] == 3

    def test_counts_hold_itc(self):
        df = make_reviewed_df(["Hold ITC"], [8000.0])
        s = calculate_review_summary(df)
        assert s["hold_itc_count"] == 1

    def test_counts_reverse_itc(self):
        df = make_reviewed_df(["Reverse ITC"], [3000.0])
        s = calculate_review_summary(df)
        assert s["reverse_itc_count"] == 1

    def test_total_itc_at_risk(self):
        df = make_reviewed_df(["Accepted", "Pending"], [1000.0, 2000.0])
        s = calculate_review_summary(df)
        assert s["total_itc_at_risk"] == 3000.0

    def test_accepted_itc(self):
        df = make_reviewed_df(["Accepted", "Pending"], [1000.0, 2000.0])
        s = calculate_review_summary(df)
        assert s["accepted_itc"] == 1000.0

    def test_hold_itc_amount(self):
        df = make_reviewed_df(["Hold ITC", "Accepted"], [4000.0, 1000.0])
        s = calculate_review_summary(df)
        assert s["hold_itc"] == 4000.0

    def test_reverse_itc_amount(self):
        df = make_reviewed_df(["Reverse ITC"], [7500.0])
        s = calculate_review_summary(df)
        assert s["reverse_itc"] == 7500.0

    def test_unresolved_itc_includes_pending_and_escalated(self):
        df = make_reviewed_df(
            ["Pending", "Escalated", "Accepted"],
            [1000.0, 2000.0, 500.0],
        )
        s = calculate_review_summary(df)
        assert s["unresolved_itc"] == 3000.0

    def test_nan_itc_treated_as_zero(self):
        df = make_reviewed_df(["Accepted"], [float("nan")])
        s = calculate_review_summary(df)
        assert s["accepted_itc"] == 0.0

    def test_total_exception_rows(self):
        df = make_reviewed_df(["Accepted", "Pending", "Escalated"], [0.0, 0.0, 0.0])
        s = calculate_review_summary(df)
        assert s["total_exception_rows"] == 3


# --- get_filing_recommendation tests ---

class TestGetFilingRecommendation:
    def _summary(self, **overrides):
        base = {
            "total_exception_rows": 5,
            "accepted_count": 5,
            "escalated_count": 0,
            "pending_count": 0,
            "hold_itc_count": 0,
            "reverse_itc_count": 0,
        }
        base.update(overrides)
        return base

    def test_pending_blocks_filing(self):
        s = self._summary(accepted_count=4, pending_count=1)
        assert "pending" in get_filing_recommendation(s).lower()

    def test_escalated_blocks_filing(self):
        s = self._summary(accepted_count=4, escalated_count=1)
        assert "escalated" in get_filing_recommendation(s).lower()

    def test_hold_itc_warns_before_filing(self):
        s = self._summary(accepted_count=4, hold_itc_count=1)
        rec = get_filing_recommendation(s)
        assert "hold" in rec.lower() or "adjust" in rec.lower()

    def test_reverse_itc_warns_before_filing(self):
        s = self._summary(accepted_count=4, reverse_itc_count=1)
        rec = get_filing_recommendation(s)
        assert "reverse" in rec.lower() or "adjust" in rec.lower()

    def test_all_accepted_ready(self):
        s = self._summary(accepted_count=5)
        assert get_filing_recommendation(s) == "Filing position appears reviewed and ready."

    def test_pending_takes_priority_over_hold(self):
        s = self._summary(accepted_count=3, pending_count=1, hold_itc_count=1)
        rec = get_filing_recommendation(s)
        assert "pending" in rec.lower()


# --- process_reviewed_report integration tests ---

class TestProcessReviewedReport:
    def test_process_returns_summary_dict(self, tmp_path):
        df = make_reviewed_df(["Accepted", "Pending"], [5000.0, 2000.0])
        path = tmp_path / "reviewed.xlsx"
        write_reviewed_excel(df, path)
        result = process_reviewed_report(path)
        assert isinstance(result, dict)

    def test_process_summary_has_filing_recommendation(self, tmp_path):
        df = make_reviewed_df(["Accepted"], [5000.0])
        path = tmp_path / "reviewed.xlsx"
        write_reviewed_excel(df, path)
        result = process_reviewed_report(path)
        assert "filing_recommendation" in result

    def test_process_normalizes_statuses(self, tmp_path):
        df = make_reviewed_df(["accepted"], [5000.0])
        path = tmp_path / "reviewed.xlsx"
        write_reviewed_excel(df, path)
        result = process_reviewed_report(path)
        assert result["accepted_count"] == 1

    def test_process_raises_for_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            process_reviewed_report(tmp_path / "missing.xlsx")

    def test_process_raises_for_invalid_status(self, tmp_path):
        df = make_reviewed_df(["Approved"], [5000.0])
        path = tmp_path / "invalid.xlsx"
        write_reviewed_excel(df, path)
        with pytest.raises(ValueError):
            process_reviewed_report(path)
