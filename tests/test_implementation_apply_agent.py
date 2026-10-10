
import pytest
from pathlib import Path

from agents.implementation_apply_agent import ImplementationApplyAgent
from orchestrator.state import WorkflowState


@pytest.mark.asyncio
async def test_apply_failure_rolls_back_modified_file(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path
    source_file = project_root / "app" / "models.py"
    source_file.parent.mkdir(parents=True)

    original_content = "original content\n"
    source_file.write_text(original_content, encoding="utf-8")

    workflow_id = "rollback-test"

    state = WorkflowState(
        workflow_id=workflow_id,
        requirement="Test implementation rollback",
    )

    state.artifacts["implementation_proposal"] = {
        "type": "implementation-proposal",
        "workflow_id": workflow_id,
        "status": "PROPOSED",
        "summary": "Test rollback",
        "edits": [
            {
                "path": "app/models.py",
                "original": original_content,
                "search": "original content",
                "replace": "updated content",
            }
        ],
    }

    agent = ImplementationApplyAgent(project_root=project_root)

    # Inject a failure when the agent tries to write the updated source.
    original_write_text = Path.write_text

    def fail_on_updated_content(self, data, *args, **kwargs):
        if self == source_file and data == "updated content\n":
            raise OSError("Simulated write failure")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_on_updated_content)

    with pytest.raises(OSError, match="Simulated write failure"):
        await agent.execute(state)

    assert source_file.read_text(encoding="utf-8") == original_content

    rollback_events = [
        event
        for event in state.audit_events
        if event["event"] == "IMPLEMENTATION_ROLLBACK"
    ]
    assert len(rollback_events) == 1
    assert rollback_events[0]["files"] == []

    assert not any(
        event["event"] == "IMPLEMENTATION_APPLIED"
        for event in state.audit_events
    )
