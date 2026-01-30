# Human Reviewer Guidelines

## Purpose

This document provides guidance for human reviewers evaluating LLM-generated audit outputs from the Excel Model Evaluation system. Your role is to assess whether the LLM's analysis is accurate, actionable, and appropriately calibrated.

---

## Review Process Overview

### Step 1: Establish Context
- Review the original Excel model being audited
- Understand the model's purpose (DCF, LBO, operating model, etc.)
- Note the complexity score assigned by the system

### Step 2: Evaluate Each Finding
For each LLM-generated finding, assess:
1. **Accuracy**: Is the finding factually correct?
2. **Materiality**: Does the severity match the actual impact?
3. **Actionability**: Can an analyst act on this guidance?
4. **Completeness**: Are important details missing?

### Step 3: Score and Document
- Apply rubric scores from `eval/llm_rubrics/`
- Document specific examples supporting your scores
- Note any patterns across findings

### Step 4: Provide Final Assessment
- Overall quality rating (1-5)
- Summary of strengths and weaknesses
- Recommendations for system improvement

---

## Evaluation Dimensions

### 1. Factual Accuracy

**What to check:**
- Cell references exist and contain stated values/formulas
- Formula descriptions accurately reflect actual formulas
- Error classifications are correct (e.g., #REF! vs #VALUE!)
- Dependency chains are accurately traced

**Red flags:**
- References to non-existent cells or sheets
- Mischaracterized formula logic
- Invented data or assumptions
- Incorrect error type identification

**Scoring:**
| Score | Criteria |
|-------|----------|
| 5 | All factual claims verifiable, no errors |
| 4 | Minor inaccuracies that don't affect conclusions |
| 3 | Some errors but main findings are accurate |
| 2 | Significant errors affecting reliability |
| 1 | Fundamental factual errors, untrustworthy |

### 2. Materiality Calibration

**What to check:**
- Severity ratings match actual impact on model outputs
- Critical findings genuinely affect key outputs
- Low-severity findings aren't over-escalated
- Priority ordering reflects true risk

**Red flags:**
- All findings marked as "Critical"
- Material issues dismissed as minor
- No consideration of downstream effects
- Missing context about model use case

**Scoring:**
| Score | Criteria |
|-------|----------|
| 5 | Severity perfectly calibrated to impact |
| 4 | Generally appropriate with minor miscalibrations |
| 3 | Reasonable but inconsistent calibration |
| 2 | Frequent over/under-estimation of severity |
| 1 | Severity ratings essentially random |

### 3. Reasoning Quality

**What to check:**
- Logical chain from observation to conclusion
- Appropriate confidence expression
- Valid causal claims
- Acknowledgment of uncertainty

**Red flags:**
- Conclusions unsupported by evidence
- Overconfident statements about uncertain issues
- Spurious causal claims
- Missing hedging language where needed

**Scoring:**
| Score | Criteria |
|-------|----------|
| 5 | Rigorous, traceable reasoning throughout |
| 4 | Clear logic with minor gaps |
| 3 | Generally sound but some leaps |
| 2 | Weak logical connections |
| 1 | Conclusions disconnected from evidence |

### 4. Actionability

**What to check:**
- Specific enough for an analyst to act on
- Clear next steps or remediation path
- Appropriate level of detail
- Prioritization guidance

**Red flags:**
- Vague recommendations ("review this area")
- Missing cell references for issues
- No suggested remediation approach
- Unclear priority ordering

**Scoring:**
| Score | Criteria |
|-------|----------|
| 5 | Immediately actionable with clear steps |
| 4 | Actionable with minor clarification needed |
| 3 | Direction clear but implementation ambiguous |
| 2 | Vague guidance requiring significant interpretation |
| 1 | No actionable guidance provided |

### 5. Scope Adherence

**What to check:**
- Stays within audit/review mandate
- Doesn't make investment recommendations
- Doesn't invent external data
- Appropriate boundary awareness

**Red flags:**
- Investment advice or trading signals
- Business strategy recommendations
- Made-up market data or benchmarks
- Overreach into valuation conclusions

**Scoring:**
| Score | Criteria |
|-------|----------|
| 5 | Perfect scope discipline throughout |
| 4 | Stays in scope with explicit acknowledgment |
| 3 | Occasional minor scope creep |
| 2 | Regular boundary violations |
| 1 | Severe scope creep affecting reliability |

---

## Common Patterns to Watch For

### Positive Patterns (Increase Score)
- Explicit uncertainty acknowledgment ("This may indicate...", "Consider whether...")
- Specific cell references with formula content
- Proportional severity to impact
- Clear remediation paths
- Appropriate escalation recommendations

### Negative Patterns (Decrease Score)
- Confident claims without evidence
- Generic findings applicable to any model
- All issues treated with equal severity
- Missing context about why something matters
- Recommendations without verification steps

### Hallucination Indicators (Major Concern)
- Cell references that don't exist
- Formula descriptions that don't match reality
- References to sheets not in the workbook
- Made-up values or calculations
- Fictional external data

---

## Disagreement Resolution

When reviewers disagree on scores:

1. **Document the disagreement**: Note specific points of contention
2. **Reference the rubric**: Cite relevant scale descriptions
3. **Provide examples**: Point to specific output elements
4. **Seek third opinion**: For 2+ point disagreements on any dimension
5. **Document resolution**: Record final decision and rationale

---

## Review Documentation Template

```markdown
## Review Summary

**Model Reviewed:** [Model name/ID]
**Review Date:** [Date]
**Reviewer:** [Name]

### Overall Scores
- Factual Accuracy: [1-5]
- Materiality Calibration: [1-5]
- Reasoning Quality: [1-5]
- Actionability: [1-5]
- Scope Adherence: [1-5]
- **Overall:** [1-5]

### Key Strengths
- [Strength 1]
- [Strength 2]

### Key Weaknesses
- [Weakness 1]
- [Weakness 2]

### Notable Examples

**Strong Output Example:**
> [Quote from LLM output]

Why this is strong: [Explanation]

**Weak Output Example:**
> [Quote from LLM output]

Why this is weak: [Explanation]

### Recommendations
- [Recommendation 1]
- [Recommendation 2]
```

---

## Calibration Exercises

To maintain consistent scoring across reviewers:

1. **Weekly calibration sessions**: Review same output independently, compare scores
2. **Edge case discussions**: Monthly review of borderline cases
3. **Score distribution monitoring**: Track for drift over time
4. **Cross-reviewer correlation**: Aim for r > 0.8 on dimension scores

---

## Escalation Criteria

Immediately escalate if:
- Hallucination detected (fabricated facts)
- Recommendations could cause material harm
- Severe scope violations (investment advice)
- Pattern of critical failures across reviews
- Evidence of systematic bias

Escalation path:
1. Document specific concern
2. Notify team lead
3. Quarantine affected outputs
4. Root cause analysis
5. System adjustment if needed
