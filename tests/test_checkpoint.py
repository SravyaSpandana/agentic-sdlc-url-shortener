from orchestrator.checkpoint import CheckpointManager
from orchestrator.state import WorkflowState, WorkflowStatus
from orchestrator.executor import WorkflowExecutor
from orchestrator.graph import WorkflowGraph

def test_executor_rollback_updates_metrics():
    graph = WorkflowGraph()
    executor = WorkflowExecutor(
        graph=graph,
        agents={},
    )

    state = WorkflowState(
        workflow_id="rollback-metrics-test",
        requirement="Build URL shortener",
    )

    # Create a checkpoint with the architecture completed.
    state.task_status["architecture"] = "COMPLETED"
    state.artifacts["architecture"] = {
        "components": ["FastAPI", "SQLite"]
    }

    executor.checkpoint_manager.create(
        state,
        task_id="architecture",
    )

    # Simulate a change after the checkpoint.
    state.task_status["implementation"] = "COMPLETED"
    state.artifacts["implementation"] = {
        "status": "BAD_CHANGE"
    }

    executor.rollback_to_checkpoint(
        state,
        task_id="architecture",
    )

    assert state.status == WorkflowStatus.ROLLED_BACK
    assert "implementation" not in state.task_status
    assert "implementation" not in state.artifacts
    assert executor.metrics.rollbacks == 1

    assert any(
        event["event"] == "WORKFLOW_ROLLBACK"
        for event in state.audit_events
    )


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