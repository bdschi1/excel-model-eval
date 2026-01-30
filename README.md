# Hedge Fund Excel Model Auditor 📊

**A Forensic Analysis System for Institutional Financial Models**

Traditional model review involves spot-checking formulas manually. This tool takes a different approach: it ingests Excel workbooks as **Directed Acyclic Graphs (DAGs)**, mapping the logical flow of data from assumptions to valuation. This allows for the instant detection of structural risks that human analysts often miss.

![Streamlit Badge](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python Badge](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)

### Quick Start
```bash
pip install -r requirements.txt
streamlit run app.py
# Upload sample_models/BOBWEIR_Model.xlsx to test
```

### Enable AI Analysis (Optional)
```bash
pip install anthropic python-dotenv  # or: pip install openai python-dotenv
cp .env.example .env
# Edit .env and add your API key
```

---

## 🚀 Key Features

* **Dual-State Ingestion**: Loads models in two parallel states—**Values** (for numerical validation) and **Formulas** (for logic tracing).
* **Dependency Graph Engine**: Uses `networkx` to map every cell as a node. Detects circular references and orphaned calculation chains instantly.
* **Forensic Audits**:
    * **Hard-Coded Plugs**: Identifies manual overrides in forecast years (e.g., hard-coding 5% growth in a formula row).
    * **Accounting Integrity**: Verifies Balance Sheet balancing ($Assets - (Liabs + Equity) = 0$).
    * **Link Rot**: Flags broken dependencies on external local files (e.g., `C:/Users/Analyst/Desktop/Budget.xlsx`).
* **Board-Ready Reporting**: Generates a PDF Executive Memo and a grouped Excel Datatape of all findings.
* **Complexity Scoring**: Algorithms rate model complexity (1-5) based on graph topology and formula density.
* **LLM-Powered Analysis** *(Optional)*: Generate narrative summaries of findings using Claude or GPT-4, with built-in scope boundaries to prevent investment advice.

---

## 🛠️ Installation

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/your-username/excel-model-eval.git](https://github.com/your-username/excel-model-eval.git)
    cd excel-model-eval
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🖥️ Usage

1.  **Launch the Dashboard**
    ```bash
    streamlit run app.py
    ```

2.  **Upload a Model**
    * Drag and drop any `.xlsx` or `.xlsm` file.
    * *Note: CSV files are supported for value inspection but cannot be audited for formula logic.*
    * **Try the sample model:** Upload `sample_models/BOBWEIR_Model.xlsx` to see the auditor in action.

3.  **Analyze & Download**
    * Review the **Complexity Score** and top-level risks in the dashboard.
    * Download the **PDF Memo** and **Excel Datatape** from the sidebar.

---

## 🧪 Sample Model: BOBWEIR Pharmaceuticals

The repo includes a fully-functional sample financial model for testing:

**`sample_models/BOBWEIR_Model.xlsx`**

| Sheet | Contents |
|-------|----------|
| Cover | Company overview, product portfolio |
| Assumptions | Growth rates, margins, working capital drivers |
| Revenue | 6-product revenue build ($3B total) |
| IS | Income Statement with linked formulas |
| BS | Balance Sheet with working capital calcs |
| CF | Cash Flow Statement |
| DCF | DCF valuation with terminal value |

**Company Profile:**
- Specialty pharma focused on rare diseases & oncology
- $3B revenue from 6 products (Neurex, Oncovir, Hemaguard, Cardioshield, Dermaclear, Respiron)
- 5-year projection (2024E-2028E)

**Intentional Issues for Auditor Testing:**
- 1 hard-coded plug in projection period (Revenue sheet, Neurex 2025E)
- Full formula linkages for tracing

To regenerate the sample model:
```bash
python scripts/create_sample_model.py
```

---

## 📂 Project Structure

```text
excel-model-eval/
├── src/                       # Core audit engine
│   ├── ingestion.py           # Dual-state loading logic
│   ├── dependency.py          # Graph construction & topology analysis
│   ├── auditor.py             # Heuristic engines with explanations
│   ├── reporting.py           # PDF/Excel generation & Complexity scoring
│   └── llm_analyzer.py        # LLM integration with safety boundaries
├── eval/                      # LLM Evaluation Framework
│   └── llm_rubrics/           # YAML rubrics for grading LLM outputs
├── human_review/              # Human-in-the-loop artifacts
│   ├── reviewer_guidelines.md
│   └── sample_reviews/        # Good, borderline, and failed examples
├── trainer_tasks/             # Mercor-style evaluation exercises
├── docs/                      # Documentation
│   ├── failure_modes.md       # LLM failure pattern catalog
│   └── transferability.md     # Cross-domain application guide
├── sample_models/             # Test models (included in repo)
│   └── BOBWEIR_Model.xlsx     # Fully-functional sample
├── scripts/                   # Utility scripts
│   └── create_sample_model.py # Regenerate sample model
├── app.py                     # Streamlit Frontend
├── .env.example               # Template for API keys
├── data/                      # Your input models (gitignored)
├── RESULTS/                   # Generated reports (gitignored)
└── requirements.txt           # Dependencies
```

---

## 🤖 LLM Integration Architecture

The optional LLM module (`src/llm_analyzer.py`) demonstrates **safe LLM integration** in a domain-specific tool:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Audit Engine   │ --> │   LLM Analyzer   │ --> │  Human Review    │
│   (Deterministic)│     │   (Reasoning)    │     │  (Final Call)    │
│                  │     │                  │     │                  │
│ - Graph analysis │     │ - Narrative gen  │     │ - Verify claims  │
│ - Issue detection│     │ - Prioritization │     │ - Act on findings│
│ - Severity calc  │     │ - Explanations   │     │ - Approve changes│
└──────────────────┘     └──────────────────┘     └──────────────────┘
        CONTROL               REASONING               DECISION
```

### Safety Boundaries (Enforced in System Prompt)

| Allowed | Forbidden |
|---------|-----------|
| Explain findings | Investment recommendations |
| Prioritize by materiality | Valuation opinions |
| Suggest remediation steps | Price targets |
| Express uncertainty | Invent data not in findings |
| Reference specific cells | Business strategy advice |

### Why This Matters

The LLM **analyzes and explains** but doesn't **decide or execute**. This separation:
- Prevents harmful autonomous actions
- Keeps humans in the loop for decisions
- Makes outputs auditable and evaluable
- Allows systematic testing via rubrics

---

## 🧠 What This Repo Teaches About LLM-Guided Systems

This project demonstrates key principles for building **safe, interpretable, and evaluable** systems where LLMs guide domain-specific analysis.

### Core Design Principles

| Principle | How It's Applied |
|-----------|------------------|
| **Separate reasoning from control** | LLM provides analysis; execution stays deterministic |
| **Inject guidance safely** | Structured prompts with explicit scope boundaries |
| **Evaluate non-numeric outputs** | Rubrics for strategy quality, reasoning fidelity, safety |
| **Design ablations for prompts** | Failure mode documentation enables systematic testing |
| **Interpretability over autonomy** | Human reviewer artifacts require explainability |

### Key Lessons

1. **When to Separate Reasoning from Control**
   - Let LLMs analyze, explain, and recommend
   - Keep execution (file changes, calculations) in deterministic code
   - Example: LLM identifies issues → Python code generates reports

2. **How to Inject LLM Guidance Safely**
   - Define explicit scope boundaries (audit vs. investment advice)
   - Require evidence grounding for all claims
   - Build in uncertainty calibration requirements
   - Create explicit "do not do" lists

3. **How to Evaluate Non-Numeric Outputs**
   - Multi-dimensional rubrics (see `eval/llm_rubrics/`)
   - Concrete failure examples at each scale point
   - Human reviewer calibration exercises
   - Cross-reviewer correlation tracking

4. **How to Design Ablations for Prompts**
   - Document failure modes systematically (see `docs/failure_modes.md`)
   - Create test cases targeting each failure mode
   - Compare outputs from different prompt framings
   - Track failure mode frequency over time

5. **Why Interpretability Beats End-to-End Autonomy**
   - Explainable reasoning enables human oversight
   - Traceable evidence chains support audit requirements
   - Modular design allows targeted improvements
   - Clear scope boundaries prevent harmful overreach

### Transferability

These principles apply beyond financial models:

| Domain | Application |
|--------|-------------|
| **Compliance** | Regulatory document analysis with audit trails |
| **Healthcare** | Clinical decision support with evidence grounding |
| **Cybersecurity** | Threat analysis with confidence calibration |
| **Operations** | Process optimization with scope-bounded recommendations |
| **Policy** | Impact assessment with uncertainty quantification |

See `docs/transferability.md` for detailed cross-domain mappings.

---

## 📋 Evaluation Framework

This repository includes a comprehensive LLM evaluation layer:

### Rubrics (`eval/llm_rubrics/`)
- **strategy_quality.yaml**: Economic plausibility, actionability, proportionality
- **reasoning_fidelity.yaml**: Signal-action consistency, uncertainty calibration
- **safety_and_scope.yaml**: Scope adherence, data invention risk, harm prevention

### Human Review (`human_review/`)
- **reviewer_guidelines.md**: Process and scoring criteria
- **sample_reviews/**: Good, borderline, and failed output examples

### Failure Modes (`docs/failure_modes.md`)
- Narrative overfitting, regime anchoring, false confidence
- Detection methods and mitigation strategies
- Cross-cutting pattern analysis

### Evaluator Tasks (`trainer_tasks/`)
- Grade outputs, identify failures, propose prompt fixes
- Mercor-style evaluation exercises

---

## 🎯 For AI Trainers and Evaluators

This repo demonstrates competencies valued in AI training roles:

1. **Rubric Design**: Creating evaluation criteria for subjective outputs
2. **Failure Analysis**: Systematic documentation of how models fail
3. **Human-AI Collaboration**: Designing review workflows and guidelines
4. **Safety Boundaries**: Implementing scope constraints that prevent harm
5. **Cross-Domain Thinking**: Abstracting patterns beyond the original domain

See `trainer_tasks/` for hands-on evaluation exercises