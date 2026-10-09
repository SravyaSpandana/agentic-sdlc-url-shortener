from orchestrator.state import WorkflowState, WorkflowStatus


class Replanner:

    def replan(
        self,
        state: WorkflowState,
        affected_tasks: list[str],
        reason: str,
    ) -> None:

        for task_id in affected_tasks:
            if task_id in state.task_status:
                state.task_status.pop(task_id)

            state.artifacts.pop(task_id, None)

        state.status = WorkflowStatus.REPLANNING

        state.decisions.append(
            {
                "type": "REPLAN",
                "reason": reason,
                "affected_tasks": affected_tasks,
            }
        )

        state.audit_events.append(
            {
                "event": "WORKFLOW_REPLANNED",
                "reason": reason,
                "affected_tasks": affected_tasks,
            }
        )