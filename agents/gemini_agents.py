
import json
import re

from agents.base import BaseAgent
from llm.gemini_client import GeminiModelClient


def _parse_json_response(text: str) -> dict:
    """Parse a JSON object returned by Gemini."""
    text = text.strip()

    # Handle JSON wrapped in Markdown code fences.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Gemini returned invalid JSON."
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "Gemini response must be a JSON object."
        )

    return result


class GeminiRequirementAgent(BaseAgent):
    name = "requirement-agent"

    def __init__(self, client: GeminiModelClient):
        self.client = client

    async def execute(self, state) -> dict:
        response = await self.client.generate_text(
            system_prompt=(
                "You are a senior business analyst for a software "
                "engineering team. Analyze requirements carefully. "
                "Identify functional requirements, non-functional "
                "requirements, assumptions, and ambiguities. "
                "Do not invent facts. Return only a valid JSON object "
                "with keys: type, summary, functional_requirements, "
                "non_functional_requirements, assumptions, ambiguities."
            ),
            user_prompt=(
                "Analyze this software requirement:\n"
                f"{state.requirement}"
            ),
        )

        result = _parse_json_response(response)
        result.setdefault("type", "requirements")
        return result


class GeminiArchitectureAgent(BaseAgent):
    name = "architecture-agent"

    def __init__(self, client: GeminiModelClient):
        self.client = client

    async def execute(self, state) -> dict:
        requirements = state.artifacts.get("requirements", {})
        if not requirements:
            requirements = {"summary": state.requirement}

        response = await self.client.generate_text(
            system_prompt=(
                "You are a senior software architect. Design a "
                "practical architecture for a URL shortener using "
                "the project context and requirements provided. "
                "Consider API design, storage, redirects, validation, "
                "security, scalability, and observability. "
                "Return only a valid JSON object with keys: type, "
                "components, decisions, risks."
            ),
            user_prompt=(
                "Original requirement:\n"
                f"{state.requirement}\n\n"
                "Requirement analysis:\n"
                f"{json.dumps(requirements, default=str)}"
            ),
        )

        result = _parse_json_response(response)
        result.setdefault("type", "architecture")
        return result


class GeminiSecurityAgent(BaseAgent):
    name = "security-agent"

    def __init__(self, client: GeminiModelClient):
        self.client = client

    async def execute(self, state) -> dict:
        requirements = state.artifacts.get("requirements", {})
        architecture = state.artifacts.get("architecture", {})
        risk_analysis = state.artifacts.get("risk_analysis", {})

        response = await self.client.generate_text(
            system_prompt=(
                "You are a security reviewer assessing a URL shortener "
                "design. Review URL validation, redirect abuse, input "
                "handling, access control where applicable, sensitive "
                "data, rate limiting, and operational risks. "
                "This is a design-level review, not a verified code "
                "scan. Do not claim that vulnerabilities were tested. "
                "Return only a valid JSON object with keys: type, "
                "status, findings, recommendations. Use REVIEW_REQUIRED "
                "if important information is missing."
            ),
            user_prompt=(
                "Requirement:\n"
                f"{state.requirement}\n\n"
                "Requirements analysis:\n"
                f"{json.dumps(requirements, default=str)}\n\n"
                "Architecture:\n"
                f"{json.dumps(architecture, default=str)}"
                "\n\nIndependent risk analysis:\n"
                f"{json.dumps(risk_analysis, default=str)}"
            ),
        )

        result = _parse_json_response(response)
        result.setdefault("type", "security-review")
        return result
class GeminiRiskAnalysisAgent(BaseAgent):
    name = "risk-analysis-agent"

    def __init__(self, client: GeminiModelClient):
        self.client = client

    async def execute(self, state) -> dict:
        response = await self.client.generate_text(
            system_prompt=(
                "You are an independent software delivery risk analyst. "
                "Analyze the original requirement for delivery, reliability, "
                "operational, and data risks. Do not assume an architecture "
                "has already been selected. Return only a valid JSON object "
                "with keys: type, risks, mitigations."
            ),
            user_prompt=(
                "Analyze this software requirement:\n"
                f"{state.requirement}"
            ),
        )

        result = _parse_json_response(response)
        result.setdefault("type", "independent-risk-analysis")
        return result
