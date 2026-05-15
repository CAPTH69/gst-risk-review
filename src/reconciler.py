"""
reconciler.py - Match purchase register invoices against GSTR-2B.

The core reconciliation logic for Sprint 2. Each invoice in the purchase
register is compared against what the supplier reported in GSTR-2B, and
classified into one of these statuses:

  matched            - invoice present in both, amounts agree
  missing_in_2b      - invoice in purchase register but not in GSTR-2B
  extra_in_2b        - invoice in GSTR-2B but not in purchase register
  amount_mismatch    - invoice in both, but total_itc differs
  duplicate_in_purchase - same key appears more than once in purchase register
  duplicate_in_gstr2b   - same key appears more than once in GSTR-2B
"""

import pandas as pd

# The match key: supplier + invoice number (both cleaned)
MATCH_KEY = ["clean_supplier_gstin", "clean_invoice_no"]

# Tolerance for floating point amount comparison (e.g. rounding differences)
AMOUNT_TOLERANCE = 0.01


def _find_duplicates(df, label):
    """
    Split df into two parts:
      - first_occurrences: one row per unique key (the first seen) — used for matching
      - extra_dups: all subsequent rows with a repeated key — flagged as duplicates

    Policy: keep the first occurrence for normal reconciliation so the matching
    GSTR-2B invoice is not incorrectly classified as extra_in_2b. Only the
    repeated purchase rows are flagged as duplicate_in_purchase.

    Args:
        df: cleaned DataFrame (must have clean_supplier_gstin, clean_invoice_no)
        label: 'purchase' or 'gstr2b' — used to set the status value

    Returns:
        (extra_dups_df, first_occurrences_df)
    """
    # Mark every row beyond the first occurrence of each key
    is_extra_dup = df.duplicated(subset=MATCH_KEY, keep="first")

    extra_dups = df[is_extra_dup].copy()
    first_occurrences = df[~is_extra_dup].copy()

    if extra_dups.empty:
        return pd.DataFrame(), first_occurrences

    extra_dups["status"] = f"duplicate_in_{label}"
    extra_dups["mismatch_reason"] = f"Repeated match key — later occurrence in {label}"

    return extra_dups, first_occurrences


def _classify_row(row):
    """
    Given a merged row (outer join of PR and GSTR-2B), return (status, mismatch_reason).
    """
    pr_itc = row["purchase_total_itc"]
    g2b_itc = row["gstr2b_total_itc"]

    pr_missing = pd.isna(pr_itc)
    g2b_missing = pd.isna(g2b_itc)

    if pr_missing:
        return "extra_in_2b", "Invoice found in GSTR-2B but not in purchase register"

    if g2b_missing:
        return "missing_in_2b", "Invoice found in purchase register but not in GSTR-2B"

    if abs(pr_itc - g2b_itc) <= AMOUNT_TOLERANCE:
        return "matched", ""

    return "amount_mismatch", f"ITC differs: purchase={pr_itc}, gstr2b={g2b_itc}"


def reconcile_invoices(purchase_df, gstr2b_df):
    """
    Match purchase register invoices against GSTR-2B and classify each one.

    Both DataFrames must already be cleaned (have clean_invoice_no and
    clean_supplier_gstin columns, and float amount columns).

    Returns a DataFrame with columns:
      invoice_no, supplier_gstin, status, mismatch_reason,
      purchase_total_itc, gstr2b_total_itc
    """
    # Step 1: Separate out duplicate-key rows from each side
    pr_dups, pr_unique = _find_duplicates(purchase_df, "purchase")
    g2b_dups, g2b_unique = _find_duplicates(gstr2b_df, "gstr2b")

    # Step 2: Outer merge unique rows from both sides on the match key
    merged = pd.merge(
        pr_unique[MATCH_KEY + ["invoice_no", "supplier_gstin", "total_itc"]].rename(
            columns={"invoice_no": "pr_invoice_no", "supplier_gstin": "pr_supplier_gstin", "total_itc": "purchase_total_itc"}
        ),
        g2b_unique[MATCH_KEY + ["invoice_no", "supplier_gstin", "total_itc"]].rename(
            columns={"invoice_no": "g2b_invoice_no", "supplier_gstin": "g2b_supplier_gstin", "total_itc": "gstr2b_total_itc"}
        ),
        on=MATCH_KEY,
        how="outer",
    )

    # Step 3: Classify each merged row
    statuses = []
    reasons = []
    for _, row in merged.iterrows():
        status, reason = _classify_row(row)
        statuses.append(status)
        reasons.append(reason)

    merged["status"] = statuses
    merged["mismatch_reason"] = reasons

    # Step 4: Build clean output — use whichever side has the invoice_no / gstin
    merged["invoice_no"] = merged["pr_invoice_no"].fillna(merged["g2b_invoice_no"])
    merged["supplier_gstin"] = merged["pr_supplier_gstin"].fillna(merged["g2b_supplier_gstin"])

    output_cols = ["invoice_no", "supplier_gstin", "status", "mismatch_reason",
                   "purchase_total_itc", "gstr2b_total_itc"]
    result = merged[output_cols].copy()

    # Step 5: Append duplicate rows from purchase register
    if not pr_dups.empty:
        pr_dup_out = pr_dups[["invoice_no", "supplier_gstin", "status", "mismatch_reason"]].copy()
        pr_dup_out["purchase_total_itc"] = pr_dups["total_itc"].values
        pr_dup_out["gstr2b_total_itc"] = float("nan")
        result = pd.concat([result, pr_dup_out[output_cols]], ignore_index=True)

    # Step 6: Append duplicate rows from GSTR-2B
    if not g2b_dups.empty:
        g2b_dup_out = g2b_dups[["invoice_no", "supplier_gstin", "status", "mismatch_reason"]].copy()
        g2b_dup_out["gstr2b_total_itc"] = g2b_dups["total_itc"].values
        g2b_dup_out["purchase_total_itc"] = float("nan")
        result = pd.concat([result, g2b_dup_out[output_cols]], ignore_index=True)

    return result
