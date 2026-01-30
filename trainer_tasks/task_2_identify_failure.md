# Task 2: Identify Failure Modes

## Objective

Analyze the following LLM outputs to identify specific failure modes from `docs/failure_modes.md`. This task tests your ability to diagnose why LLM outputs fail and categorize the type of failure.

---

## Instructions

1. Read each LLM output carefully
2. Identify **all** failure modes present (there may be multiple)
3. Provide the specific text that demonstrates each failure
4. Explain why this qualifies as that failure mode
5. Suggest how the output could be corrected

**Time allocation:** 25-35 minutes total

---

## Output 1

### Context
Model: Subscription SaaS company financial model
Task: Audit model structure and flag issues

### LLM Output
```
COMPREHENSIVE ANALYSIS: SaaS Business Health

The model reveals a compelling growth story. Revenue acceleration
from 35% to 45% YoY suggests the company is hitting product-market
fit and entering a viral growth phase. The declining churn rate
(from 8% to 5% monthly) indicates strong customer satisfaction
and sticky product features.

The unit economics are particularly impressive:
- LTV:CAC ratio improving from 2.5x to 4.2x
- Payback period shrinking from 18 months to 11 months
- Gross margin expansion from 72% to 78%

These metrics suggest the company is transitioning from growth-stage
to scale-stage, which typically commands premium multiples in M&A
scenarios. I estimate the company would trade at 12-15x ARR in the
current market.

AUDIT FINDINGS:
1. Cell 'MRR'!E23 calculates net revenue retention incorrectly
2. The cohort analysis in 'Cohorts' tab has incomplete data
3. Some CAC calculations reference deleted cells (#REF! errors)

Recommendation: Fix the technical issues, but the fundamental
business trajectory is strong.
```

### Your Analysis

**Failure Modes Identified:**

| Failure Mode | Supporting Evidence | Why This Qualifies |
|--------------|--------------------|--------------------|
| | | |
| | | |
| | | |

**How to Correct:**
[Your suggestions]

---

## Output 2

### Context
Model: Manufacturing company operating model
Task: Review working capital assumptions

### LLM Output
```
FINDING: Working Capital Analysis

The working capital assumptions appear conservative based on
industry standards:

Current Model Assumptions:
- Days Sales Outstanding: 45 days (cell 'WC'!D8)
- Days Inventory Outstanding: 60 days (cell 'WC'!D9)
- Days Payable Outstanding: 35 days (cell 'WC'!D10)
- Cash Conversion Cycle: 70 days

Industry Benchmarks (Manufacturing):
- DSO: 40-50 days
- DIO: 55-70 days
- DPO: 40-50 days
- CCC: 50-70 days

The model's assumptions are within normal ranges. However, I notice
that working capital as a percentage of revenue is declining from
25% to 18% over the forecast period. This is definitely achievable -
companies like Toyota and Apple have achieved working capital
efficiency of 10-15% of revenue through supply chain optimization.

Given the improving efficiency trajectory and strong comparable
companies, the working capital assumptions are validated.

Confidence: HIGH
```

### Your Analysis

**Failure Modes Identified:**

| Failure Mode | Supporting Evidence | Why This Qualifies |
|--------------|--------------------|--------------------|
| | | |
| | | |
| | | |

**How to Correct:**
[Your suggestions]

---

## Output 3

### Context
Model: Infrastructure project finance model
Task: Verify debt service coverage calculations

### LLM Output
```
FINDING: DSCR Calculation Review

Status: MEDIUM - Potential calculation issue

Initial Assessment:
The debt service coverage ratio calculation in cell 'Debt'!F15
seems low at 1.15x. This is concerning because...

Actually, let me reconsider. A 1.15x DSCR is actually quite
reasonable for infrastructure projects with long-term contracted
revenues. The project has a 25-year power purchase agreement with
an investment-grade offtaker, which provides significant cash
flow visibility.

On further reflection, the DSCR is clearly adequate given the
contracted nature of revenues. In fact, 1.15x may even be conservative
since comparable infrastructure projects with similar contract
structures typically achieve financing at 1.10x or lower.

REVISED STATUS: LOW - DSCR calculation verified as appropriate

The formula at 'Debt'!F15 is =E12/E14 where:
- E12 = Cash Flow Available for Debt Service
- E14 = Total Debt Service

Both inputs trace correctly through the model. The calculation
is definitely correct and the ratio is definitely appropriate.

Confidence: HIGH
```

### Your Analysis

**Failure Modes Identified:**

| Failure Mode | Supporting Evidence | Why This Qualifies |
|--------------|--------------------|--------------------|
| | | |
| | | |
| | | |

**How to Correct:**
[Your suggestions]

---

## Output 4

### Context
Model: Pharmaceutical company pipeline valuation
Task: Check probability assumptions

### LLM Output
```
FINDING: Clinical Probability Assumptions

The model uses the following success probabilities:

Phase 1 to Phase 2: 65% (cell 'Pipeline'!D5)
Phase 2 to Phase 3: 35% (cell 'Pipeline'!D6)
Phase 3 to Approval: 60% (cell 'Pipeline'!D7)
Overall LoS: 13.65% (calculated)

These assumptions align with published industry data from
BioMedTracker and clinical development success rate studies.
The overall 13.65% probability is consistent with the historical
average for novel oncology therapeutics.

Technical Note: The formulas correctly multiply sequential
probabilities: =D5*D6*D7 in cell D8.

No issues identified with the probability framework.
```

### Your Analysis

**Failure Modes Identified:**

| Failure Mode | Supporting Evidence | Why This Qualifies |
|--------------|--------------------|--------------------|
| | | |
| | | |
| | | |

**How to Correct:**
[Your suggestions]

---

## Synthesis Questions

After completing your analysis, consider:

1. **Which failure mode appeared most frequently across outputs?**

2. **Which output had the most severe combination of failures?**

3. **Were there any outputs with no failure modes?**

4. **What common root cause might explain multiple failures?**

5. **How could system prompts be modified to prevent these failures?**

---

## Expected Analysis

*(Do not read until you've completed your analysis)*

<details>
<summary>Click to reveal expected analysis</summary>

### Output 1 - Multiple Failures
- **Narrative Overfitting**: "compelling growth story," "viral growth phase" - storytelling over analysis
- **Scope Creep**: "I estimate the company would trade at 12-15x ARR" - valuation opinion
- **Severity Calibration**: Technical issues (#REF! errors) buried under business commentary
- **False Confidence**: Strong assertions about business trajectory from limited data

### Output 2 - External Data Fabrication
- **Data Invention**: "Industry Benchmarks" with specific numbers not from model
- **Hallucinated Causation**: Companies "achieved efficiency through supply chain optimization"
- **Pattern Completion**: Assumes improvement trajectory will continue like exemplar companies
- **Scope Creep**: "validated" - making judgment calls outside audit scope

### Output 3 - Confidence Amplification
- **False Confidence Amplification**: Watch the progression: "concerning" → "actually quite reasonable" → "clearly adequate" → "definitely correct"
- **Data Invention**: "comparable infrastructure projects typically achieve financing at 1.10x" - external data
- **Regime Anchoring**: Assumes contracted revenue visibility justifies conclusions

### Output 4 - Best of the Set, But...
- **Minor Data Invention**: References "BioMedTracker and clinical development success rate studies" without verification
- **Pattern Completion**: Assumes alignment with "published industry data" without confirmation
- Otherwise relatively well-bounded

### Key Insight
Most failures involve crossing from model analysis into business judgment and introducing external "knowledge" that cannot be verified from the source material.

</details>
