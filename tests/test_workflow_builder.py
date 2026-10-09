
import pytest

from scenarios.workflow_builder import ScenarioWorkflowBuilder


@pytest.mark.parametrize(
    "scenario_name",
    ["greenfield", "brownfield", "ambiguous"],
)
def test_builder_creates_valid_workflow(scenario_name):
    scenario, graph, agents = ScenarioWorkflowBuilder().build(
        scenario_name
    )

    assert scenario["mode"]
    assert graph.tasks
    assert agents

    graph.validate()

    assert any(
        task.requires_approval
        for task in graph.tasks.values()
    )


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError, match="Unknown scenario"):
        ScenarioWorkflowBuilder().build("unknown")
