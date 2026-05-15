"""
main.py - Entry point for GST Risk Review.

Normal mode (no flags):
  Loads all three sample CSV files, validates columns, cleans data,
  runs invoice reconciliation, scores supplier risk, and writes an
  Excel exception report.

Review mode (--review FILE):
  Reads a CA-reviewed exception report Excel file and prints a filing
  recommendation summary.
"""

import argparse
from pathlib import Path

from data_loader import load_purchase_register, load_gstr2b, load_supplier_master
from validator import validate_purchase_register, validate_gstr2b, validate_supplier_master
from cleaner import clean_purchase_register, clean_gstr2b
from reconciler import reconcile_invoices
from risk_scorer import add_supplier_risk
from report_writer import prepare_exception_report, generate_report_filename, write_exception_report
from review_processor import process_reviewed_report, print_review_summary


# Paths to sample data files
DATA_DIR = Path(__file__).parent.parent / "data"
REPORTS_DIR = Path(__file__).parent.parent / "reports"

PURCHASE_REGISTER_PATH = DATA_DIR / "sample_purchase_register.csv"
GSTR2B_PATH = DATA_DIR / "sample_gstr2b.csv"
SUPPLIER_MASTER_PATH = DATA_DIR / "sample_supplier_master.csv"


def run_normal_mode():
    """Load, validate, clean, reconcile, score, and generate an Excel exception report."""
    print("=== GST Risk Review - Sprint 5 ===\n")

    # Load all three files
    purchase_df = load_purchase_register(PURCHASE_REGISTER_PATH)
    gstr2b_df = load_gstr2b(GSTR2B_PATH)
    supplier_df = load_supplier_master(SUPPLIER_MASTER_PATH)

    # Validate columns
    validate_purchase_register(purchase_df)
    validate_gstr2b(gstr2b_df)
    validate_supplier_master(supplier_df)

    # Print load summary
    print(f"Purchase Register Loaded: {len(purchase_df)} rows")
    print(f"GSTR-2B Loaded: {len(gstr2b_df)} rows")
    print(f"Supplier Master Loaded: {len(supplier_df)} rows")
    print("\nValidation successful")

    # Clean data (normalize invoice numbers, GSTINs, amounts)
    purchase_df = clean_purchase_register(purchase_df)
    gstr2b_df = clean_gstr2b(gstr2b_df)

    # Reconcile purchase register against GSTR-2B
    result_df = reconcile_invoices(purchase_df, gstr2b_df)

    # Add supplier risk scores
    result_df = add_supplier_risk(result_df, supplier_df)

    # Print reconciliation summary
    print("\nReconciliation Summary:")
    for status, count in result_df["status"].value_counts().items():
        print(f"  {status}: {count}")

    # Print supplier risk summary
    print("\nSupplier Risk Summary:")
    for level in ["High", "Medium", "Low"]:
        count = (result_df["supplier_risk_level"] == level).sum()
        print(f"  {level}: {count}")

    # Generate Excel exception report
    report_df = prepare_exception_report(result_df)
    report_path = REPORTS_DIR / generate_report_filename()
    write_exception_report(report_df, report_path)
    print(f"\nException report generated: {report_path}")
    print(f"  Exception rows: {len(report_df)}")


def run_review_mode(report_path):
    """Read a CA-reviewed Excel report and print a filing recommendation."""
    summary = process_reviewed_report(report_path)
    print_review_summary(summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GST Risk Review — pre-filing ITC risk tool for CA firms"
    )
    parser.add_argument(
        "--review",
        metavar="FILE",
        help="Path to a CA-reviewed exception report Excel file",
    )
    args = parser.parse_args()

    if args.review:
        run_review_mode(args.review)
    else:
        run_normal_mode()
