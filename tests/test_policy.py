from orchestrator.graph import TaskDefinition
from orchestrator.policy import PolicyDecision, PolicyGuard
from orchestrator.state import WorkflowState


def test_critical_task_without_approval_is_denied():

    guard = PolicyGuard()

    task = TaskDefinition(
        task_id="release",
        agent_name="release-agent",
        critical=True,
        requires_approval=False,
    )

    state = WorkflowState(
        workflow_id="policy-test",
        requirement="Release URL shortener",
    )

    result = guard.evaluate(task, state)

    assert result.decision == PolicyDecision.DENY

    assert "human approval" in result.reason

def test_normal_task_is_allowed():

    guard = PolicyGuard()

    task = TaskDefinition(
        task_id="architecture",
        agent_name="architecture-agent",
    )

    state = WorkflowState(
        workflow_id="policy-test-2",
        requirement="Build URL shortener",
    )

    result = guard.evaluate(task, state)

    assert result.decision == PolicyDecision.ALLOW