
import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from orchestrator.report import build_engineering_report
from orchestrator.executor import WorkflowExecutor
from orchestrator.state import WorkflowState, WorkflowStatus
from scenarios.workflow_builder import ScenarioWorkflowBuilder


async def run_scenario(
    scenario_name: str,
    provider: str | None = None,
) -> int:
    if provider is None:
        from llm.config import load_settings
        provider = load_settings().provider

    scenario, graph, agents = ScenarioWorkflowBuilder(
        provider=provider
    ).build(scenario_name)

    state = WorkflowState(
        workflow_id=f"{scenario_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        requirement=scenario["requirement"],
        context={
            "scenario": scenario_name,
            "mode": scenario["mode"],
            "focus": scenario["focus"],
        },
    )

    executor = WorkflowExecutor(graph=graph, agents=agents)

    print("\n" + "=" * 60)
    print(" AGENTIC SOFTWARE ENGINEERING SYSTEM")
    print("=" * 60)
    print(f"Scenario: {scenario_name}")
    print(f"Requirement: {scenario['requirement']}\n")

    try:
        while True:
            state = await executor.execute(state)

            print("\nTask status:")
            for task_id, status in state.task_status.items():
                print(f"  {task_id:<25} {status}")

            if state.status == WorkflowStatus.WAITING_FOR_APPROVAL:
                proposal = state.artifacts.get("implementation_proposal")

                if proposal:
                    print("\n" + "=" * 60)
                    print(" PROPOSED CODE CHANGES")
                    print("=" * 60)
                    print(f"Summary: {proposal.get('summary', '')}")

                    edits = proposal.get("edits", [])
                    if not edits:
                        print("No source changes proposed.")

                    for edit in edits:
                        print(f"\nFile: {edit['path']}")
                        print("\n--- BEFORE ---")
                        print(edit["search"])
                        print("\n--- AFTER ---")
                        print(edit["replace"])
                pending = [
                    approval
                    for approval in state.approvals
                    if approval["status"] == "PENDING"
                ]

                if not pending:
                    print("ERROR: Workflow is waiting without a pending approval.")
                    return 1

                
                for approval in pending:
                    print(f"\nApproval required for: {approval['task_id']}")
                    print(f"Reason: {approval['reason']}")

                    answer = input("Approve this task? [y/N]: ").strip().lower()

                    if answer == "y":
                        executor.approval_manager.approve(
                            task_id=approval["task_id"],
                            state=state,
                            approver="cli-user",
                        )
                    else:
                        executor.approval_manager.reject(
                            task_id=approval["task_id"],
                            state=state,
                            approver="cli-user",
                        )

                if any(
                    approval["status"] == "REJECTED"
                    for approval in state.approvals
                ):
                    state = await executor.execute(state)

                    state.context["rejection"] = {
                        "status": "REJECTED",
                        "approvals": [
                            {
                                "task_id": approval["task_id"],
                                "reason": approval["reason"],
                                "approver": approval.get("approver", "cli-user"),
                            }
                            for approval in state.approvals
                            if approval["status"] == "REJECTED"
                        ],
                    }

                    state.context["metrics"] = executor.metrics.to_dict()
                    report = build_engineering_report(state)

                    artifacts_dir = Path("artifacts")
                    artifacts_dir.mkdir(parents=True, exist_ok=True)
                    report_path = artifacts_dir / f"{state.workflow_id}-report.json"

                    report_path.write_text(
                        json.dumps(report, indent=2, default=str),
                        encoding="utf-8",
                    )

                    print("\nWorkflow status: REJECTED")
                    print(f"Engineering report saved to: {report_path}")
                    return 1

                continue

            break

        print("\nArtifacts:")
        print(json.dumps(state.artifacts, indent=2, default=str))

        print("\nAudit events:")
        print(json.dumps(state.audit_events, indent=2, default=str))

        state.context["metrics"] = executor.metrics.to_dict()
        
        # Generate and save the engineering report.
        report = build_engineering_report(state)

        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        report_path = artifacts_dir / f"{state.workflow_id}-report.json"

        report_path.write_text(
            json.dumps(report, indent=2, default=str),
            encoding="utf-8",
        )

        print(f"\nEngineering report saved to: {report_path}")
        print(f"Final workflow status: {state.status.value}")

        return 0 if state.status == WorkflowStatus.COMPLETED else 1

    except Exception as exc:
        print(f"\nWorkflow failed: {type(exc).__name__}: {exc}")
        return 1



def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Agentic SDLC workflow"
    )

    parser.add_argument(
        "--scenario",
        choices=["greenfield", "brownfield", "ambiguous"],
        default="greenfield",
        help="Scenario to execute",
    )

    parser.add_argument(
        "--provider",
        choices=["mock", "gemini"],
        default=None,
        help="LLM provider (defaults to LLM_PROVIDER from .env)",
    )

    args = parser.parse_args()

    return asyncio.run(
        run_scenario(args.scenario, args.provider)
    )


if __name__ == "__main__":
    raise SystemExit(main())
