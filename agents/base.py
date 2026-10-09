from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Base contract for all SDLC agents.
    """

    name: str = "base-agent"

    @abstractmethod
    async def execute(
        self,
        state: Any,
    ) -> dict:
        """
        Execute the agent against the current workflow state.
        """
        raise NotImplementedError