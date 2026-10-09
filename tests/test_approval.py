from orchestrator.approval import ApprovalManager
from orchestrator.state import (
    WorkflowState,
    WorkflowStatus,
)


def test_approval_request_is_created():

    manager = ApprovalManager()

    state = WorkflowState(
        workflow_id="approval-test-1",
        requirement="Build URL shortener",
    )

    manager.request_approval(
        task_id="implementation",
        reason="Production-impacting change",
        state=state,
    )

    assert (
        state.status
        == WorkflowStatus.WAITING_FOR_APPROVAL
    )

    assert len(state.approvals) == 1

    assert (
        state.approvals[0]["task_id"]
        == "implementation"
    )

    assert (
        state.approvals[0]["status"]
        == "PENDING"
    )


def test_human_can_approve_task():

    manager = ApprovalManager()

    state = WorkflowState(
        workflow_id="approval-test-2",
        requirement="Build URL shortener",
    )

    manager.request_approval(
        task_id="implementation",
        reason="Production-impacting change",
        state=state,
    )

    manager.approve(
        task_id="implementation",
        state=state,
        approver="senior-engineer",
    )

    assert manager.is_approved(
        "implementation",
        state,
    )

    assert (
        state.approvals[0]["approver"]
        == "senior-engineer"
    )


def test_human_can_reject_task():

    manager = ApprovalManager()

    state = WorkflowState(
        workflow_id="approval-test-3",
        requirement="Build URL shortener",
    )

    manager.request_approval(
        task_id="implementation",
        reason="Production-impacting change",
        state=state,
    )

    manager.reject(
        task_id="implementation",
        state=state,
        approver="senior-engineer",
    )

    assert not manager.is_approved(
        "implementation",
        state,
    )

    assert (
        state.approvals[0]["status"]
        == "REJECTED"
    )


def test_approving_unknown_task_fails():

    manager = ApprovalManager()

    state = WorkflowState(
        workflow_id="approval-test-4",
        requirement="Build URL shortener",
    )

    try:
        manager.approve(
            task_id="unknown-task",
            state=state,
        )

        assert False

    except ValueError as exc:

        assert (
            "No pending approval"
            in str(exc)
        )