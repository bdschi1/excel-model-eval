# Hedge Fund Excel Model Auditor

A tool for structural analysis of institutional Excel‑based financial models.

The application ingests Excel workbooks as **Directed Acyclic Graphs (DAGs)**, mapping the flow of data from assumptions to valuation and highlighting structural issues in the model.



### Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
# Upload sample_models/BOBWEIR_Model.xlsx to test
```

### Optional LLM analysis

```bash
pip install anthropic python-dotenv  # or: pip install openai python-dotenv
cp .env.example .env
# Edit .env and add your API key
```

***

## Features

- **Dual‑state ingestion**  
  Loads models in two parallel states: values (for numerical checks) and formulas (for dependency tracing).

- **Dependency graph engine**  
  Uses `networkx` to represent each cell as a node, enabling detection of circular references and disconnected calculation chains.

- **Audit checks**
  - Hard‑coded entries in forecast periods (e.g., constant growth rates in formula rows).
  - Balance sheet consistency $$(Assets - (Liabilities + Equity) = 0)$$.
  - References to missing or external files (e.g., `C:/Users/Analyst/Desktop/Budget.xlsx`).

- **Reporting artifacts**  
  Produces a PDF memo and an Excel “datatape” summarizing identified issues.

- **Complexity scoring**  
  Assigns a 1–5 complexity score using graph topology and formula density.

- **LLM‑assisted summaries (optional)**  
  Uses Claude or GPT‑4 to generate narrative summaries of findings, with prompts constrained to exclude investment advice.

***

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/excel-model-eval.git
   cd excel-model-eval
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

***

## Usage

1. Launch the dashboard:

   ```bash
   streamlit run app.py
   ```

2. Upload a model:
   - Supports `.xlsx` and `.xlsm` for formula analysis.
   - CSV files are supported for value inspection only.
   - Example: upload `sample_models/BOBWEIR_Model.xlsx` for a preconfigured test case.

3. Review outputs:
   - Inspect the complexity score and identified issues in the UI.
   - Download the PDF memo and Excel datatape from the sidebar.

***

## Sample model: BOBWEIR Pharmaceuticals

The repository includes a sample financial model for testing:

**`sample_models/BOBWEIR_Model.xlsx`**

| Sheet | Contents |
|-------|----------|
| Cover | Company overview, product list |
| Assumptions | Growth, margins, working capital drivers |
| Revenue | Revenue build for six products |
| IS | Income statement with linked formulas |
| BS | Balance sheet with working capital calculations |
| CF | Cash flow statement |
| DCF | DCF schedule and terminal value |

Company profile (synthetic example):

- Specialty pharma focused on rare diseases and oncology  
- Revenue split across six products (Neurex, Oncovir, Hemaguard, Cardioshield, Dermaclear, Respiron)  
- Projection period: 2024E–2028E  

The model includes intentional issues for testing:

- A hard‑coded revenue plug in the projection period (Revenue sheet, Neurex 2025E).  
- Full formula linkages for dependency tracing.

To regenerate the sample:

```bash
python scripts/create_sample_model.py
```

***

## Project structure

```text
excel-model-eval/
├── src/                       # Core audit engine
│   ├── ingestion.py           # Dual-state loading
│   ├── dependency.py          # Graph construction and analysis
│   ├── auditor.py             # Heuristic checks and issue catalog
│   ├── reporting.py           # PDF/Excel report generation and scoring
│   └── llm_analyzer.py        # Optional LLM integration
├── eval/                      # LLM evaluation framework
│   └── llm_rubrics/           # YAML rubrics for grading LLM outputs
├── human_review/              # Human-in-the-loop materials
│   ├── reviewer_guidelines.md
│   └── sample_reviews/
├── trainer_tasks/             # Evaluation exercises (AI trainer-style tasks)
├── docs/
│   ├── failure_modes.md       # Catalog of LLM failure patterns
│   └── transferability.md     # Notes on cross-domain use
├── sample_models/
│   └── BOBWEIR_Model.xlsx
├── scripts/
│   └── create_sample_model.py
├── app.py                     # Streamlit frontend
├── .env.example               # Template for API keys
├── data/                      # User models (gitignored)
├── RESULTS/                   # Generated reports (gitignored)
└── requirements.txt
```

***

## LLM integration architecture

The optional LLM module (`src/llm_analyzer.py`) adds a structured analysis layer on top of the deterministic audit engine:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Audit Engine   │ --> │   LLM Analyzer   │ --> │  Human Review    │
│ (Deterministic)  │     │   (Narrative)    │     │  (Final Review)  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        CONTROL               REASONING               DECISION
```

- Audit engine: graph analysis, issue detection, severity calculations.  
- LLM analyzer: text summaries, grouping and prioritization of issues, explanations.  
- Human review: verification of claims and decisions about any downstream actions.

### Prompt‑level safety constraints

The LLM is configured to:

- **Allowed**: explain findings, order issues by materiality, suggest remediation steps, express uncertainty, reference specific cells.  
- **Disallowed**: investment recommendations, valuation opinions, price targets, data invention, business strategy advice.

The model is used as an analysis and explanation component; it does not execute changes or interact with external systems.


### Design principles

| Principle | Implementation in this repo |
|----------|-----------------------------|
| Separate reasoning from control | LLM produces text analyses; code performs audits and report generation |
| Constrained guidance | Prompts enforce scope limits and evidence referencing |
| Evaluation of non‑numeric outputs | YAML rubrics and human review guidelines |
| Failure‑mode awareness | Documented patterns and targeted test cases |
| Preference for interpretability | Graph‑based checks and explicit evidence paths |

### Evaluation and trainer assets

- **Rubrics (`eval/llm_rubrics/`)**  
  - `strategy_quality.yaml`: plausibility and proportionality of proposed actions.  
  - `reasoning_fidelity.yaml`: alignment between evidence and conclusions, uncertainty handling.  
  - `safety_and_scope.yaml`: scope adherence and hallucination risk.

- **Human review (`human_review/`)**  
  - Reviewer guidelines defining process and scoring criteria.  
  - Sample reviews illustrating “good”, “borderline”, and “failed” outputs.

- **Failure modes (`docs/failure_modes.md`)**  
  - Examples: narrative overfitting, regime anchoring, unwarranted confidence.  
  - Detection strategies and mitigation options.

- **Trainer tasks (`trainer_tasks/`)**  
  - Exercises where a reviewer grades outputs, identifies failure modes, and proposes prompt or policy changes (suitable as AI trainer / RLHF evaluation tasks).

***

## Transferability

The same architecture (deterministic core + scoped LLM layer + human review + rubrics) can be adapted to other domains such as compliance, healthcare, cybersecurity, operations, and policy analysis, as discussed in `docs/transferability.md`.

---

![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white)

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![NetworkX](https://img.shields.io/badge/NetworkX-4C9A2A?style=flat)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat&logo=pydantic&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-191919?style=flat&logo=anthropic&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)

