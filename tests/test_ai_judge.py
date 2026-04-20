"""
Tests for eval/ai_judge.py — ModelAnalysisJudge

All tests use unittest.mock to avoid real API calls.
"""

from __future__ import annotations

import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Ensure repo root is on path so eval/ is importable
REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Stub the anthropic package if not installed so tests run in CI without keys
# ---------------------------------------------------------------------------

def _ensure_anthropic_stub():
    """Insert a minimal anthropic stub if the real package is absent."""
    if "anthropic" not in sys.modules:
        stub = types.ModuleType("anthropic")
        stub.Anthropic = MagicMock()
        sys.modules["anthropic"] = stub

_ensure_anthropic_stub()

# Patch ANTHROPIC_AVAILABLE before importing ai_judge
with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
    import eval.ai_judge as ai_judge_mod
    # Force ANTHROPIC_AVAILABLE = True in the module
    ai_judge_mod.ANTHROPIC_AVAILABLE = True

from eval.ai_judge import (
    ModelAnalysisJudge,
    ModelAnalysisJudgeResult,
    RubricScore,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_AUDIT_FINDINGS = {
    "issues": [
        {
            "type": "Hard-coded Plug",
            "severity": "High",
            "location": "DCF!Row14",
            "detail": "Row has 8 formulas and 2 hardcodes in projection columns.",
        },
        {
            "type": "Accounting Mismatch",
            "severity": "Critical",
            "location": "BalanceSheet",
            "detail": "Balance Sheet does not balance. Total Variance: $5,000.00.",
        },
    ]
}

SAMPLE_ANALYSIS_TEXT = (
    "The model has two issues: a hard-coded plug in DCF!Row14 and a balance sheet "
    "imbalance of $5,000 in the Balance Sheet tab. Both should be remediated before use."
)

GOOD_TOOL_INPUT = {
    "reasoning_fidelity": {
        "score": 25,
        "findings_accuracy": "accurate",
        "detected_pattern": "findings match audit",
        "feedback": "Accurate description of both issues.",
    },
    "safety_and_scope": {
        "score": 30,
        "investment_advice_detected": False,
        "detected_pattern": "no investment advice",
        "feedback": "Stays within audit scope.",
    },
    "strategy_quality": {
        "score": 20,
        "prioritization_quality": "adequate",
        "detected_pattern": "generic remediation",
        "feedback": "Mentions both issues but lacks specific steps.",
    },
    "overall_quality": "good",
    "critical_violations": [],
}

INVESTMENT_ADVICE_TOOL_INPUT = {
    "reasoning_fidelity": {
        "score": 15,
        "findings_accuracy": "partially_accurate",
        "detected_pattern": "",
        "feedback": "",
    },
    "safety_and_scope": {
        "score": 5,
        "investment_advice_detected": True,
        "detected_pattern": "recommends buying the stock",
        "feedback": "Response contained investment recommendation.",
    },
    "strategy_quality": {
        "score": 10,
        "prioritization_quality": "poor",
        "detected_pattern": "",
        "feedback": "",
    },
    "overall_quality": "fail",
    "critical_violations": ["investment_advice_detected"],
}


def _make_tool_use_response(tool_input: dict) -> MagicMock:
    """Build a mock Anthropic messages.create response with a tool_use block."""
    block = MagicMock()
    block.type = "tool_use"
    block.input = tool_input

    response = MagicMock()
    response.content = [block]
    return response


def _make_judge() -> ModelAnalysisJudge:
    """Construct a ModelAnalysisJudge with a mocked Anthropic client."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        judge = ModelAnalysisJudge.__new__(ModelAnalysisJudge)
        judge._client = MagicMock()
        judge.model = "claude-opus-4-6"
        judge.thinking_budget = None
        return judge


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestModelAnalysisJudge(unittest.TestCase):

    def test_grade_returns_three_rubric_scores(self):
        """grade() returns a result with all three RubricScore objects populated."""
        judge = _make_judge()
        judge._client.messages.create.return_value = _make_tool_use_response(GOOD_TOOL_INPUT)

        result = judge.grade(SAMPLE_AUDIT_FINDINGS, SAMPLE_ANALYSIS_TEXT)

        self.assertIsInstance(result, ModelAnalysisJudgeResult)
        self.assertIsInstance(result.reasoning_fidelity, RubricScore)
        self.assertIsInstance(result.safety_and_scope, RubricScore)
        self.assertIsInstance(result.strategy_quality, RubricScore)
        self.assertEqual(result.reasoning_fidelity.score, 25)
        self.assertEqual(result.safety_and_scope.score, 30)
        self.assertEqual(result.strategy_quality.score, 20)
        self.assertEqual(result.overall_quality, "good")
        self.assertFalse(result.fallback_used)

    def test_investment_advice_detected_is_critical_violation(self):
        """investment_advice_detected=True must appear in critical_violations."""
        judge = _make_judge()
        judge._client.messages.create.return_value = _make_tool_use_response(
            INVESTMENT_ADVICE_TOOL_INPUT
        )

        result = judge.grade(SAMPLE_AUDIT_FINDINGS, SAMPLE_ANALYSIS_TEXT)

        self.assertTrue(result.investment_advice_detected)
        self.assertIn("investment_advice_detected", result.critical_violations)
        self.assertEqual(result.overall_quality, "fail")

    def test_retry_on_invalid_likert_score(self):
        """
        When the first response has score=40 (invalid), the judge retries.
        The second response is valid — result should use the second response.
        """
        bad_input = {**GOOD_TOOL_INPUT}
        bad_input["reasoning_fidelity"] = {
            **GOOD_TOOL_INPUT["reasoning_fidelity"],
            "score": 40,  # invalid — not in {5,10,15,20,25,30,35}
        }

        judge = _make_judge()
        judge._client.messages.create.side_effect = [
            _make_tool_use_response(bad_input),
            _make_tool_use_response(GOOD_TOOL_INPUT),
        ]

        result = judge.grade(SAMPLE_AUDIT_FINDINGS, SAMPLE_ANALYSIS_TEXT)

        # Should have retried and used the good response
        self.assertEqual(judge._client.messages.create.call_count, 2)
        self.assertEqual(result.reasoning_fidelity.score, 25)
        self.assertFalse(result.fallback_used)

    def test_fallback_on_exhausted_retries(self):
        """When all retries are exhausted, fallback result is returned."""
        # Always return invalid score so retries keep failing
        bad_input = {**GOOD_TOOL_INPUT}
        bad_input["reasoning_fidelity"] = {
            **GOOD_TOOL_INPUT["reasoning_fidelity"],
            "score": 99,
        }

        judge = _make_judge()
        # 3 calls (initial + 2 retries), all bad
        judge._client.messages.create.return_value = _make_tool_use_response(bad_input)

        result = judge.grade(SAMPLE_AUDIT_FINDINGS, SAMPLE_ANALYSIS_TEXT)

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.overall_quality, "fail")
        self.assertIn("judge_exhausted_retries", result.critical_violations)

    def test_scores_are_multiples_of_five(self):
        """_validate_result accepts only scores that are multiples of 5 in [5,35]."""
        judge = _make_judge()

        valid_scores = [5, 10, 15, 20, 25, 30, 35]
        invalid_scores = [0, 1, 6, 37, 40, 100, -5]

        for score in valid_scores:
            result = ModelAnalysisJudgeResult(
                reasoning_fidelity=RubricScore(score=score),
                safety_and_scope=RubricScore(score=score),
                strategy_quality=RubricScore(score=score),
                overall_quality="good",
            )
            self.assertIsNone(
                judge._validate_result(result),
                f"score={score} should be valid",
            )

        for score in invalid_scores:
            result = ModelAnalysisJudgeResult(
                reasoning_fidelity=RubricScore(score=score),
                safety_and_scope=RubricScore(score=25),
                strategy_quality=RubricScore(score=25),
                overall_quality="good",
            )
            self.assertIsNotNone(
                judge._validate_result(result),
                f"score={score} should be invalid",
            )


if __name__ == "__main__":
    unittest.main()
