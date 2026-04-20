# ground-truth references — `fsp-skills`

Vendored copy of the `financial-analysis` plugin from Anthropic's
[financial-services-plugins](https://github.com/anthropics/financial-services-plugins)
repo, used as ground-truth reference material for ModelLens evaluation
rubrics. See `NOTICE` for license and `VERSION.txt` for the exact upstream
commit.

Content under `skills/` and `commands/` is never executed by ModelLens — it
is read-only reference material cited from rubric and builder-template YAML
files via optional `external_references` / `fsp_reference` fields.

## Skills (9)

- `skills/3-statements/SKILL.md` — integrated income statement / balance sheet / cash flow model
- `skills/check-deck/SKILL.md` — pitch-deck QA and consistency review
- `skills/check-model/SKILL.md` — Excel model structural and consistency review
- `skills/competitive-analysis/SKILL.md` — competitor benchmarking and peer positioning
- `skills/comps-analysis/SKILL.md` — trading comparables analysis and implied valuation
- `skills/dcf-model/SKILL.md` — discounted cash flow model construction and assumptions
- `skills/lbo-model/SKILL.md` — leveraged buyout model with debt schedule and returns
- `skills/ppt-template-creator/SKILL.md` — PowerPoint branded layout authoring *(not currently cited — deferred)*
- `skills/skill-creator/SKILL.md` — meta-skill for authoring new skills *(not currently cited — out of scope)*

## Commands (8)

- `commands/3-statements.md`
- `commands/check-deck.md`
- `commands/competitive-analysis.md`
- `commands/comps.md`
- `commands/dcf.md`
- `commands/debug-model.md`
- `commands/lbo.md`
- `commands/ppt-template.md` *(not currently cited — deferred)*

## Mapping — which ModelLens component cites which reference

| ModelLens component | Plugin skill(s) | Plugin command(s) |
|---|---|---|
| `builder/dcf_builder.py` + `builder/templates/dcf_defaults.yaml` | `dcf-model` | `dcf.md` |
| `builder/comps_builder.py` + `builder/templates/comps_peers.yaml` | `comps-analysis`, `competitive-analysis` | `comps.md`, `competitive-analysis.md` |
| `builder/operating_model.py` | `3-statements` | `3-statements.md` |
| (eval-only, no builder counterpart) | `lbo-model` | `lbo.md` |
| `src/auditor.py` (issue explanations) | `check-model` | `debug-model.md` |
| `eval/llm_rubrics/strategy_quality.yaml` | `check-model`, `dcf-model` | `debug-model.md` |
| `eval/llm_rubrics/reasoning_fidelity.yaml` | `check-model`, `3-statements` | `debug-model.md`, `3-statements.md` |
| `eval/llm_rubrics/safety_and_scope.yaml` | — (ModelLens-owned safety surface) | — |

## Deferred

- `ppt-template-creator/` and `commands/ppt-template.md` are copied for
  completeness but **not cited** by any ModelLens rubric or template. They
  support a future layout-teaching workstream (teaching ModelLens a firm's
  branded report format) that is intentionally out of scope for this
  integration. When that workstream lands, it will plug into
  `src/reporting.py`.
- `skill-creator/` is a meta-skill for authoring new skills and is not
  relevant to ModelLens evaluation.

## Updating

This directory is a vendored snapshot, not a live mirror. To re-vendor
against a newer upstream commit:

1. Pull the latest `financial-services-plugins` clone.
2. Replace `skills/` and `commands/` with `cp -R` from
   `financial-analysis/`.
3. Update `VERSION.txt` (new `upstream_sha`, `upstream_date`,
   `vendored_on`).
4. Run `pytest tests/test_fsp_references.py -v` to confirm cited paths
   still resolve.
5. Review this `INDEX.md` and each rubric / template `external_references`
   / `fsp_reference` block for new or removed skills.
