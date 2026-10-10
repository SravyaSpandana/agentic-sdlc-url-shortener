import asyncio

from agents.base import BaseAgent


class MockRequirementAgent(BaseAgent):

    name = "requirement-agent"

    async def execute(self, state):

        await asyncio.sleep(0.1)

        return {
            "type": "requirements",
            "summary": state.requirement,
        }


class MockArchitectureAgent(BaseAgent):

    name = "architecture-agent"

    async def execute(self, state):

        await asyncio.sleep(0.1)

        return {
            "type": "architecture",
            "components": [
                "FastAPI",
                "URL Service",
                "Repository",
                "SQLite",
            ],
        }


class MockSecurityAgent(BaseAgent):

    name = "security-agent"

    async def execute(self, state):

        await asyncio.sleep(0.1)

        return {
            "type": "security-review",
            "status": "PASS",
        }


class MockImplementationAgent(BaseAgent):

    name = "implementation-agent"

    async def execute(self, state):

        await asyncio.sleep(0.1)

        return {
            "type": "implementation",
            "status": "COMPLETED",
        }


class MockTestAgent(BaseAgent):

    name = "test-agent"

    async def execute(self, state):

        await asyncio.sleep(0.1)

        return {
            "type": "test-results",
            "status": "PASS",
        }


class MockRiskAnalysisAgent(BaseAgent):
    name = "risk-analysis-agent"

    async def execute(self, state):
        await asyncio.sleep(0.1)
        return {
            "type": "independent-risk-analysis",
            "risks": [
                "URL redirect abuse",
                "Service availability",
                "Data retention"
            ],
            "mitigations": [
                "Validate destination URLs",
                "Monitor service health",
                "Define a retention policy"
            ]
        }
