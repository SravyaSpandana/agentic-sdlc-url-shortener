
import pytest

from scenarios.definitions import SCENARIOS, get_scenario


@pytest.mark.parametrize(
    "name",
    ["greenfield", "brownfield", "ambiguous"],
)
def test_scenario_has_requirement_and_tasks(name):
    scenario = get_scenario(name)

    assert scenario["requirement"]
    assert scenario["mode"]
    assert scenario["expected_tasks"]
    assert scenario["focus"]


def test_brownfield_scenario_checks_compatibility():
    scenario = get_scenario("brownfield")

    assert "codebase_analysis" in scenario["expected_tasks"]
    assert "impact_analysis" in scenario["expected_tasks"]
    assert "backward compatibility" in scenario["focus"]


def test_ambiguous_scenario_identifies_missing_requirements():
    scenario = get_scenario("ambiguous")

    assert "ambiguity_analysis" in scenario["expected_tasks"]
    assert "record assumptions" in scenario["focus"]


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError, match="Unknown scenario"):
        get_scenario("unknown")
