"""
main.py - Entry point for GST Risk Review.

Loads all three sample CSV files, validates columns, cleans data,
runs invoice reconciliation, scores supplier risk, and prints a summary.
"""

from pathlib import Path
from data_loader import load_purchase_register, load_gstr2b, load_supplier_master
from validator import validate_purchase_register, validate_gstr2b, validate_supplier_master
from cleaner import clean_purchase_register, clean_gstr2b
from reconciler import reconcile_invoices
from risk_scorer import add_supplier_risk


# Paths to sample data files
DATA_DIR = Path(__file__).parent.parent / "data"

PURCHASE_REGISTER_PATH = DATA_DIR / "sample_purchase_register.csv"
GSTR2B_PATH = DATA_DIR / "sample_gstr2b.csv"
SUPPLIER_MASTER_PATH = DATA_DIR / "sample_supplier_master.csv"


def main():
    print("=== GST Risk Review - Sprint 3 ===\n")

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


if __name__ == "__main__":
    main()
