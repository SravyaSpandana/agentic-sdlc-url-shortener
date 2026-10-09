from orchestrator.checkpoint import CheckpointManager
from orchestrator.state import WorkflowState, WorkflowStatus


def test_checkpoint_can_restore_workflow_state():

    manager = CheckpointManager()

    state = WorkflowState(
        workflow_id="checkpoint-test",
        requirement="Build URL shortener",
    )

    state.task_status["architecture"] = "COMPLETED"

    state.artifacts["architecture"] = {
        "components": ["FastAPI", "SQLite"]
    }

    manager.create(
        state,
        task_id="implementation",
    )

    # Simulate a bad change
    state.task_status["implementation"] = "COMPLETED"

    state.artifacts["implementation"] = {
        "status": "BAD_CHANGE"
    }

    manager.rollback(
        state,
        task_id="implementation",
    )

    assert "implementation" not in state.task_status

    assert "implementation" not in state.artifacts

    assert state.task_status["architecture"] == "COMPLETED"

    assert state.status == WorkflowStatus.ROLLED_BACK

    assert any(
        event["event"] == "WORKFLOW_ROLLBACK"
        for event in state.audit_events
    )