"""Judge agreement metrics for excel-model-eval.

Compares ModelAnalysisJudge (AI narrative grader) vs ModelAuditor (deterministic
heuristic) on the same workbook.

Because the AI judge grades narrative quality while the auditor detects structural
issues, direct score comparison is not meaningful. Instead, this module measures:

  - issue_mention_rate: fraction of auditor-detected issues mentioned in the AI
    analysis (recall from the auditor's perspective).
  - false_positive_rate: fraction of AI-mentioned issues NOT in the auditor
    findings (precision complement).

Warns when issue_mention_rate < 0.7 (AI is missing >30% of known issues).

# module_version: 1.0.0
# date: 2026-04-04
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# Issue type keywords used for text-matching in the AI analysis narrative.
# Keys are canonical auditor issue types; values are search terms.
_ISSUE_KEYWORDS: dict[str, list[str]] = {
    "External Link": ["external link", "external reference", "external file", "broken link"],
    "Calculation Error": [
        "calculation error", "#ref", "#name", "#value", "#div/0", "error cell",
        "formula error",
    ],
    "Hard-coded Plug": [
        "hard-coded", "hardcoded", "hard coded", "plug", "manual override",
        "hardcode",
    ],
    "Accounting Mismatch": [
        "accounting mismatch", "balance sheet imbalance", "does not balance",
        "balance check fails", "imbalance",
    ],
    "Circular Reference": [
        "circular reference", "circular ref", "circularity",
    ],
}

# Default fallback: use the issue type string itself as a keyword.
_FALLBACK_MATCH_THRESHOLD = 0.7  # mention_rate threshold


@dataclass
class EMEAgreementResult:
    """Overlap metrics between AI analysis and auditor findings."""

    issue_mention_rate: float    # fraction of auditor issues mentioned by AI
    false_positive_rate: float   # fraction of AI issues not in auditor findings
    n_auditor_issues: int
    n_ai_issues: int
    warning: str = ""


class ModelAnalysisAgreement:
    """Measures how well the AI analysis covers deterministic auditor findings.

    Since the AI judge and the auditor measure different things (narrative
    quality vs structural issues), Cohen's kappa is not applicable. Instead,
    this class measures recall (how many auditor issues the AI mentions) and
    precision complement (how many AI issue mentions have no auditor support).

    Usage::

        from eval.judge_agreement import ModelAnalysisAgreement

        agreement = ModelAnalysisAgreement()
        result = agreement.compare(
            audit_findings={"issues": [{"type": "Hard-coded Plug", ...}]},
            ai_analysis_text="The model contains several hard-coded values...",
        )
        print(result.issue_mention_rate)   # e.g. 0.85
        print(result.false_positive_rate)  # e.g. 0.10
    """

    MENTION_RATE_WARN_THRESHOLD = 0.7  # warn if AI misses >30% of auditor issues

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare(
        self,
        audit_findings: dict,
        ai_analysis_text: str,
    ) -> EMEAgreementResult:
        """Compare AI analysis coverage against auditor findings.

        Args:
            audit_findings: Output from ModelAuditor.run_all_checks() — either
                a list of issue dicts or a dict with an ``"issues"`` key. Each
                issue dict must have a ``"type"`` key (e.g. "Hard-coded Plug").
            ai_analysis_text: Free-text narrative produced by LLMAnalyzer.

        Returns:
            EMEAgreementResult with mention_rate and false_positive_rate.
        """
        issues = self._normalise_findings(audit_findings)
        analysis_lower = ai_analysis_text.lower()

        if not issues:
            # No auditor findings — agreement trivially satisfied.
            n_ai = self._count_ai_issue_types(analysis_lower)
            fpr = 1.0 if n_ai > 0 else 0.0
            warning = ""
            if n_ai > 0:
                warning = (
                    "Auditor found no issues but AI analysis mentions issue-related terms. "
                    "Consider whether the AI is generating unsupported findings."
                )
                logger.warning(warning)
            return EMEAgreementResult(
                issue_mention_rate=1.0,
                false_positive_rate=fpr,
                n_auditor_issues=0,
                n_ai_issues=n_ai,
                warning=warning,
            )

        # Deduplicate by issue type for rate computation.
        auditor_types = list({iss.get("type", "") for iss in issues if iss.get("type")})
        n_auditor = len(auditor_types)

        # Count how many auditor issue types are mentioned in the AI text.
        mentioned = 0
        for issue_type in auditor_types:
            if self._is_mentioned(issue_type, analysis_lower):
                mentioned += 1

        mention_rate = mentioned / n_auditor if n_auditor > 0 else 1.0

        # Count distinct AI-mentioned issue types not in auditor findings.
        all_known_types = set(auditor_types)
        n_ai_issues = 0
        false_positives = 0
        for iss_type, keywords in _ISSUE_KEYWORDS.items():
            if self._text_matches_keywords(analysis_lower, keywords):
                n_ai_issues += 1
                if iss_type not in all_known_types:
                    false_positives += 1

        fpr = false_positives / n_ai_issues if n_ai_issues > 0 else 0.0

        warning = ""
        if mention_rate < self.MENTION_RATE_WARN_THRESHOLD:
            warning = (
                f"AI analysis mentions only {mention_rate:.1%} of auditor-detected issues "
                f"(threshold: {self.MENTION_RATE_WARN_THRESHOLD:.1%}). "
                "The AI analysis may be under-reporting structural problems found by the auditor."
            )
            logger.warning(warning)

        return EMEAgreementResult(
            issue_mention_rate=mention_rate,
            false_positive_rate=fpr,
            n_auditor_issues=n_auditor,
            n_ai_issues=n_ai_issues,
            warning=warning,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_findings(audit_findings: dict | list) -> list[dict]:
        """Normalise audit_findings to a list of issue dicts."""
        if isinstance(audit_findings, list):
            return audit_findings
        if isinstance(audit_findings, dict):
            val = audit_findings.get("issues", audit_findings)
            if isinstance(val, list):
                return val
        return []

    @staticmethod
    def _is_mentioned(issue_type: str, text_lower: str) -> bool:
        """Check if an auditor issue type is referenced in the AI text.

        Uses the _ISSUE_KEYWORDS lookup if available, otherwise falls back
        to the issue type string itself (lowercased).
        """
        keywords = _ISSUE_KEYWORDS.get(issue_type)
        if keywords:
            return ModelAnalysisAgreement._text_matches_keywords(text_lower, keywords)
        # Fallback: simple substring match on lowercased type name.
        return issue_type.lower() in text_lower

    @staticmethod
    def _text_matches_keywords(text_lower: str, keywords: list[str]) -> bool:
        """Return True if any keyword appears in the lowercased text."""
        return any(kw in text_lower for kw in keywords)

    def _count_ai_issue_types(self, text_lower: str) -> int:
        """Count how many distinct issue-type categories appear in the AI text."""
        count = 0
        for keywords in _ISSUE_KEYWORDS.values():
            if self._text_matches_keywords(text_lower, keywords):
                count += 1
        return count
