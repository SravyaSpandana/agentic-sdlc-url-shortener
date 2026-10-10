
SCENARIOS = {
    "greenfield": {
        "requirement": (
            "Build a URL shortener from scratch with URL creation, "
            "redirection, expiration, analytics, and automated tests."
        ),
        "mode": "GREENFIELD",
        "expected_tasks": [
            "requirements",
            "architecture",
            "security",
            "implementation",
            "tests",
            "documentation",
        ],
        "focus": [
            "requirement decomposition",
            "architecture design",
            "implementation and testing",
        ],
    },
    "brownfield": {
        "requirement": (
            "Extend the existing URL shortener with analytics while "
            "preserving existing APIs and redirect behavior."
        ),
        "mode": "BROWNFIELD",
        "expected_tasks": [
            "codebase_analysis",
            "impact_analysis",
            "architecture",
            "security",
            "implementation",
            "regression_tests",
            "documentation",
        ],
        "focus": [
            "existing codebase analysis",
            "API and data-flow impact",
            "backward compatibility",
        ],
    },
    "ambiguous": {
        "requirement": (
            "Build a URL shortener for high traffic with analytics. "
            "Retention, traffic volume, and availability targets "
            "are not specified."
        ),
        "mode": "AMBIGUOUS",
        "expected_tasks": [
            "requirements",
            "ambiguity_analysis",
            "architecture",
            "security",
            "implementation",
            "tests",
            "documentation",
        ],
        "focus": [
            "identify missing requirements",
            "record assumptions",
            "request clarification for material decisions",
        ],
    },
}


def get_scenario(name: str) -> dict:
    try:
        return SCENARIOS[name]
    except KeyError:
        raise ValueError(f"Unknown scenario: {name}") from None
