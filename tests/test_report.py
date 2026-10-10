
from orchestrator.report import build_engineering_report
from orchestrator.state import WorkflowState, WorkflowStatus


def test_engineering_report_contains_workflow_evidence():
    state = WorkflowState(
        workflow_id="report-test",
        requirement="Build a URL shortener",
        status=WorkflowStatus.COMPLETED,
    )

    state.task_status["requirements"] = "COMPLETED"
    state.artifacts["requirements"] = {
        "summary": "URL shortener requirements"
    }
    state.context["assumptions"] = ["Default URL expiry is configurable"]

    report = build_engineering_report(state)

    assert report["workflow_id"] == "report-test"
    assert report["status"] == "COMPLETED"
    assert report["tasks"][0]["task_id"] == "requirements"
    assert report["assumptions"]
    assert "audit_events" in report
    assert "validation" in report
