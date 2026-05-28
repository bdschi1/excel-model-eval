"""
LLM Analyzer Module

Generates narrative analysis of audit findings using an LLM.
Supports both Anthropic (Claude) and OpenAI APIs.

The LLM's role is strictly bounded:
- Analyze and explain findings (reasoning)
- DO NOT make investment recommendations (control stays with humans)
- Ground all claims in the actual audit data
- Express appropriate uncertainty

Phase 1A change: Anthropic call path uses tool_use for guaranteed structured
output. A retry-with-error-feedback loop (max 2 retries) handles malformed
responses. The existing public interface is unchanged.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

MAX_PROMPT_ISSUES = 50

# API clients - imported conditionally
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def _format_system(system: str | None) -> list[dict] | str | None:
    """Wrap system prompts >= 400 chars with cache_control for prompt caching."""
    if not system or len(system) < 400:
        return system
    return [
        {
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }
    ]


# ---------------------------------------------------------------------------
# System prompt (unchanged from original)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a financial model audit analyst. Your role is to analyze audit findings and provide clear, actionable explanations.

## Your Scope (DO)
- Explain what each finding means in plain language
- Describe the potential impact on model reliability
- Prioritize findings by materiality
- Suggest specific remediation steps
- Acknowledge uncertainty where appropriate

## Out of Scope (DO NOT)
- Make investment recommendations ("buy", "sell", "undervalued")
- Opine on whether the company is a good investment
- Invent data not present in the findings
- Provide valuation conclusions
- Make predictions about stock price or company performance

## Response Format
Structure your analysis as:
1. Executive Summary (2-3 sentences)
2. Critical Issues (if any)
3. High Priority Items
4. Medium Priority Items
5. Recommended Next Steps

Be specific. Reference the actual locations and details from the findings.
Express confidence levels: "definitely" only for verified facts, "likely/may" for inferences.
"""


# ---------------------------------------------------------------------------
# Tool schema for structured Anthropic output
# ---------------------------------------------------------------------------

_ANALYSIS_TOOL: dict = {
    "name": "produce_model_analysis",
    "description": (
        "Produce a structured narrative analysis of Excel model audit findings. "
        "All fields must be grounded in the provided findings — do not invent data."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": "2-3 sentence summary of overall model health and top concerns.",
            },
            "critical_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "finding": {"type": "string"},
                        "impact": {"type": "string"},
                    },
                    "required": ["location", "finding", "impact"],
                },
                "description": "Critical-severity findings with location, finding text, and impact.",
            },
            "high_priority_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "finding": {"type": "string"},
                        "impact": {"type": "string"},
                    },
                    "required": ["location", "finding", "impact"],
                },
            },
            "medium_priority_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "finding": {"type": "string"},
                        "impact": {"type": "string"},
                    },
                    "required": ["location", "finding", "impact"],
                },
            },
            "recommended_next_steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of concrete remediation steps.",
            },
        },
        "required": [
            "executive_summary",
            "critical_issues",
            "high_priority_items",
            "medium_priority_items",
            "recommended_next_steps",
        ],
    },
}

# Validation: required top-level fields in tool output
_REQUIRED_ANALYSIS_FIELDS = {
    "executive_summary",
    "critical_issues",
    "high_priority_items",
    "medium_priority_items",
    "recommended_next_steps",
}


# ---------------------------------------------------------------------------
# Prompt builder (unchanged logic)
# ---------------------------------------------------------------------------

def create_findings_prompt(issues: list, model_name: str, complexity_score: int) -> str:
    """Format audit findings into a prompt for the LLM."""

    # Group issues by severity
    critical = [i for i in issues if i.get('severity', '').lower() == 'critical']
    high = [i for i in issues if i.get('severity', '').lower() == 'high']
    medium = [i for i in issues if i.get('severity', '').lower() == 'medium']

    prompt = f"""Analyze the following audit findings for the financial model: {model_name}
Model Complexity Score: {complexity_score}/5

## Audit Findings

### Critical Issues ({len(critical)})
"""
    for i in critical:
        prompt += f"- **{i['type']}** at `{i['location']}`: {i['detail']}\n"

    prompt += f"\n### High Severity ({len(high)})\n"
    for i in high:
        prompt += f"- **{i['type']}** at `{i['location']}`: {i['detail']}\n"

    prompt += f"\n### Medium Severity ({len(medium)})\n"
    for i in medium:
        prompt += f"- **{i['type']}** at `{i['location']}`: {i['detail']}\n"

    prompt += """
## Your Task
Provide a narrative analysis of these findings suitable for a senior investment professional.
Focus on materiality and actionability. Be specific about locations and impacts.
"""

    return prompt


def _structured_to_narrative(structured: dict) -> str:
    """Convert structured tool output to the narrative string expected by callers."""
    parts: list[str] = []

    summary = structured.get("executive_summary", "")
    if summary:
        parts.append(f"## Executive Summary\n{summary}")

    critical = structured.get("critical_issues", [])
    if critical:
        parts.append("## Critical Issues")
        for item in critical:
            parts.append(
                f"- **{item.get('location', 'Unknown')}**: {item.get('finding', '')} "
                f"— Impact: {item.get('impact', '')}"
            )

    high = structured.get("high_priority_items", [])
    if high:
        parts.append("## High Priority Items")
        for item in high:
            parts.append(
                f"- **{item.get('location', 'Unknown')}**: {item.get('finding', '')} "
                f"— Impact: {item.get('impact', '')}"
            )

    medium = structured.get("medium_priority_items", [])
    if medium:
        parts.append("## Medium Priority Items")
        for item in medium:
            parts.append(
                f"- **{item.get('location', 'Unknown')}**: {item.get('finding', '')} "
                f"— Impact: {item.get('impact', '')}"
            )

    steps = structured.get("recommended_next_steps", [])
    if steps:
        parts.append("## Recommended Next Steps")
        for idx, step in enumerate(steps, 1):
            parts.append(f"{idx}. {step}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# LLMAnalyzer
# ---------------------------------------------------------------------------

class LLMAnalyzer:
    """
    Generates LLM-powered narrative analysis of audit findings.

    Supports:
    - Anthropic Claude (preferred) — uses tool_use for structured output
    - OpenAI GPT-4

    Set API key via environment variable:
    - ANTHROPIC_API_KEY for Claude
    - OPENAI_API_KEY for GPT-4
    """

    def __init__(self, provider: str = "anthropic") -> None:
        """
        Initialize the analyzer.

        Args:
            provider: "anthropic" or "openai"
        """
        self.provider = provider.lower()
        self.client = None
        self.model: Optional[str] = None

        if self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7")

        elif self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.client = openai.OpenAI(api_key=api_key)
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o")  # update when model is deprecated
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'anthropic' or 'openai'")

    def _truncate_issues(self, issues: list) -> tuple[list, bool]:
        """Priority-weighted truncation: Critical > High > Medium."""
        if len(issues) <= MAX_PROMPT_ISSUES:
            return list(issues), False
        severity_order = {"Critical": 0, "High": 1, "Medium": 2}
        sorted_issues = sorted(
            issues, key=lambda i: severity_order.get(i.get("severity", ""), 3)
        )
        return sorted_issues[:MAX_PROMPT_ISSUES], True

    def analyze(
        self,
        issues: list,
        model_name: str = "Unknown",
        complexity_score: int = 3,
        grade: bool = False,
    ) -> dict:
        """
        Generate narrative analysis of audit findings.

        Args:
            issues: List of issue dictionaries from ModelAuditor
            model_name: Name of the model being audited
            complexity_score: Complexity score (1-5)
            grade: If True, also grade the produced analysis via ModelAnalysisJudge
                   (requires ANTHROPIC_API_KEY regardless of provider)

        Returns:
            dict with 'analysis' (str) and 'metadata' (dict).
            When grade=True, adds 'grade' key with ModelAnalysisJudgeResult.
        """
        if not issues:
            result = {
                "analysis": (
                    "No issues were identified in this model. "
                    "The audit found no critical, high, or medium severity findings."
                ),
                "metadata": {
                    "provider": self.provider,
                    "model": self.model,
                    "issue_count": 0,
                    "prompt_truncated": False,
                    "prompt_issue_count": 0,
                },
            }
            if grade:
                result["grade"] = None
            return result

        original_count = len(issues)
        prompt_issues, was_truncated = self._truncate_issues(issues)
        prompt = create_findings_prompt(prompt_issues, model_name, complexity_score)

        if was_truncated:
            prompt += (
                f"\n\n**Note:** Showing top {MAX_PROMPT_ISSUES} of "
                f"{original_count} total issues by severity.\n"
            )

        if self.provider == "anthropic":
            analysis_text = self._call_anthropic(prompt)
        else:
            analysis_text = self._call_openai(prompt)

        result = {
            "analysis": analysis_text,
            "metadata": {
                "provider": self.provider,
                "model": self.model,
                "issue_count": len(issues),
                "critical_count": len(
                    [i for i in issues if i.get('severity', '').lower() == 'critical']
                ),
                "high_count": len(
                    [i for i in issues if i.get('severity', '').lower() == 'high']
                ),
                "medium_count": len(
                    [i for i in issues if i.get('severity', '').lower() == 'medium']
                ),
                "prompt_truncated": was_truncated,
                "prompt_issue_count": len(prompt_issues),
            },
        }

        if grade:
            result["grade"] = self.grade_analysis(
                issues=issues,
                analysis_text=analysis_text,
            )

        return result

    def grade_analysis(
        self,
        issues: list,
        analysis_text: str,
    ) -> object:
        """
        Grade the analysis using ModelAnalysisJudge.

        Requires ANTHROPIC_API_KEY (judge always uses Anthropic regardless of
        the analyzer's provider setting).

        Returns ModelAnalysisJudgeResult, or None if judge is unavailable.
        """
        try:
            # Import here to avoid circular imports; eval/ is not on default path
            import pathlib
            import sys
            repo_root = pathlib.Path(__file__).parent.parent
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
            from eval.ai_judge import ModelAnalysisJudge  # type: ignore
            judge = ModelAnalysisJudge()
            return judge.grade(
                audit_findings={"issues": issues},
                analysis_text=analysis_text,
            )
        except Exception as exc:
            logger.warning("Grading failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Anthropic — tool_use path with retry-with-error-feedback
    # ------------------------------------------------------------------

    def _call_anthropic(self, prompt: str, max_retries: int = 2) -> str:
        """
        Call Anthropic Claude API using tool_use for structured output.

        Falls back to plain text response if all retries fail.
        """
        messages: list[dict] = [{"role": "user", "content": prompt}]
        last_error: Optional[str] = None

        for attempt in range(max_retries + 1):
            if last_error and attempt > 0:
                # Retry-with-error-feedback: append the validation error
                messages = messages + [
                    {
                        "role": "assistant",
                        "content": (
                            f"[previous attempt had a validation error: {last_error}]"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Your previous response failed validation: {last_error}. "
                            "Please call produce_model_analysis again with all required fields present."
                        ),
                    },
                ]

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    system=_format_system(SYSTEM_PROMPT),
                    tools=[_ANALYSIS_TOOL],
                    tool_choice={"type": "tool", "name": "produce_model_analysis"},
                    messages=messages,
                )
            except (anthropic.APIError, anthropic.APIConnectionError,
                    anthropic.RateLimitError, anthropic.APIStatusError) as exc:
                last_error = str(exc)
                continue

            # Extract tool_use block
            tool_input: Optional[dict] = None
            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    tool_input = block.input
                    break

            if tool_input is None:
                last_error = "No tool_use block in response"
                continue

            # Validate required fields present
            missing = _REQUIRED_ANALYSIS_FIELDS - set(tool_input.keys())
            if missing:
                last_error = f"Missing required fields: {missing}"
                continue

            # Success — convert to narrative string
            return _structured_to_narrative(tool_input)

        # All retries exhausted — best-effort plain text fallback
        try:
            fallback = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=_format_system(SYSTEM_PROMPT),
                messages=[{"role": "user", "content": prompt}],
            )
            text = next((b.text for b in fallback.content if b.type == "text"), "")
            return text or "[Analysis unavailable: empty fallback response]"
        except (anthropic.APIError, anthropic.APIConnectionError,
                anthropic.RateLimitError, anthropic.APIStatusError):
            return (
                "[Analysis unavailable: structured output failed after retries "
                f"and fallback also failed. Last error: {last_error}]"
            )

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API (plain text, unchanged)."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content
        except (openai.APIError, openai.APIConnectionError,
                openai.RateLimitError) as exc:
            return f"[Analysis unavailable: OpenAI API error: {exc}]"


# ---------------------------------------------------------------------------
# Convenience function (backward-compatible, interface unchanged)
# ---------------------------------------------------------------------------

def analyze_findings_with_llm(
    issues: list,
    model_name: str = "Unknown",
    complexity_score: int = 3,
    provider: str = "anthropic",
    audit_id: str = None,
) -> Optional[dict]:
    """
    Convenience function to analyze findings with LLM.

    Returns None if API key not configured (graceful degradation).

    Args:
        issues: List of issue dictionaries
        model_name: Name of model being audited
        complexity_score: Complexity score (1-5)
        provider: "anthropic" or "openai"
        audit_id: Optional identifier for correlating log messages

    Returns:
        dict with analysis results, or None if LLM not available
    """
    _audit_id = audit_id or ""

    # Check if API key is available
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        return None
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        logger.info("[%s] Starting LLM analysis with provider=%s", _audit_id, provider)
        analyzer = LLMAnalyzer(provider=provider)
        result = analyzer.analyze(issues, model_name, complexity_score)
        logger.info("[%s] LLM analysis complete", _audit_id)
        return result
    except Exception as e:
        logger.error("[%s] LLM analysis failed (%s): %s", _audit_id, type(e).__name__, e)
        return None
