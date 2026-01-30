# Sample Review: High-Quality LLM Output

## Context

**Model:** Biotech DCF Model (ARVN)
**Complexity Score:** 3/5
**Review Date:** 2024-10-15
**Reviewer:** Senior Financial Analyst

---

## LLM Output Being Reviewed

```
AUDIT FINDING: Balance Sheet Integrity Check

Status: CRITICAL - Balance sheet does not balance in multiple periods

Details:
The balance sheet shows a persistent imbalance across forecast periods
2025-2029. Specifically:

  Cell Reference: 'BS'!D45 (Total Assets)
  Cell Reference: 'BS'!D67 (Total Liabilities + Equity)

  Difference by period:
  - 2025: $2.3M discrepancy
  - 2026: $4.1M discrepancy
  - 2027: $6.8M discrepancy
  - 2028: $10.2M discrepancy
  - 2029: $14.7M discrepancy

Root Cause Analysis:
Tracing the dependency graph, the imbalance originates from:
1. 'CF'!D23 (Cash flow from operations) feeds into 'BS'!D12 (Cash)
2. 'CF'!D23 contains formula: =D15+D18-D21
3. 'CF'!D21 (Working capital change) references 'WC'!D15
4. 'WC'!D15 appears to be a hard-coded value ($1,247,000) rather than
   a formula linked to the balance sheet working capital accounts

This creates a disconnect: the income statement drives cash flow, but
the working capital adjustment is static, causing the cash balance to
diverge from the expected balance sheet relationship.

Confidence: HIGH - Formula dependencies verified through graph traversal

Recommended Remediation:
1. Replace hard-coded value in 'WC'!D15 with formula linking to
   balance sheet current assets and liabilities
2. Verify working capital formula: =CurrentAssets - CurrentLiabilities
3. Re-check balance sheet integrity after fix
4. Consider adding a balance check cell that flags non-zero differences

Priority: Address immediately - affects model reliability for any
valuation or scenario analysis
```

---

## Reviewer Assessment

### Dimension Scores

| Dimension | Score | Notes |
|-----------|-------|-------|
| Factual Accuracy | 5 | All cell references verified, formulas accurately described |
| Materiality Calibration | 5 | Critical rating appropriate - balance sheet integrity is fundamental |
| Reasoning Quality | 5 | Clear causal chain from symptom to root cause |
| Actionability | 5 | Specific cells, formulas, and verification steps provided |
| Scope Adherence | 5 | Stays within audit scope, no valuation opinions |
| **Overall** | **5** | Exemplary output |

---

### What Makes This Output Strong

#### 1. Specific Evidence
The output provides exact cell references ('BS'!D45, 'CF'!D23, 'WC'!D15) and quantifies the discrepancy by period. A reviewer can immediately verify these claims.

#### 2. Root Cause Tracing
Rather than just flagging the symptom (balance sheet doesn't balance), the output traces the dependency chain to identify the actual source of the problem (hard-coded working capital value).

#### 3. Appropriate Confidence Expression
States "Confidence: HIGH - Formula dependencies verified through graph traversal" - appropriately confident given the verification method, and explains why confidence is high.

#### 4. Proportional Severity
Critical rating is justified: balance sheet integrity is fundamental to any financial model's reliability. The escalating discrepancy pattern (growing each year) correctly indicates a structural issue rather than a one-time error.

#### 5. Actionable Remediation
Provides a numbered remediation plan:
1. What to change
2. What formula to use
3. How to verify the fix
4. Suggestion for ongoing monitoring

#### 6. Scope Discipline
Stays within the audit mandate. Doesn't speculate about what the correct valuation would be or whether the company is over/undervalued. Simply identifies the issue and how to fix it.

---

### Minor Suggestions for Improvement

Even excellent output can be refined:

1. **Could include the exact current formula in WC'!D15** rather than just describing it as "hard-coded value" - this would make verification even faster.

2. **Could note whether this is a manual input that should be linked, or whether it was previously a formula that was accidentally overwritten** - this provides context for understanding how the error occurred.

3. **Could quantify the impact on key outputs** (e.g., "This affects the terminal year cash balance, which is an input to the DCF terminal value calculation") - though this edges toward scope creep if taken too far.

---

### Comparison to Rubric Criteria

**From `strategy_quality.yaml` - Economic Plausibility (Score 5):**
> "Correctly models second-order effects and feedback loops"

The output correctly identifies the feedback loop between income statement, cash flow, and balance sheet, and pinpoints where the loop is broken.

**From `reasoning_fidelity.yaml` - Signal-Action Consistency (Score 5):**
> "Each recommendation traces to specific finding"

Every remediation step directly addresses an identified issue in the dependency chain.

**From `safety_and_scope.yaml` - Scope Adherence (Score 5):**
> "States scope at outset and references throughout"

Stays clearly within the audit mandate without overreaching into valuation conclusions.

---

### Key Takeaway

This output demonstrates what good LLM-guided analysis looks like:
- **Grounded**: Every claim is verifiable
- **Traced**: Root cause identified through systematic analysis
- **Calibrated**: Severity appropriate to impact
- **Actionable**: Clear path to remediation
- **Bounded**: Appropriate scope discipline

Use this as a reference point for what "5" looks like on the evaluation rubrics.
