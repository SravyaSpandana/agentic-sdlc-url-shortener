
import json
from pathlib import Path

from agents.base import BaseAgent


class ImplementationProposalAgent(BaseAgent):
    name = "implementation-proposal-agent"

    ALLOWED_FILES = {
        "app/models.py",
        "app/api/routes.py",
        "app/services/url_service.py",
        "app/repository/url_repository.py",
    }

    def __init__(self, client, project_root: Path | None = None):
        self.client = client
        self.project_root = (
            project_root or Path(__file__).resolve().parent.parent
        ).resolve()

    async def execute(self, state):
        source_files = {}

        for relative_path in sorted(self.ALLOWED_FILES):
            path = (self.project_root / relative_path).resolve()

            if not path.is_relative_to(self.project_root):
                raise ValueError("Source path escaped project root")

            if path.is_file():
                source_files[relative_path] = path.read_text(
                    encoding="utf-8"
                )

        prompt = {
            "requirement": state.requirement,
            "security_findings": state.artifacts.get("security"),
            "source_files": source_files,
        }

        response = await self.client.generate_text(
            system_prompt=(
                "You are a cautious software engineer reviewing an "
                "existing FastAPI URL shortener. Propose one small, "
                "useful, backward-compatible improvement grounded in "
                "the supplied code and security findings. Return only "
                "valid JSON: "
                '{"summary":"...", "edits":[{"path":"app/...", '
                '"search":"exact existing text", '
                '"replace":"replacement text"}]}. '
                "Every search string must match exactly once. "
                "Only edit supplied allowlisted source files. "
                "Do not edit tests, dependencies, configuration, or "
                "workflow code. Do not execute commands. "
                "Return an empty edits list only if no safe, useful "
                "improvement can be justified."
            ),
            user_prompt=json.dumps(prompt, ensure_ascii=False),
        )

        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        proposal = json.loads(text)

        if not isinstance(proposal, dict):
            raise ValueError("Proposal must be a JSON object")

        edits = proposal.get("edits")
        if not isinstance(edits, list) or len(edits) > 3:
            raise ValueError("Proposal must contain at most three edits")

        validated = []
        seen_paths = set()

        for edit in edits:
            if not isinstance(edit, dict):
                raise ValueError("Each edit must be an object")

            relative_path = edit.get("path")
            search = edit.get("search")
            replacement = edit.get("replace")

            if relative_path not in self.ALLOWED_FILES:
                raise ValueError(f"File is not allowlisted: {relative_path}")

            if relative_path in seen_paths:
                raise ValueError(f"Duplicate file edit: {relative_path}")

            if not isinstance(search, str) or not search:
                raise ValueError("Search text must be non-empty")

            if not isinstance(replacement, str):
                raise ValueError("Replacement must be a string")

            original = source_files.get(relative_path)
            if original is None or original.count(search) != 1:
                raise ValueError(
                    f"Search text must match exactly once in {relative_path}"
                )

            seen_paths.add(relative_path)
            validated.append({
                "path": relative_path,
                "search": search,
                "replace": replacement,
                "original": original,
            })

        proposal_path = (
            self.project_root
            / "artifacts"
            / "proposals"
            / f"{state.workflow_id}.json"
        )
        proposal_path.parent.mkdir(parents=True, exist_ok=True)

        saved_proposal = {
            "workflow_id": state.workflow_id,
            "summary": str(proposal.get("summary", "")),
            "status": "PROPOSED" if validated else "NO_CHANGES",
            "edits": validated,
        }

        proposal_path.write_text(
            json.dumps(saved_proposal, indent=2),
            encoding="utf-8",
        )

        state.audit_events.append({
            "event": "IMPLEMENTATION_PROPOSED",
            "proposal_path": str(proposal_path),
            "files": [edit["path"] for edit in validated],
        })

        return {
            "type": "implementation-proposal",
            **saved_proposal,
            "proposal_path": str(proposal_path),
        }