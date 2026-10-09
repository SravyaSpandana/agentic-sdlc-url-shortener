import asyncio
from typing import Any

from agents.base import BaseAgent
from orchestrator.failure import (
    FailureClassifier,
    FailureType,
)
from orchestrator.graph import WorkflowGraph
from orchestrator.retry import RetryPolicy
from orchestrator.state import (
    WorkflowState,
    WorkflowStatus,
)


class WorkflowExecutor:

    def __init__(
        self,
        graph: WorkflowGraph,
        agents: dict[str, BaseAgent],
        retry_policy: RetryPolicy | None = None,
        failure_classifier: FailureClassifier | None = None,
    ):
        self.graph = graph
        self.agents = agents

        self.retry_policy = (
            retry_policy
            or RetryPolicy()
        )

        self.failure_classifier = (
            failure_classifier
            or FailureClassifier()
        )

    async def execute(
        self,
        state: WorkflowState,
    ) -> WorkflowState:

        self.graph.validate()

        state.status = WorkflowStatus.RUNNING

        completed_tasks: set[str] = set()

        while len(completed_tasks) < len(
            self.graph.tasks
        ):

            ready_tasks = self.graph.get_ready_tasks(
                completed_tasks
            )

            if not ready_tasks:
                raise RuntimeError(
                    "No tasks are ready. "
                    "Workflow may contain unresolved dependencies."
                )

            await self._execute_parallel(
                ready_tasks,
                state,
            )

            for task in ready_tasks:

                completed_tasks.add(
                    task.task_id
                )

                state.task_status[
                    task.task_id
                ] = "COMPLETED"

        state.status = WorkflowStatus.COMPLETED

        return state

    async def _execute_parallel(
        self,
        tasks: list[Any],
        state: WorkflowState,
    ) -> None:

        executions = []

        for task in tasks:

            agent = self.agents.get(
                task.agent_name
            )

            if not agent:
                raise ValueError(
                    f"No agent registered for "
                    f"'{task.agent_name}'"
                )

            executions.append(
                self._execute_task(
                    task,
                    agent,
                    state,
                )
            )

        await asyncio.gather(
            *executions
        )

    async def _execute_task(
        self,
        task: Any,
        agent: BaseAgent,
        state: WorkflowState,
    ) -> None:

        state.task_status[
            task.task_id
        ] = "RUNNING"

        retry_count = state.retry_counts.get(
            task.task_id,
            0,
        )

        while True:

            try:

                result = await agent.execute(
                    state
                )

                state.artifacts[
                    task.task_id
                ] = result

                return

            except Exception as exc:

                classification = (
                    self.failure_classifier.classify(
                        exc
                    )
                )

                self._record_failure(
                    task_id=task.task_id,
                    classification=classification,
                    state=state,
                )

                if (
                    classification.failure_type
                    == FailureType.TRANSIENT
                ):

                    if self.retry_policy.can_retry(
                        retry_count
                    ):

                        retry_count += 1

                        state.retry_counts[
                            task.task_id
                        ] = retry_count

                        state.status = (
                            WorkflowStatus.RETRYING
                        )

                        continue

                    state.task_status[
                        task.task_id
                    ] = "FAILED"

                    state.status = (
                        WorkflowStatus.FAILED
                    )

                    raise

                if (
                    classification.failure_type
                    == FailureType.POLICY_VIOLATION
                ):

                    state.task_status[
                        task.task_id
                    ] = "SAFE_STOP"

                    state.status = (
                        WorkflowStatus.SAFE_STOP
                    )

                    raise

                state.task_status[
                    task.task_id
                ] = "FAILED"

                state.status = (
                    WorkflowStatus.FAILED
                )

                raise

    @staticmethod
    def _record_failure(
        task_id: str,
        classification: Any,
        state: WorkflowState,
    ) -> None:

        state.audit_events.append(
            {
                "event": "TASK_FAILED",
                "task_id": task_id,
                "failure_type": (
                    classification.failure_type.value
                ),
                "reason": classification.reason,
            }
        )