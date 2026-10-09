from orchestrator.state import WorkflowStatus


class ApprovalManager:

    def request_approval(self, task_id: str, reason: str, state) -> None:
        if self.has_pending_approval(task_id, state):
            return

        state.approvals.append(
            {
                "task_id": task_id,
                "reason": reason,
                "status": "PENDING",
            }
        )

        state.task_status[task_id] = "WAITING_FOR_APPROVAL"
        state.status = WorkflowStatus.WAITING_FOR_APPROVAL

        state.audit_events.append(
            {
                "event": "APPROVAL_REQUESTED",
                "task_id": task_id,
                "reason": reason,
            }
        )

    def has_pending_approval(self, task_id: str, state) -> bool:
        return any(
            approval["task_id"] == task_id
            and approval["status"] == "PENDING"
            for approval in state.approvals
        )

    def is_approved(self, task_id: str, state) -> bool:
        return any(
            approval["task_id"] == task_id
            and approval["status"] == "APPROVED"
            for approval in state.approvals
        )

    def is_rejected(self, task_id: str, state) -> bool:
        return any(
            approval["task_id"] == task_id
            and approval["status"] == "REJECTED"
            for approval in state.approvals
        )

    def approve(
        self,
        task_id: str,
        state,
        approver: str = "human",
    ) -> None:

        for approval in state.approvals:
            if (
                approval["task_id"] == task_id
                and approval["status"] == "PENDING"
            ):
                approval["status"] = "APPROVED"
                approval["approver"] = approver

                state.audit_events.append(
                    {
                        "event": "APPROVAL_GRANTED",
                        "task_id": task_id,
                        "approver": approver,
                    }
                )
                return

        raise ValueError(
            f"No pending approval found for task '{task_id}'"
        )

    def reject(
        self,
        task_id: str,
        state,
        approver: str = "human",
    ) -> None:

        for approval in state.approvals:
            if (
                approval["task_id"] == task_id
                and approval["status"] == "PENDING"
            ):
                approval["status"] = "REJECTED"
                approval["approver"] = approver

                state.audit_events.append(
                    {
                        "event": "APPROVAL_REJECTED",
                        "task_id": task_id,
                        "approver": approver,
                    }
                )
                return

        raise ValueError(
            f"No pending approval found for task '{task_id}'"
        )