# Cross-Domain Transferability

This document maps the architectural patterns from the Excel Model Auditor to other domains. The core pattern — **Strategist → Planner → Executor** — applies wherever LLM guidance must be translated into safe, auditable actions.

---

## The Core Pattern

### Financial Model Auditor Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  STRATEGIST │ --> │   PLANNER   │ --> │  EXECUTOR   │
│             │     │             │     │             │
│ Analyzes    │     │ Prioritizes │     │ Generates   │
│ structure   │     │ findings    │     │ reports     │
│ Identifies  │     │ Sequences   │     │ Applies     │
│ patterns    │     │ actions     │     │ changes     │
└─────────────┘     └─────────────┘     └─────────────┘
     LLM               Hybrid            Deterministic
   Judgment           Logic               Code
```

### Key Properties
1. **LLM handles reasoning**, not execution
2. **Structured interfaces** between layers
3. **Human oversight** at layer boundaries
4. **Auditable outputs** at each stage

---

## Domain Mappings

### 1. Compliance Workflows

**Use Case:** Regulatory document analysis, policy compliance checking

| Financial Audit | Compliance Audit |
|-----------------|------------------|
| Excel model | Regulatory filings, contracts |
| Cell formulas | Policy clauses, requirements |
| Dependency graph | Obligation relationships |
| Audit findings | Compliance gaps |
| Severity levels | Risk ratings |
| Remediation plan | Corrective action plan |

**Strategist Layer:**
- Analyzes documents for regulatory requirements
- Identifies gaps between policy and practice
- Flags ambiguous interpretations

**Planner Layer:**
- Prioritizes compliance gaps by risk
- Sequences remediation activities
- Identifies dependencies between actions

**Executor Layer:**
- Generates compliance reports
- Creates audit trails
- Updates tracking systems

**Failure Modes to Monitor:**
- **Scope creep:** Legal advice instead of compliance observations
- **Hallucination:** Citing non-existent regulations
- **Overconfidence:** Definitive compliance statements (only courts/regulators decide)

---

### 2. Medical Triage / Clinical Decision Support

**Use Case:** Patient assessment, diagnostic support, treatment planning

| Financial Audit | Clinical Decision Support |
|-----------------|---------------------------|
| Excel model | Patient data, test results |
| Cell formulas | Clinical indicators, vitals |
| Dependency graph | Symptom-condition relationships |
| Audit findings | Clinical alerts |
| Severity levels | Acuity scores |
| Remediation plan | Care pathway |

**Strategist Layer:**
- Analyzes patient presentation
- Identifies patterns suggesting conditions
- Flags concerning combinations

**Planner Layer:**
- Prioritizes diagnostic workup
- Sequences tests by informativeness
- Balances urgency vs. invasiveness

**Executor Layer:**
- Generates clinical summaries
- Creates order sets
- Documents decision rationale

**Failure Modes to Monitor:**
- **Scope creep:** Diagnosis instead of diagnostic support
- **Overconfidence:** "Definitely condition X" language
- **Regime anchoring:** Typical presentation bias (missing atypical cases)
- **Harm potential:** Recommendations that could delay critical care

**Critical Safety Boundaries:**
- LLM NEVER makes final diagnostic decisions
- All recommendations require physician review
- "Unlikely" doesn't mean "rule out"
- Explicit uncertainty for life-threatening differentials

---

### 3. Fraud Detection

**Use Case:** Transaction monitoring, anomaly detection, investigation support

| Financial Audit | Fraud Detection |
|-----------------|-----------------|
| Excel model | Transaction data |
| Cell formulas | Transaction rules, patterns |
| Dependency graph | Account relationships |
| Audit findings | Suspicious activity alerts |
| Severity levels | Risk scores |
| Remediation plan | Investigation queue |

**Strategist Layer:**
- Analyzes transaction patterns
- Identifies anomalies and outliers
- Flags suspicious relationship networks

**Planner Layer:**
- Prioritizes alerts by risk and evidence quality
- Sequences investigation steps
- Groups related cases

**Executor Layer:**
- Generates SAR narratives
- Creates case files
- Updates monitoring rules

**Failure Modes to Monitor:**
- **Scope creep:** Guilt determination instead of risk flagging
- **Pattern completion:** Seeing fraud where normal variation exists
- **Confirmation bias:** Over-weighting evidence that fits initial hypothesis
- **False confidence:** "Definitely fraud" vs. "warrants investigation"

**Critical Safety Boundaries:**
- LLM flags for investigation, doesn't conclude guilt
- False positive costs (customer friction) must be balanced
- Demographic bias must be monitored
- Evidence must be specific and documented

---

### 4. Policy Analysis / Impact Assessment

**Use Case:** Legislative analysis, policy impact modeling, regulatory review

| Financial Audit | Policy Analysis |
|-----------------|-----------------|
| Excel model | Policy documents, legislation |
| Cell formulas | Policy mechanisms, criteria |
| Dependency graph | Stakeholder impact chains |
| Audit findings | Policy concerns |
| Severity levels | Impact magnitude |
| Remediation plan | Amendment recommendations |

**Strategist Layer:**
- Analyzes policy mechanisms
- Identifies affected stakeholder groups
- Flags unintended consequences

**Planner Layer:**
- Prioritizes impacts by magnitude
- Maps stakeholder trade-offs
- Identifies mitigation options

**Executor Layer:**
- Generates impact summaries
- Creates stakeholder briefings
- Documents analytical rationale

**Failure Modes to Monitor:**
- **Scope creep:** Policy advocacy instead of analysis
- **Hallucinated causation:** Asserting impacts without mechanism
- **Regime anchoring:** Assuming current conditions persist
- **Narrative overfitting:** Coherent story over rigorous analysis

**Critical Safety Boundaries:**
- Distinguish analytical observations from normative positions
- Acknowledge uncertainty in causal claims
- Present multiple perspectives on contested impacts
- Separate "what will happen" from "what should happen"

---

### 5. Cybersecurity Threat Analysis

**Use Case:** Threat intelligence, vulnerability assessment, incident response

| Financial Audit | Threat Analysis |
|-----------------|-----------------|
| Excel model | System logs, network data |
| Cell formulas | Security rules, baselines |
| Dependency graph | Attack paths, dependencies |
| Audit findings | Security alerts |
| Severity levels | CVSS / risk scores |
| Remediation plan | Mitigation actions |

**Strategist Layer:**
- Analyzes system behavior patterns
- Identifies potential attack indicators
- Flags suspicious sequences

**Planner Layer:**
- Prioritizes threats by impact and likelihood
- Sequences response actions
- Identifies containment dependencies

**Executor Layer:**
- Generates incident reports
- Creates playbook actions
- Documents investigation timeline

**Failure Modes to Monitor:**
- **Scope creep:** Attack execution instead of detection
- **Pattern completion:** Seeing APT when it's noise
- **False confidence:** "Definitely compromised" vs. "warrants investigation"
- **Hallucination:** Fabricating IOCs or TTPs

**Critical Safety Boundaries:**
- Detection and analysis only, never offensive actions
- False positive costs must be balanced against risk
- Attribution requires high evidence bar
- Remediation actions need human authorization

---

## Cross-Cutting Principles

### 1. Separation of Concerns

| Layer | Responsibility | Control Type |
|-------|---------------|--------------|
| Strategist | Analysis, pattern recognition | LLM judgment |
| Planner | Prioritization, sequencing | Hybrid logic |
| Executor | Output generation, system updates | Deterministic |

**Principle:** Push decisions toward deterministic layers where possible. Reserve LLM judgment for analysis, not action.

### 2. Evidence Grounding

Every claim must trace to verifiable source:

| Claim Type | Evidence Requirement |
|------------|---------------------|
| Factual observation | Specific data reference |
| Pattern identification | Multiple supporting examples |
| Causal claim | Mechanism explanation + evidence |
| Risk assessment | Quantified factors |
| Recommendation | Logical link to finding |

**Principle:** Ungrounded claims are hallucination risks. Require explicit evidence for all assertions.

### 3. Uncertainty Calibration

| Confidence Level | Evidence Standard | Language |
|------------------|-------------------|----------|
| HIGH | Directly verified | "The data shows..." |
| MEDIUM | Consistent with evidence | "This suggests..." |
| LOW | Plausible inference | "This may indicate..." |
| SPECULATION | Beyond available data | "If true, this would..." |

**Principle:** Confidence must match evidence quality. Penalize overconfidence heavily.

### 4. Scope Discipline

| In Scope | Out of Scope |
|----------|--------------|
| Analysis | Decisions |
| Observation | Judgment |
| Risk flagging | Risk acceptance |
| Option identification | Option selection |
| Impact assessment | Value judgment |

**Principle:** LLMs inform human judgment; they don't replace it.

### 5. Harm Prevention

| Action Category | Human Oversight Required |
|-----------------|--------------------------|
| Read-only analysis | Low (audit trail) |
| Report generation | Medium (review before distribution) |
| System modifications | High (explicit approval) |
| Irreversible actions | Critical (multi-party sign-off) |

**Principle:** Consequence magnitude determines oversight intensity.

---

## Implementing Transfers

### Checklist for New Domain

1. **Map the vocabulary**
   - What is your "Excel model"?
   - What are your "formulas" (rules, relationships)?
   - What is your "audit finding" (alert, concern)?

2. **Define the layers**
   - What does your Strategist analyze?
   - What does your Planner prioritize?
   - What does your Executor generate?

3. **Identify failure modes**
   - What does scope creep look like in your domain?
   - What could be hallucinated?
   - What overconfident claims are dangerous?

4. **Set safety boundaries**
   - What must the LLM NEVER do?
   - What requires human approval?
   - What evidence bar applies?

5. **Design rubrics**
   - Adapt `strategy_quality.yaml` dimensions
   - Adapt `reasoning_fidelity.yaml` dimensions
   - Adapt `safety_and_scope.yaml` dimensions

6. **Create evaluation artifacts**
   - Sample good outputs for your domain
   - Sample borderline outputs
   - Sample failed outputs

---

## Example: Porting to HR Analytics

### Domain Mapping

| Financial Audit | HR Analytics |
|-----------------|--------------|
| Excel model | HRIS data, performance records |
| Cell formulas | HR policies, compensation rules |
| Dependency graph | Org structure, approval chains |
| Audit findings | Policy concerns, equity flags |
| Severity levels | Risk / legal exposure |
| Remediation plan | HR action items |

### Failure Mode Adaptation

| Generic Mode | HR-Specific Manifestation |
|--------------|---------------------------|
| Scope creep | Employment decisions, legal conclusions |
| Hallucination | Fabricated policy provisions, fake precedents |
| Overconfidence | "Definitely discriminatory" vs. "warrants review" |
| Harm potential | Recommendations affecting employment |

### Safety Boundaries

```
The system shall NOT:
- Make hiring, firing, or promotion decisions
- Conclude discrimination (legal determination)
- Access protected health information
- Recommend individual compensation changes
- Generate performance ratings

The system SHALL:
- Flag patterns warranting HR review
- Identify policy inconsistencies
- Highlight equity metrics for investigation
- Document analytical rationale
```

---

## Conclusion

The Strategist → Planner → Executor pattern transfers to any domain where:

1. Complex data requires intelligent analysis
2. Findings must be prioritized and sequenced
3. Outputs must be auditable and explainable
4. Human oversight is required for decisions
5. Safety boundaries must be maintained

The specific vocabulary changes; the architecture remains.
