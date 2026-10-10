
import json
from pathlib import Path

from agents.base import BaseAgent
from agents.implementation_proposal_agent import ImplementationProposalAgent


class ImplementationApplyAgent(BaseAgent):
    name = "implementation-apply-agent"

    def __init__(self, project_root: Path | None = None):
        self.project_root = (
            project_root or Path(__file__).resolve().parent.parent
        ).resolve()

    async def execute(self, state):
        proposal = state.artifacts.get("implementation_proposal")

        if not proposal:
            raise ValueError("No saved implementation proposal exists")

        if proposal.get("workflow_id") != state.workflow_id:
            raise ValueError("Proposal belongs to a different workflow")

        if proposal.get("status") == "NO_CHANGES":
            return {
                "type": "implementation",
                "status": "NO_CHANGES",
                "files_changed": [],
            }

        edits = proposal.get("edits")
        if not isinstance(edits, list) or not edits or len(edits) > 3:
            raise ValueError("Invalid or empty implementation proposal")

        # Validate every edit before modifying any source file.
        validated = []
        seen_paths = set()

        for edit in edits:
            relative_path = edit.get("path")
            if relative_path not in ImplementationProposalAgent.ALLOWED_FILES:
                raise ValueError(f"File is not allowlisted: {relative_path}")

            if relative_path in seen_paths:
                raise ValueError(f"Duplicate file edit: {relative_path}")

            seen_paths.add(relative_path)

            target = (self.project_root / relative_path).resolve()
            if not target.is_relative_to(self.project_root):
                raise ValueError("Target path escaped project root")

            if not target.is_file():
                raise ValueError(f"Target file does not exist: {relative_path}")

            original = edit.get("original")
            search = edit.get("search")
            replacement = edit.get("replace")

            if not all(isinstance(value, str) for value in
                       (original, search, replacement)) or not search:
                raise ValueError("Malformed proposal edit")

            current = target.read_text(encoding="utf-8")
            if current != original:
                raise RuntimeError(
                    f"Source changed after proposal: {relative_path}"
                )

            if current.count(search) != 1:
                raise ValueError(
                    f"Search text must match exactly once: {relative_path}"
                )

            validated.append({
                "path": relative_path,
                "target": target,
                "original": current,
                "updated": current.replace(search, replacement, 1),
            })

        backup_dir = (
            self.project_root
            / "artifacts"
            / "implementation-backups"
            / state.workflow_id
        )
        backup_dir.mkdir(parents=True, exist_ok=True)

        backups = {}
        changed_paths = []

        try:
            # Create all backups before changing any source file.
            for edit in validated:
                backup_path = backup_dir / edit["path"].replace("/", "__")
                backup_path.write_text(edit["original"], encoding="utf-8")
                backups[edit["path"]] = backup_path

            # Recheck all source files immediately before applying.
            for edit in validated:
                if edit["target"].read_text(encoding="utf-8") != edit["original"]:
                    raise RuntimeError(
                        f"Source changed before apply: {edit['path']}"
                    )

            for edit in validated:
                edit["target"].write_text(
                    edit["updated"],
                    encoding="utf-8",
                )
                changed_paths.append(edit["path"])

        except Exception:
            rollback_errors = []

            for edit in validated:
                backup_path = backups.get(edit["path"])
                if backup_path and backup_path.is_file():
                    try:
                        edit["target"].write_text(
                            backup_path.read_text(encoding="utf-8"),
                            encoding="utf-8",
                        )
                    except OSError as rollback_error:
                        rollback_errors.append(
                            f"{edit['path']}: {rollback_error}"
                        )

            state.audit_events.append({
                "event": "IMPLEMENTATION_ROLLBACK",
                "files": changed_paths,
                "rollback_errors": rollback_errors,
            })

            if rollback_errors:
                raise RuntimeError(
                    "Apply failed and rollback was incomplete: "
                    + "; ".join(rollback_errors)
                )

            raise

        state.audit_events.append({
            "event": "IMPLEMENTATION_APPLIED",
            "files_changed": changed_paths,
            "backup_directory": str(backup_dir),
        })

        return {
            "type": "implementation",
            "status": "APPLIED",
            "summary": proposal.get("summary", ""),
            "files_changed": changed_paths,
            "backup_directory": str(backup_dir),
        }