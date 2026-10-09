from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskDefinition:
    task_id: str
    agent_name: str

    dependencies: list[str] = field(
        default_factory=list
    )

    requires_approval: bool = False

    critical: bool = False

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class WorkflowGraph:

    def __init__(self):
        self.tasks: dict[str, TaskDefinition] = {}

    def add_task(
        self,
        task: TaskDefinition,
    ) -> None:

        if task.task_id in self.tasks:
            raise ValueError(
                f"Task already exists: {task.task_id}"
            )

        if task.task_id in task.dependencies:
            raise ValueError(
                f"Task cannot depend on itself: {task.task_id}"
            )

        self.tasks[task.task_id] = task

    def get_task(
        self,
        task_id: str,
    ) -> TaskDefinition:

        return self.tasks[task_id]

    def get_ready_tasks(
        self,
        completed_tasks: set[str],
    ) -> list[TaskDefinition]:

        ready = []

        for task in self.tasks.values():

            if task.task_id in completed_tasks:
                continue

            if all(
                dependency in completed_tasks
                for dependency in task.dependencies
            ):
                ready.append(task)

        return ready

    def validate(self) -> None:
        """
        Validate the workflow graph before execution.

        Checks:
        - all dependencies exist
        - no circular dependencies
        """

        self._validate_dependencies()
        self._validate_no_cycles()

    def _validate_dependencies(self) -> None:

        for task in self.tasks.values():

            for dependency in task.dependencies:

                if dependency not in self.tasks:
                    raise ValueError(
                        f"Task '{task.task_id}' "
                        f"depends on unknown task '{dependency}'"
                    )

    def _validate_no_cycles(self) -> None:

        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(task_id: str) -> None:

            if task_id in visiting:
                raise ValueError(
                    f"Circular dependency detected involving "
                    f"task '{task_id}'"
                )

            if task_id in visited:
                return

            visiting.add(task_id)

            task = self.tasks[task_id]

            for dependency in task.dependencies:
                visit(dependency)

            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in self.tasks:
            visit(task_id)