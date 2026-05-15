# GST Risk Review

A pre-filing GST risk review tool for Indian CA firms.

## What This Project Does

Before filing a GST return, a CA firm needs to verify that:
- Invoices in the purchase register match what suppliers reported in GSTR-2B
- Suppliers are active and filing returns (inactive suppliers = invalid ITC)
- No ITC is being claimed on mismatched or missing invoices

This project builds that verification system step by step. **Sprint 1** focuses on loading the raw data and confirming it is structurally valid before any analysis begins.

---

## Why Sprint 1 Exists

You cannot reconcile data you cannot read. Sprint 1 answers one question:

> "Can we load all three input files and confirm they have the columns we expect?"

This is the foundation. Every future sprint (matching, risk scoring, reports) builds on top of it.

---

## Project Structure

```
gst-risk-review/
  data/
    sample_purchase_register.csv   # Client's purchase invoices (fake data)
    sample_gstr2b.csv              # Supplier-reported invoices from GST portal (fake)
    sample_supplier_master.csv     # GSTIN status and risk notes for each supplier

  src/
    data_loader.py                 # Functions to load each CSV
    validator.py                   # Functions to check required columns
    main.py                        # Entry point - loads and validates all files

  tests/
    test_data_loader.py            # Tests for loading functions
    test_validator.py              # Tests for validation functions

  docs/
    product_thesis.md              # What we are building and why
    research_gap.md                # Where existing tools fall short
    failure_cases.md               # Known edge cases to handle later

  reports/                         # Output reports will be saved here (Sprint 3+)
  requirements.txt
  gap_log.md
```

---

## How to Install Dependencies

Make sure you have Python 3.11 or higher.

```bash
# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

---

## How to Run main.py

```bash
# From the project root (gst-risk-review/)
cd src
python main.py
```

Expected output:
```
=== GST Risk Review - Sprint 1 ===

Purchase Register Loaded: 20 rows
GSTR-2B Loaded: 18 rows
Supplier Master Loaded: 10 rows

Validation successful
```

---

## How to Run Tests

```bash
# From the project root (gst-risk-review/)
pytest tests/ -v
```

You should see all tests pass.

---

## Sample Data Notes

The sample CSVs contain realistic but completely fake data. Built-in test cases for future sprints:

| Scenario | Detail |
|---|---|
| Invoices in purchase register but NOT in GSTR-2B | INV-2024-013, INV-2024-018 |
| Invoice in GSTR-2B but NOT in purchase register | INV-2024-020 |
| Amount mismatch (same invoice, different values) | INV-2024-008 (₹90k in PR, ₹95k in GSTR-2B) |
| Duplicate invoice in purchase register | INV-2024-001 appears twice — first occurrence reconciles normally, second is flagged `duplicate_in_purchase` |
| Inactive supplier (ITC claim invalid) | Global Goods Ltd - GSTIN cancelled |
| Non-filing supplier (ITC at risk) | Eastern Traders - no returns filed |

---

## Duplicate Invoice Policy

When the same `(supplier_gstin, invoice_no)` appears more than once in the purchase register:

- The **first occurrence** enters normal reconciliation (matched / missing_in_2b / amount_mismatch)
- Every **later occurrence** is flagged `duplicate_in_purchase` in the output
- The corresponding GSTR-2B invoice is **not** classified as `extra_in_2b` — because the first purchase occurrence covers it

This prevents a false alarm: a CA should see "you have a duplicate entry" — not "GSTR-2B has an unrecognised invoice."

---

## Sprint 3: Supplier Risk Scoring

Each reconciled invoice is scored against the supplier's GSTIN status and return-filing behavior.

### How Risk Is Calculated

Risk factors are additive. The final score is capped at 100.

| Signal | Points |
|---|---|
| Inactive GSTIN | +75 |
| Suspended GSTIN | +75 |
| Non-Filer supplier | +75 |
| Irregular Filer | +40 |
| Invoice missing in GSTR-2B | +40 |
| Amount mismatch | +35 |
| Duplicate invoice in purchase register | +75 |
| Invoice only in GSTR-2B | +10 |
| Supplier not found in master | +35 |

### Risk Levels

| Score | Level |
|---|---|
| 0–30 | Low |
| 31–70 | Medium |
| 71–100 | High |

### Sample Data Output

```
Reconciliation Summary:
  matched: 16
  missing_in_2b: 2
  extra_in_2b: 1
  amount_mismatch: 1
  duplicate_in_purchase: 1

Supplier Risk Summary:
  High: 7
  Medium: 2
  Low: 12
```

---

## Sprint 4: Exception Report (Excel Output)

After reconciliation and risk scoring, the tool generates a CA-readable Excel file.

### What the Report Contains

Only exception rows are included — invoices where something needs CA attention:
- Any reconciliation status other than `matched`
- Any `matched` invoice where the supplier risk is Medium or High

Each row includes 12 columns:

| Column | What It Shows |
|---|---|
| Invoice No | Invoice identifier |
| Supplier GSTIN | Supplier's GST registration number |
| Supplier Name | Supplier's name from the master |
| Reconciliation Status | matched / missing_in_2b / amount_mismatch / etc. |
| Mismatch Reason | Why it didn't match (if applicable) |
| Supplier Risk Level | High / Medium / Low |
| Supplier Risk Score | Numeric score (0–100) |
| Supplier Risk Reasons | Human-readable risk explanation |
| Purchase ITC | ITC claimed in purchase register |
| GSTR-2B ITC | ITC as per GSTR-2B |
| ITC At Risk | Estimated rupee amount at risk |
| Suggested CA Action | "Review before filing", "Verify supporting documents", etc. |

### Excel Formatting
- Bold header row
- Frozen top row (scroll without losing headers)
- Autofilter on all columns
- Row colour: red = High risk, amber = Medium risk
- Sensible column widths

### Where the Report Is Saved
```
reports/exception_report_YYYYMMDD.xlsx
```

### Sample Output
```
Exception report generated: .../reports/exception_report_20260516.xlsx
  Exception rows: 9
```

---

## Sprint 6: Evaluation System

After reconciliation and risk scoring, the tool can now measure how accurate its outputs are by comparing them against a ground-truth labels file.

### Why Evaluation Matters

Without labels, you only know *what* the tool produced. With labels, you know *whether it was correct*. This is what separates a prototype from a tool you can trust before filing.

### What `data/labels.csv` Is

A human-authored ground-truth file with 20 rows (one per unique invoice in the sample data). Each row records:

| Column | What It Contains |
|---|---|
| invoice_no | Invoice identifier (raw, as in source data) |
| supplier_gstin | Supplier GSTIN |
| expected_status | matched / missing_in_2b / extra_in_2b / amount_mismatch / duplicate_in_purchase |
| expected_supplier_risk_level | Low / Medium / High |
| expected_is_exception | True / False — should this row appear in the exception report? |
| expected_itc_at_risk | Rupee amount of ITC at risk |

### How to Run Evaluation

```bash
# From the project root
cd src
python main.py --evaluate

# With a custom labels path
python main.py --evaluate --labels ../data/labels.csv
```

### What the Evaluation Report Shows

```
Evaluation Report:
  Total labelled rows: 20

Accuracy:
  Status accuracy: 100.0%
  Risk level accuracy: 100.0%
  Exception detection accuracy: 100.0%
  ITC at risk accuracy: 100.0%

Errors:
  False positive exceptions: 0
  False negative exceptions: 0
  Missing actual rows: 0
```

### Metric Definitions

| Metric | What It Measures |
|---|---|
| Status accuracy | % of invoices classified with the correct reconciliation status |
| Risk level accuracy | % of invoices assigned the correct supplier risk level |
| Exception detection accuracy | % of invoices correctly identified as exception / non-exception |
| ITC at risk accuracy | % of invoices where ITC at risk matches the label within ₹0.01 |
| False positive exceptions | Invoices flagged as exceptions when they should not be |
| False negative exceptions | Invoices missed as exceptions when they should have been flagged |
| Missing actual rows | Labels that had no matching row in the pipeline output |

---

## Next Sprint Preview: Sprint 7 — Streamlit Dashboard / UI

Sprint 7 will add a lightweight local UI so the CA firm can upload CSVs, view the exception report, and step through the review workflow without touching the terminal.
