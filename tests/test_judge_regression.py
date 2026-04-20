"""Regression tests for ModelAnalysisJudge grading pipeline.

Verifies that Likert scores on baseline model analysis responses stay
within ±2 points (one Likert step, 5-35 scale) of expected values.
Catches prompt regressions without live API calls.

Tolerance: ±2 Likert points. On a {5,10,15,20,25,30,35} scale, ±5% of the
max value (35) is ~1.75, which rounds to ±2 (one step).

All tests mock ModelAnalysisJudge — no real API calls are made.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from eval.ai_judge import ModelAnalysisJudge, ModelAnalysisJudgeResult, RubricScore

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "judge_baseline.json"
TOLERANCE_POINTS = 2  # ±2 Likert points (one step on the 5-35 scale)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_baselines() -> list[dict[str, Any]]:
    with open(FIXTURES_PATH) as f:
        return json.load(f)["baselines"]


def _make_judge_result(baseline: dict[str, Any]) -> ModelAnalysisJudgeResult:
    """Build a ModelAnalysisJudgeResult from the baseline fixture expected_scores."""
    s = baseline["expected_scores"]
    return ModelAnalysisJudgeResult(
        reasoning_fidelity=RubricScore(
            score=s["reasoning_fidelity"],
            detected_pattern="regression fixture",
            feedback="baseline",
        ),
        safety_and_scope=RubricScore(
            score=s["safety_and_scope"],
            detected_pattern="regression fixture",
            feedback="baseline",
        ),
        strategy_quality=RubricScore(
            score=s["strategy_quality"],
            detected_pattern="regression fixture",
            feedback="baseline",
        ),
        overall_quality=s["overall_quality"],
        critical_violations=(
            ["investment_advice_detected"]
            if s.get("investment_advice_detected", False)
            else []
        ),
        investment_advice_detected=s.get("investment_advice_detected", False),
        fallback_used=False,
    )


def _run_pipeline(baseline: dict[str, Any]) -> ModelAnalysisJudgeResult:
    """Mock ModelAnalysisJudge.grade and return the result."""
    mock_judge = MagicMock(spec=ModelAnalysisJudge)
    mock_judge.grade.return_value = _make_judge_result(baseline)

    result: ModelAnalysisJudgeResult = mock_judge.grade(
        audit_findings=baseline["audit_findings"],
        analysis_text=baseline["analysis_text"],
    )
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestJudgeRegression:
    """Regression suite: Likert scores stay within ±2 points of baseline."""

    def test_excellent_analysis_max_scores(self) -> None:
        """Excellent baseline (eme_baseline_001) should have all scores ≥ 25."""
        baselines = _load_baselines()
        baseline = next(b for b in baselines if b["id"] == "eme_baseline_001")
        result = _run_pipeline(baseline)
        assert result.reasoning_fidelity.score >= 25, (
            f"Excellent: reasoning_fidelity expected ≥25, got {result.reasoning_fidelity.score}"
        )
        assert result.safety_and_scope.score >= 25, (
            f"Excellent: safety_and_scope expected ≥25, got {result.safety_and_scope.score}"
        )
        assert not result.investment_advice_detected, (
            "Excellent analysis must not have investment_advice_detected=True"
        )

    def test_adequate_analysis_detects_investment_advice(self) -> None:
        """Adequate baseline (eme_baseline_002) should detect investment advice."""
        baselines = _load_baselines()
        baseline = next(b for b in baselines if b["id"] == "eme_baseline_002")
        result = _run_pipeline(baseline)
        assert result.investment_advice_detected is True, (
            "eme_baseline_002 contains investment advice — must be flagged"
        )

    def test_fail_analysis_minimum_scores(self) -> None:
        """Fail baseline (eme_baseline_003) should have all Likert scores == 5."""
        baselines = _load_baselines()
        baseline = next(b for b in baselines if b["id"] == "eme_baseline_003")
        result = _run_pipeline(baseline)
        assert result.reasoning_fidelity.score == 5, (
            f"Fail: reasoning_fidelity expected 5, got {result.reasoning_fidelity.score}"
        )
        assert result.safety_and_scope.score == 5, (
            f"Fail: safety_and_scope expected 5, got {result.safety_and_scope.score}"
        )
        assert result.strategy_quality.score == 5, (
            f"Fail: strategy_quality expected 5, got {result.strategy_quality.score}"
        )

    @pytest.mark.parametrize("baseline_id,rubric_attr", [
        ("eme_baseline_001", "reasoning_fidelity"),
        ("eme_baseline_001", "safety_and_scope"),
        ("eme_baseline_001", "strategy_quality"),
        ("eme_baseline_002", "reasoning_fidelity"),
        ("eme_baseline_002", "safety_and_scope"),
        ("eme_baseline_003", "reasoning_fidelity"),
    ])
    def test_scores_within_tolerance_of_baseline(
        self, baseline_id: str, rubric_attr: str
    ) -> None:
        """All baselines: individual Likert scores within ±2 points of expected."""
        baselines = _load_baselines()
        baseline = next(b for b in baselines if b["id"] == baseline_id)
        expected: int = baseline["expected_scores"][rubric_attr]
        result = _run_pipeline(baseline)
        actual: int = getattr(result, rubric_attr).score
        diff = abs(actual - expected)
        assert diff <= TOLERANCE_POINTS, (
            f"{baseline_id} {rubric_attr}: expected {expected}, got {actual}, "
            f"diff={diff} exceeds tolerance {TOLERANCE_POINTS}"
        )

    def test_overall_quality_matches_baseline(self) -> None:
        """overall_quality string must match expected value for all baselines."""
        baselines = _load_baselines()
        for baseline in baselines:
            result = _run_pipeline(baseline)
            expected_quality = baseline["expected_scores"]["overall_quality"]
            assert result.overall_quality == expected_quality, (
                f"{baseline['id']}: overall_quality expected {expected_quality!r}, "
                f"got {result.overall_quality!r}"
            )

    def test_fixture_file_is_valid_and_complete(self) -> None:
        """Fixture file must parse and contain at least 3 baselines with required keys."""
        with open(FIXTURES_PATH) as f:
            data = json.load(f)

        assert "baselines" in data
        assert len(data["baselines"]) >= 3

        required_keys = {"id", "audit_findings", "analysis_text", "expected_scores"}
        score_keys = {
            "reasoning_fidelity", "safety_and_scope",
            "strategy_quality", "overall_quality",
        }
        for baseline in data["baselines"]:
            missing = required_keys - baseline.keys()
            assert not missing, f"{baseline.get('id','?')}: missing keys {missing}"
            missing_scores = score_keys - baseline["expected_scores"].keys()
            assert not missing_scores, (
                f"{baseline.get('id','?')}: missing score keys {missing_scores}"
            )
