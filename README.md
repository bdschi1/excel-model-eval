<!-- excel-model-eval/README.md | Last updated: 2026-04-23 -->

# ModelLens

![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![NetworkX](https://img.shields.io/badge/NetworkX-4C9A2A?style=flat)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat&logo=pydantic&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-191919?style=flat&logo=anthropic&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)

A structural audit tool for Excel-based financial models. It reads an Excel workbook, maps every cell and formula into a dependency graph, runs deterministic checks for common modeling errors (hard-coded plugs, broken references, balance sheet imbalances), and produces a PDF memo and Excel report of findings. An optional LLM layer can generate narrative summaries — but the core audit is purely rule-based and does not require any API keys.

This is a continually developed project. Features, interfaces, and test coverage expand over time as new research ideas and workflow needs arise.

**Key questions this project answers:**
- *Does this Excel model have structural errors that could affect the output?*
- *Where are the hard-coded overrides hiding in this workbook?*

## Quick Start

```bash
./run.sh            # setup + launch Streamlit app
```

Or manually:

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

Run `./run.sh help` for all commands (`setup`, `app`, `cli`, `test`).

### Optional LLM analysis

```bash
pip install anthropic python-dotenv  # or: pip install openai python-dotenv
cp .env.example .env
# Edit .env and add your API key
```

### CI mode

```bash
python main.py --ci                       # audit sample model, JSON to stdout
python main.py path/to/model.xlsx --ci    # audit any model
```

Runs the deterministic audit and emits a single JSON blob to stdout with
`ci_mode`, `model`, `critical_issues_found`, `threshold_max_critical`, `pass`,
and `summary` fields. Exits non-zero when critical issues exceed the threshold
(default 5, set by `_CI_THRESHOLD_MAX_CRITICAL` in `main.py`). LLM analysis
uses Haiku when an API key is available; otherwise the deterministic checks
run alone.

### SEC EDGAR value-check (optional)

```bash
python main.py path/to/model.xlsx --ticker NVDA
```

Or enter a ticker in the Streamlit app's **Ticker (optional)** field. When a
ticker is supplied, historical cells whose labels match a set of GAAP
concepts are cross-checked against SEC EDGAR XBRL company facts.

- **Phase A (Core 6 GAAP):** Revenues, NetIncomeLoss, Assets, Liabilities,
  CashAndCashEquivalentsAtCarryingValue, NetCashProvidedByUsedInOperatingActivities.
- **Phase B (Extended):** adds GrossProfit, OperatingIncomeLoss, ProfitLoss,
  StockholdersEquity, LongTermDebtNoncurrent, EPS variants, CapEx, plus a
  derived Free Cash Flow and a derived total long-term debt check.
- Filters out prior-year comparatives, non-GAAP labels, and segment/quarterly
  sheets; tries multiple scale buckets (1, 1e3, 1e6, 1e9 USD); downgrades
  inconclusive matches from Critical to Medium to keep noise low.

Requires the `requests` library (already in `requirements.txt`). Per SEC
fair-use policy, set `MODELLENS_EDGAR_UA` to a contact email before calling
the EDGAR API — the default User-Agent is a placeholder and the SEC will
reject it. The check is opt-in; omit `--ticker` to skip it entirely.

```bash
export MODELLENS_EDGAR_UA="ModelLens/1.0 (you@example.com)"
```

---

## How It Works

The audit runs in four phases:

```
╔═══════════════════════════════════════════════════════════╗
║                      EXCEL FILE                           ║
║               .xlsx workbook upload                       ║
╚═══════════════════════════════╤═══════════════════════════╝
                                ▼
┌─ PHASE 1 ── Ingestion ───────────────────────────────────┐
│  Dual-state loading (values + formulas)                   │
└───────────────────────────────┬───────────────────────────┘
                                ▼
┌─ PHASE 2 ── Dependency Graph ────────────────────────────┐
│  networkx DAG of cell references and cross-sheet flows    │
└───────────────────────────────┬───────────────────────────┘
                                ▼
┌─ PHASE 3 ── Audit Checks ───────────────────────────────┐
│  Deterministic heuristics (plugs, BS integrity, refs)     │
└───────────────────────────────┬───────────────────────────┘
                                ▼
┌─ PHASE 4 ── Reporting ──────────────────────────────────┐
│  Complexity score, issue catalog, remediation             │
│  (PDF memo + Excel datatape)                              │
└──────────────────────────────────────────────────────────┘
```

1. **Ingestion** — Loads the workbook twice: once for calculated values, once for raw formulas. This enables both numerical checks and logical tracing.

2. **Dependency graph** — Parses every formula into a directed graph using networkx. Each cell is a node; each reference is an edge. This reveals circular references, orphaned cells, and cross-sheet data flows.

3. **Audit checks** — Three core checks run against the graph and values:
   - **Hard-coded plugs** — Rows where most cells are formulas but some projection-period cells are constants (analysts overriding the model).
   - **Balance sheet integrity** — Checks that Assets = Liabilities + Equity across all projection periods (tolerance: ±$1).
   - **Broken/external references** — Detects `#REF!`, `#NAME?`, `#DIV/0!`, and links to external files.

4. **Reporting** — Produces a complexity score (1–5 based on sheet count, formula density, and interdependency), a PDF memo, and an Excel datatape with all findings. Each report is stamped with a run fingerprint of the form `YYYYMMDD_HHMMSS-<sha8>` (first 8 hex chars of SHA-256 over the issue list) embedded in the PDF footer and Excel metadata — useful for comparing two runs of the same model for drift.

### LLM Layer (Optional)

```
┌─ CONTROL ── Audit Engine ────────────────────────────────┐
│  Deterministic checks (heuristic-based)                   │
└───────────────────────────────┬───────────────────────────┘
                                ▼
┌─ REASONING ── LLM Analyzer ─────────────────────────────┐
│  Narrative summary of findings (scoped, no advice)        │
└───────────────────────────────┬───────────────────────────┘
                                ▼
┌─ DECISION ── Human Review ──────────────────────────────┐
│  Final review of audit results + LLM narrative            │
└──────────────────────────────────────────────────────────┘
```

The LLM receives audit findings and produces narrative summaries. The AI judge (`eval/ai_judge.py`) supports an optional `thinking_budget` parameter for extended thinking, and LLM analyzer response parsing is thinking-block-safe (handles mixed thinking + text content blocks). System prompts ≥400 chars are automatically wrapped in `cache_control: {"type": "ephemeral"}` for Anthropic prompt caching, reducing token cost on repeated calls. The Anthropic path uses a `tool_use` call (`produce_model_analysis`) for structured output with a retry-on-malformed-response loop (max 2 retries) — no user-facing flag. The LLM is constrained at the prompt level:

- **Allowed**: explain findings, prioritize by materiality, suggest remediation, reference specific cells.
- **Disallowed**: investment recommendations, valuation opinions, price targets, data invention.

### Sample Model

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

### Financial Model Builder

The `builder/` module is an independent financial modeling library included in this repo for convenience. It does not interact with the audit engine.

It provides programmatic construction of:
- **DCF models** — scenario-weighted discounted cash flow with sensitivity tables
- **Comparable company analysis** — peer selection and implied valuation
- **Operating models** — segment-based revenue build-up with margin waterfall and working-capital projections

Each builder uses Pydantic for input validation — growth rates, cost percentages, working-capital days, and trading multiples are bounds-checked at construction — and produces structured outputs with markdown reports. Output validators flag structural issues at warning or error severity (errors fire when a model is unusable, e.g. terminal FCF ≤ 0, negative EV, or negative equity per share). See `examples/saas_dcf_walkthrough.py` for usage.

### Evaluation Framework

**Rubrics** (`eval/llm_rubrics/`) — YAML-based rubrics for grading LLM audit narratives: `safety_and_scope.yaml` (scope adherence, hallucination risk), `strategy_quality.yaml` (plausibility and proportionality of recommendations), `reasoning_fidelity.yaml` (evidence grounding, logical consistency, uncertainty calibration).

**Failure modes** (`docs/failure_modes.md`) — Catalog of 10 LLM failure patterns with detection strategies: narrative overfitting, regime anchoring, false confidence amplification, explanation-action divergence, scope creep, hallucinated causation, severity inflation, and others.

**Human review** (`human_review/`) — Reviewer guidelines and sample reviews (good / borderline / failed outputs) for calibrating human evaluators.

**Trainer tasks** (`trainer_tasks/`) — Exercises for AI trainer / RLHF evaluation: grade outputs on rubrics, identify failure modes, propose prompt or policy fixes.

### Transferability

The architecture (deterministic core → scoped LLM layer → human review → rubrics) maps to other domains. See `docs/transferability.md` for patterns in compliance, clinical decision support, fraud detection, and cybersecurity.

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| Separate reasoning from control | LLM produces text; code performs audits and report generation |
| Constrained guidance | Prompts enforce scope limits and evidence referencing |
| Evaluation of non-numeric outputs | YAML rubrics and human review guidelines |
| Failure-mode awareness | Documented patterns and targeted test cases |
| Preference for interpretability | Graph-based checks and explicit evidence paths |

## Policy

The audit engine is deterministic; the LLM is optional and constrained.

1. **Separate reasoning from control.** Code performs audits and produces reports; the LLM layer generates narrative summaries only -- it never replaces heuristic checks.
2. **No investment advice, ever.** The LLM is prompt-constrained: allowed to explain findings and suggest remediation, disallowed from investment recommendations, valuation opinions, or price targets.
3. **Graph-based interpretability.** Every finding traces to specific cells via a networkx dependency DAG -- no black-box conclusions.
4. **Dual-state loading for correctness.** Workbooks are ingested as both values and formulas so numerical checks and dependency tracing each use the appropriate representation.
5. **Failure-mode awareness built in.** Documented LLM failure patterns (narrative overfitting, false confidence amplification, hallucinated causation) have targeted detection strategies and test cases.
6. **Human review is the final gate.** Audit results and LLM narratives are artifacts for human decision-making, not autonomous conclusions.

The tool exists to structurally audit Excel financial models for hidden errors using deterministic graph analysis, with an optional scoped LLM layer that explains but never advises.

---

## Architecture

```text
excel-model-eval/
├── src/                       # Core audit engine
│   ├── ingestion.py           # Dual-state loading
│   ├── dependency.py          # Graph construction and analysis
│   ├── auditor.py             # Heuristic checks and issue catalog
│   ├── reporting.py           # PDF/Excel report generation and scoring
│   ├── llm_analyzer.py        # Optional LLM integration
│   └── edgar_validator.py     # SEC EDGAR XBRL cross-validation (Phase A+B)
├── builder/                   # Financial model builder (independent)
│   ├── dcf_builder.py         # DCF valuation engine
│   ├── comps_builder.py       # Comparable company analysis
│   ├── operating_model.py     # Revenue/cost projections
│   ├── assumptions.py         # Pydantic input schema
│   ├── validators.py          # Business logic checks
│   └── outputs.py             # Result data structures
├── eval/                      # LLM evaluation framework
│   ├── ai_judge.py            # LLM-as-judge scorer (optional thinking_budget for extended thinking)
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

## Testing

```bash
pytest tests/ -v
```

---

## Ground-truth references

Evaluation rubrics and builder templates cite vendored content at
[`references/fsp-skills/`](./references/fsp-skills/) — a verbatim copy of
the `financial-analysis` plugin from Anthropic's
[`financial-services-plugins`](https://github.com/anthropics/financial-services-plugins)
repo (Apache-2.0). The content is read-only reference material used to
anchor rubric expectations to widely-used financial-modeling conventions;
no ModelLens code loads these files at runtime. See
[`references/fsp-skills/INDEX.md`](./references/fsp-skills/INDEX.md) for
the mapping of each ModelLens component to its cited skill(s) and
[`NOTICE`](./references/fsp-skills/NOTICE) for license terms. Scores
produced by ModelLens remain probabilistic — citing a plugin skill
indicates reference material consulted, not a guarantee of compliance.

Rubric YAMLs surface these citations via an optional `external_references:`
top-level block; builder templates via an optional `fsp_reference:` block.
Both blocks are advisory and can be omitted without affecting scoring.

---

## Contributing

Under active development. Contributions welcome — areas for improvement include additional audit heuristics, workbook format support, LLM evaluation rubrics, and model builder capabilities.

## License

MIT

---

***Curiosity compounds. Rigor endures.***
