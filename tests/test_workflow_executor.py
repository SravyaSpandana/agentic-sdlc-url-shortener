import pytest
import asyncio

from orchestrator.graph import TaskDefinition, WorkflowGraph
from orchestrator.state import WorkflowState, WorkflowStatus

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

    assert state.status == WorkflowStatus.COMPLETED

    # The task failed once, then recovered.
    assert executor.metrics.retries == 1
    assert executor.metrics.task_failures == 1

    # Confirm the retry is visible in the audit trail.
    assert any(
        event["event"] == "TASK_FAILED"
        for event in state.audit_events
    )

    assert any(
        event["event"] == "TASK_RETRY"
        for event in state.audit_events
    )

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

class TrackingAgent(BaseAgent):

    name = "tracking-agent"

    def __init__(self):
        self.executed = False

    async def execute(self, state):
        self.executed = True
        return {
            "status": "COMPLETED"
        }


@pytest.mark.asyncio
async def test_approval_required_task_waits_before_execution():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="implementation",
            agent_name="tracking-agent",
            requires_approval=True,
            critical=True,
            metadata={
                "approval_reason": "Production-impacting implementation"
            },
        )
    )

    agent = TrackingAgent()

    executor = WorkflowExecutor(
        graph=graph,
        agents={
            "tracking-agent": agent
        },
    )

    state = WorkflowState(
        workflow_id="approval-integration-test",
        requirement="Build URL shortener",
    )

    result = await executor.execute(state)

    assert result.status == WorkflowStatus.WAITING_FOR_APPROVAL
    assert agent.executed is False
    assert result.task_status["implementation"] == "WAITING_FOR_APPROVAL"
    assert result.approvals[0]["status"] == "PENDING"

@pytest.mark.asyncio

@pytest.mark.asyncio
async def test_replan_and_resume_reruns_affected_tasks():
    execution_counts = {
        "requirements": 0,
        "architecture": 0,
        "implementation": 0,
    }

    class CountingAgent:
        def __init__(self, name):
            self.name = name

        async def execute(self, state):
            execution_counts[self.name] += 1
            return {
                "task": self.name,
                "run": execution_counts[self.name],
            }

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="requirements",
            agent_name="requirements",
        )
    )
    graph.add_task(
        TaskDefinition(
            task_id="architecture",
            agent_name="architecture",
            dependencies=["requirements"],
        )
    )
    graph.add_task(
        TaskDefinition(
            task_id="implementation",
            agent_name="implementation",
            dependencies=["architecture"],
        )
    )

    agents = {
        name: CountingAgent(name)
        for name in execution_counts
    }

    executor = WorkflowExecutor(
        graph=graph,
        agents=agents,
    )

    state = WorkflowState(
        workflow_id="replan-resume-test",
        requirement="Build URL shortener",
    )

    # Simulate a previously completed workflow.
    for task_id in graph.tasks:
        state.task_status[task_id] = "COMPLETED"
        state.artifacts[task_id] = {
            "old_result": task_id,
        }

    result = await executor.replan_and_resume(
        state=state,
        affected_tasks=["architecture"],
        reason="Architecture requirements changed",
    )

    assert result.status == WorkflowStatus.COMPLETED

    # Unaffected work should not execute again.
    assert execution_counts["requirements"] == 0

    # The changed task and its downstream dependent must rerun.
    assert execution_counts["architecture"] == 1
    assert execution_counts["implementation"] == 1

    assert executor.metrics.replans == 1

    assert any(
        event["event"] == "WORKFLOW_REPLANNED"
        for event in result.audit_events
    )

    assert result.artifacts["architecture"]["run"] == 1
    assert result.artifacts["implementation"]["run"] == 1

def test_independent_tasks_run_in_parallel_and_synchronize():
    async def run_test():
        both_started = asyncio.Event()
        started = set()

        class ParallelAgent(BaseAgent):
            def __init__(self, task_name):
                self.task_name = task_name

            async def execute(self, state):
                started.add(self.task_name)

                if len(started) == 2:
                    both_started.set()

                # Both branches must start before either can finish.
                await asyncio.wait_for(
                    both_started.wait(), timeout=2
                )

                return {"task": self.task_name}

        class JoinAgent(BaseAgent):
            async def execute(self, state):
                # Both upstream artifacts must exist before this runs.
                assert "branch_a" in state.artifacts
                assert "branch_b" in state.artifacts

                return {"synchronized": True}

        graph = WorkflowGraph()
        graph.add_task(TaskDefinition(task_id="start", agent_name="start"))
        graph.add_task(TaskDefinition(
            task_id="branch_a",
            agent_name="branch_a",
            dependencies=["start"],
        ))
        graph.add_task(TaskDefinition(
            task_id="branch_b",
            agent_name="branch_b",
            dependencies=["start"],
        ))
        graph.add_task(TaskDefinition(
            task_id="join",
            agent_name="join",
            dependencies=["branch_a", "branch_b"],
        ))

        class StartAgent(BaseAgent):
            async def execute(self, state):
                return {"ready": True}

        agents = {
            "start": StartAgent(),
            "branch_a": ParallelAgent("branch_a"),
            "branch_b": ParallelAgent("branch_b"),
            "join": JoinAgent(),
        }

        state = WorkflowState(
            workflow_id="parallel-test",
            requirement="Verify parallel execution",
        )

        result = await WorkflowExecutor(graph, agents).execute(state)

        assert result.status == WorkflowStatus.COMPLETED
        assert started == {"branch_a", "branch_b"}
        assert result.artifacts["join"]["synchronized"] is True

    asyncio.run(run_test())
