"""
test_evaluator.py - Tests for the Sprint 6 evaluation system.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evaluator import (
    load_labels,
    validate_labels,
    prepare_actual_results,
    normalize_eval_key,
    compare_results,
    calculate_accuracy_metrics,
    run_evaluation,
    REQUIRED_LABEL_COLUMNS,
)
from data_loader import load_purchase_register, load_gstr2b, load_supplier_master
from cleaner import clean_purchase_register, clean_gstr2b
from reconciler import reconcile_invoices
from risk_scorer import add_supplier_risk

DATA_DIR = Path(__file__).parent.parent / "data"
LABELS_PATH = DATA_DIR / "labels.csv"


# --- Helpers ---

def make_enriched_row(
    invoice_no="INV-001",
    supplier_gstin="27AABCU9603R1ZX",
    status="matched",
    risk_level="Low",
    pr_itc=9000.0,
    g2b_itc=9000.0,
):
    return {
        "invoice_no": invoice_no,
        "supplier_gstin": supplier_gstin,
        "status": status,
        "mismatch_reason": "",
        "supplier_name": "Test Supplier",
        "supplier_risk_score": 0,
        "supplier_risk_level": risk_level,
        "supplier_risk_reasons": "No risk",
        "purchase_total_itc": pr_itc,
        "gstr2b_total_itc": g2b_itc,
    }


def make_enriched_df(*rows):
    return pd.DataFrame(rows)


def make_labels_row(
    invoice_no="INV-001",
    supplier_gstin="27AABCU9603R1ZX",
    expected_status="matched",
    expected_risk_level="Low",
    expected_is_exception=False,
    expected_itc=0.0,
):
    return {
        "invoice_no": invoice_no,
        "supplier_gstin": supplier_gstin,
        "expected_status": expected_status,
        "expected_supplier_risk_level": expected_risk_level,
        "expected_is_exception": expected_is_exception,
        "expected_itc_at_risk": expected_itc,
    }


def make_labels_df(*rows):
    return pd.DataFrame(rows)


def full_pipeline_df():
    pr = clean_purchase_register(load_purchase_register(DATA_DIR / "sample_purchase_register.csv"))
    g2b = clean_gstr2b(load_gstr2b(DATA_DIR / "sample_gstr2b.csv"))
    sm = load_supplier_master(DATA_DIR / "sample_supplier_master.csv")
    return add_supplier_risk(reconcile_invoices(pr, g2b), sm)


# --- load_labels tests ---

class TestLoadLabels:
    def test_loads_valid_labels_csv(self):
        df = load_labels(LABELS_PATH)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_missing_labels_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_labels(tmp_path / "nonexistent.csv")

    def test_missing_file_error_contains_path(self, tmp_path):
        path = tmp_path / "missing.csv"
        with pytest.raises(FileNotFoundError, match=str(path)):
            load_labels(path)

    def test_empty_labels_file_raises_value_error(self, tmp_path):
        empty = tmp_path / "empty.csv"
        empty.write_text("invoice_no,supplier_gstin\n")  # header only = empty DataFrame
        with pytest.raises(ValueError):
            load_labels(empty)


# --- validate_labels tests ---

class TestValidateLabels:
    def test_passes_when_all_columns_present(self):
        df = load_labels(LABELS_PATH)
        assert validate_labels(df) is True

    def test_raises_when_required_column_missing(self):
        df = make_labels_df(make_labels_row()).drop(columns=["expected_status"])
        with pytest.raises(ValueError):
            validate_labels(df)

    def test_error_message_names_missing_column(self):
        df = make_labels_df(make_labels_row()).drop(columns=["expected_itc_at_risk"])
        with pytest.raises(ValueError, match="expected_itc_at_risk"):
            validate_labels(df)


# --- prepare_actual_results tests ---

class TestPrepareActualResults:
    def test_creates_actual_status_column(self):
        df = make_enriched_df(make_enriched_row(status="matched"))
        result = prepare_actual_results(df)
        assert "actual_status" in result.columns

    def test_creates_actual_supplier_risk_level_column(self):
        df = make_enriched_df(make_enriched_row(risk_level="High"))
        result = prepare_actual_results(df)
        assert "actual_supplier_risk_level" in result.columns

    def test_creates_actual_is_exception_column(self):
        df = make_enriched_df(make_enriched_row())
        result = prepare_actual_results(df)
        assert "actual_is_exception" in result.columns

    def test_matched_low_is_not_exception(self):
        df = make_enriched_df(make_enriched_row(status="matched", risk_level="Low"))
        result = prepare_actual_results(df)
        assert result["actual_is_exception"].iloc[0] == False

    def test_missing_in_2b_is_exception(self):
        df = make_enriched_df(make_enriched_row(status="missing_in_2b", risk_level="Low"))
        result = prepare_actual_results(df)
        assert result["actual_is_exception"].iloc[0] == True

    def test_matched_high_risk_is_exception(self):
        df = make_enriched_df(make_enriched_row(status="matched", risk_level="High"))
        result = prepare_actual_results(df)
        assert result["actual_is_exception"].iloc[0] == True

    def test_matched_medium_risk_is_exception(self):
        df = make_enriched_df(make_enriched_row(status="matched", risk_level="Medium"))
        result = prepare_actual_results(df)
        assert result["actual_is_exception"].iloc[0] == True

    def test_actual_itc_at_risk_missing_in_2b(self):
        df = make_enriched_df(make_enriched_row(status="missing_in_2b", pr_itc=9000.0))
        result = prepare_actual_results(df)
        assert result["actual_itc_at_risk"].iloc[0] == 9000.0

    def test_actual_itc_at_risk_amount_mismatch(self):
        df = make_enriched_df(make_enriched_row(status="amount_mismatch", pr_itc=9000.0, g2b_itc=9500.0))
        result = prepare_actual_results(df)
        assert result["actual_itc_at_risk"].iloc[0] == 500.0

    def test_actual_itc_at_risk_matched_low_is_zero(self):
        df = make_enriched_df(make_enriched_row(status="matched", risk_level="Low", pr_itc=9000.0))
        result = prepare_actual_results(df)
        assert result["actual_itc_at_risk"].iloc[0] == 0.0

    def test_does_not_modify_input(self):
        df = make_enriched_df(make_enriched_row())
        original_cols = list(df.columns)
        prepare_actual_results(df)
        assert list(df.columns) == original_cols


# --- normalize_eval_key tests ---

class TestNormalizeEvalKey:
    def test_invoice_no_normalization(self):
        df = make_enriched_df(make_enriched_row(invoice_no="inv-2024-001 "))
        result = normalize_eval_key(df)
        assert result["eval_invoice_no"].iloc[0] == "INV2024001"

    def test_gstin_normalization(self):
        df = make_enriched_df(make_enriched_row(supplier_gstin=" 27aabcu9603r1zx"))
        result = normalize_eval_key(df)
        assert result["eval_supplier_gstin"].iloc[0] == "27AABCU9603R1ZX"

    def test_lowercase_invoice_still_joins(self):
        # After normalization, "inv-2024-001" == "INV-2024-001" → both → "INV2024001"
        df1 = make_enriched_df(make_enriched_row(invoice_no="inv-2024-001"))
        df2 = make_enriched_df(make_enriched_row(invoice_no="INV-2024-001"))
        r1 = normalize_eval_key(df1)
        r2 = normalize_eval_key(df2)
        assert r1["eval_invoice_no"].iloc[0] == r2["eval_invoice_no"].iloc[0]

    def test_hyphen_and_nohyphen_invoice_match(self):
        df1 = make_enriched_df(make_enriched_row(invoice_no="INV-001"))
        df2 = make_enriched_df(make_enriched_row(invoice_no="INV001"))
        r1 = normalize_eval_key(df1)
        r2 = normalize_eval_key(df2)
        assert r1["eval_invoice_no"].iloc[0] == r2["eval_invoice_no"].iloc[0]

    def test_does_not_modify_original(self):
        df = make_enriched_df(make_enriched_row())
        original_cols = list(df.columns)
        normalize_eval_key(df)
        assert list(df.columns) == original_cols


# --- compare_results tests ---

class TestCompareResults:
    def _make_actual(self, **kw):
        return prepare_actual_results(make_enriched_df(make_enriched_row(**kw)))

    def _make_labels(self, **kw):
        return make_labels_df(make_labels_row(**kw))

    def test_status_correct_when_matching(self):
        actual = self._make_actual(status="matched")
        labels = self._make_labels(expected_status="matched")
        result = compare_results(actual, labels)
        assert result["status_correct"].iloc[0] == True

    def test_status_correct_false_when_different(self):
        actual = self._make_actual(status="missing_in_2b")
        labels = self._make_labels(expected_status="matched")
        result = compare_results(actual, labels)
        assert result["status_correct"].iloc[0] == False

    def test_risk_level_correct_when_matching(self):
        actual = self._make_actual(risk_level="High")
        labels = self._make_labels(expected_risk_level="High")
        result = compare_results(actual, labels)
        assert result["risk_level_correct"].iloc[0] == True

    def test_risk_level_correct_false_when_different(self):
        actual = self._make_actual(risk_level="Low")
        labels = self._make_labels(expected_risk_level="High")
        result = compare_results(actual, labels)
        assert result["risk_level_correct"].iloc[0] == False

    def test_exception_correct_when_matching(self):
        actual = self._make_actual(status="matched", risk_level="Low")
        labels = self._make_labels(expected_is_exception=False)
        result = compare_results(actual, labels)
        assert result["exception_correct"].iloc[0] == True

    def test_exception_correct_false_when_different(self):
        actual = self._make_actual(status="matched", risk_level="Low")
        labels = self._make_labels(expected_is_exception=True)
        result = compare_results(actual, labels)
        assert result["exception_correct"].iloc[0] == False

    def test_itc_at_risk_correct_within_tolerance(self):
        actual = self._make_actual(status="missing_in_2b", pr_itc=9000.0)
        labels = self._make_labels(expected_status="missing_in_2b", expected_itc=9000.0)
        result = compare_results(actual, labels)
        assert result["itc_at_risk_correct"].iloc[0] == True

    def test_itc_at_risk_correct_false_outside_tolerance(self):
        actual = self._make_actual(status="missing_in_2b", pr_itc=9000.0)
        labels = self._make_labels(expected_status="missing_in_2b", expected_itc=9100.0)
        result = compare_results(actual, labels)
        assert result["itc_at_risk_correct"].iloc[0] == False

    def test_missing_actual_row_marked_incorrect(self):
        # Label for a GSTIN that doesn't appear in actual
        actual = self._make_actual(supplier_gstin="27AABCU9603R1ZX")
        labels = self._make_labels(supplier_gstin="99ZZZZZ9999Z9ZZ")
        result = compare_results(actual, labels)
        assert result["status_correct"].iloc[0] == False

    def test_missing_actual_row_has_nan_actual_status(self):
        actual = self._make_actual(supplier_gstin="27AABCU9603R1ZX")
        labels = self._make_labels(supplier_gstin="99ZZZZZ9999Z9ZZ")
        result = compare_results(actual, labels)
        assert pd.isna(result["actual_status"].iloc[0])

    def test_all_label_rows_kept(self):
        actual = self._make_actual()
        labels = make_labels_df(
            make_labels_row(invoice_no="INV-001"),
            make_labels_row(invoice_no="INV-999", supplier_gstin="99ZZZZZ9999Z9ZZ"),
        )
        result = compare_results(actual, labels)
        assert len(result) == 2


# --- calculate_accuracy_metrics tests ---

class TestCalculateAccuracyMetrics:
    def _perfect_comparison(self):
        actual = prepare_actual_results(make_enriched_df(
            make_enriched_row(status="matched", risk_level="Low"),
            make_enriched_row(invoice_no="INV-002", status="missing_in_2b", risk_level="High", pr_itc=5000.0),
        ))
        labels = make_labels_df(
            make_labels_row(expected_status="matched", expected_risk_level="Low", expected_is_exception=False, expected_itc=0.0),
            make_labels_row(invoice_no="INV-002", expected_status="missing_in_2b", expected_risk_level="High", expected_is_exception=True, expected_itc=5000.0),
        )
        return compare_results(actual, labels)

    def test_100_percent_accuracy_case(self):
        comp = self._perfect_comparison()
        metrics = calculate_accuracy_metrics(comp)
        assert metrics["status_accuracy"] == 100.0
        assert metrics["risk_level_accuracy"] == 100.0
        assert metrics["exception_accuracy"] == 100.0
        assert metrics["itc_at_risk_accuracy"] == 100.0

    def test_partial_accuracy_case(self):
        # 1 correct, 1 wrong status → 50%
        actual = prepare_actual_results(make_enriched_df(
            make_enriched_row(status="matched", risk_level="Low"),
            make_enriched_row(invoice_no="INV-002", status="missing_in_2b", risk_level="Low"),
        ))
        labels = make_labels_df(
            make_labels_row(expected_status="matched"),
            make_labels_row(invoice_no="INV-002", expected_status="matched"),
        )
        comp = compare_results(actual, labels)
        metrics = calculate_accuracy_metrics(comp)
        assert metrics["status_accuracy"] == 50.0

    def test_false_positive_exception_count(self):
        actual = prepare_actual_results(make_enriched_df(
            make_enriched_row(status="missing_in_2b", risk_level="High"),
        ))
        labels = make_labels_df(
            make_labels_row(expected_is_exception=False, expected_status="missing_in_2b", expected_risk_level="High"),
        )
        comp = compare_results(actual, labels)
        metrics = calculate_accuracy_metrics(comp)
        assert metrics["false_positive_exceptions"] == 1

    def test_false_negative_exception_count(self):
        actual = prepare_actual_results(make_enriched_df(
            make_enriched_row(status="matched", risk_level="Low"),
        ))
        labels = make_labels_df(
            make_labels_row(expected_is_exception=True),
        )
        comp = compare_results(actual, labels)
        metrics = calculate_accuracy_metrics(comp)
        assert metrics["false_negative_exceptions"] == 1

    def test_missing_actual_rows_count(self):
        actual = prepare_actual_results(make_enriched_df(
            make_enriched_row(supplier_gstin="27AABCU9603R1ZX"),
        ))
        labels = make_labels_df(
            make_labels_row(supplier_gstin="99ZZZZZ9999Z9ZZ"),
        )
        comp = compare_results(actual, labels)
        metrics = calculate_accuracy_metrics(comp)
        assert metrics["missing_actual_rows"] == 1

    def test_percentages_rounded_to_2_decimals(self):
        # 2 out of 3 correct → 66.67%
        actual = prepare_actual_results(make_enriched_df(
            make_enriched_row(invoice_no="INV-001", status="matched", risk_level="Low"),
            make_enriched_row(invoice_no="INV-002", status="matched", risk_level="Low"),
            make_enriched_row(invoice_no="INV-003", status="missing_in_2b", risk_level="Low"),
        ))
        labels = make_labels_df(
            make_labels_row(invoice_no="INV-001", expected_status="matched"),
            make_labels_row(invoice_no="INV-002", expected_status="matched"),
            make_labels_row(invoice_no="INV-003", expected_status="matched"),
        )
        comp = compare_results(actual, labels)
        metrics = calculate_accuracy_metrics(comp)
        assert metrics["status_accuracy"] == 66.67

    def test_total_labels_count(self):
        comp = self._perfect_comparison()
        metrics = calculate_accuracy_metrics(comp)
        assert metrics["total_labels"] == 2

    def test_required_keys_present(self):
        comp = self._perfect_comparison()
        metrics = calculate_accuracy_metrics(comp)
        required = [
            "total_labels", "status_correct", "status_accuracy",
            "risk_level_correct", "risk_level_accuracy",
            "exception_correct", "exception_accuracy",
            "itc_at_risk_correct", "itc_at_risk_accuracy",
            "false_positive_exceptions", "false_negative_exceptions",
            "missing_actual_rows",
        ]
        for key in required:
            assert key in metrics, f"Missing key: {key}"


# --- Integration tests ---

class TestIntegration:
    def test_run_evaluation_returns_tuple(self):
        enriched = full_pipeline_df()
        comparison_df, metrics = run_evaluation(enriched, LABELS_PATH)
        assert isinstance(comparison_df, pd.DataFrame)
        assert isinstance(metrics, dict)

    def test_metrics_has_filing_relevant_keys(self):
        enriched = full_pipeline_df()
        _, metrics = run_evaluation(enriched, LABELS_PATH)
        assert "total_labels" in metrics
        assert "status_accuracy" in metrics
        assert "false_positive_exceptions" in metrics

    def test_total_labels_greater_than_zero(self):
        enriched = full_pipeline_df()
        _, metrics = run_evaluation(enriched, LABELS_PATH)
        assert metrics["total_labels"] > 0

    def test_all_accuracies_between_0_and_100(self):
        enriched = full_pipeline_df()
        _, metrics = run_evaluation(enriched, LABELS_PATH)
        for key in ["status_accuracy", "risk_level_accuracy", "exception_accuracy", "itc_at_risk_accuracy"]:
            assert 0.0 <= metrics[key] <= 100.0, f"{key} out of range: {metrics[key]}"

    def test_sample_labels_all_correct(self):
        # labels.csv is ground-truth derived from the pipeline itself — should be 100%
        enriched = full_pipeline_df()
        _, metrics = run_evaluation(enriched, LABELS_PATH)
        assert metrics["status_accuracy"] == 100.0
        assert metrics["risk_level_accuracy"] == 100.0
        assert metrics["exception_accuracy"] == 100.0
        assert metrics["itc_at_risk_accuracy"] == 100.0
