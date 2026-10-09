import pytest

from orchestrator.failure import (
    FailureClassifier,
    FailureType,
)


@pytest.fixture
def classifier():
    return FailureClassifier()


def test_timeout_is_transient(classifier):

    result = classifier.classify(
        TimeoutError("LLM request timed out")
    )

    assert result.failure_type == FailureType.TRANSIENT


def test_connection_error_is_transient(classifier):

    result = classifier.classify(
        ConnectionError("Service unavailable")
    )

    assert result.failure_type == FailureType.TRANSIENT


def test_value_error_is_permanent(classifier):

    result = classifier.classify(
        ValueError("Invalid generated artifact")
    )

    assert result.failure_type == FailureType.PERMANENT


def test_permission_error_is_policy_violation(classifier):

    result = classifier.classify(
        PermissionError("Security policy violation")
    )

    assert (
        result.failure_type
        == FailureType.POLICY_VIOLATION
    )


def test_unknown_exception_is_unknown(classifier):

    result = classifier.classify(
        RuntimeError("Unexpected failure")
    )

    assert result.failure_type == FailureType.UNKNOWN