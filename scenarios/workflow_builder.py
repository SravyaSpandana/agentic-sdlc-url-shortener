from agents.base import BaseAgent
from agents.mock_agents import (
    MockArchitectureAgent,
    MockImplementationAgent,
    MockRequirementAgent,
    MockSecurityAgent,
    MockTestAgent,
    MockRiskAnalysisAgent,
)
from orchestrator.graph import TaskDefinition, WorkflowGraph
from scenarios.definitions import get_scenario
from llm.config import load_settings
from llm.gemini_client import GeminiModelClient
from agents.gemini_agents import (
    GeminiArchitectureAgent,
    GeminiRequirementAgent,
    GeminiSecurityAgent,
    GeminiRiskAnalysisAgent
)

class ScenarioWorkflowBuilder:
    """Build a workflow graph and agent registry for a scenario."""

    def __init__(self, provider: str = "mock"):
        if provider not in {"mock", "gemini"}:
            raise ValueError(
                "provider must be either 'mock' or 'gemini'."
            )
        self.provider = provider

    def build(self, scenario_name: str):
        scenario = get_scenario(scenario_name)

        graph = WorkflowGraph()

        if self.provider == "gemini":
            settings = load_settings()

            if settings.provider != "gemini":
                raise ValueError(
                    "Set LLM_PROVIDER=gemini in .env "
                    "to enable Gemini agents."
                )

            client = GeminiModelClient(settings)

            agents: dict[str, BaseAgent] = {
                "requirement-agent": GeminiRequirementAgent(client),
                "architecture-agent": GeminiArchitectureAgent(client),
                "security-agent": GeminiSecurityAgent(client),
                "implementation-agent": MockImplementationAgent(),
                "test-agent": MockTestAgent(),
                "risk-analysis-agent": GeminiRiskAnalysisAgent(client),
            }
        else:
            agents: dict[str, BaseAgent] = {
                "requirement-agent": MockRequirementAgent(),
                "architecture-agent": MockArchitectureAgent(),
                "security-agent": MockSecurityAgent(),
                "implementation-agent": MockImplementationAgent(),
                "test-agent": MockTestAgent(),
                "risk-analysis-agent": MockRiskAnalysisAgent(),
            }

        # Keep your existing greenfield, brownfield, and
        # ambiguous task definitions below this point unchanged.
        if scenario_name == "greenfield":        
            tasks = [
                TaskDefinition(
                    task_id="requirements",
                    agent_name="requirement-agent",
                ),
                TaskDefinition(
                    task_id="architecture",
                    agent_name="architecture-agent",
                    dependencies=["requirements"],
                ),
                TaskDefinition(
                    task_id="risk_analysis",
                    agent_name="risk-analysis-agent",
                    dependencies=["requirements"],
                ),
                TaskDefinition(
                    task_id="security",
                    agent_name="security-agent",
                    dependencies=["architecture", "risk_analysis"],
                ),
                TaskDefinition(
                    task_id="implementation",
                    agent_name="implementation-agent",
                    dependencies=["security"],
                    requires_approval=True,
                    critical=True,
                    metadata={
                        "approval_reason":
                            "Approve implementation before execution"
                    },
                ),
                TaskDefinition(
                    task_id="tests",
                    agent_name="test-agent",
                    dependencies=["implementation"],
                ),
            ]


        elif scenario_name == "brownfield":
            tasks = [
                TaskDefinition(
                    task_id="codebase_analysis",
                    agent_name="requirement-agent",
                ),
                TaskDefinition(
                    task_id="impact_analysis",
                    agent_name="architecture-agent",
                    dependencies=["codebase_analysis"],
                ),
                TaskDefinition(
                    task_id="security",
                    agent_name="security-agent",
                    dependencies=["impact_analysis"],
                ),
                TaskDefinition(
                    task_id="implementation",
                    agent_name="implementation-agent",
                    dependencies=["security"],
                    requires_approval=True,
                    critical=True,
                    metadata={
                        "approval_reason":
                            "Approve backward-compatible changes"
                    },
                ),
                TaskDefinition(
                    task_id="regression_tests",
                    agent_name="test-agent",
                    dependencies=["implementation"],
                ),
            ]

        else:  # ambiguous
            tasks = [
                TaskDefinition(
                    task_id="requirements",
                    agent_name="requirement-agent",
                ),
                TaskDefinition(
                    task_id="ambiguity_analysis",
                    agent_name="architecture-agent",
                    dependencies=["requirements"],
                ),
                TaskDefinition(
                    task_id="security",
                    agent_name="security-agent",
                    dependencies=["ambiguity_analysis"],
                ),
                TaskDefinition(
                    task_id="implementation",
                    agent_name="implementation-agent",
                    dependencies=["security"],
                    requires_approval=True,
                    critical=True,
                    metadata={
                        "approval_reason":
                            "Confirm assumptions before implementation"
                    },
                ),
                TaskDefinition(
                    task_id="tests",
                    agent_name="test-agent",
                    dependencies=["implementation"],
                ),
            ]

        for task in tasks:
            graph.add_task(task)

        graph.validate()

        return scenario, graph, agents