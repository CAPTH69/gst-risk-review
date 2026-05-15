"""
evaluator.py - Measure accuracy of the GST Risk Review pipeline.

Loads ground-truth labels, compares them against actual pipeline output,
and produces accuracy metrics a CA or developer can use to track quality.

Label file format (data/labels.csv):
  invoice_no, supplier_gstin, expected_status, expected_supplier_risk_level,
  expected_is_exception, expected_itc_at_risk
"""

from pathlib import Path

import pandas as pd

from cleaner import clean_invoice_no, clean_gstin
from report_writer import calculate_itc_at_risk

REQUIRED_LABEL_COLUMNS = [
    "invoice_no",
    "supplier_gstin",
    "expected_status",
    "expected_supplier_risk_level",
    "expected_is_exception",
    "expected_itc_at_risk",
]

ITC_TOLERANCE = 0.01


def load_labels(file_path):
    """
    Load the labels CSV and return a DataFrame.

    Raises:
        FileNotFoundError: if the file does not exist
        ValueError: if the file is empty
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Labels file not found: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"Labels file is empty: {path}")

    return df


def validate_labels(df):
    """
    Check that the labels DataFrame has all required columns.

    Raises:
        ValueError: listing every missing column name
    """
    missing = set(REQUIRED_LABEL_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in labels file: {sorted(missing)}")
    return True


def prepare_actual_results(enriched_df):
    """
    Extract evaluation-relevant columns from the enriched pipeline output.

    Returns a DataFrame with:
      invoice_no, supplier_gstin,
      actual_status, actual_supplier_risk_level,
      actual_is_exception, actual_itc_at_risk
    """
    df = enriched_df.copy()

    df["actual_status"] = df["status"]
    df["actual_supplier_risk_level"] = df["supplier_risk_level"]
    df["actual_is_exception"] = (df["status"] != "matched") | (df["supplier_risk_level"] != "Low")
    df["actual_itc_at_risk"] = df.apply(calculate_itc_at_risk, axis=1)

    return df[[
        "invoice_no",
        "supplier_gstin",
        "actual_status",
        "actual_supplier_risk_level",
        "actual_is_exception",
        "actual_itc_at_risk",
    ]]


def normalize_eval_key(df):
    """
    Add normalized join-key columns to df in-place.

    Adds:
      eval_invoice_no  — cleaned invoice number (uppercase, no hyphens/spaces)
      eval_supplier_gstin — cleaned GSTIN (uppercase, stripped)

    Returns the modified DataFrame copy.
    """
    df = df.copy()

    invoice_col = "invoice_no"
    gstin_col = "supplier_gstin"

    df["eval_invoice_no"] = df[invoice_col].apply(clean_invoice_no)
    df["eval_supplier_gstin"] = df[gstin_col].apply(clean_gstin)

    return df


def compare_results(actual_df, labels_df):
    """
    Join actual results against labels and assess correctness per row.

    - Labels are the left side (all label rows are kept).
    - actual_df is deduplicated on (eval_invoice_no, eval_supplier_gstin) keeping
      first occurrence — avoids many-to-many for duplicate-key rows.
    - Unmatched label rows get NaN for actual fields and False for correctness.

    Returns a comparison DataFrame with per-row correct/incorrect flags.
    """
    labels = normalize_eval_key(labels_df)
    actual = normalize_eval_key(actual_df)

    # Deduplicate actual to first occurrence per key — prevents many-to-many join
    actual = actual.drop_duplicates(subset=["eval_invoice_no", "eval_supplier_gstin"], keep="first")

    merged = labels.merge(
        actual,
        on=["eval_invoice_no", "eval_supplier_gstin"],
        how="left",
        suffixes=("", "_actual"),
    )

    # Use label invoice_no/supplier_gstin as canonical identifiers
    result = pd.DataFrame()
    result["invoice_no"] = merged["invoice_no"]
    result["supplier_gstin"] = merged["supplier_gstin"]

    result["expected_status"] = merged["expected_status"]
    result["actual_status"] = merged["actual_status"]
    result["status_correct"] = result["expected_status"] == result["actual_status"]

    result["expected_supplier_risk_level"] = merged["expected_supplier_risk_level"]
    result["actual_supplier_risk_level"] = merged["actual_supplier_risk_level"]
    result["risk_level_correct"] = (
        result["expected_supplier_risk_level"] == result["actual_supplier_risk_level"]
    )

    result["expected_is_exception"] = merged["expected_is_exception"].astype(bool)
    # actual_is_exception may be NaN for unmatched rows
    result["actual_is_exception"] = merged["actual_is_exception"]
    result["exception_correct"] = result["expected_is_exception"] == result["actual_is_exception"]

    result["expected_itc_at_risk"] = pd.to_numeric(merged["expected_itc_at_risk"], errors="coerce")
    result["actual_itc_at_risk"] = pd.to_numeric(merged["actual_itc_at_risk"], errors="coerce")
    result["itc_at_risk_correct"] = (
        (result["expected_itc_at_risk"] - result["actual_itc_at_risk"]).abs() <= ITC_TOLERANCE
    )

    # Rows where actual had no match — force all correctness to False
    missing_mask = result["actual_status"].isna()
    for col in ["status_correct", "risk_level_correct", "exception_correct", "itc_at_risk_correct"]:
        result.loc[missing_mask, col] = False

    return result


def calculate_accuracy_metrics(comparison_df):
    """
    Aggregate the comparison DataFrame into accuracy metrics.

    Returns a dict with counts, percentages (0–100, 2 dp), and error counts.
    """
    df = comparison_df
    n = len(df)

    if n == 0:
        return {
            "total_labels": 0,
            "status_correct": 0,
            "status_accuracy": 0.0,
            "risk_level_correct": 0,
            "risk_level_accuracy": 0.0,
            "exception_correct": 0,
            "exception_accuracy": 0.0,
            "itc_at_risk_correct": 0,
            "itc_at_risk_accuracy": 0.0,
            "false_positive_exceptions": 0,
            "false_negative_exceptions": 0,
            "missing_actual_rows": 0,
        }

    def pct(count):
        return round(count / n * 100, 2)

    sc = int(df["status_correct"].sum())
    rlc = int(df["risk_level_correct"].sum())
    ec = int(df["exception_correct"].sum())
    itcc = int(df["itc_at_risk_correct"].sum())

    missing = int(df["actual_status"].isna().sum())

    fp = int(
        ((df["expected_is_exception"] == False) & (df["actual_is_exception"] == True)).sum()
    )
    fn = int(
        ((df["expected_is_exception"] == True) & (df["actual_is_exception"] == False)).sum()
    )

    return {
        "total_labels": n,
        "status_correct": sc,
        "status_accuracy": pct(sc),
        "risk_level_correct": rlc,
        "risk_level_accuracy": pct(rlc),
        "exception_correct": ec,
        "exception_accuracy": pct(ec),
        "itc_at_risk_correct": itcc,
        "itc_at_risk_accuracy": pct(itcc),
        "false_positive_exceptions": fp,
        "false_negative_exceptions": fn,
        "missing_actual_rows": missing,
    }


def print_evaluation_report(metrics):
    """
    Print a formatted evaluation report to stdout.
    """
    print("Evaluation Report:")
    print(f"  Total labelled rows: {metrics['total_labels']}")
    print()
    print("Accuracy:")
    print(f"  Status accuracy: {metrics['status_accuracy']}%")
    print(f"  Risk level accuracy: {metrics['risk_level_accuracy']}%")
    print(f"  Exception detection accuracy: {metrics['exception_accuracy']}%")
    print(f"  ITC at risk accuracy: {metrics['itc_at_risk_accuracy']}%")
    print()
    print("Errors:")
    print(f"  False positive exceptions: {metrics['false_positive_exceptions']}")
    print(f"  False negative exceptions: {metrics['false_negative_exceptions']}")
    print(f"  Missing actual rows: {metrics['missing_actual_rows']}")


def run_evaluation(enriched_df, labels_path):
    """
    Orchestrate the full evaluation pipeline.

    Steps:
      1. Load labels
      2. Validate labels columns
      3. Prepare actual results from enriched_df
      4. Compare actual vs labels
      5. Calculate accuracy metrics

    Returns:
        (comparison_df, metrics)
    """
    labels_df = load_labels(labels_path)
    validate_labels(labels_df)
    actual_df = prepare_actual_results(enriched_df)
    comparison_df = compare_results(actual_df, labels_df)
    metrics = calculate_accuracy_metrics(comparison_df)
    return comparison_df, metrics
