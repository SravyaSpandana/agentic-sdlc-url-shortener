
from datetime import datetime, timedelta, timezone

from orchestrator.metrics import WorkflowMetrics


def test_metrics_capture_workflow_duration_and_reliability():
    start = datetime.now(timezone.utc)

    metrics = WorkflowMetrics(started_at=start)
    metrics.retries = 2
    metrics.rollbacks = 1
    metrics.replans = 1
    metrics.task_failures = 1

    metrics.completed_at = start + timedelta(seconds=3)
    metrics.status = "COMPLETED"

    result = metrics.to_dict()

    assert result["status"] == "COMPLETED"
    assert result["duration_seconds"] == 3.0
    assert result["retries"] == 2
    assert result["rollbacks"] == 1
    assert result["replans"] == 1
    assert result["task_failures"] == 1
