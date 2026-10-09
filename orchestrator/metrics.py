
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class WorkflowMetrics:
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None
    status: str = "RUNNING"
    retries: int = 0
    rollbacks: int = 0
    replans: int = 0
    task_failures: int = 0

    @property
    def duration_seconds(self) -> float | None:
        if self.completed_at is None:
            return None
        return max(
            0.0,
            (self.completed_at - self.started_at).total_seconds(),
        )

    def finish(self, status: str) -> None:
        self.status = status
        self.completed_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "retries": self.retries,
            "rollbacks": self.rollbacks,
            "replans": self.replans,
            "task_failures": self.task_failures,
        }

    def record_event(self, event: dict) -> None:
        event_type = event.get("event")

        if event_type == "TASK_FAILED":
            self.task_failures += 1

        elif event_type == "TASK_RETRY":
            self.retries += 1

        elif event_type == "WORKFLOW_ROLLBACK":
            self.rollbacks += 1

        elif event_type == "WORKFLOW_REPLANNED":
            self.replans += 1
