from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    BLOCKED = "BLOCKED"
    REPLANNING = "REPLANNING"
    ROLLED_BACK = "ROLLED_BACK"
    SAFE_STOP = "SAFE_STOP"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowState(BaseModel):
    workflow_id: str
    requirement: str

    status: WorkflowStatus = WorkflowStatus.CREATED

    context: dict[str, Any] = Field(default_factory=dict)

    artifacts: dict[str, Any] = Field(default_factory=dict)

    decisions: list[dict[str, Any]] = Field(default_factory=list)

    audit_events: list[dict[str, Any]] = Field(default_factory=list)

    task_status: dict[str, str] = Field(default_factory=dict)

    retry_counts: dict[str, int] = Field(default_factory=dict)

    approvals: list[dict[str, Any]] = Field(default_factory=list)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )