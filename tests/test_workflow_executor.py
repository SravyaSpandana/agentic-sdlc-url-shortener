import pytest

from agents.base import BaseAgent
from agents.mock_agents import (
    MockArchitectureAgent,
    MockImplementationAgent,
    MockRequirementAgent,
    MockSecurityAgent,
    MockTestAgent,
)
from orchestrator.executor import WorkflowExecutor
from orchestrator.graph import (
    TaskDefinition,
    WorkflowGraph,
)
from orchestrator.retry import RetryPolicy
from orchestrator.state import (
    WorkflowState,
    WorkflowStatus,
)


class FlakyAgent(BaseAgent):

    name = "flaky-agent"

    def __init__(self, failures_before_success: int):
        self.failures_before_success = failures_before_success
        self.attempts = 0

    async def execute(self, state):

        self.attempts += 1

        if self.attempts <= self.failures_before_success:
            raise TimeoutError(
                "Temporary failure"
            )

        return {
            "status": "PASS",
            "attempts": self.attempts,
        }


class AlwaysFailingAgent(BaseAgent):

    name = "always-failing-agent"

    async def execute(self, state):

        raise ValueError(
            "Permanent failure"
        )


@pytest.mark.asyncio
async def test_workflow_executes_in_dependency_order():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="requirements",
            agent_name="requirement-agent",
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
            dependencies=["architecture"],
        )
    )

    graph.add_task(
        TaskDefinition(
            task_id="tests",
            agent_name="test-agent",
            dependencies=[
                "security",
                "implementation",
            ],
        )
    )

    agents = {
        "requirement-agent": MockRequirementAgent(),
        "architecture-agent": MockArchitectureAgent(),
        "security-agent": MockSecurityAgent(),
        "implementation-agent": MockImplementationAgent(),
        "test-agent": MockTestAgent(),
    }

    executor = WorkflowExecutor(
        graph=graph,
        agents=agents,
    )

    state = WorkflowState(
        workflow_id="test-workflow-1",
        requirement="Build a URL shortener",
    )

    result = await executor.execute(state)

    assert result.status == WorkflowStatus.COMPLETED

    assert set(result.task_status.keys()) == {
        "requirements",
        "architecture",
        "security",
        "implementation",
        "tests",
    }

    assert all(
        status == "COMPLETED"
        for status in result.task_status.values()
    )

    assert "requirements" in result.artifacts
    assert "architecture" in result.artifacts
    assert "security" in result.artifacts
    assert "implementation" in result.artifacts
    assert "tests" in result.artifacts


@pytest.mark.asyncio
async def test_transient_failure_succeeds_after_retry():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="implementation",
            agent_name="flaky-agent",
        )
    )

    agent = FlakyAgent(
        failures_before_success=1
    )

    executor = WorkflowExecutor(
        graph=graph,
        agents={
            "flaky-agent": agent,
        },
        retry_policy=RetryPolicy(
            max_retries=2
        ),
    )

    state = WorkflowState(
        workflow_id="retry-test-1",
        requirement="Build URL shortener",
    )

    result = await executor.execute(state)

    assert result.status == WorkflowStatus.COMPLETED

    assert agent.attempts == 2

    assert result.retry_counts[
        "implementation"
    ] == 1


@pytest.mark.asyncio
async def test_retry_limit_is_respected():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="implementation",
            agent_name="always-failing-agent",
        )
    )

    agent = AlwaysFailingAgent()

    executor = WorkflowExecutor(
        graph=graph,
        agents={
            "always-failing-agent": agent,
        },
        retry_policy=RetryPolicy(
            max_retries=2
        ),
    )

    state = WorkflowState(
        workflow_id="retry-test-2",
        requirement="Build URL shortener",
    )

    with pytest.raises(
        ValueError,
        match="Permanent failure",
    ):
        await executor.execute(state)

    assert state.status == WorkflowStatus.FAILED

    # Permanent failures should NOT be retried.
    assert state.retry_counts == {}


@pytest.mark.asyncio
async def test_successful_agent_does_not_retry():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="implementation",
            agent_name="flaky-agent",
        )
    )

    agent = FlakyAgent(
        failures_before_success=0
    )

    executor = WorkflowExecutor(
        graph=graph,
        agents={
            "flaky-agent": agent,
        },
        retry_policy=RetryPolicy(
            max_retries=2
        ),
    )

    state = WorkflowState(
        workflow_id="retry-test-3",
        requirement="Build URL shortener",
    )

    result = await executor.execute(state)

    assert result.status == WorkflowStatus.COMPLETED

    assert agent.attempts == 1

    assert "implementation" not in (
        result.retry_counts
    )


@pytest.mark.asyncio
async def test_permanent_failure_is_not_retried():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="implementation",
            agent_name="permanent-failure-agent",
        )
    )

    class PermanentFailureAgent(BaseAgent):

        name = "permanent-failure-agent"

        def __init__(self):
            self.attempts = 0

        async def execute(self, state):

            self.attempts += 1

            raise ValueError(
                "Invalid generated artifact"
            )

    agent = PermanentFailureAgent()

    executor = WorkflowExecutor(
        graph=graph,
        agents={
            "permanent-failure-agent": agent,
        },
        retry_policy=RetryPolicy(
            max_retries=2
        ),
    )

    state = WorkflowState(
        workflow_id="classification-test-1",
        requirement="Build URL shortener",
    )

    with pytest.raises(
        ValueError,
        match="Invalid generated artifact",
    ):
        await executor.execute(state)

    assert agent.attempts == 1

    assert state.status == WorkflowStatus.FAILED

    assert state.retry_counts == {}

    assert (
        state.audit_events[0]["failure_type"]
        == "PERMANENT"
    )


@pytest.mark.asyncio
async def test_policy_violation_causes_safe_stop():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="security",
            agent_name="security-failure-agent",
        )
    )

    class SecurityFailureAgent(BaseAgent):

        name = "security-failure-agent"

        async def execute(self, state):

            raise PermissionError(
                "Security policy violation"
            )

    agent = SecurityFailureAgent()

    executor = WorkflowExecutor(
        graph=graph,
        agents={
            "security-failure-agent": agent,
        },
        retry_policy=RetryPolicy(
            max_retries=2
        ),
    )

    state = WorkflowState(
        workflow_id="classification-test-2",
        requirement="Build URL shortener",
    )

    with pytest.raises(
        PermissionError,
        match="Security policy violation",
    ):
        await executor.execute(state)

    assert (
        state.status
        == WorkflowStatus.SAFE_STOP
    )

    assert state.retry_counts == {}

    assert (
        state.task_status["security"]
        == "SAFE_STOP"
    )

    assert (
        state.audit_events[0]["failure_type"]
        == "POLICY_VIOLATION"
    )


@pytest.mark.asyncio
async def test_transient_failure_is_retried():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="implementation",
            agent_name="transient-failure-agent",
        )
    )

    class TransientFailureAgent(BaseAgent):

        name = "transient-failure-agent"

        def __init__(self):
            self.attempts = 0

        async def execute(self, state):

            self.attempts += 1

            if self.attempts == 1:
                raise TimeoutError(
                    "Temporary timeout"
                )

            return {
                "status": "PASS"
            }

    agent = TransientFailureAgent()

    executor = WorkflowExecutor(
        graph=graph,
        agents={
            "transient-failure-agent": agent,
        },
        retry_policy=RetryPolicy(
            max_retries=2
        ),
    )

    state = WorkflowState(
        workflow_id="classification-test-3",
        requirement="Build URL shortener",
    )

    result = await executor.execute(state)

    assert (
        result.status
        == WorkflowStatus.COMPLETED
    )

    assert agent.attempts == 2

    assert (
        result.retry_counts["implementation"]
        == 1
    )

    assert (
        result.audit_events[0]["failure_type"]
        == "TRANSIENT"
    )

@pytest.mark.asyncio
async def test_transient_failure_exhausts_retry_limit():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="implementation",
            agent_name="always-failing-transient-agent",
        )
    )

    class AlwaysFailingTransientAgent(BaseAgent):

        name = "always-failing-transient-agent"

        def __init__(self):
            self.attempts = 0

        async def execute(self, state):

            self.attempts += 1

            raise TimeoutError(
                "Service temporarily unavailable"
            )

    agent = AlwaysFailingTransientAgent()

    executor = WorkflowExecutor(
        graph=graph,
        agents={
            "always-failing-transient-agent": agent,
        },
        retry_policy=RetryPolicy(
            max_retries=2
        ),
    )

    state = WorkflowState(
        workflow_id="retry-exhaustion-test",
        requirement="Build URL shortener",
    )

    with pytest.raises(
        TimeoutError,
        match="Service temporarily unavailable",
    ):
        await executor.execute(state)

    # Initial attempt + 2 retries = 3 attempts
    assert agent.attempts == 3

    assert state.status == WorkflowStatus.FAILED

    assert (
        state.retry_counts["implementation"]
        == 2
    )

    assert (
        state.audit_events[-1]["failure_type"]
        == "TRANSIENT"
    )