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
from orchestrator.approval import ApprovalManager
from orchestrator.policy import PolicyDecision, PolicyGuard
from orchestrator.replanner import Replanner
from orchestrator.metrics import WorkflowMetrics

class WorkflowExecutor:

    def __init__(
        self,
        graph: WorkflowGraph,
        agents: dict[str, BaseAgent],
        retry_policy: RetryPolicy | None = None,
        failure_classifier: FailureClassifier | None = None,
        approval_manager: ApprovalManager | None = None,
        policy_guard: PolicyGuard | None = None,
        replanner: Replanner | None = None,
        metrics: WorkflowMetrics | None = None,
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
        self.approval_manager = (
            approval_manager or ApprovalManager()
        )

        self.policy_guard = policy_guard or PolicyGuard()
        self.replanner = replanner or Replanner()
        self.metrics = metrics or WorkflowMetrics()

    async def execute(self, state: WorkflowState) -> WorkflowState:
        self.graph.validate()

    # Recover already-completed tasks when resuming a workflow.
        completed_tasks = {
            task_id
            for task_id, status in state.task_status.items()
            if status == "COMPLETED"
        }

        state.status = WorkflowStatus.RUNNING

        while len(completed_tasks) < len(self.graph.tasks):

            ready_tasks = self.graph.get_ready_tasks(completed_tasks)

            if not ready_tasks:
                if state.status == WorkflowStatus.WAITING_FOR_APPROVAL:
                    return state

                raise RuntimeError(
                    "No tasks are ready. "
                    "Workflow may contain unresolved dependencies."
                )

            executable_tasks = []
            waiting_for_approval = False

            for task in ready_tasks:

            # --------------------------------------------------
            # 1. POLICY GATE
            # --------------------------------------------------
                policy_result = self.policy_guard.evaluate(
                    task,
                    state,
                )

                if policy_result.decision == PolicyDecision.DENY:

                    state.task_status[task.task_id] = "SAFE_STOP"
                    state.status = WorkflowStatus.SAFE_STOP

                    state.audit_events.append(
                        {
                            "event": "POLICY_VIOLATION",
                            "task_id": task.task_id,
                            "reason": policy_result.reason,
                        }
                    )

                    return state

            # --------------------------------------------------
            # 2. NORMAL TASK
            # --------------------------------------------------
                if not task.requires_approval:
                    executable_tasks.append(task)
                    continue

            # --------------------------------------------------
            # 3. APPROVAL ALREADY REJECTED
            # --------------------------------------------------
                if self.approval_manager.is_rejected(
                    task.task_id,
                    state,
                ):

                    state.task_status[task.task_id] = "BLOCKED"
                    state.status = WorkflowStatus.BLOCKED

                    state.audit_events.append(
                        {
                            "event": "TASK_BLOCKED",
                            "task_id": task.task_id,
                            "reason": "Human approval rejected",
                        }
                    )

                    return state

            # --------------------------------------------------
            # 4. APPROVAL ALREADY GRANTED
            # --------------------------------------------------
                if self.approval_manager.is_approved(
                    task.task_id,
                    state,
                ):
                    executable_tasks.append(task)
                    continue

            # --------------------------------------------------
            # 5. REQUEST HUMAN APPROVAL
            # --------------------------------------------------
                self.approval_manager.request_approval(
                    task_id=task.task_id,
                    reason=task.metadata.get(
                        "approval_reason",
                        "High-impact engineering action",
                    ),
                    state=state,
                )

                waiting_for_approval = True

        # ------------------------------------------------------
        # 6. EXECUTE ALL APPROVED / NORMAL TASKS IN PARALLEL
        # ------------------------------------------------------
            if executable_tasks:

                await self._execute_parallel(
                    executable_tasks,
                    state,
                )

                for task in executable_tasks:

                    completed_tasks.add(task.task_id)

                    state.task_status[
                        task.task_id
                    ] = "COMPLETED"

        # ------------------------------------------------------
        # 7. PAUSE IF HUMAN APPROVAL IS REQUIRED
        # ------------------------------------------------------
            if waiting_for_approval:

                state.status = (
                    WorkflowStatus.WAITING_FOR_APPROVAL
                )

                return state

    # ----------------------------------------------------------
    # 8. WORKFLOW COMPLETED
    # ----------------------------------------------------------
        state.status = WorkflowStatus.COMPLETED

        self.metrics.finish(state.status.value)

        return state

    async def replan_and_resume(
        self,
        state: WorkflowState,
        affected_tasks: list[str],
        reason: str,
    ) -> WorkflowState:
        """Invalidate stale work and resume the existing workflow."""

        # Validate task IDs before modifying workflow state.
        unknown_tasks = set(affected_tasks) - set(self.graph.tasks)

        if unknown_tasks:
            raise ValueError(
                f"Cannot replan unknown tasks: {sorted(unknown_tasks)}"
            )

        # Invalidate affected tasks and their stale artifacts.
        self.replanner.replan(
            state=state,
            affected_tasks=affected_tasks,
            reason=reason,
        )

        # Resume using the existing state and dependency graph.
        return await self.execute(state)

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

                self.metrics.record_event(state.audit_events[-1])

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

                        state.audit_events.append(
                            {
                                "event": "TASK_RETRY",
                                "task_id": task.task_id,
                                "retry_count": retry_count,
                            }
                        )
                        self.metrics.record_event(state.audit_events[-1])

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
                "failure_type": classification.failure_type.value,
                "reason": classification.reason,
            }
        )
