# LLM Failure Modes in Financial Model Analysis

This document catalogs common failure patterns observed when LLMs analyze financial models. Understanding these failure modes is essential for:
- Designing robust evaluation criteria
- Training human reviewers to spot problems
- Improving system guardrails
- Building better prompts and constraints

---

## Table of Contents

1. [Narrative Overfitting](#1-narrative-overfitting)
2. [Regime Anchoring](#2-regime-anchoring)
3. [False Confidence Amplification](#3-false-confidence-amplification)
4. [Explanation-Action Divergence](#4-explanation-action-divergence)
5. [Prompt-Induced Bias](#5-prompt-induced-bias)
6. [Scope Creep](#6-scope-creep)
7. [Hallucinated Causation](#7-hallucinated-causation)
8. [Severity Inflation](#8-severity-inflation)
9. [Pattern Completion Errors](#9-pattern-completion-errors)
10. [Context Window Degradation](#10-context-window-degradation)

---

## 1. Narrative Overfitting

### Symptom
The LLM constructs a coherent narrative that "explains" the model's behavior, but the narrative is more about telling a good story than accurately describing reality.

### Root Cause
LLMs are trained to produce fluent, coherent text. When analyzing complex systems, they may prioritize narrative coherence over factual accuracy, essentially "writing a story" about the model rather than reporting observations.

### Example
**Bad output:**
> "The model tells a clear story of a company transitioning from growth to maturity. The declining capex assumptions reflect management's belief that the core business is fully built out, while the margin expansion captures operating leverage as the company scales."

**Problem:** The model may simply have declining capex because someone copied a template. The LLM invented a business narrative to explain mechanical assumptions.

### Detection Method
- Ask: "Is this narrative verifiable from the model, or is it inferred?"
- Check: Are there alternative explanations that equally fit the data?
- Verify: Does the model actually contain evidence of this "story"?

### Mitigation
- Require explicit evidence for any narrative claims
- Separate "observations" (verifiable) from "interpretations" (inferred)
- Add guardrails against business strategy language
- Prompt: "Only describe what is mechanically present in the model"

---

## 2. Regime Anchoring

### Symptom
The LLM applies evaluation criteria from one regime (e.g., normal market conditions) when another regime applies, or assumes current conditions will persist indefinitely.

### Root Cause
Training data predominantly reflects "normal" conditions. The LLM may not appropriately adjust its analysis for crisis periods, high-growth phases, or structural breaks.

### Example
**Bad output:**
> "The 15% revenue decline assumption in Year 1 appears overly pessimistic. Typical forecast errors are in the 3-5% range, suggesting this is an unrealistic stress case."

**Problem:** The model might be for a pandemic scenario, recession analysis, or a company facing material headwinds. The LLM anchored to "normal" baselines.

### Detection Method
- Check: Does the model have explicit scenario labels the LLM ignored?
- Ask: Are there contextual factors that justify deviation from typical patterns?
- Verify: Did the LLM acknowledge the possibility of non-standard regimes?

### Mitigation
- Include scenario context in the prompt
- Ask the LLM to consider multiple possible regimes
- Flag outputs that assert "typical" or "normal" without acknowledging alternatives
- Add explicit questions: "What regime does this model appear to assume?"

---

## 3. False Confidence Amplification

### Symptom
The LLM expresses high confidence in conclusions that are inherently uncertain, or its confidence increases as it generates more text supporting a position.

### Root Cause
Autoregressive generation: each token conditions on previous tokens. As the LLM builds an argument, it becomes increasingly committed to that argument, even if the initial position was tentative.

### Example
**Bad output (progression within single response):**
> "The working capital assumptions seem aggressive..."
> "The aggressive working capital assumptions clearly indicate..."
> "Given the clearly problematic working capital assumptions, immediate remediation is required."

**Problem:** Tentative observation escalated to definitive conclusion within a single response, without new evidence.

### Detection Method
- Track confidence language through the response
- Check: Did confidence increase without new evidence?
- Flag: Definitive language ("clearly," "obviously," "certainly") for uncertain claims

### Mitigation
- Require confidence levels to be stated and maintained
- Add explicit uncertainty acknowledgment requirements
- Review for escalating language patterns
- Prompt: "Maintain consistent confidence levels throughout your response"

---

## 4. Explanation-Action Divergence

### Symptom
The LLM's explanation doesn't logically support its recommendation, or the recommendation addresses a different issue than what was explained.

### Root Cause
The explanation and recommendation may be generated somewhat independently. The LLM may produce a coherent explanation, then generate a "typical" recommendation without ensuring logical connection.

### Example
**Bad output:**
> **Explanation:** "The model contains a circular reference between cells D15 and F23, creating an iterative calculation loop."
>
> **Recommendation:** "Review the revenue growth assumptions for reasonableness and consider adding sensitivity analysis."

**Problem:** The explanation identifies a circular reference issue, but the recommendation addresses something completely different (revenue assumptions).

### Detection Method
- For each recommendation, ask: "Does this directly address the identified issue?"
- Check: Could the explanation be removed and the recommendation still make sense?
- Verify: Is there a logical chain from finding to fix?

### Mitigation
- Require explicit linkage: "Because [finding], therefore [action]"
- Add validation step: "Does your recommendation address the identified issue?"
- Structure output to enforce explanation→action coupling
- Review recommendations independently of explanations

---

## 5. Prompt-Induced Bias

### Symptom
The LLM's analysis is skewed by framing in the prompt or prior context, finding what it was implicitly told to find.

### Root Cause
LLMs are highly sensitive to priming. If the context suggests problems exist, the LLM may be biased toward finding problems. If previous findings were critical, subsequent findings may be similarly severe.

### Example
**Context bias:**
> Prompt: "Audit this model for errors and issues."
> Result: LLM finds numerous "issues" including stylistic preferences presented as errors.

**Severity anchoring:**
> Previous finding: "CRITICAL: Balance sheet doesn't balance"
> Next finding: "CRITICAL: Cell formatting inconsistent"

**Problem:** The "error-finding" frame biases toward finding errors; previous critical finding biases toward critical severity.

### Detection Method
- Compare outputs from neutral vs. problem-seeking prompts
- Check: Are findings genuinely issues or just observations?
- Verify: Is severity consistent with a neutral baseline?

### Mitigation
- Use neutral framing: "Analyze" rather than "Find problems"
- Reset context between findings to avoid severity anchoring
- Include positive observations to balance the frame
- Calibrate with known-good models to establish baseline

---

## 6. Scope Creep

### Symptom
The LLM ventures beyond its defined role, providing analysis or recommendations outside its mandate (e.g., investment advice from an audit tool).

### Root Cause
LLMs try to be helpful. If they perceive a way to add value, they may do so even when it exceeds their defined scope. Additionally, training data may include examples of broader analysis.

### Example
**Bad output:**
> "Based on this audit, the model suggests the company is undervalued. Management should consider accelerating the acquisition timeline."

**Problem:** An audit tool should not provide valuation opinions or strategic recommendations.

### Detection Method
- Check: Does the output stay within the defined role?
- Flag: Language indicating opinions on value, strategy, or decisions
- Verify: Are recommendations about model structure or business decisions?

### Mitigation
- Explicit role definition in prompts
- Negative examples: "Do NOT provide investment advice"
- Output filtering for forbidden patterns
- Clear scope statements in system prompts

---

## 7. Hallucinated Causation

### Symptom
The LLM asserts causal relationships that aren't supported by the model structure, confusing correlation, mechanical linkage, and economic causation.

### Root Cause
LLMs pattern-match on causal language from training data. They may apply causal language to describe mechanical formula linkages or coincidental patterns.

### Example
**Bad output:**
> "Revenue growth causes margin expansion in this model, demonstrating operating leverage."

**Problem:** The model may simply have both revenue growth and margin expansion as independent assumptions. The LLM invented a causal mechanism.

### Detection Method
- Check: Is there actually a formula linking these concepts?
- Ask: Is this economic causation, mechanical linkage, or coincidence?
- Verify: Could the relationship be reversed or spurious?

### Mitigation
- Require explicit formula references for causal claims
- Distinguish vocabulary: "linked to" vs. "drives" vs. "causes"
- Add validation: "Trace the formula dependency for this claim"
- Train evaluators to spot false causation

---

## 8. Severity Inflation

### Symptom
Issues are consistently rated more severe than warranted, with too many "CRITICAL" or "HIGH" findings for issues that are actually minor.

### Root Cause
- Training data may over-represent severe findings
- "Helpful" bias leads to flagging things as important
- Lack of calibration against actual impact

### Example
**Bad output:**
> "CRITICAL: The model uses hard-coded values for tax rates instead of formula references."

**Problem:** Hard-coded tax rates may be perfectly appropriate and have minimal impact. CRITICAL should be reserved for fundamental structural failures.

### Detection Method
- Check: Does the severity match actual output impact?
- Compare: What percentage of findings are CRITICAL vs. industry baseline?
- Verify: Would an experienced analyst agree with the severity?

### Mitigation
- Provide severity calibration examples
- Require impact quantification for high-severity findings
- Add reviewer override for severity adjustment
- Track severity distribution and flag outlier patterns

---

## 9. Pattern Completion Errors

### Symptom
The LLM completes a pattern it recognizes from training data, even when the actual model diverges from that pattern.

### Root Cause
Strong pattern priors from training. If the LLM has seen many DCF models with a particular structure, it may "see" that structure even when it's not present.

### Example
**Bad output:**
> "The terminal value calculation uses a perpetuity growth method with a 2.5% growth rate."

**Problem:** The model actually uses an exit multiple method with no perpetuity calculation. The LLM completed the "typical DCF" pattern.

### Detection Method
- Verify: Does the described element actually exist?
- Check: Is the LLM describing what's there or what's "usually" there?
- Test: Ask about non-standard elements to see if patterns override reality

### Mitigation
- Require cell references for structural claims
- Add verification prompts: "Confirm the formula at [cell reference]"
- Test with intentionally non-standard models
- Flag language like "typically" or "usually" as pattern-completion risk

---

## 10. Context Window Degradation

### Symptom
Quality degrades for complex models as the LLM approaches context limits, with later analysis being less accurate or more generic than earlier analysis.

### Root Cause
Attention mechanisms become diluted with large contexts. Information from early in the context may be "forgotten" or given less weight.

### Example
**Early in analysis:**
> "Cell A15 contains the formula =SUM(B5:B14)*1.05, which applies a 5% growth factor to the sum of historical values."

**Late in analysis:**
> "The growth assumptions appear reasonable and consistent with the model structure."

**Problem:** Specific, verifiable analysis degrades to vague, generic statements.

### Detection Method
- Compare specificity of early vs. late findings
- Check: Are later findings as well-cited as earlier ones?
- Track: Cell reference density throughout the output

### Mitigation
- Chunk analysis into smaller segments
- Prioritize critical areas for early analysis
- Use structured output to maintain consistency
- Implement rolling summarization for long analyses

---

## Cross-Cutting Patterns

### Compound Failures
Many real failures combine multiple modes:
- **Narrative overfitting + Hallucinated causation**: Inventing a business story with fake causal mechanisms
- **False confidence + Scope creep**: Confident investment advice
- **Pattern completion + Severity inflation**: Seeing "typical" errors that aren't there and rating them high

### Detection Priorities
Based on harm potential, prioritize detection of:
1. **Scope creep** (investment advice) - direct harm risk
2. **Hallucinated data** (invented facts) - reliability risk
3. **Explanation-action divergence** (reasoning failure) - usefulness risk
4. **Severity inflation** (calibration failure) - efficiency risk

### System Improvements
Each failure mode suggests system improvements:
| Failure Mode | System Improvement |
|--------------|-------------------|
| Narrative overfitting | Require evidence tags |
| Regime anchoring | Include scenario context |
| False confidence | Confidence tracking |
| Explanation-action divergence | Structured output |
| Prompt-induced bias | Neutral framing |
| Scope creep | Role constraints |
| Hallucinated causation | Formula verification |
| Severity inflation | Calibration examples |
| Pattern completion | Cell reference requirements |
| Context degradation | Chunked analysis |

---

## Using This Document

### For Evaluators
- Use as a checklist when reviewing LLM outputs
- Reference specific failure modes in feedback
- Track which failure modes occur most frequently

### For System Designers
- Design guardrails targeting each failure mode
- Create test cases that probe for these failures
- Build detection mechanisms into the pipeline

### For Trainers
- Create training examples that avoid these patterns
- Include negative examples showing each failure
- Develop exercises that test for failure mode recognition
