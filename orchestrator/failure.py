from enum import Enum


class FailureType(str, Enum):
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    UNKNOWN = "UNKNOWN"


class FailureClassification:
    """
    Represents the result of classifying an agent failure.
    """

    def __init__(
        self,
        failure_type: FailureType,
        reason: str,
    ):
        self.failure_type = failure_type
        self.reason = reason


class FailureClassifier:
    """
    Classifies agent exceptions into recovery categories.
    """

    def classify(
        self,
        exception: Exception,
    ) -> FailureClassification:

        if isinstance(
            exception,
            (TimeoutError, ConnectionError),
        ):
            return FailureClassification(
                failure_type=FailureType.TRANSIENT,
                reason=str(exception),
            )

        if isinstance(
            exception,
            ValueError,
        ):
            return FailureClassification(
                failure_type=FailureType.PERMANENT,
                reason=str(exception),
            )

        if isinstance(
            exception,
            PermissionError,
        ):
            return FailureClassification(
                failure_type=FailureType.POLICY_VIOLATION,
                reason=str(exception),
            )

        return FailureClassification(
            failure_type=FailureType.UNKNOWN,
            reason=str(exception),
        )