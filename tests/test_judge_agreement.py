"""Tests for eval/judge_agreement.py — ModelAnalysisAgreement.

No network access required; all computations are pure Python text matching.
"""

from __future__ import annotations

import unittest

from eval.judge_agreement import EMEAgreementResult, ModelAnalysisAgreement


def _make_findings(issue_types: list[str]) -> dict:
    """Build a minimal audit_findings dict with the given issue types."""
    return {
        "issues": [
            {"type": t, "severity": "High", "location": "Sheet1!A1", "detail": "test"}
            for t in issue_types
        ]
    }


class TestEMEAgreementResultFields(unittest.TestCase):
    """Test 1: EMEAgreementResult has all required fields."""

    def test_agreement_result_has_required_fields(self) -> None:
        result = EMEAgreementResult(
            issue_mention_rate=0.85,
            false_positive_rate=0.1,
            n_auditor_issues=7,
            n_ai_issues=8,
            warning="",
        )
        self.assertIsInstance(result.issue_mention_rate, float)
        self.assertIsInstance(result.false_positive_rate, float)
        self.assertIsInstance(result.n_auditor_issues, int)
        self.assertIsInstance(result.n_ai_issues, int)
        self.assertIsInstance(result.warning, str)
        self.assertEqual(result.issue_mention_rate, 0.85)
        self.assertEqual(result.n_auditor_issues, 7)


class TestMentionRateComputation(unittest.TestCase):
    """Test 2: mention_rate and false_positive_rate computed correctly."""

    def test_full_mention_rate(self) -> None:
        """AI text mentions all auditor issue types."""
        agreement = ModelAnalysisAgreement()
        findings = _make_findings(["Hard-coded Plug", "External Link"])
        analysis = (
            "The model contains several hard-coded values inserted as plugs. "
            "Additionally, an external link to another workbook was detected."
        )
        result = agreement.compare(findings, analysis)
        self.assertAlmostEqual(result.issue_mention_rate, 1.0, places=4)
        self.assertEqual(result.n_auditor_issues, 2)

    def test_partial_mention_rate(self) -> None:
        """AI text mentions 1 of 2 issue types."""
        agreement = ModelAnalysisAgreement()
        findings = _make_findings(["Hard-coded Plug", "Circular Reference"])
        analysis = "The model has a hardcoded value on row 12."
        result = agreement.compare(findings, analysis)
        # Only Hard-coded Plug mentioned, not Circular Reference.
        self.assertAlmostEqual(result.issue_mention_rate, 0.5, places=4)

    def test_false_positive_rate(self) -> None:
        """AI mentions issue type not in auditor findings."""
        agreement = ModelAnalysisAgreement()
        findings = _make_findings(["Hard-coded Plug"])
        # AI mentions circular reference which auditor did not flag.
        analysis = "The model has a circular reference in its interest calc. Also hardcoded values."
        result = agreement.compare(findings, analysis)
        # AI found: Hard-coded Plug + Circular Reference = 2 issue types, 1 not in auditor.
        self.assertGreater(result.false_positive_rate, 0.0)
        self.assertLessEqual(result.false_positive_rate, 1.0)

    def test_empty_findings_no_ai_mentions(self) -> None:
        """No auditor issues, AI says nothing relevant — rate trivially 1.0."""
        agreement = ModelAnalysisAgreement()
        findings = _make_findings([])
        analysis = "The model appears structurally sound. No issues detected."
        result = agreement.compare(findings, analysis)
        self.assertAlmostEqual(result.issue_mention_rate, 1.0, places=4)
        self.assertEqual(result.n_auditor_issues, 0)
        self.assertEqual(result.warning, "")


class TestWarningTriggered(unittest.TestCase):
    """Test 3: warning is populated when mention_rate < 0.7."""

    def test_warning_triggered_below_threshold(self) -> None:
        agreement = ModelAnalysisAgreement()
        # 4 issue types, AI mentions only 1 → mention_rate = 0.25 < 0.7.
        findings = _make_findings([
            "Hard-coded Plug",
            "External Link",
            "Circular Reference",
            "Accounting Mismatch",
        ])
        analysis = "The model has a hardcoded value on row 12."
        result = agreement.compare(findings, analysis)
        self.assertLess(result.issue_mention_rate, 0.7)
        self.assertNotEqual(result.warning, "")
        self.assertIn("threshold", result.warning.lower())

    def test_no_warning_above_threshold(self) -> None:
        agreement = ModelAnalysisAgreement()
        findings = _make_findings(["Hard-coded Plug"])
        analysis = "Several hard-coded plugs were identified in projection rows."
        result = agreement.compare(findings, analysis)
        self.assertGreaterEqual(result.issue_mention_rate, 0.7)
        self.assertEqual(result.warning, "")

    def test_no_auditor_issues_no_ai_mentions_no_warning(self) -> None:
        agreement = ModelAnalysisAgreement()
        result = agreement.compare(_make_findings([]), "The model looks fine.")
        self.assertEqual(result.warning, "")


if __name__ == "__main__":
    unittest.main()
