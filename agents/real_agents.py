
import asyncio
import sys
from pathlib import Path

from agents.base import BaseAgent


class RealTestAgent(BaseAgent):
    """Runs the project's actual pytest suite."""

    name = "test-agent"

    def __init__(
        self,
        project_root: Path | None = None,
        timeout_seconds: int = 120,
    ):
        self.project_root = (
            project_root or Path(__file__).resolve().parent.parent
        ).resolve()
        self.timeout_seconds = timeout_seconds

    async def execute(self, state):
        tests_dir = self.project_root / "tests"

        if not tests_dir.is_dir():
            raise ValueError(
                f"Tests directory not found: {tests_dir}"
            )

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pytest",
                "-q",
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(
                    f"pytest exceeded {self.timeout_seconds} seconds"
                )

        except OSError as exc:
            raise RuntimeError(
                f"Could not start pytest: {exc}"
            ) from exc

        output = stdout.decode("utf-8", errors="replace")
        result = {
            "type": "test-results",
            "status": (
                "PASS" if process.returncode == 0 else "FAIL"
            ),
            "exit_code": process.returncode,
            "command": "python -m pytest -q",
            "output": output[-12000:],
        }

        # Keep the actual result visible in the workflow audit.
        state.audit_events.append({
            "event": "TEST_EXECUTION_COMPLETED",
            "exit_code": process.returncode,
            "status": result["status"],
        })

        return result