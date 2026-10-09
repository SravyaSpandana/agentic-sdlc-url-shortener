from copy import deepcopy

from orchestrator.state import WorkflowState, WorkflowStatus


class CheckpointManager:

    def create(self, state: WorkflowState, task_id: str) -> None:
        state.context.setdefault("checkpoints", {})

        state.context["checkpoints"][task_id] = {
            "task_status": deepcopy(state.task_status),
            "artifacts": deepcopy(state.artifacts),
            "retry_counts": deepcopy(state.retry_counts),
            "status": state.status.value,
        }

        state.audit_events.append(
            {
                "event": "CHECKPOINT_CREATED",
                "task_id": task_id,
            }
        )

    def rollback(self, state: WorkflowState, task_id: str) -> None:
        checkpoints = state.context.get("checkpoints", {})

        checkpoint = checkpoints.get(task_id)

        if not checkpoint:
            raise ValueError(
                f"No checkpoint found for task '{task_id}'"
            )

        state.task_status = deepcopy(
            checkpoint["task_status"]
        )

        state.artifacts = deepcopy(
            checkpoint["artifacts"]
        )

        state.retry_counts = deepcopy(
            checkpoint["retry_counts"]
        )

        state.status = WorkflowStatus.ROLLED_BACK

        state.audit_events.append(
            {
                "event": "WORKFLOW_ROLLBACK",
                "task_id": task_id,
            }
        )