"""Tests for the vendored `references/fsp-skills/` ground-truth tree.

These checks are structural only — no LLM, no network, no filesystem writes.
They guard against drift in the vendored copy, broken citation paths in
rubric / template YAML, and backward-incompatible edits to GRADE_TOOL.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Matches either a bare or quoted `*path: <value>` line in the YAML files.
# We parse with regex rather than a YAML library because PyYAML is not a
# runtime dependency of this repo and the rubric/template YAMLs are read
# only as reference documents.
_CITATION_LINE = re.compile(
    r"^\s*(?:path|command_path|related_skill_path)\s*:\s*"
    r"(?:\"([^\"]+)\"|'([^']+)'|(\S+))\s*(?:#.*)?$",
    re.MULTILINE,
)


def _extract_cited_paths(yaml_text: str) -> list[str]:
    """Return every `path:` / `command_path:` / `related_skill_path:` value."""
    return [m.group(1) or m.group(2) or m.group(3) for m in _CITATION_LINE.finditer(yaml_text)]

REPO_ROOT = Path(__file__).resolve().parent.parent
FSP_ROOT = REPO_ROOT / "references" / "fsp-skills"

RUBRIC_FILES = [
    REPO_ROOT / "eval" / "llm_rubrics" / "strategy_quality.yaml",
    REPO_ROOT / "eval" / "llm_rubrics" / "reasoning_fidelity.yaml",
    REPO_ROOT / "eval" / "llm_rubrics" / "safety_and_scope.yaml",
]

TEMPLATE_FILES = [
    REPO_ROOT / "builder" / "templates" / "dcf_defaults.yaml",
    REPO_ROOT / "builder" / "templates" / "comps_peers.yaml",
]


# ---------------------------------------------------------------------------
# 1. Rubric `external_references` paths must resolve
# ---------------------------------------------------------------------------
def test_rubric_external_reference_paths_resolve():
    for rubric_path in RUBRIC_FILES:
        text = rubric_path.read_text()
        if "external_references:" not in text:
            continue
        # Trim to the external_references block so we don't scan other lines
        block = text.split("external_references:", 1)[1]
        cited_paths = [p for p in _extract_cited_paths(block) if p.startswith("references/fsp-skills/")]
        assert cited_paths, (
            f"{rubric_path.name}: external_references block present but no paths extracted"
        )
        for cited in cited_paths:
            resolved = REPO_ROOT / cited
            assert resolved.is_file(), (
                f"{rubric_path.name} cites {cited} but file does not exist"
            )


# ---------------------------------------------------------------------------
# 2. Template `fsp_reference` paths must resolve
# ---------------------------------------------------------------------------
def test_template_fsp_reference_paths_resolve():
    for tmpl_path in TEMPLATE_FILES:
        text = tmpl_path.read_text()
        if "fsp_reference:" not in text:
            continue
        block = text.split("fsp_reference:", 1)[1]
        cited_paths = [p for p in _extract_cited_paths(block) if p.startswith("references/fsp-skills/")]
        assert cited_paths, (
            f"{tmpl_path.name}: fsp_reference block present but no paths extracted"
        )
        for cited in cited_paths:
            resolved = REPO_ROOT / cited
            assert resolved.is_file(), (
                f"{tmpl_path.name} fsp_reference cites {cited} but file does not exist"
            )


# ---------------------------------------------------------------------------
# 3. INDEX.md mentions every vendored SKILL.md and every commands/*.md
# ---------------------------------------------------------------------------
def test_index_mentions_every_vendored_file():
    index = FSP_ROOT / "INDEX.md"
    assert index.is_file(), "references/fsp-skills/INDEX.md missing"
    index_text = index.read_text()

    for skill_md in (FSP_ROOT / "skills").glob("*/SKILL.md"):
        skill_slug = skill_md.parent.name
        assert skill_slug in index_text, (
            f"INDEX.md does not mention vendored skill '{skill_slug}'"
        )

    for cmd_md in (FSP_ROOT / "commands").glob("*.md"):
        assert cmd_md.name in index_text, (
            f"INDEX.md does not mention vendored command '{cmd_md.name}'"
        )


# ---------------------------------------------------------------------------
# 4. GRADE_TOOL input_schema still validates baseline-shaped responses
#    (consulted_references absent) and forward-compat responses (present).
# ---------------------------------------------------------------------------
def _sample_baseline_response() -> dict:
    return {
        "reasoning_fidelity": {
            "score": 30,
            "findings_accuracy": "accurate",
            "detected_pattern": "cell_level_grounding",
            "feedback": "All findings tied to audit evidence.",
        },
        "safety_and_scope": {
            "score": 35,
            "investment_advice_detected": False,
            "detected_pattern": "scoped",
            "feedback": "No investment advice.",
        },
        "strategy_quality": {
            "score": 25,
            "prioritization_quality": "good",
            "detected_pattern": "ordered_by_severity",
            "feedback": "Clear ordering; concrete steps.",
        },
        "overall_quality": "good",
        "critical_violations": [],
    }


def test_grade_tool_validates_without_consulted_references():
    jsonschema = pytest.importorskip("jsonschema")
    from eval.ai_judge import GRADE_TOOL

    jsonschema.validate(
        instance=_sample_baseline_response(),
        schema=GRADE_TOOL["input_schema"],
    )


def test_grade_tool_validates_with_consulted_references():
    jsonschema = pytest.importorskip("jsonschema")
    from eval.ai_judge import GRADE_TOOL

    resp = _sample_baseline_response()
    resp["consulted_references"] = [
        {
            "skill": "financial-analysis/dcf-model",
            "path": "references/fsp-skills/skills/dcf-model/SKILL.md",
            "rationale": "Checked against canonical DCF construction conventions.",
        },
        {"skill": "financial-analysis/check-model"},  # rationale + path optional
    ]
    jsonschema.validate(instance=resp, schema=GRADE_TOOL["input_schema"])


def test_grade_tool_required_unchanged():
    """Backward-compat guard: consulted_references must stay OPTIONAL."""
    from eval.ai_judge import GRADE_TOOL

    required = GRADE_TOOL["input_schema"]["required"]
    assert required == [
        "reasoning_fidelity",
        "safety_and_scope",
        "strategy_quality",
        "overall_quality",
    ], f"GRADE_TOOL required list changed unexpectedly: {required}"
    assert "consulted_references" not in required


# ---------------------------------------------------------------------------
# 5. Baseline regression fixture is still loadable as JSON (sanity).
# ---------------------------------------------------------------------------
def test_judge_baseline_fixture_parses():
    fixture = REPO_ROOT / "tests" / "fixtures" / "judge_baseline.json"
    assert fixture.is_file()
    data = json.loads(fixture.read_text())
    assert "baselines" in data
    assert isinstance(data["baselines"], list)
    assert len(data["baselines"]) >= 1
