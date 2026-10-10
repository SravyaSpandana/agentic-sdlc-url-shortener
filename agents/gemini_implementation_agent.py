
import json
from pathlib import Path

from agents.base import BaseAgent


class GeminiImplementationAgent(BaseAgent):
    """Generate and safely apply small source-code edits using Gemini."""

    name = "implementation-agent"

    ALLOWED_FILES = {
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

        if not source_files:
            raise ValueError("No allowed source files were found")

        prompt = {
            "requirement": state.requirement,
            "existing_artifacts": {
                key: state.artifacts.get(key)
                for key in ("requirements", "architecture", "security")
                if key in state.artifacts
            },
            "source_files": source_files,
        }

        response = await self.client.generate_text(
            system_prompt=(
                "You are a cautious software engineer modifying an "
                "existing Python FastAPI URL shortener. Inspect the "
                "provided source before proposing changes. Choose one "
                "small, useful, backward-compatible improvement related "
                "to the requirement. Do not rewrite the application. "
                "Return only valid JSON with this shape: "
                '{"summary":"...", "edits":[{"path":"app/...", '
                '"search":"exact existing text", '
                '"replace":"replacement text"}]}. '
                "Each search string must match exactly once. "
                "Only edit the supplied source files. Do not edit tests, "
                "configuration, dependencies, workflows, or security "
                "controls. Do not use shell commands or add dependencies. "
                "If no safe improvement is justified, return an empty "
                "edits list and explain why in summary."
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

        try:
            proposal = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Gemini did not return valid implementation JSON"
            ) from exc

        edits = proposal.get("edits")
        if not isinstance(edits, list):
            raise ValueError("Gemini response must contain an edits list")

        if len(edits) > 3:
            raise ValueError("At most three file edits are allowed")

        # Validate every edit before writing any file.
        validated = []
        seen_paths = set()

        for edit in edits:
            relative_path = edit.get("path")
            search = edit.get("search")
            replacement = edit.get("replace")

            if relative_path not in self.ALLOWED_FILES:
                raise ValueError(
                    f"File is not allowlisted: {relative_path}"
                )

            if relative_path in seen_paths:
                raise ValueError(
                    f"Multiple edits to one file are not supported: "
                    f"{relative_path}"
                )

            if not isinstance(search, str) or not search:
                raise ValueError("Each edit needs non-empty search text")

            if not isinstance(replacement, str):
                raise ValueError("Each edit needs replacement text")

            original = source_files.get(relative_path)
            if original is None:
                raise ValueError(
                    f"Source was not supplied to Gemini: {relative_path}"
                )

            if original.count(search) != 1:
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

        if not validated:
            return {
                "type": "implementation",
                "status": "NO_CHANGES",
                "summary": proposal.get("summary", "No safe change proposed"),
                "files_changed": [],
            }

        # Save backups outside source folders before applying changes.
        backup_dir = (
            self.project_root
            / "artifacts"
            / "implementation-backups"
            / state.workflow_id
        )
        backup_dir.mkdir(parents=True, exist_ok=True)

        changed_paths = []

        try:
            for edit in validated:
                relative_path = edit["path"]
                target = (self.project_root / relative_path).resolve()

                if not target.is_relative_to(self.project_root):
                    raise ValueError("Target path escaped project root")

                # Detect source changes made after Gemini read the files.
                current = target.read_text(encoding="utf-8")
                if current != edit["original"]:
                    raise RuntimeError(
                        f"Source changed during generation: {relative_path}"
                    )

                backup_path = backup_dir / relative_path.replace("/", "__")
                backup_path.write_text(current, encoding="utf-8")

                updated = current.replace(
                    edit["search"],
                    edit["replace"],
                    1,
                )
                target.write_text(updated, encoding="utf-8")
                changed_paths.append(relative_path)

        except Exception:
            # Best-effort restoration if an edit fails partway through.
            for edit in validated:
                relative_path = edit["path"]
                target = self.project_root / relative_path
                backup_path = backup_dir / relative_path.replace("/", "__")
                if backup_path.is_file():
                    target.write_text(
                        backup_path.read_text(encoding="utf-8"),
                        encoding="utf-8",
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