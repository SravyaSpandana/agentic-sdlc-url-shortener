
from orchestrator.state import WorkflowState, WorkflowStatus
from orchestrator.graph import WorkflowGraph


class Replanner:

    def __init__(self, graph: WorkflowGraph | None = None):
        self.graph = graph

    def _get_downstream_tasks(
        self,
        affected_tasks: list[str],
    ) -> list[str]:
        if self.graph is None:
            return list(affected_tasks)

        invalidated = set(affected_tasks)
        changed = True

        while changed:
            changed = False

            for task in self.graph.tasks.values():
                if (
                    task.task_id not in invalidated
                    and any(
                        dependency in invalidated
                        for dependency in task.dependencies
                    )
                ):
                    invalidated.add(task.task_id)
                    changed = True

        # Keep the graph's task order for deterministic output.
        return [
            task_id
            for task_id in self.graph.tasks
            if task_id in invalidated
        ]

    def replan(
        self,
        state: WorkflowState,
        affected_tasks: list[str],
        reason: str,
    ) -> None:
        invalidated_tasks = self._get_downstream_tasks(
            affected_tasks
        )

        for task_id in invalidated_tasks:
            state.task_status.pop(task_id, None)
            state.artifacts.pop(task_id, None)
            state.retry_counts.pop(task_id, None)

        state.status = WorkflowStatus.REPLANNING

        state.decisions.append(
            {
                "type": "REPLAN",
                "reason": reason,
                "affected_tasks": list(affected_tasks),
                "invalidated_tasks": invalidated_tasks,
            }
        )

        state.audit_events.append(
            {
                "event": "WORKFLOW_REPLANNED",
                "reason": reason,
                "affected_tasks": list(affected_tasks),
                "invalidated_tasks": invalidated_tasks,
            }
        )
