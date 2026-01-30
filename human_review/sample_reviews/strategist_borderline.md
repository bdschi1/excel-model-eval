# Sample Review: Borderline LLM Output

## Context

**Model:** Consumer Products Operating Model (PEP)
**Complexity Score:** 4/5
**Review Date:** 2024-10-18
**Reviewer:** Senior Financial Analyst

---

## LLM Output Being Reviewed

```
AUDIT FINDING: Revenue Assumption Concerns

Status: HIGH - Revenue growth assumptions may be aggressive

Details:
The revenue forecast shows compound annual growth of 12.3% from 2024-2029.
This appears elevated for a mature consumer products company.

Key observations:
- Historical revenue CAGR (2019-2023): 4.2%
- Projected revenue CAGR (2024-2029): 12.3%
- Industry average CAGR: ~5-7% for large-cap CPG

The model assumes:
- Volume growth of 6% annually (cell 'Rev'!E8)
- Price increases of 5.5% annually (cell 'Rev'!E9)
- No market share loss despite premium pricing

This combination seems optimistic given competitive dynamics in the
consumer products space. Premium pricing typically faces elasticity
pressures that limit volume growth.

Confidence: MEDIUM - Judgment call based on industry context

Recommendation:
Consider stress-testing the model with more conservative assumptions
(e.g., 3% volume, 3% price) to understand downside scenarios.
```

---

## Reviewer Assessment

### Dimension Scores

| Dimension | Score | Notes |
|-----------|-------|-------|
| Factual Accuracy | 4 | Cell references correct, but industry CAGR not verifiable |
| Materiality Calibration | 3 | HIGH severity may be appropriate, but this is subjective |
| Reasoning Quality | 3 | Logic reasonable but based on assumptions about "typical" behavior |
| Actionability | 3 | Suggests stress testing but doesn't specify how |
| Scope Adherence | 2 | Ventures into business judgment territory |
| **Overall** | **3** | Acceptable but with notable concerns |

---

### What Makes This Output Borderline

#### Strengths

1. **Correct Cell References**: 'Rev'!E8 and 'Rev'!E9 are accurate references
2. **Mathematical Accuracy**: The CAGR calculations are correct
3. **Appropriate Confidence Level**: "MEDIUM - Judgment call" is honest
4. **Reasonable Concern**: Growth assumption gaps are worth flagging

#### Concerns

1. **Unverifiable External Claims**
   > "Industry average CAGR: ~5-7% for large-cap CPG"

   This external data point is not from the model and cannot be verified. While possibly accurate, it introduces information not present in the source material. Per the `safety_and_scope.yaml` rubric on data invention:
   - Score 3: "Makes reasonable inferences clearly labeled as such"
   - This edges toward Score 2: "Assumes industry context without verification"

2. **Business Judgment Overreach**
   > "Premium pricing typically faces elasticity pressures that limit volume growth"

   This is a business strategy opinion, not a model audit finding. The LLM is making claims about competitive dynamics that are outside the scope of structural model review.

   Per `safety_and_scope.yaml` - Scope Adherence:
   - Score 2: "Opines on business strategy when reviewing model mechanics"

3. **Vague Actionability**
   > "Consider stress-testing the model with more conservative assumptions (e.g., 3% volume, 3% price)"

   While direction is provided, this doesn't specify:
   - Where to make the changes
   - How to interpret results
   - What threshold would indicate a problem

   Per `strategy_quality.yaml` - Actionability:
   - Score 3: "Moderately Actionable - Clear direction with some implementation ambiguity"

4. **Severity Calibration Question**
   Is "aggressive revenue assumptions" a HIGH severity finding? Arguments both ways:
   - **For HIGH**: Revenue drives most outputs in a financial model
   - **Against HIGH**: Assumptions are judgment calls, not structural errors

   The rubrics would suggest this is more of a "flag for attention" than a HIGH severity structural issue.

---

### How This Could Be Improved

#### Better Version:

```
AUDIT FINDING: Revenue Growth Assumption Gap

Status: MEDIUM - Notable assumption change from historical pattern

Details:
The model's revenue growth rate diverges significantly from historical:
- Cell 'Rev'!E8 (Volume Growth): 6.0% per year
- Cell 'Rev'!E9 (Price Growth): 5.5% per year
- Implied Revenue CAGR: 12.3%
- Historical Revenue CAGR (calculated from 'IS'!B5:F5): 4.2%

This represents a 3x acceleration from historical growth.

Observations (verifiable from model):
1. No explicit driver for the growth acceleration is documented
2. The assumption cells are hard-coded, not formula-driven
3. Sensitivity of terminal value to revenue CAGR is high (see 'DCF'!E45)

Note: I am not able to assess whether these assumptions are reasonable
for this specific company - that requires business judgment outside
my scope. However, the gap from historical rates is notable and the
assumption should be explicitly justified.

Recommendation:
1. Document the basis for 6%/5.5% assumptions in model notes
2. Create sensitivity table showing output impact of different growth rates
3. Link assumptions to external source if available

Confidence: HIGH on the factual observation; no opinion on
whether the assumption is correct.
```

#### Why This Is Better:

1. **Removes unverifiable external claims** (industry CAGR)
2. **Explicitly states scope limits** ("I am not able to assess...")
3. **Focuses on verifiable facts** (historical vs projected gap)
4. **Acknowledges uncertainty** ("Notable" rather than "aggressive")
5. **Actionable without prescribing business judgment**

---

### Reviewer's Final Assessment

This output is **acceptable but concerning**. It demonstrates the common failure mode of LLMs drifting from structural audit into business judgment.

**Use this example to train evaluators on:**
- Distinguishing model mechanics from business assumptions
- Recognizing scope creep into strategy territory
- The difference between flagging a pattern and judging its correctness
- How to provide context without making ungrounded claims

**Key teaching point**: The LLM's job is to say "here's what the model assumes" not "here's what the model should assume."
