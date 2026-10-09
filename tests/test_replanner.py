from orchestrator.replanner import Replanner
from orchestrator.state import WorkflowState, WorkflowStatus


def test_replanner_invalidates_affected_tasks():

    state = WorkflowState(
        workflow_id="replan-test",
        requirement="Build URL shortener",
    )

    state.task_status["architecture"] = "COMPLETED"
    state.task_status["security"] = "COMPLETED"
    state.task_status["implementation"] = "COMPLETED"
    state.task_status["tests"] = "COMPLETED"

    state.artifacts["architecture"] = {
        "status": "OLD"
    }

    state.artifacts["implementation"] = {
        "status": "OLD"
    }

    replanner = Replanner()

    replanner.replan(
        state=state,
        affected_tasks=[
            "architecture",
            "security",
            "implementation",
            "tests",
        ],
        reason="Security requirement changed",
    )

    assert "architecture" not in state.task_status
    assert "security" not in state.task_status
    assert "implementation" not in state.task_status
    assert "tests" not in state.task_status

    assert "architecture" not in state.artifacts
    assert "implementation" not in state.artifacts

    assert state.status == WorkflowStatus.REPLANNING

    assert len(state.decisions) == 1
    assert state.decisions[0]["type"] == "REPLAN"

    assert any(
        event["event"] == "WORKFLOW_REPLANNED"
        for event in state.audit_events
    )