<!-- excel-model-eval/README.md | Last updated: 2026-06-13 -->

# ModelLens

![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![tests](https://img.shields.io/badge/tests-371%20passing-brightgreen?style=flat)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

Structural audit tool for Excel-based financial models. Reads a workbook, maps every cell and formula into a `networkx` dependency graph, runs deterministic checks for common modeling errors (hard-coded plugs, broken references, balance-sheet imbalances), and produces a PDF memo + Excel datatape. An optional LLM layer writes narrative summaries; the core audit is rule-based and runs with no API keys.

**Plain English:** Drop in an Excel model, get back a list of structural errors and where they hide.

## Install

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install anthropic python-dotenv   # optional LLM layer
cp .env.example .env                  # add API key only if using the LLM layer
```

## Usage

```
streamlit run app.py                     # UI
python main.py model.xlsx                # CLI audit
python main.py model.xlsx --ci           # JSON to stdout, non-zero exit on critical threshold
python main.py model.xlsx --ticker NVDA  # SEC EDGAR XBRL cross-check
```

EDGAR cross-check needs `MODELLENS_EDGAR_UA="ModelLens/1.0 (you@example.com)"` (SEC rejects the default UA).

## What it does

- Dual-state ingestion (values + formulas), `networkx` dependency graph
- Deterministic checks: hard-coded plugs, broken refs, balance-sheet integrity (0.1% / $1k floor)
- PDF memo + Excel datatape with a run fingerprint
- Optional LLM narrative, constrained to explaining findings (no recommendations or price targets)

## Tests

```
pytest tests/ -v
```

## License

MIT
