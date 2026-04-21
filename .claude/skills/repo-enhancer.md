# Skill: Repository Enhancement from ZIP

Transform a simple or incomplete repository (extracted from a .zip file) into a production-ready, portfolio-quality project with comprehensive documentation, evaluation frameworks, and LLM integration patterns.

---

## Trigger

User provides a .zip file or asks to enhance/professionalize an incomplete repository.

---

## Phase 1: Assessment & Extraction

### 1.1 Extract and Analyze

```bash
# Extract the zip
unzip <filename>.zip -d ./extracted_repo

# Inventory what exists
find ./extracted_repo -type f -name "*.py" -o -name "*.js" -o -name "*.ts"
```

### 1.2 Identify Core Functionality

Determine:
- **Primary purpose**: What does this tool do?
- **Domain**: What field/industry does it serve?
- **Technical stack**: Python/JS/TS? Web app? CLI? API?
- **Current state**: MVP? Prototype? Half-finished?

### 1.3 Gap Analysis Checklist

Check for presence/absence of:

| Category | Items to Check |
|----------|----------------|
| **Core Code** | Main entry point, source directory structure, modules |
| **Dependencies** | requirements.txt / package.json |
| **Configuration** | .env.example, config files |
| **Documentation** | README.md, inline comments, docstrings |
| **Testing** | Test files, test data |
| **Git** | .gitignore, LICENSE |
| **CI/CD** | GitHub Actions, pre-commit hooks |

---

## Phase 2: Structure Enhancement

### 2.1 Standard Directory Structure

Create missing directories following this pattern:

```text
project-name/
├── src/                       # Core application code
│   ├── __init__.py
│   ├── main_module.py         # Primary logic
│   └── llm_analyzer.py        # LLM integration (if applicable)
├── eval/                      # LLM Evaluation Framework
│   └── llm_rubrics/           # YAML rubrics for grading outputs
├── human_review/              # Human-in-the-loop artifacts
│   ├── reviewer_guidelines.md
│   └── sample_reviews/        # Good, borderline, failed examples
├── trainer_tasks/             # Evaluation exercises
├── docs/                      # Extended documentation
│   ├── failure_modes.md       # LLM failure pattern catalog
│   └── transferability.md     # Cross-domain applications
├── sample_data/               # Example inputs (allowed in git)
├── scripts/                   # Utility scripts
├── data/                      # User data (gitignored)
├── RESULTS/                   # Generated outputs (gitignored)
├── app.py                     # Frontend/entry point (if web app)
├── .env.example               # Template for secrets
├── .gitignore                 # Comprehensive ignore file
├── LICENSE                    # MIT or appropriate license
├── README.md                  # Professional documentation
└── requirements.txt           # Dependencies
```

### 2.2 Create .gitignore

```gitignore
# Data Protection
data/
RESULTS/
temp_data/
*.xlsx
*.xlsm
*.csv

# Exception: Sample data for testing
!sample_data/*
!sample_models/*

# Logs
*.log
history.csv

# Python
__pycache__/
*.pyc
.DS_Store
*.egg-info/
dist/
build/

# Environment variables (NEVER commit)
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
```

### 2.3 Create .env.example

```bash
# LLM API Keys (choose one)
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here

# Optional Configuration
DEBUG=false
LOG_LEVEL=INFO
```

---

## Phase 3: Documentation Enhancement

### 3.1 README.md Template

Structure the README with:

```markdown
# Project Name

**One-line description of what this does**

Expanded explanation (2-3 sentences) explaining the approach and why it matters.

![Badge 1](badge_url) ![Badge 2](badge_url)

### Quick Start
```bash
pip install -r requirements.txt
python app.py  # or: streamlit run app.py
```

### Enable AI Analysis (Optional)
```bash
pip install anthropic python-dotenv
cp .env.example .env
# Edit .env with your API key
```

---

## Key Features

* **Feature 1**: Description
* **Feature 2**: Description
* **Feature 3**: Description
* **LLM-Powered Analysis** *(Optional)*: Description with safety note

---

## Installation

1. Clone the Repository
2. Install Dependencies
3. Configure Environment (if using LLM)

---

## Usage

Step-by-step instructions with code blocks.

---

## Sample Data

Description of included sample data for testing.

---

## Project Structure

```text
[Full directory tree]
```

---

## LLM Integration Architecture (if applicable)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Core Engine    │ --> │   LLM Analyzer   │ --> │  Human Review    │
│   (Deterministic)│     │   (Reasoning)    │     │  (Final Call)    │
└──────────────────┘     └──────────────────┘     └──────────────────┘
      CONTROL               REASONING               DECISION
```

### Safety Boundaries

| Allowed | Forbidden |
|---------|-----------|
| Explain findings | Domain-inappropriate advice |
| Prioritize by relevance | Decisions outside scope |
| Suggest next steps | Invent data not present |

---

## Evaluation Framework

- Rubrics in `eval/llm_rubrics/`
- Human review process in `human_review/`
- Failure modes documented in `docs/failure_modes.md`

---

## For AI Trainers and Evaluators

This repo demonstrates:
1. Rubric Design
2. Failure Analysis
3. Human-AI Collaboration
4. Safety Boundaries
5. Cross-Domain Thinking

See `trainer_tasks/` for hands-on exercises.

---

## License

MIT License - see LICENSE file
```

### 3.2 LICENSE (MIT)

```text
MIT License

Copyright (c) [YEAR] [AUTHOR]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Phase 4: LLM Evaluation Framework

### 4.1 Create Rubrics (eval/llm_rubrics/)

Create YAML rubrics for evaluating LLM outputs. Template:

```yaml
# eval/llm_rubrics/[dimension]_quality.yaml

rubric:
  name: [Dimension] Quality Assessment
  version: "1.0"
  domain: [Domain Description]

dimensions:
  [dimension_1]:
    description: |
      What this dimension measures
    scale:
      1:
        label: "Failure"
        description: "Complete failure description"
        examples:
          - "Concrete example of score 1"
      2:
        label: "Poor"
        description: "Poor quality description"
        examples:
          - "Concrete example of score 2"
      3:
        label: "Acceptable"
        description: "Meets minimum bar"
        examples:
          - "Concrete example of score 3"
      4:
        label: "Good"
        description: "Above average quality"
        examples:
          - "Concrete example of score 4"
      5:
        label: "Excellent"
        description: "Exceptional quality"
        examples:
          - "Concrete example of score 5"

evaluation_guidance:
  aggregation_method: weighted_average
  dimension_weights:
    [dimension_1]: 0.30
    [dimension_2]: 0.25
  minimum_acceptable_score: 3.0
  excellence_threshold: 4.5
```

Create 3 rubrics:
1. **output_quality.yaml** - Domain-specific quality metrics
2. **reasoning_fidelity.yaml** - Logic and evidence grounding
3. **safety_and_scope.yaml** - Boundary adherence

### 4.2 Create Human Review Guidelines (human_review/reviewer_guidelines.md)

```markdown
# Human Review Guidelines

## Purpose

Guidelines for human reviewers evaluating LLM-generated outputs.

## Review Process

### Step 1: Initial Read
- Read the output without scoring
- Note first impressions

### Step 2: Rubric Application
- Score each dimension independently
- Document evidence for each score

### Step 3: Cross-Check
- Verify claims against source data
- Check for failure modes

### Step 4: Final Assessment
- Calculate aggregate score
- Write summary feedback

## Scoring Calibration

### Score 1-2: Reject
Output has fundamental problems requiring regeneration.

### Score 3: Conditional Accept
Output is usable with significant caveats or edits.

### Score 4: Accept
Output is good quality with minor issues.

### Score 5: Exemplary
Output demonstrates best practices.

## Common Pitfalls

1. **Anchoring**: Don't let first impression dominate
2. **Halo effect**: Score dimensions independently
3. **Severity creep**: Maintain consistent standards

## Escalation

Escalate to senior reviewer if:
- Score disagreement > 1.5 points
- Potential safety violation
- Novel failure mode discovered
```

### 4.3 Create Sample Reviews (human_review/sample_reviews/)

Create 3 examples:
- **example_good.md** - Score 4-5, well-executed output
- **example_borderline.md** - Score 3, acceptable with issues
- **example_fail.md** - Score 1-2, clear failures

---

## Phase 5: Failure Modes Documentation

### 5.1 Create docs/failure_modes.md

Document 8-10 failure patterns specific to the domain:

```markdown
# LLM Failure Modes in [Domain]

## Table of Contents
1. [Failure Mode 1]
2. [Failure Mode 2]
...

## 1. [Failure Mode Name]

### Symptom
What the failure looks like in outputs.

### Root Cause
Why this failure occurs.

### Example
**Bad output:**
> Concrete example of the failure

**Problem:** Explanation of what's wrong.

### Detection Method
- How to spot this failure
- Questions to ask
- Verification steps

### Mitigation
- Prompt improvements
- System guardrails
- Human review focus areas

---

## Cross-Cutting Patterns

### Compound Failures
Common combinations of failure modes.

### Detection Priorities
Ranked by harm potential.

### System Improvements
| Failure Mode | System Improvement |
|--------------|-------------------|
| Mode 1 | Improvement 1 |
```

### 5.2 Create docs/transferability.md

```markdown
# Cross-Domain Transferability Guide

## Core Principles

These principles transfer beyond [original domain]:

| Principle | Application |
|-----------|-------------|
| Separate reasoning from control | LLM analyzes; code executes |
| Explicit scope boundaries | Define allowed/forbidden |
| Evidence grounding | Require citations |
| Uncertainty calibration | Express confidence levels |

## Domain Mappings

### [Domain 1] Application

| Original Concept | [Domain 1] Equivalent |
|------------------|----------------------|
| Concept A | Equivalent A |

### [Domain 2] Application

...

## Adaptation Checklist

When adapting to new domain:
- [ ] Identify domain-specific failure modes
- [ ] Create appropriate rubrics
- [ ] Define scope boundaries
- [ ] Build sample data
- [ ] Establish human review process
```

---

## Phase 6: Trainer Tasks

### 6.1 Create trainer_tasks/ Directory

Create 3 evaluation exercises:

**task_1_grade_outputs.md**
```markdown
# Task 1: Grade LLM Outputs

## Objective
Apply rubrics to grade provided outputs.

## Materials
- 3 sample outputs (provided)
- Rubrics from eval/llm_rubrics/

## Instructions
1. Read each output carefully
2. Score using each rubric dimension
3. Calculate weighted aggregate
4. Write justification for each score

## Deliverables
- Completed scoring sheets
- Written justifications
- Identified improvement areas

## Time Estimate
45-60 minutes
```

**task_2_identify_failure.md**
```markdown
# Task 2: Identify Failure Modes

## Objective
Detect failure patterns in LLM outputs.

## Materials
- 5 outputs containing failures (provided)
- docs/failure_modes.md reference

## Instructions
1. Read each output
2. Identify which failure mode(s) are present
3. Cite specific evidence
4. Suggest mitigation

## Deliverables
- Failure mode identification for each output
- Evidence citations
- Mitigation recommendations
```

**task_3_prompt_fix.md**
```markdown
# Task 3: Fix Prompts to Prevent Failures

## Objective
Modify prompts to prevent identified failures.

## Materials
- Original prompts that produced failures
- Failure mode analysis from Task 2

## Instructions
1. Analyze why the original prompt allowed the failure
2. Propose specific prompt modifications
3. Explain how each modification addresses the failure
4. Predict potential side effects

## Deliverables
- Modified prompts
- Explanation of changes
- Side effect analysis
```

---

## Phase 7: LLM Integration (Optional)

### 7.1 Create src/llm_analyzer.py

```python
"""
LLM Integration Module with Safety Boundaries

Provides Claude/OpenAI integration for analyzing outputs
with explicit scope constraints to prevent harmful recommendations.
"""

import os
from typing import Optional

# System prompt with safety boundaries
SYSTEM_PROMPT = """You are a [domain] analysis assistant. Your role is to analyze
[inputs] and provide insights.

## Your Role
- Analyze provided data
- Explain findings clearly
- Prioritize by relevance/severity
- Suggest next steps for human review

## Out of Scope (DO NOT)
- [Forbidden action 1 for this domain]
- [Forbidden action 2]
- [Forbidden action 3]
- Invent data not present in the inputs
- Express certainty about uncertain conclusions

## Output Format
Structure your response with:
1. Executive Summary (2-3 sentences)
2. Key Findings (prioritized list)
3. Recommended Next Steps (for human reviewer)
4. Caveats and Limitations

Always ground claims in specific evidence from the input data.
"""


def analyze_with_llm(
    data: dict,
    provider: str = "anthropic",
    model: Optional[str] = None
) -> dict:
    """
    Analyze data using LLM with safety boundaries.

    Args:
        data: Dictionary containing data to analyze
        provider: 'anthropic' or 'openai'
        model: Specific model to use (defaults to best available)

    Returns:
        dict with 'analysis' text and 'model_used' identifier
    """
    if provider == "anthropic":
        return _analyze_anthropic(data, model)
    elif provider == "openai":
        return _analyze_openai(data, model)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _analyze_anthropic(data: dict, model: Optional[str] = None) -> dict:
    """Use Anthropic Claude for analysis."""
    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic package not installed. Run: pip install anthropic"}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set in environment"}

    client = anthropic.Anthropic(api_key=api_key)
    model = model or "claude-sonnet-4-20250514"

    user_message = _format_data_for_analysis(data)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        return {
            "analysis": response.content[0].text,
            "model_used": model,
            "provider": "anthropic"
        }
    except Exception as e:
        return {"error": str(e)}


def _analyze_openai(data: dict, model: Optional[str] = None) -> dict:
    """Use OpenAI GPT for analysis."""
    try:
        import openai
    except ImportError:
        return {"error": "openai package not installed. Run: pip install openai"}

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY not set in environment"}

    client = openai.OpenAI(api_key=api_key)
    model = model or "gpt-4o"

    user_message = _format_data_for_analysis(data)

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )
        return {
            "analysis": response.choices[0].message.content,
            "model_used": model,
            "provider": "openai"
        }
    except Exception as e:
        return {"error": str(e)}


def _format_data_for_analysis(data: dict) -> str:
    """Format data dictionary into prompt-friendly text."""
    lines = ["# Data for Analysis", ""]
    for key, value in data.items():
        lines.append(f"## {key}")
        lines.append(str(value))
        lines.append("")
    return "\n".join(lines)


def check_llm_available() -> dict:
    """Check which LLM providers are available."""
    available = {}

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            available["anthropic"] = True
        except ImportError:
            available["anthropic"] = "package not installed"
    else:
        available["anthropic"] = "API key not set"

    if os.environ.get("OPENAI_API_KEY"):
        try:
            import openai
            available["openai"] = True
        except ImportError:
            available["openai"] = "package not installed"
    else:
        available["openai"] = "API key not set"

    return available
```

### 7.2 Update requirements.txt

```text
# Core dependencies
[existing dependencies]

# LLM Integration (optional)
anthropic>=0.18.0
openai>=1.0.0
python-dotenv>=1.0.0
```

---

## Phase 8: Sample Data

### 8.1 Create Sample Data Generator

Create a script to generate realistic sample data:

```python
# scripts/create_sample_data.py
"""Generate sample data for testing and demonstration."""

def create_sample():
    """Create sample input data with intentional issues for testing."""
    # Implementation depends on domain
    pass

if __name__ == "__main__":
    create_sample()
    print("Sample data created successfully!")
```

### 8.2 Include Sample in Repo

- Place generated samples in `sample_data/` or `sample_models/`
- Update .gitignore to allow: `!sample_data/*`
- Document samples in README

---

## Phase 9: Final Verification

### 9.1 Pre-Push Checklist

Verify before pushing:

- [ ] README is comprehensive and accurate
- [ ] LICENSE file contains actual license text
- [ ] .gitignore protects sensitive data
- [ ] .env.example exists (no actual secrets)
- [ ] requirements.txt lists all dependencies
- [ ] Sample data is included and documented
- [ ] All rubrics have concrete examples
- [ ] Failure modes are domain-specific
- [ ] Trainer tasks are actionable
- [ ] LLM integration has safety boundaries

### 9.2 Test Commands

```bash
# Verify no secrets are staged
git diff --cached --name-only | xargs grep -l "API_KEY\|SECRET\|PASSWORD" || echo "Clean"

# Check .gitignore is working
git status --ignored

# Verify sample data is included
ls sample_data/ || ls sample_models/

# Test the app runs
python app.py --help  # or: streamlit run app.py
```

---

## Customization Notes

### Domain Adaptation

When adapting this pattern to different domains:

1. **Rubrics**: Modify dimensions to match domain-specific quality criteria
2. **Failure Modes**: Identify failures unique to the domain
3. **Safety Boundaries**: Define what's forbidden in this context
4. **Sample Data**: Create realistic examples with intentional issues

### Scope Scaling

For smaller projects, minimum viable enhancement:
- README.md (professional)
- .gitignore (comprehensive)
- LICENSE
- requirements.txt
- One rubric
- Basic failure modes doc

For portfolio/showcase projects, include full framework.

---

## Output

After running this skill, the repository should:

1. Have professional structure matching industry standards
2. Include comprehensive documentation
3. Protect sensitive data via .gitignore
4. Demonstrate LLM evaluation competencies
5. Be ready for GitHub push and portfolio showcase
