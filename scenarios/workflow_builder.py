
from agents.mock_agents import (
    MockArchitectureAgent,
    MockImplementationAgent,
    MockRequirementAgent,
    MockSecurityAgent,
    MockTestAgent,
)
from agents.base import BaseAgent
from orchestrator.graph import TaskDefinition, WorkflowGraph
from scenarios.definitions import get_scenario


class ScenarioWorkflowBuilder:
    """Build a workflow graph and agent registry for a scenario."""

    def build(self, scenario_name: str):
        scenario = get_scenario(scenario_name)

        graph = WorkflowGraph()

        # Reuse deterministic mock agents for reliable demonstrations.
        agents: dict[str, BaseAgent] = {
            "requirement-agent": MockRequirementAgent(),
            "architecture-agent": MockArchitectureAgent(),
            "security-agent": MockSecurityAgent(),
            "implementation-agent": MockImplementationAgent(),
            "test-agent": MockTestAgent(),
        }

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
                    task_id="security",
                    agent_name="security-agent",
                    dependencies=["architecture"],
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
