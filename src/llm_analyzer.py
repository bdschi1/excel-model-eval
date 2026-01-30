"""
LLM Analyzer Module

Generates narrative analysis of audit findings using an LLM.
Supports both Anthropic (Claude) and OpenAI APIs.

The LLM's role is strictly bounded:
- Analyze and explain findings (reasoning)
- DO NOT make investment recommendations (control stays with humans)
- Ground all claims in the actual audit data
- Express appropriate uncertainty
"""

import os
import json
from typing import Optional

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


# System prompt defining the LLM's role and boundaries
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


class LLMAnalyzer:
    """
    Generates LLM-powered narrative analysis of audit findings.

    Supports:
    - Anthropic Claude (preferred)
    - OpenAI GPT-4

    Set API key via environment variable:
    - ANTHROPIC_API_KEY for Claude
    - OPENAI_API_KEY for GPT-4
    """

    def __init__(self, provider: str = "anthropic"):
        """
        Initialize the analyzer.

        Args:
            provider: "anthropic" or "openai"
        """
        self.provider = provider.lower()
        self.client = None
        self.model = None

        if self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = "claude-sonnet-4-20250514"

        elif self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.client = openai.OpenAI(api_key=api_key)
            self.model = "gpt-4-turbo-preview"
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'anthropic' or 'openai'")

    def analyze(self, issues: list, model_name: str = "Unknown",
                complexity_score: int = 3) -> dict:
        """
        Generate narrative analysis of audit findings.

        Args:
            issues: List of issue dictionaries from ModelAuditor
            model_name: Name of the model being audited
            complexity_score: Complexity score (1-5)

        Returns:
            dict with 'analysis' (str) and 'metadata' (dict)
        """
        if not issues:
            return {
                "analysis": "No issues were identified in this model. The audit found no critical, high, or medium severity findings.",
                "metadata": {
                    "provider": self.provider,
                    "model": self.model,
                    "issue_count": 0
                }
            }

        prompt = create_findings_prompt(issues, model_name, complexity_score)

        if self.provider == "anthropic":
            response = self._call_anthropic(prompt)
        else:
            response = self._call_openai(prompt)

        return {
            "analysis": response,
            "metadata": {
                "provider": self.provider,
                "model": self.model,
                "issue_count": len(issues),
                "critical_count": len([i for i in issues if i.get('severity', '').lower() == 'critical']),
                "high_count": len([i for i in issues if i.get('severity', '').lower() == 'high']),
                "medium_count": len([i for i in issues if i.get('severity', '').lower() == 'medium'])
            }
        }

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content


def analyze_findings_with_llm(issues: list, model_name: str = "Unknown",
                               complexity_score: int = 3,
                               provider: str = "anthropic") -> Optional[dict]:
    """
    Convenience function to analyze findings with LLM.

    Returns None if API key not configured (graceful degradation).

    Args:
        issues: List of issue dictionaries
        model_name: Name of model being audited
        complexity_score: Complexity score (1-5)
        provider: "anthropic" or "openai"

    Returns:
        dict with analysis results, or None if LLM not available
    """
    # Check if API key is available
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        return None
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        analyzer = LLMAnalyzer(provider=provider)
        return analyzer.analyze(issues, model_name, complexity_score)
    except Exception as e:
        print(f"LLM analysis failed: {e}")
        return None
