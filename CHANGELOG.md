# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] - 2026-02-16

### Added
- Dual-state Excel ingestion engine (values + formulas in parallel)
- Networkx-based dependency graph construction with circular reference detection
- Audit checks: hard-coded forecast entries, balance sheet consistency, external file references
- PDF memo and Excel datatape report generation
- 1-5 complexity scoring from graph topology and formula density
- Streamlit dashboard for upload, visualization, and report download
- Optional LLM narrative layer (Claude and GPT-4) with prompt-level safety constraints
- YAML rubrics for grading LLM outputs (strategy quality, reasoning fidelity, safety/scope)
- Human review guidelines and sample reviews
- Trainer tasks for AI evaluator exercises
- Sample model: BOBWEIR Pharmaceuticals (7-sheet workbook with intentional issues)
