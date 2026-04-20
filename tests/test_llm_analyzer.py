"""
Tests for src/llm_analyzer.py — LLMAnalyzer (Phase 1A changes)

Verifies:
1. Anthropic call path uses tool_use
2. Retry-with-error-feedback fires on malformed tool response
3. Existing public interface (analyze / analyze_findings_with_llm) is unchanged
4. OpenAI call path
5. Prompt truncation at MAX_PROMPT_ISSUES
"""

from __future__ import annotations

import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Ensure repo root is on path
REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Stub anthropic if absent
# ---------------------------------------------------------------------------

def _ensure_anthropic_stub():
    if "anthropic" not in sys.modules:
        stub = types.ModuleType("anthropic")
        stub.Anthropic = MagicMock()
        sys.modules["anthropic"] = stub

_ensure_anthropic_stub()


# ---------------------------------------------------------------------------
# Stub openai if absent
# ---------------------------------------------------------------------------

def _ensure_openai_stub():
    if "openai" not in sys.modules:
        stub = types.ModuleType("openai")
        stub.OpenAI = MagicMock()
        sys.modules["openai"] = stub

_ensure_openai_stub()

# Force availability flags then import
import src.llm_analyzer as llm_mod

llm_mod.ANTHROPIC_AVAILABLE = True
llm_mod.OPENAI_AVAILABLE = True

from src.llm_analyzer import LLMAnalyzer, analyze_findings_with_llm

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ISSUES = [
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
        "detail": "Balance Sheet does not balance. Variance: $5,000.",
    },
]

VALID_TOOL_INPUT = {
    "executive_summary": "Two issues found: a plug in DCF and a balance sheet imbalance.",
    "critical_issues": [
        {
            "location": "BalanceSheet",
            "finding": "Balance sheet does not balance.",
            "impact": "Model outputs are unreliable.",
        }
    ],
    "high_priority_items": [
        {
            "location": "DCF!Row14",
            "finding": "Hard-coded value in projection row.",
            "impact": "Assumptions do not flow through correctly.",
        }
    ],
    "medium_priority_items": [],
    "recommended_next_steps": [
        "Trace balance sheet imbalance to root cause.",
        "Replace hard-coded plug in DCF!Row14 with formula.",
    ],
}


def _make_tool_use_response(tool_input: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.input = tool_input
    response = MagicMock()
    response.content = [block]
    return response


def _make_text_response(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "message"
    block.text = text
    # Not a tool_use block
    response = MagicMock()
    response.content = [block]
    return response


def _make_analyzer() -> LLMAnalyzer:
    """Build an LLMAnalyzer with a mocked Anthropic client (no real API key needed)."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer.provider = "anthropic"
        analyzer.model = "claude-sonnet-4-20250514"
        analyzer.client = MagicMock()
        return analyzer


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLLMAnalyzerToolUse(unittest.TestCase):

    def test_tool_use_structured_output(self):
        """
        The Anthropic call path must use tool_use:
        - tools= must include the produce_model_analysis schema
        - tool_choice= must force that specific tool
        """
        analyzer = _make_analyzer()
        analyzer.client.messages.create.return_value = _make_tool_use_response(VALID_TOOL_INPUT)

        result = analyzer.analyze(SAMPLE_ISSUES, model_name="TestModel", complexity_score=3)

        self.assertIn("analysis", result)
        self.assertIsInstance(result["analysis"], str)
        self.assertGreater(len(result["analysis"]), 0)

        # Inspect how messages.create was called
        call_kwargs = analyzer.client.messages.create.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]

        # tools= must be present and contain produce_model_analysis
        tools = kwargs.get("tools", [])
        tool_names = [t.get("name") for t in tools]
        self.assertIn("produce_model_analysis", tool_names)

        # tool_choice must force the specific tool
        tool_choice = kwargs.get("tool_choice", {})
        self.assertEqual(tool_choice.get("type"), "tool")
        self.assertEqual(tool_choice.get("name"), "produce_model_analysis")

    def test_retry_on_malformed_tool_response(self):
        """
        When the first response is missing required fields, the analyzer must retry
        and append error feedback to the messages before the second call.
        """
        # First response: missing 'recommended_next_steps'
        incomplete_input = {k: v for k, v in VALID_TOOL_INPUT.items()
                            if k != "recommended_next_steps"}

        analyzer = _make_analyzer()
        analyzer.client.messages.create.side_effect = [
            _make_tool_use_response(incomplete_input),
            _make_tool_use_response(VALID_TOOL_INPUT),
        ]

        result = analyzer.analyze(SAMPLE_ISSUES, model_name="TestModel", complexity_score=3)

        # Should have called the API twice (initial + 1 retry)
        self.assertEqual(analyzer.client.messages.create.call_count, 2)
        self.assertIn("analysis", result)
        # Second call must have more messages than the first (error feedback appended)
        first_call_msgs = analyzer.client.messages.create.call_args_list[0]
        second_call_msgs = analyzer.client.messages.create.call_args_list[1]
        first_msgs = (first_call_msgs.kwargs or first_call_msgs[1]).get("messages", [])
        second_msgs = (second_call_msgs.kwargs or second_call_msgs[1]).get("messages", [])
        self.assertGreater(len(second_msgs), len(first_msgs),
                           "Retry must append error feedback to messages")

    def test_backward_compat_existing_interface_unchanged(self):
        """
        The public interface of LLMAnalyzer.analyze() and analyze_findings_with_llm()
        must be unchanged:
        - Returns dict with 'analysis' (str) and 'metadata' (dict)
        - metadata contains: provider, model, issue_count, critical_count,
                             high_count, medium_count
        - Empty issues returns no-issue message without calling the API
        """
        analyzer = _make_analyzer()
        analyzer.client.messages.create.return_value = _make_tool_use_response(VALID_TOOL_INPUT)

        # --- Non-empty issues ---
        result = analyzer.analyze(SAMPLE_ISSUES, model_name="MyModel", complexity_score=4)

        self.assertIn("analysis", result)
        self.assertIn("metadata", result)
        self.assertIsInstance(result["analysis"], str)

        meta = result["metadata"]
        self.assertEqual(meta["provider"], "anthropic")
        self.assertEqual(meta["issue_count"], 2)
        self.assertIn("critical_count", meta)
        self.assertIn("high_count", meta)
        self.assertIn("medium_count", meta)
        self.assertEqual(meta["critical_count"], 1)
        self.assertEqual(meta["high_count"], 1)
        self.assertEqual(meta["medium_count"], 0)

        # --- Empty issues — no API call ---
        analyzer.client.messages.create.reset_mock()
        empty_result = analyzer.analyze([], model_name="Empty", complexity_score=1)

        self.assertIn("analysis", empty_result)
        self.assertIn("No issues were identified", empty_result["analysis"])
        analyzer.client.messages.create.assert_not_called()

        # --- analyze_findings_with_llm convenience wrapper ---
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("src.llm_analyzer.LLMAnalyzer") as MockAnalyzer:
                mock_instance = MagicMock()
                mock_instance.analyze.return_value = {
                    "analysis": "Test analysis",
                    "metadata": {"provider": "anthropic", "model": "x", "issue_count": 1},
                }
                MockAnalyzer.return_value = mock_instance

                conv_result = analyze_findings_with_llm(
                    SAMPLE_ISSUES, "ConvModel", complexity_score=2, provider="anthropic"
                )

        self.assertIsNotNone(conv_result)
        self.assertIn("analysis", conv_result)


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------

def _make_openai_response(content: str) -> MagicMock:
    """Build a mock OpenAI ChatCompletion response."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_openai_analyzer() -> LLMAnalyzer:
    """Build an LLMAnalyzer with a mocked OpenAI client."""
    analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
    analyzer.provider = "openai"
    analyzer.model = "gpt-4o"
    analyzer.client = MagicMock()
    return analyzer


def _make_issues(n: int, severity: str = "Medium") -> list[dict]:
    """Generate n identical issues with the given severity."""
    return [
        {
            "type": "Test Issue",
            "severity": severity,
            "location": f"Sheet1!R{i}",
            "detail": f"Issue {i}",
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# OpenAI tests (Gap 23)
# ---------------------------------------------------------------------------

class TestOpenAI(unittest.TestCase):

    def test_openai_call_returns_content(self):
        """_call_openai returns the message content string."""
        analyzer = _make_openai_analyzer()
        analyzer.client.chat.completions.create.return_value = _make_openai_response(
            "Test analysis"
        )
        result = analyzer._call_openai("prompt text")
        self.assertEqual(result, "Test analysis")

    def test_openai_analyze_end_to_end(self):
        """Full analyze() with provider='openai' returns analysis + metadata."""
        analyzer = _make_openai_analyzer()
        analyzer.client.chat.completions.create.return_value = _make_openai_response(
            "Full analysis text"
        )
        result = analyzer.analyze(SAMPLE_ISSUES, model_name="OAIModel", complexity_score=3)
        self.assertIn("analysis", result)
        self.assertIn("metadata", result)
        self.assertEqual(result["analysis"], "Full analysis text")
        self.assertEqual(result["metadata"]["provider"], "openai")

    def test_openai_empty_issues(self):
        """Empty issues list returns canned response, no API call."""
        analyzer = _make_openai_analyzer()
        result = analyzer.analyze([], model_name="Empty", complexity_score=1)
        self.assertIn("No issues were identified", result["analysis"])
        analyzer.client.chat.completions.create.assert_not_called()


# ---------------------------------------------------------------------------
# Prompt truncation tests (Gap 15)
# ---------------------------------------------------------------------------

class TestPromptTruncation(unittest.TestCase):

    def test_prompt_truncation_caps_at_50(self):
        """200 issues are capped to MAX_PROMPT_ISSUES; prompt contains truncation note."""
        from src.llm_analyzer import MAX_PROMPT_ISSUES

        analyzer = _make_openai_analyzer()
        analyzer.client.chat.completions.create.return_value = _make_openai_response(
            "Truncated analysis"
        )
        issues = _make_issues(200)
        result = analyzer.analyze(issues, model_name="Big", complexity_score=3)

        self.assertTrue(result["metadata"]["prompt_truncated"])
        self.assertEqual(result["metadata"]["prompt_issue_count"], MAX_PROMPT_ISSUES)
        self.assertEqual(result["metadata"]["issue_count"], 200)
        # Verify the truncation note was in the prompt sent to the API
        call_kwargs = analyzer.client.chat.completions.create.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        user_msg = kwargs["messages"][-1]["content"]
        self.assertIn(f"top {MAX_PROMPT_ISSUES} of 200 total issues", user_msg)

    def test_prompt_truncation_preserves_critical(self):
        """Critical issues sort before Medium when truncated."""

        analyzer = _make_openai_analyzer()
        analyzer.client.chat.completions.create.return_value = _make_openai_response(
            "Sorted analysis"
        )
        critical_issues = _make_issues(30, severity="Critical")
        medium_issues = _make_issues(30, severity="Medium")
        all_issues = medium_issues + critical_issues  # Medium first in input

        result = analyzer.analyze(all_issues, model_name="Sort", complexity_score=3)

        self.assertTrue(result["metadata"]["prompt_truncated"])
        # All 30 Critical should be in the prompt (since 30 < 50)
        call_kwargs = analyzer.client.chat.completions.create.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        user_msg = kwargs["messages"][-1]["content"]
        self.assertIn("Critical Issues (30)", user_msg)

    def test_truncation_does_not_mutate_input(self):
        """The caller's original issue list must not be modified."""
        analyzer = _make_openai_analyzer()
        analyzer.client.chat.completions.create.return_value = _make_openai_response(
            "Analysis"
        )
        issues = _make_issues(100)
        original_len = len(issues)
        analyzer.analyze(issues, model_name="Mut", complexity_score=2)
        self.assertEqual(len(issues), original_len)


if __name__ == "__main__":
    unittest.main()
