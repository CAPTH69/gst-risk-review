# Failure Cases: Known Edge Cases for Future Sprints

This document tracks real-world scenarios that can break the reconciliation logic.
Each case should eventually have a test that covers it.

---

## Data Quality Failures

| Case | Description | Sprint |
|---|---|---|
| Whitespace in invoice numbers | "INV-001 " vs "INV-001" — won't match | Sprint 2 |
| Inconsistent date formats | "05-01-2024" vs "2024-01-05" | Sprint 2 |
| Mixed case supplier names | "Reliable traders" vs "RELIABLE TRADERS" | Sprint 2 |
| Extra spaces in GSTIN | "27AABCU9603R1ZX " — breaks exact match | Sprint 2 |
| Partial invoices (split payments) | Same invoice split across two rows | Sprint 2 |

---

## ITC Eligibility Failures

| Case | Description | Sprint |
|---|---|---|
| Supplier GSTIN cancelled | ITC claim is invalid — must flag | Sprint 3 |
| Supplier is a non-filer | GSTR-1 not filed — ITC won't reflect in GSTR-2B | Sprint 3 |
| Supplier filed late | GSTR-2B shows up in wrong month | Sprint 3 |
| Invoice date vs return period mismatch | Invoice dated Jan but filed in Mar | Sprint 3 |
| Composition dealer supplier | Cannot issue tax invoices — ITC not eligible | Sprint 3 |

---

## Reconciliation Failures

| Case | Description | Sprint |
|---|---|---|
| Invoice in PR but not in GSTR-2B | Supplier didn't report it — ITC at risk | Sprint 2 ✓ |
| Invoice in GSTR-2B but not in PR | Client missed entering it — potential under-claim | Sprint 2 ✓ |
| Amount mismatch (taxable value) | PR says ₹90k, GSTR-2B says ₹95k | Sprint 2 ✓ |
| Amount mismatch (tax amount) | Rounding differences vs actual error | Sprint 2 ✓ |
| Duplicate invoices in PR | Same invoice entered twice — inflated ITC claim | Sprint 2 ✓ |

### Duplicate Handling Policy (implemented Sprint 2)

When the same `(supplier_gstin, invoice_no)` key appears more than once in the purchase register:

- The **first occurrence** is used for normal reconciliation (matched, missing_in_2b, amount_mismatch, etc.)
- Every **subsequent occurrence** is flagged as `duplicate_in_purchase` and appended to the output separately
- This prevents the corresponding GSTR-2B invoice from being incorrectly classified as `extra_in_2b`

The same policy applies to duplicate keys in GSTR-2B (`duplicate_in_gstr2b`).

**Why this matters:** If the tool discarded all occurrences of a duplicated key, INV-2024-001 (present once in GSTR-2B) would appear as `extra_in_2b` — misleading the CA into thinking GSTR-2B has an unrecognized invoice. The correct signal is: "you have a duplicate entry in your purchase register, and the supplier's GSTR-2B is fine."

---

## Supplier Risk Failures (Sprint 3)

| Case | Description | Sprint |
|---|---|---|
| Inactive GSTIN supplier | ITC claim legally invalid — GSTIN cancelled by department | Sprint 3 ✓ |
| Suspended GSTIN supplier | GSTIN deactivated — CA must not file ITC from this supplier | Sprint 3 ✓ |
| Non-filing supplier | Supplier didn't file GSTR-1 — ITC will never appear in GSTR-2B | Sprint 3 ✓ |
| Irregular filer supplier | Returns filed late — ITC may appear in wrong tax period | Sprint 3 ✓ |
| Unknown supplier (not in master) | Cannot verify GSTIN status — score +35, Medium risk by default | Sprint 3 ✓ |
| Non-filer + missing in GSTR-2B | Compound risk — ITC not only unfiled but also absent from 2B | Sprint 3 ✓ |
| Score overflow (>100) | Multiple factors can add to >100 — capped at 100 | Sprint 3 ✓ |

### What Is Not Covered Yet
| Case | Description | Sprint |
|---|---|---|
| Supplier GSTIN changed mid-year | Different GSTINs for same legal entity across periods | Sprint 4 |
| GSTIN format validation | Check that GSTIN is 15 chars and matches state code pattern | Sprint 4 |
| Supplier master staleness | Risk note may be outdated if master isn't refreshed regularly | Sprint 4 |

---

## Report Generation Failures (Sprint 4)

| Case | Handled? | Description |
|---|---|---|
| No exception rows | ✓ | Returns header-only Excel; does not crash |
| Unknown supplier in exceptions | ✓ | Supplier name = "Unknown Supplier"; score = +35 |
| Missing purchase_total_itc (NaN) | ✓ | `calculate_itc_at_risk` returns 0.0 safely |
| Amount mismatch with one side blank | ✓ | Treats NaN as 0.0 before subtraction |
| Matched invoice from high-risk supplier | ✓ | Included in exceptions; ITC = purchase_total_itc |
| `extra_in_2b` row (no purchase ITC) | ✓ | ITC at risk = 0.0; action = "Check whether invoice is missing from books" |
| Reports dir missing | ✓ | `mkdir(parents=True, exist_ok=True)` creates it |

### What Is Not Covered Yet
| Case | Description | Sprint |
|---|---|---|
| CA annotates the Excel and tool re-reads it | No re-read / review workflow yet | Sprint 5 |
| Duplicate sheet name on same date | Re-running overwrites — no versioning | Sprint 5 |
| Report with 1000+ rows | Column widths are fixed — may truncate long text | Sprint 5 |

---

## Evaluation Failures (Sprint 6)

| Case | Handled? | Description |
|---|---|---|
| Missing labels file | ✓ | FileNotFoundError with readable path message |
| Empty labels file | ✓ | ValueError — header-only CSV raises before evaluation starts |
| Missing required label column | ✓ | ValueError listing all missing column names |
| Label row not found in actual output | ✓ | actual fields = NaN; all correctness flags = False |
| Expected status differs from actual | ✓ | status_correct = False; counted in status_accuracy denominator |
| Expected risk level differs from actual | ✓ | risk_level_correct = False |
| False positive exception | ✓ | expected_is_exception=False, actual=True; counted in false_positive_exceptions |
| False negative exception | ✓ | expected_is_exception=True, actual=False; counted in false_negative_exceptions |
| ITC at risk mismatch | ✓ | itc_at_risk_correct = False if abs diff > 0.01 |
| Duplicate key in actual (same invoice_no + gstin) | ✓ | actual deduplicated keeping first; duplicate row not labeled |

### What Is Not Covered Yet
| Case | Description | Sprint |
|---|---|---|
| Label versioning | No way to know which pipeline version produced which labels | Sprint 7 |
| Per-supplier accuracy breakdown | Overall accuracy hides supplier-level gaps | Sprint 7 |
| Automatic label generation | Labels must be authored manually — no labeling UI | Sprint 7 |

---

## Notes

- Every failure case above should become a test case in `tests/` when that sprint arrives.
- The goal is to know what breaks *before* deploying, not after.
