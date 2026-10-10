from orchestrator.graph import TaskDefinition, WorkflowGraph
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

def test_replanner_invalidates_downstream_tasks():
    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(task_id="requirements", agent_name="requirements")
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
    graph.add_task(
        TaskDefinition(
            task_id="tests",
            agent_name="tests",
            dependencies=["implementation"],
        )
    )

    replanner = Replanner(graph=graph)

    state = WorkflowState(
        workflow_id="replan-test",
        requirement="Build URL shortener",
    )

    # All tasks were completed before the requirement changed.
    for task_id in graph.tasks:
        state.task_status[task_id] = "COMPLETED"
        state.artifacts[task_id] = {"result": task_id}
        state.retry_counts[task_id] = 0

    replanner.replan(
        state=state,
        affected_tasks=["architecture"],
        reason="Architecture requirement changed",
    )

    # Preserve unaffected upstream work.
    assert state.task_status["requirements"] == "COMPLETED"
    assert "requirements" in state.artifacts

    # Invalidate the changed task and all downstream work.
    expected_invalidated = {
        "architecture",
        "implementation",
        "tests",
    }

    for task_id in expected_invalidated:
        assert task_id not in state.task_status
        assert task_id not in state.artifacts
        assert task_id not in state.retry_counts

    assert state.status == WorkflowStatus.REPLANNING

    event = state.audit_events[-1]
    assert event["event"] == "WORKFLOW_REPLANNED"
    assert set(event["invalidated_tasks"]) == expected_invalidated
