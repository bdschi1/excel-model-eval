# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## What This Is

A structural analysis tool for institutional Excel-based financial models. It ingests Excel workbooks as directed acyclic graphs (DAGs) using networkx, runs deterministic audit checks (hard-coded values, balance sheet consistency, external references), and produces PDF/Excel reports with a 1-5 complexity score. An optional LLM layer (Claude or GPT-4) generates narrative summaries constrained to exclude investment advice.

## Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run
streamlit run app.py

# Tests
pytest tests/ -v

# Lint
ruff check .
```

## Architecture

- `src/ingestion.py` -- Dual-state loader: reads workbooks as both values and formulas in parallel
- `src/dependency.py` -- Builds a networkx DAG from cell references; detects circular refs and disconnected chains
- `src/auditor.py` -- Heuristic checks: hard-coded forecast entries, balance sheet imbalances, external file references
- `src/reporting.py` -- Generates PDF memo and Excel datatape; computes 1-5 complexity score from graph topology
- `src/llm_analyzer.py` -- Optional LLM integration (Anthropic/OpenAI) with prompt-level safety constraints
- `app.py` -- Streamlit frontend for upload, visualization, and report download
- `eval/llm_rubrics/` -- YAML rubrics for grading LLM narrative outputs (strategy quality, reasoning fidelity, safety/scope)

## Key Patterns

- Deterministic audit engine runs first; LLM layer is optional and additive (never replaces heuristic checks)
- LLM prompts are scoped: allowed to explain findings and suggest remediation, disallowed from investment recommendations or price targets
- Workbooks are loaded in two states (values + formulas) so numerical checks and dependency tracing use the appropriate representation
- Reports are artifacts (PDF + Excel datatape), not interactive

## Testing Conventions

- Tests live in `tests/` with a smoke test and module-specific test files (DCF builder, comps builder, operating model, validators)
- Run with `pytest tests/ -v`
- No external API calls in tests; LLM integration is optional and not tested in CI
