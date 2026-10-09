from datetime import datetime, timezone

from orchestrator.state import WorkflowState
from orchestrator.metrics import WorkflowMetrics

def build_engineering_report(state: WorkflowState) -> dict:
    """Build a reviewable summary from actual workflow state."""

    task_results = []

    for task_id, status in state.task_status.items():
        task_results.append(
            {
                "task_id": task_id,
                "status": status,
                "artifact": state.artifacts.get(task_id),
            }
        )

    return {
        "workflow_id": state.workflow_id,
        "requirement": state.requirement,
        "status": state.status.value,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assumptions": state.context.get("assumptions", []),
        "decisions": state.decisions,
        "tasks": task_results,
        "approvals": state.approvals,
        "audit_events": state.audit_events,
        "risks_and_limitations": state.context.get(
            "risks_and_limitations", []
        ),
        "validation": {
            "test_artifacts": [
                artifact
                for task_id, artifact in state.artifacts.items()
                if "test" in task_id.lower()
            ],
        },
        "metrics": state.context.get("metrics", {}),
    }
