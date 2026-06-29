from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional

class BaseAgent(ABC):
    """
    Abstract Base Class for all AI Agents in the platform (Chef, Gardener, Baker, etc.).
    Enforces standardized interfaces for simple chat, streaming, and tool execution.
    """
    def __init__(self, name: str, description: str, system_prompt: str):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt

    @abstractmethod
    async def chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        diet_preference: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Processes a single user message and returns a fully completed string response.
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        message: str,
        history: List[Dict[str, str]],
        diet_preference: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Processes a user message and yields token chunks asynchronously for real-time streaming.
        """
        pass

    @abstractmethod
    def get_tools(self) -> List[Any]:
        """
        Returns a list of callable tool definitions bound to this agent.
        """
        pass
