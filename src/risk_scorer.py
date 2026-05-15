"""
risk_scorer.py - Assign a risk score to each reconciled invoice.

Combines supplier GSTIN/filing status from the supplier master with the
reconciliation outcome to produce a numeric risk score (0–100), a risk
level (Low / Medium / High), and a human-readable reason string for the CA.

Risk scoring logic:
  Inactive GSTIN        +75  → ITC claim legally invalid
  Suspended GSTIN       +75  → GSTIN deactivated by department
  Non-Filer             +75  → Supplier didn't file returns; ITC won't appear in 2B
  Irregular Filer       +40  → Supplier files late; ITC may appear in wrong period
  Missing in GSTR-2B   +40  → Supplier didn't report this invoice; ITC at risk
  Amount mismatch       +35  → Tax amounts differ between PR and GSTR-2B
  Duplicate in PR       +75  → ITC may be overclaimed (same invoice counted twice)
  Extra in GSTR-2B      +10  → Invoice in 2B but not in PR; possible missed entry
  Unknown supplier      +35  → Supplier not found in master; cannot verify status
  Matched + clean        +0  → No risk signals
"""

import pandas as pd
from cleaner import clean_gstin


def clean_supplier_status(value):
    """Normalize gstin_status to uppercase string. Returns '' for null."""
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def clean_return_filing_status(value):
    """Normalize return_filing_status to uppercase string. Returns '' for null."""
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def calculate_supplier_risk_score(gstin_status, return_filing_status, reconciliation_status, found_in_master):
    """
    Return an integer risk score (0–100) for a single invoice row.

    Args:
        gstin_status: cleaned (uppercased) gstin_status string
        return_filing_status: cleaned (uppercased) return_filing_status string
        reconciliation_status: status string from reconcile_invoices output
        found_in_master: bool — True if supplier was found in supplier master

    Returns:
        int — risk score between 0 and 100
    """
    score = 0

    # Supplier GSTIN/filing status signals
    if "INACTIVE" in gstin_status:
        score += 75
    if "SUSPENDED" in gstin_status:
        score += 75
    if "NON-FILER" in return_filing_status or "NON FILER" in return_filing_status:
        score += 75
    elif "IRREGULAR" in return_filing_status:
        # elif so Irregular Filer doesn't also fire when Non-Filer is present
        score += 40

    # Reconciliation outcome signals
    if reconciliation_status == "missing_in_2b":
        score += 40
    elif reconciliation_status == "amount_mismatch":
        score += 35
    elif reconciliation_status == "duplicate_in_purchase":
        score += 75
    elif reconciliation_status == "extra_in_2b":
        score += 10

    # Unknown supplier — cannot verify compliance
    if not found_in_master:
        score += 35

    return min(score, 100)


def get_risk_level(score):
    """
    Convert a numeric score to a human-readable risk level.

    0–30  → Low
    31–70 → Medium
    71–100 → High
    """
    if score <= 30:
        return "Low"
    if score <= 70:
        return "Medium"
    return "High"


def build_risk_reasons(gstin_status, return_filing_status, reconciliation_status, found_in_master):
    """
    Build a readable list of risk reason strings for the CA.

    Returns a single string with reasons separated by '; ', or
    'No major supplier risk detected' when no risk signals are found.
    """
    reasons = []

    if "INACTIVE" in gstin_status:
        reasons.append("Inactive GSTIN")
    if "SUSPENDED" in gstin_status:
        reasons.append("Suspended GSTIN")
    if "NON-FILER" in return_filing_status or "NON FILER" in return_filing_status:
        reasons.append("Non-filer supplier")
    elif "IRREGULAR" in return_filing_status:
        reasons.append("Irregular filer")

    if reconciliation_status == "missing_in_2b":
        reasons.append("Invoice missing in GSTR-2B")
    elif reconciliation_status == "amount_mismatch":
        reasons.append("Amount mismatch")
    elif reconciliation_status == "duplicate_in_purchase":
        reasons.append("Duplicate invoice in purchase register")
    elif reconciliation_status == "extra_in_2b":
        reasons.append("Invoice only in GSTR-2B")

    if not found_in_master:
        reasons.append("Supplier not found in master")

    if not reasons:
        return "No major supplier risk detected"

    return "; ".join(reasons)


def add_supplier_risk(reconciliation_df, supplier_master_df):
    """
    Enrich the reconciliation DataFrame with supplier risk columns.

    Joins on clean_supplier_gstin (normalized GSTIN) so that minor
    formatting differences between the two files don't break the join.

    Adds columns:
      supplier_name         — from supplier master, or "Unknown Supplier"
      gstin_status          — from supplier master
      return_filing_status  — from supplier master
      supplier_risk_score   — integer 0–100
      supplier_risk_level   — Low / Medium / High
      supplier_risk_reasons — human-readable explanation string

    All reconciliation rows are preserved (left join).
    """
    # Step 1: Normalize the join key in supplier master
    sm = supplier_master_df.copy()
    sm["clean_supplier_gstin"] = sm["supplier_gstin"].apply(clean_gstin)

    # Step 2: Normalize join key in reconciliation result
    # reconcile_invoices returns raw supplier_gstin — re-clean here for safety
    rec = reconciliation_df.copy()
    rec["clean_supplier_gstin"] = rec["supplier_gstin"].apply(clean_gstin)

    # Step 3: Left join — keeps every reconciliation row
    joined = pd.merge(
        rec,
        sm[["clean_supplier_gstin", "supplier_name", "gstin_status", "return_filing_status"]],
        on="clean_supplier_gstin",
        how="left",
    )

    # Step 4: Detect unknown suppliers (not found in master)
    joined["found_in_master"] = joined["supplier_name"].notna()

    # Step 5: Clean status strings (NaN → "" for unknown suppliers)
    joined["gstin_status_clean"] = joined["gstin_status"].apply(clean_supplier_status)
    joined["return_filing_status_clean"] = joined["return_filing_status"].apply(clean_return_filing_status)

    # Step 6: Calculate score, level, and reasons per row
    joined["supplier_risk_score"] = joined.apply(
        lambda row: calculate_supplier_risk_score(
            row["gstin_status_clean"],
            row["return_filing_status_clean"],
            row["status"],
            row["found_in_master"],
        ),
        axis=1,
    )

    joined["supplier_risk_level"] = joined["supplier_risk_score"].apply(get_risk_level)

    joined["supplier_risk_reasons"] = joined.apply(
        lambda row: build_risk_reasons(
            row["gstin_status_clean"],
            row["return_filing_status_clean"],
            row["status"],
            row["found_in_master"],
        ),
        axis=1,
    )

    # Step 7: Clean up — fill unknown supplier name, drop temp columns
    joined["supplier_name"] = joined["supplier_name"].fillna("Unknown Supplier")
    joined = joined.drop(columns=["gstin_status_clean", "return_filing_status_clean",
                                  "found_in_master", "clean_supplier_gstin"])

    return joined
