import pytest

from orchestrator.graph import (
    TaskDefinition,
    WorkflowGraph,
)


def test_valid_workflow_graph():

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

    graph.validate()


def test_unknown_dependency_is_rejected():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="architecture",
            agent_name="architecture-agent",
            dependencies=["requirements"],
        )
    )

    with pytest.raises(
        ValueError,
        match="unknown task",
    ):
        graph.validate()


def test_self_dependency_is_rejected():

    graph = WorkflowGraph()

    with pytest.raises(
        ValueError,
        match="cannot depend on itself",
    ):
        graph.add_task(
            TaskDefinition(
                task_id="architecture",
                agent_name="architecture-agent",
                dependencies=["architecture"],
            )
        )


def test_circular_dependency_is_rejected():

    graph = WorkflowGraph()

    graph.add_task(
        TaskDefinition(
            task_id="requirements",
            agent_name="requirement-agent",
            dependencies=["testing"],
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
            task_id="testing",
            agent_name="test-agent",
            dependencies=["architecture"],
        )
    )

    with pytest.raises(
        ValueError,
        match="Circular dependency",
    ):
        graph.validate()


def test_ready_tasks_are_returned():

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
            dependencies=["requirements"],
        )
    )

    graph.validate()

    ready = graph.get_ready_tasks(
        completed_tasks={"requirements"}
    )

    ready_ids = {
        task.task_id
        for task in ready
    }

    assert ready_ids == {
        "architecture",
        "security",
    }