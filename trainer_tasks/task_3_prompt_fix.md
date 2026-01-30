# Task 3: Propose Prompt Improvements

## Objective

Given examples of problematic LLM outputs, design prompt modifications that would prevent or mitigate the identified failure modes. This task tests your ability to translate failure analysis into actionable prompt engineering.

---

## Instructions

1. Review the problematic output
2. Identify the root cause of the failure
3. Propose specific prompt additions or modifications
4. Explain why your changes would help
5. Consider potential unintended consequences

**Time allocation:** 30-40 minutes total

---

## Scenario 1: Scope Creep into Investment Advice

### Problematic Output
```
AUDIT FINDING: Valuation Assessment

Based on my analysis, this acquisition target is overvalued at the
proposed $45/share. Given the company's declining market share and
competitive pressures, I recommend the buyer reduce their bid to
$35-38/share or walk away from the transaction.

The IRR of 12% is below typical hurdle rates for strategic acquirers.
Management should reconsider this investment.
```

### Current Prompt (Simplified)
```
You are a financial model auditor. Analyze the uploaded Excel model
and identify any issues with its structure, formulas, or assumptions.
Provide recommendations for improvement.
```

### Your Task

**Root Cause Analysis:**
Why does the current prompt allow this failure?

[Your answer]

**Proposed Prompt Modification:**
Write the improved prompt section that would prevent this failure.

[Your answer]

**Explanation:**
Why would these changes help?

[Your answer]

**Potential Unintended Consequences:**
Could your changes cause other problems?

[Your answer]

---

## Scenario 2: Hallucinated External Data

### Problematic Output
```
FINDING: Revenue Growth Assessment

The model assumes 15% revenue growth, which compares to:
- Industry average: 8-10%
- Top quartile performers: 12-14%
- Historical company growth: 11%

The assumption appears aggressive relative to these benchmarks.
```

### Current Prompt (Simplified)
```
You are a financial model auditor. Review the model and assess
whether the assumptions are reasonable. Use your knowledge of
industry standards to provide context.
```

### Your Task

**Root Cause Analysis:**
Why does the current prompt allow this failure?

[Your answer]

**Proposed Prompt Modification:**
Write the improved prompt section that would prevent this failure.

[Your answer]

**Explanation:**
Why would these changes help?

[Your answer]

**Potential Unintended Consequences:**
Could your changes cause other problems?

[Your answer]

---

## Scenario 3: Confidence Without Evidence

### Problematic Output
```
FINDING: Working Capital Analysis

The working capital assumptions are clearly incorrect. The company
will definitely face a cash crunch in Year 3 if these assumptions
are not revised. This is a critical error that must be fixed
immediately.

Confidence: HIGH
```

### Current Prompt (Simplified)
```
You are a financial model auditor. Identify issues and rate their
severity. Express your confidence in your findings.
```

### Your Task

**Root Cause Analysis:**
Why does the current prompt allow this failure?

[Your answer]

**Proposed Prompt Modification:**
Write the improved prompt section that would prevent this failure.

[Your answer]

**Explanation:**
Why would these changes help?

[Your answer]

**Potential Unintended Consequences:**
Could your changes cause other problems?

[Your answer]

---

## Scenario 4: Explanation-Action Mismatch

### Problematic Output
```
FINDING: Circular Reference Detection

The model contains a circular reference between cells 'IS'!D15 and
'BS'!E23. This creates an iterative calculation that Excel resolves
through successive approximation. The circular reference occurs
because the interest expense depends on average debt balance, which
depends on cash flow, which depends on net income, which includes
interest expense.

RECOMMENDATION:
Consider adding sensitivity analysis on the revenue growth assumptions
to understand the impact on valuation. Also review the depreciation
methodology for consistency with GAAP.
```

### Current Prompt (Simplified)
```
You are a financial model auditor. For each issue you find,
explain what you observed and provide a recommendation.
```

### Your Task

**Root Cause Analysis:**
Why does the current prompt allow this failure?

[Your answer]

**Proposed Prompt Modification:**
Write the improved prompt section that would prevent this failure.

[Your answer]

**Explanation:**
Why would these changes help?

[Your answer]

**Potential Unintended Consequences:**
Could your changes cause other problems?

[Your answer]

---

## Synthesis: Design a Complete Prompt

Based on your analysis of all four scenarios, design a comprehensive prompt that addresses all identified failure modes.

### Your Complete Prompt Design

```
[Write your complete prompt here]
```

### Prompt Design Rationale

| Failure Mode | Prompt Element That Addresses It |
|--------------|----------------------------------|
| Scope creep | |
| Data hallucination | |
| Overconfidence | |
| Explanation-action mismatch | |

### Trade-offs in Your Design

What trade-offs did you make in your prompt design?

[Your answer]

---

## Expected Approaches

*(Do not read until you've completed your prompt designs)*

<details>
<summary>Click to reveal expected approaches</summary>

### Scenario 1: Scope Creep

**Root Cause:** Prompt says "provide recommendations" without defining boundaries.

**Effective additions:**
- "Your role is LIMITED to structural model review. Do NOT provide:"
- Explicit forbidden list: valuation opinions, buy/sell recommendations, price guidance
- "If asked about value or investment merit, respond: 'That assessment is outside my audit scope.'"

### Scenario 2: Data Hallucination

**Root Cause:** Prompt invites external knowledge with "use your knowledge of industry standards."

**Effective additions:**
- "Only reference data that is explicitly present in the model."
- "Do NOT cite external benchmarks, industry averages, or comparable companies unless they are documented in the model."
- "If external context would be helpful, note: 'External benchmarking data is not available in this model.'"

### Scenario 3: Overconfidence

**Root Cause:** Prompt allows confidence claims without evidence requirements.

**Effective additions:**
- "Confidence levels must be justified by specific evidence:"
- "HIGH confidence: Formula verified, cell reference confirmed, calculation traced"
- "MEDIUM confidence: Pattern observed but not all links verified"
- "LOW confidence: Inference based on limited data"
- "Avoid words like 'definitely', 'clearly', 'obviously' unless formula verification supports them."

### Scenario 4: Explanation-Action Mismatch

**Root Cause:** No requirement to link recommendation to finding.

**Effective additions:**
- "Each recommendation MUST directly address the specific issue identified."
- "Format: 'Because [specific finding], recommend [specific action to address that finding].'"
- "Do NOT include recommendations unrelated to the identified issue."

### Complete Prompt Key Elements

1. **Role definition with explicit boundaries**
2. **Forbidden actions list**
3. **Evidence requirements for claims**
4. **Structured output format enforcing finding→recommendation linkage**
5. **Confidence calibration criteria**
6. **Data sourcing constraints**

</details>
