# Research Gap: Where Existing GST Automation Falls Short

## What Already Exists

GST automation is a large and growing space in India. Existing tools cover:

| Category | Examples |
|---|---|
| Return filing automation | ClearTax, Zoho Books, TallyPrime |
| E-invoicing (IRN generation) | NIC portal, Tally, SAP |
| ITC reconciliation (enterprise) | GSTN offline tool, ERP integrations |
| Fraud detection (government) | GSTN analytics, risk-based GST audits |
| Invoice matching (large firms) | SAP, Oracle, large CA firm software |
| AI for GST notices | Legal-tech startups, limited scope |

These tools are well-built for their intended users: large enterprises, government systems, and technology-heavy CA firms.

---

## What Is Missing

The gap is at the **small CA firm level**, which is where most Indian tax practitioners work.

Specifically, what does not exist (or is not accessible to small firms):

### 1. Pre-filing ITC risk detection
Most tools reconcile after the fact — after a notice arrives. There is no lightweight, practitioner-facing tool that runs a risk check *before* the return is filed.

### 2. Supplier risk scoring for practitioners
Knowing that a supplier is inactive or a non-filer is critical for ITC eligibility. No small-firm tool surfaces this as a pre-filing risk signal.

### 3. CA-reviewed exception reports
Existing reconciliation outputs are raw data dumps. A CA needs a prioritized, readable exception report they can sign off on — not a 5000-row Excel file.

### 4. Human-in-the-loop validation
The practitioner's judgment matters. Automated tools give outputs; they do not create a review workflow where a CA can override, annotate, or approve findings before filing.

### 5. Evaluation and failure tracking
No existing small-firm tool tracks how often its reconciliation is wrong, what edge cases fail, or how accuracy improves over time.

---

## Our Approach

1. **Start deterministic.** Build a rule-based reconciliation engine first. No AI.
2. **Validate against real failure cases.** Document what breaks and why.
3. **Add AI only after the core works.** Use LLMs for explanations and summaries, not for core matching logic.
4. **Keep it practitioner-friendly.** Outputs should be readable by a CA, not just a data engineer.

The research gap is not in the technology — it is in the workflow, the audience, and the design.
