"""
main.py - Entry point for GST Risk Review Sprint 1.

Loads all three sample CSV files, validates their columns, and prints a summary.
Run this to confirm the project is set up correctly.
"""

from pathlib import Path
from data_loader import load_purchase_register, load_gstr2b, load_supplier_master
from validator import validate_purchase_register, validate_gstr2b, validate_supplier_master


# Paths to sample data files
DATA_DIR = Path(__file__).parent.parent / "data"

PURCHASE_REGISTER_PATH = DATA_DIR / "sample_purchase_register.csv"
GSTR2B_PATH = DATA_DIR / "sample_gstr2b.csv"
SUPPLIER_MASTER_PATH = DATA_DIR / "sample_supplier_master.csv"


def main():
    print("=== GST Risk Review - Sprint 1 ===\n")

    # Load all three files
    purchase_df = load_purchase_register(PURCHASE_REGISTER_PATH)
    gstr2b_df = load_gstr2b(GSTR2B_PATH)
    supplier_df = load_supplier_master(SUPPLIER_MASTER_PATH)

    # Validate columns
    validate_purchase_register(purchase_df)
    validate_gstr2b(gstr2b_df)
    validate_supplier_master(supplier_df)

    # Print summary
    print(f"Purchase Register Loaded: {len(purchase_df)} rows")
    print(f"GSTR-2B Loaded: {len(gstr2b_df)} rows")
    print(f"Supplier Master Loaded: {len(supplier_df)} rows")
    print("\nValidation successful")


if __name__ == "__main__":
    main()
