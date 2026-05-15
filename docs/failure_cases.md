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

## Evaluation Failures

| Case | Description | Sprint |
|---|---|---|
| False positives in mismatch detection | Tool flags a match as a mismatch due to formatting | Sprint 4 |
| Missing coverage metrics | No way to know what % of invoices were reconciled | Sprint 4 |
| No audit trail | No record of what was flagged, reviewed, or overridden | Sprint 4 |

---

## Notes

- Every failure case above should become a test case in `tests/` when that sprint arrives.
- The goal is to know what breaks *before* deploying, not after.
