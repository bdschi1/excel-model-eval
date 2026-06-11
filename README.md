<!-- excel-model-eval/README.md | Last updated: 2026-06-03 -->

# ModelLens

![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![NetworkX](https://img.shields.io/badge/NetworkX-4C9A2A?style=flat)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat&logo=pydantic&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-191919?style=flat&logo=anthropic&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)
![tests](https://img.shields.io/badge/tests-371%20passing-brightgreen?style=flat)

Structural audit tool for Excel-based financial models. Reads a workbook, maps every cell and formula into a `networkx` dependency graph, runs deterministic checks for common modeling errors (hard-coded plugs, broken references, balance-sheet imbalances), and produces a PDF memo + Excel datatape. An optional LLM layer generates narrative summaries — the core audit is rule-based and runs without any API keys.

**Plain English:** Drop an Excel model in, get back a list of structural errors and where they hide. Optional Claude/GPT layer writes a plain-English summary of the findings.

Local-only.

## Run

```
# Via b-man launcher: select "ExcelEval"
# Or manually:
cd ~/code/work/bds_repos/Tier_1/excel-model-eval
source .venv/bin/activate
streamlit run app.py
python main.py path/to/model.xlsx           # CLI
python main.py path/to/model.xlsx --ci      # JSON to stdout, non-zero exit on critical count > threshold
python main.py path/to/model.xlsx --ticker NVDA   # SEC EDGAR XBRL value cross-check
```

## Install

```
cd ~/code/work/bds_repos/Tier_1/excel-model-eval
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install anthropic python-dotenv         # optional LLM layer
cp .env.example .env                        # add API key if using LLM layer
```

## Tests

```
pytest tests/ -v
```

## Notes

- Four phases: ingestion (dual-state values + formulas), `networkx` dependency graph, audit checks (hard-coded plugs, BS integrity at 0.1% tolerance / $1k floor, broken refs), reporting (PDF + Excel datatape with `YYYYMMDD_HHMMSS-<sha8>` run fingerprint).
- EDGAR check requires `MODELLENS_EDGAR_UA="ModelLens/1.0 (you@example.com)"` (SEC fair-use policy rejects the default UA). Filters prior-year comparatives, non-GAAP labels, and segment/quarterly sheets; downgrades inconclusive matches from Critical to Medium.
- LLM layer is prompt-constrained: allowed to explain findings and suggest remediation, disallowed from investment recommendations, valuation opinions, or price targets.
- Sample model at `sample_models/BOBWEIR_Model.xlsx` with an intentional revenue plug for testing.
- `builder/` module is an independent DCF / comps / operating-model library; does not interact with the audit engine.
