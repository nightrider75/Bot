from abc import ABC, abstractmethod
from typing import List, Optional

from bot.bot_hub.functions.types import (
    FunctionInstance,
    FunctionInvocationInputs,
    FunctionInvocationOutputs,
    BotFunction,
)


class FunctionProviderInterface(ABC):
    @abstractmethod
    async def list_functions(self) -> List[BotFunction]:
        """List Functions available in the provider."""

    @abstractmethod
    async def get_function_schema(self, function_id: str) -> Optional[BotFunction]:
        """Get the schema for a specific function by its ID."""

    @abstractmethod
    async def invoke_function(
        self, function: FunctionInstance, inputs: FunctionInvocationInputs
    ) -> FunctionInvocationOutputs:
        """Invoke a function with the given inputs and return the outputs."""
