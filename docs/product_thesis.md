# Product Thesis: GST Risk Review

## What We Are Building

GST Risk Review is a pre-filing risk review system for CA firms in India.

The system helps a Chartered Accountant verify, before filing a client's GST return, that:

1. Every invoice in the client's purchase register is also reflected in GSTR-2B (the auto-populated ITC statement from the GST portal).
2. The tax amounts match between the purchase register and GSTR-2B.
3. Every supplier the client is claiming ITC from is active, GST-compliant, and filing returns.

If any of these checks fail, the CA firm gets a flagged exception report they can review and act on before filing — not after receiving a GST notice.

---

## The Problem It Solves

Under GST rules (specifically Rule 36(4) and the GSTR-2B matching framework), a buyer can claim Input Tax Credit (ITC) only if:
- The supplier has filed their returns (GSTR-1)
- The invoice appears in GSTR-2B
- The amounts match

If a CA firm files a return with mismatched or unmatched ITC, the client may receive a demand notice, penalty, or interest from the GST department.

Today, many small CA firms do this reconciliation manually in Excel — which is slow, error-prone, and often happens under deadline pressure.

---

## How It Grows

**Sprint 1 (now):** Load CSVs, validate column structure.

**Sprint 2:** Clean data, match invoices, flag mismatches.

**Sprint 3:** Score supplier risk (inactive GSTIN, non-filer, irregular filer).

**Sprint 4:** Generate a CA-reviewed exception report (PDF or Excel).

**Sprint 5+:** AI-assisted explanations of mismatches. Human-in-the-loop review. Evaluation tracking.

---

## Design Principles

- **Deterministic first.** No AI until the core reconciliation logic is solid and tested.
- **CA-centric.** The output is designed for a practitioner reviewing it, not an algorithm acting on it.
- **Failure-aware.** Every sprint tracks what broke, what was learned, and what needs fixing.
- **Simple inputs.** CSV files from the client. No portal integration in early sprints.
