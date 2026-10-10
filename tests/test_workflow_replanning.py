import pytest

from agents.base import BaseAgent
from orchestrator.executor import WorkflowExecutor
from orchestrator.graph import TaskDefinition, WorkflowGraph
from orchestrator.state import WorkflowState, WorkflowStatus


class CountingAgent(BaseAgent):
    def __init__(self, name):
        self.name = name
        self.calls = 0

    async def execute(self, state):
        self.calls += 1
        return {
            "agent": self.name,
            "execution": self.calls,
        }


@pytest.mark.asyncio
async def test_replanning_reruns_affected_tasks_only():
    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="requirements",
            agent_name="requirements-agent",
        )
    )
    graph.add_task(
        TaskDefinition(
            task_id="architecture",
            agent_name="architecture-agent",
            dependencies=["requirements"],
        )
    )
    graph.add_task(
        TaskDefinition(
            task_id="security",
            agent_name="security-agent",
            dependencies=["architecture"],
        )
    )
    graph.add_task(
        TaskDefinition(
            task_id="implementation",
            agent_name="implementation-agent",
            dependencies=["security"],
        )
    )
    graph.add_task(
        TaskDefinition(
            task_id="tests",
            agent_name="test-agent",
            dependencies=["implementation"],
        )
    )

    agents = {
        name: CountingAgent(name)
        for name in [
            "requirements-agent",
            "architecture-agent",
            "security-agent",
            "implementation-agent",
            "test-agent",
        ]
    }

    executor = WorkflowExecutor(graph=graph, agents=agents)

    state = WorkflowState(
        workflow_id="replanning-integration-test",
        requirement="Build a secure URL shortener",
    )

    # First run: execute the complete workflow.
    result = await executor.execute(state)

    assert result.status == WorkflowStatus.COMPLETED

    assert agents["requirements-agent"].calls == 1
    assert agents["architecture-agent"].calls == 1

    # Second run: architecture changed, so invalidate it and
    # every downstream task that depends on its output.
    result = await executor.replan_and_resume(
        state=result,
        affected_tasks=[
            "architecture",
            "security",
            "implementation",
            "tests",
        ],
        reason="Security review requires an architecture change",
    )

    assert result.status == WorkflowStatus.COMPLETED

    # Unaffected work must not run again.
    assert agents["requirements-agent"].calls == 1

    # Affected work must run again.
    assert agents["architecture-agent"].calls == 2
    assert agents["security-agent"].calls == 2
    assert agents["implementation-agent"].calls == 2
    assert agents["test-agent"].calls == 2

    # Replanning must be traceable.
    assert any(
        event["event"] == "WORKFLOW_REPLANNED"
        for event in result.audit_events
    )