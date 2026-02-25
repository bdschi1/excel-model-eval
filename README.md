# Hedge Fund Excel Model Auditor

![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![NetworkX](https://img.shields.io/badge/NetworkX-4C9A2A?style=flat)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat&logo=pydantic&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-191919?style=flat&logo=anthropic&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)

A structural audit tool for Excel-based financial models. It reads an Excel workbook, maps every cell and formula into a dependency graph, runs deterministic checks for common modeling errors (hard-coded plugs, broken references, balance sheet imbalances), and produces a PDF memo and Excel report of findings. An optional LLM layer can generate narrative summaries — but the core audit is purely rule-based and does not require any API keys.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Streamlit dashboard
streamlit run app.py
# Upload sample_models/BOBWEIR_Model.xlsx to test

# CLI
python main.py                                    # runs against sample model
python main.py path/to/your_model.xlsx            # runs against any model
```

### Optional LLM analysis

```bash
pip install anthropic python-dotenv  # or: pip install openai python-dotenv
cp .env.example .env
# Edit .env and add your API key
```

---

## How It Works

The audit runs in four phases:

```
Excel file → Ingestion → Dependency Graph → Audit Checks → PDF/Excel Report
               (dual-state:        (networkx DAG)      (deterministic      (complexity score,
                values +                                 heuristics)         issue catalog,
                formulas)                                                    remediation)
```

1. **Ingestion** — Loads the workbook twice: once for calculated values, once for raw formulas. This enables both numerical checks and logical tracing.

2. **Dependency graph** — Parses every formula into a directed graph using networkx. Each cell is a node; each reference is an edge. This reveals circular references, orphaned cells, and cross-sheet data flows.

3. **Audit checks** — Three core checks run against the graph and values:
   - **Hard-coded plugs** — Rows where most cells are formulas but some projection-period cells are constants (analysts overriding the model).
   - **Balance sheet integrity** — Checks that Assets = Liabilities + Equity across all projection periods (tolerance: ±$1).
   - **Broken/external references** — Detects `#REF!`, `#NAME?`, `#DIV/0!`, and links to external files.

4. **Reporting** — Produces a complexity score (1–5 based on sheet count, formula density, and interdependency), a PDF memo, and an Excel datatape with all findings.

### LLM layer (optional)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Audit Engine   │ --> │   LLM Analyzer   │ --> │  Human Review    │
│ (Deterministic)  │     │   (Narrative)    │     │  (Final Review)  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        CONTROL               REASONING               DECISION
```

The LLM receives audit findings and produces narrative summaries. It is constrained at the prompt level:

- **Allowed**: explain findings, prioritize by materiality, suggest remediation, reference specific cells.
- **Disallowed**: investment recommendations, valuation opinions, price targets, data invention.

---

## Sample Model

The repo includes a synthetic test case: **BOBWEIR Pharmaceuticals** (`sample_models/BOBWEIR_Model.xlsx`).

| Sheet | Contents |
|-------|----------|
| Cover | Company overview, product list |
| Assumptions | Growth, margins, working capital drivers |
| Revenue | Revenue build for six products |
| IS | Income statement with linked formulas |
| BS | Balance sheet with working capital calculations |
| CF | Cash flow statement |
| DCF | DCF schedule and terminal value |

Intentional issues for testing: a hard-coded revenue plug (Revenue sheet, Neurex 2025E) and full formula linkages for dependency tracing. Regenerate with `python scripts/create_sample_model.py`.

---

## Financial Model Builder

The `builder/` module is an independent financial modeling library included in this repo for convenience. It does not interact with the audit engine.

It provides programmatic construction of:
- **DCF models** — scenario-weighted discounted cash flow with sensitivity tables
- **Comparable company analysis** — peer selection and implied valuation
- **Operating models** — revenue/cost projections with flag detection

Each builder uses Pydantic for input validation and produces structured outputs with markdown reports. See `examples/saas_dcf_walkthrough.py` for usage.

---

## Evaluation Framework

### Rubrics (`eval/llm_rubrics/`)

YAML-based rubrics for grading LLM audit narratives:

- `safety_and_scope.yaml` — scope adherence, hallucination risk
- `strategy_quality.yaml` — plausibility and proportionality of recommendations
- `reasoning_fidelity.yaml` — evidence grounding, logical consistency, uncertainty calibration

### Failure modes (`docs/failure_modes.md`)

Catalog of 10 LLM failure patterns with detection strategies: narrative overfitting, regime anchoring, false confidence amplification, explanation-action divergence, scope creep, hallucinated causation, severity inflation, and others.

### Human review (`human_review/`)

Reviewer guidelines and sample reviews (good / borderline / failed outputs) for calibrating human evaluators.

### Trainer tasks (`trainer_tasks/`)

Exercises for AI trainer / RLHF evaluation: grade outputs on rubrics, identify failure modes, propose prompt or policy fixes.

---

## Transferability

The architecture (deterministic core → scoped LLM layer → human review → rubrics) maps to other domains. See `docs/transferability.md` for patterns in compliance, clinical decision support, fraud detection, and cybersecurity.

---

## Project Structure

```text
excel-model-eval/
├── src/                       # Core audit engine
│   ├── ingestion.py           # Dual-state loading
│   ├── dependency.py          # Graph construction and analysis
│   ├── auditor.py             # Heuristic checks and issue catalog
│   ├── reporting.py           # PDF/Excel report generation and scoring
│   └── llm_analyzer.py        # Optional LLM integration
├── builder/                   # Financial model builder (independent)
│   ├── dcf_builder.py         # DCF valuation engine
│   ├── comps_builder.py       # Comparable company analysis
│   ├── operating_model.py     # Revenue/cost projections
│   ├── assumptions.py         # Pydantic input schema
│   ├── validators.py          # Business logic checks
│   └── outputs.py             # Result data structures
├── eval/                      # LLM evaluation framework
│   └── llm_rubrics/           # YAML rubrics for grading LLM outputs
├── human_review/              # Human-in-the-loop materials
├── trainer_tasks/             # Evaluation exercises
├── docs/
│   ├── failure_modes.md       # LLM failure pattern catalog
│   └── transferability.md     # Cross-domain architecture mapping
├── sample_models/
│   └── BOBWEIR_Model.xlsx
├── scripts/
│   └── create_sample_model.py
├── app.py                     # Streamlit frontend
├── main.py                    # CLI entry point
├── .env.example               # Template for API keys
└── requirements.txt
```

---

## Design Principles

| Principle | Implementation |
|-----------|---------------|
| Separate reasoning from control | LLM produces text; code performs audits and report generation |
| Constrained guidance | Prompts enforce scope limits and evidence referencing |
| Evaluation of non-numeric outputs | YAML rubrics and human review guidelines |
| Failure-mode awareness | Documented patterns and targeted test cases |
| Preference for interpretability | Graph-based checks and explicit evidence paths |

---

## Related Work

- **FinanceQA** (Mateega et al., 2025) — Benchmark showing frontier LLMs fail ~60% of realistic financial analysis tasks, particularly hand-spreading and assumption-based questions. [arXiv:2501.18062](https://arxiv.org/abs/2501.18062)
- **PRBench** (Akyurek et al., 2025) — 19,356 expert-curated binary criteria for professional reasoning evaluation. Informs the rubric-based grading approach. [arXiv:2511.11562](https://arxiv.org/abs/2511.11562)
- **Fin-o1** (Qian et al., 2025) — Domain-specific chain-of-thought training for financial reasoning. Relevant to evaluating LLM capability on formula auditing. [arXiv:2502.08127](https://arxiv.org/abs/2502.08127)
