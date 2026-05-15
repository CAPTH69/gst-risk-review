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
**Sprint 2 — Data Cleaning + Invoice Matching** ✓ Complete

---

## Sprint 3 — Supplier Risk Scoring

**Date:** 2024-05

### What I Built
- `src/risk_scorer.py` — five functions:
  - `clean_supplier_status` / `clean_return_filing_status` — normalize status strings
  - `calculate_supplier_risk_score` — additive scoring (0–100, capped): 8 risk signals
  - `get_risk_level` — Low / Medium / High thresholds
  - `build_risk_reasons` — human-readable reason string for the CA
  - `add_supplier_risk` — joins supplier master to reconciliation result on clean GSTIN
- `tests/test_risk_scorer.py` — 59 tests across all 5 functions
- Updated `main.py` — prints Supplier Risk Summary (High/Medium/Low counts)
- Updated `docs/failure_cases.md` — supplier risk edge cases documented
- Sample data output: **High: 7, Medium: 2, Low: 12** across 21 reconciled rows

### What I Learned
- Joining on raw `supplier_gstin` would silently fail for case/whitespace mismatches. Cleaning both sides before joining is the correct pattern.
- Using `elif` for Irregular Filer (after Non-Filer check) prevents double-counting. Additive scoring still needs careful rule ordering.
- "Unknown supplier" is a meaningful risk signal — a CA cannot verify ITC eligibility for a supplier not in their master list.
- The score cap at 100 prevents numeric confusion but hides how many risk factors stacked. Sprint 4 may want to surface individual factor counts separately.

### What Remains Weak
- `risk_note` column in supplier master is loaded but not used — it contains free-text CA notes that could enrich the reason string in future.
- GSTIN format validation (15-char, state code check) is not implemented — a malformed GSTIN would join to nothing and be silently treated as unknown.
- No handling for suppliers whose GSTIN changed mid-year (same legal entity, different GSTIN).

### Next Sprint
**Sprint 4 — Exception Report Generation**
- Take the enriched result DataFrame (reconciliation + risk scores)
- Generate a structured exception report: only rows with status ≠ matched OR risk_level ≠ Low
- Output as Excel (`.xlsx`) using `openpyxl` or `xlsxwriter`
- Format: colored rows by risk level (red = High, amber = Medium, green = Low)
- CA-readable columns: Invoice No, Supplier, Status, Risk Level, Risk Reasons, ITC Amount at Risk
- New module: `src/report_writer.py`
- New tests: `tests/test_report_writer.py`

---

## Sprint 4 — Excel Exception Report

**Date:** 2026-05

### What I Built
- `src/report_writer.py` — six functions:
  - `calculate_itc_at_risk` — rupee amount at risk per row (status + risk level aware)
  - `filter_exception_rows` — excludes only matched+Low rows; returns copy
  - `get_suggested_ca_action` — priority-ordered action string for the CA
  - `prepare_exception_report` — filters, enriches, renames to 12 CA-readable columns
  - `generate_report_filename` — dated filename `exception_report_YYYYMMDD.xlsx`
  - `write_exception_report` — openpyxl-formatted Excel with colours, freeze, autofilter
- `tests/test_report_writer.py` — 37 tests including empty-report edge case
- `requirements.txt` updated with `openpyxl>=3.1.0`
- Sample output: **9 exception rows** from 21 reconciled invoices (High=7, Medium=2 in risk)

### What I Learned
- openpyxl column indexes are 1-based; finding the risk column dynamically from the header row avoids fragile hardcoded positions.
- Writing an empty DataFrame (header-only) to Excel is valid and must not crash — `ws.max_row` will be 1 (header only) so the row-colouring loop simply doesn't execute.
- `pandas.ExcelWriter` as a context manager (`with ... as writer`) is the correct pattern — it saves and closes the workbook on exit, ensuring the file is always flushed.

### What Remains Weak
- ITC at risk for `duplicate_in_purchase` shows the full purchase ITC, not just the incremental duplicate amount. The CA should understand this is the claimable amount for that specific duplicate row.
- No validation that the Excel file is readable after writing (we only check file existence and size).
- Column widths are fixed estimates — long supplier names or reason strings may overflow.

### Next Sprint
**Sprint 5 — CA Review Workflow**
- Let the CA mark rows as "Reviewed" / "Accepted" / "Escalated" in the Excel file
- Re-read a reviewed report and compute final ITC filing position
- Track which exceptions were resolved vs. pending
- Or alternatively: structured text output (JSON/CSV) for integration with CA firm software
