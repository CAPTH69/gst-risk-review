# Gap Log — GST Risk Review

A running log of what was built, what was learned, what broke, and what comes next.

---

## Sprint 1 — Project Setup + Data Loading + Validation

**Date:** 2024-05

### What I Built
- Project folder structure: `data/`, `src/`, `tests/`, `docs/`, `reports/`
- Three sample CSV files with realistic fake GST data:
  - `sample_purchase_register.csv` — 20 rows (includes 1 duplicate)
  - `sample_gstr2b.csv` — 18 rows (2 invoices missing vs purchase register, 1 extra)
  - `sample_supplier_master.csv` — 10 suppliers (1 inactive, 1 non-filer, 1 suspended)
- `data_loader.py` — load any CSV with clean error handling
- `validator.py` — check required columns with readable error messages
- `main.py` — CLI entry point that loads and validates all 3 files
- `tests/test_data_loader.py` and `tests/test_validator.py` — pytest coverage
- `docs/product_thesis.md`, `docs/research_gap.md`, `docs/failure_cases.md`

### What I Learned
- The hardest part of GST reconciliation is data quality, not the matching logic itself.
- Fake data must encode the real failure modes (mismatches, duplicates, missing rows) or tests are meaningless.
- Column validation should give the CA a full list of missing columns in one error, not crash on the first missing one.
- Keeping `main.py` in `src/` requires `sys.path` adjustment in tests — a known Python project layout tradeoff.

### What Broke
- Nothing critical in Sprint 1. The load + validate flow is intentionally simple.
- `main.py` uses relative imports via `sys.path` manipulation — this works for Sprint 1 but should be replaced with a proper package install (`pip install -e .`) in a later sprint.

### What I Need to Understand Next
- How to normalize invoice numbers reliably (strip whitespace, uppercase, remove leading zeros)
- How to handle date format differences across different client software exports
- Whether to match on invoice_no + supplier_gstin together, or invoice_no alone (risk of collision)
- How GSTR-2B actually differs from GSTR-2A and why it matters for ITC eligibility

### Next Sprint
**Sprint 2 — Data Cleaning + Invoice Matching**
- Normalize invoice_no and supplier_gstin (strip, upper, dedupe)
- Normalize invoice_date to a single format
- Match purchase register vs GSTR-2B on (invoice_no, supplier_gstin)
- Output: DataFrame with columns — invoice_no, supplier_gstin, status (matched / missing_in_2b / extra_in_2b / amount_mismatch)
- New tests: matching logic, edge cases from `docs/failure_cases.md`
