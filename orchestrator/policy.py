from dataclasses import dataclass
from enum import Enum


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass
class PolicyResult:
    decision: PolicyDecision
    reason: str


class PolicyGuard:

    def evaluate(self, task, state) -> PolicyResult:

        # Critical production-impacting tasks require approval.
        if task.critical and not task.requires_approval:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=(
                    "Critical task must have an explicit "
                    "human approval gate."
                ),
            )

        # Prevent agents from performing unrestricted release actions.
        if task.metadata.get("action") == "PRODUCTION_RELEASE":
            if not task.requires_approval:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason="Production release requires human approval.",
                )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Task satisfies workflow policy.",
        )