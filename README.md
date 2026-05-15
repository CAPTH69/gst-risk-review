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
| Duplicate invoice in purchase register | INV-2024-001 appears twice |
| Inactive supplier (ITC claim invalid) | Global Goods Ltd - GSTIN cancelled |
| Non-filing supplier (ITC at risk) | Eastern Traders - no returns filed |

---

## Next Sprint Preview: Sprint 2 — Data Cleaning + Invoice Matching

Sprint 2 will:
- Normalize invoice numbers and dates (handle whitespace, format differences)
- Match purchase register rows against GSTR-2B rows by invoice number + GSTIN
- Identify: missing invoices, extra invoices, amount mismatches
- Output a structured reconciliation result as a DataFrame
