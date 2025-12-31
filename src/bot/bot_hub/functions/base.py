"""
Empty functions provider implementation.

This module provides an empty implementation of the FunctionsInterface
that does not store anything and always returns empty results.
"""

from typing import List

from bot.bot_hub.functions.interface import (
    FunctionProviderInterface,
)
from bot.bot_hub.functions.types import (
    FunctionInstance,
    FunctionInvocationInputs,
    FunctionInvocationOutputs,
    BotFunction,
)


class EmptyFunctionsProvider(FunctionProviderInterface):
    """
    Empty functions provider that does not store any functions.

    This provider implements the FunctionsInterface but does not maintain
    any state or storage. It always returns empty results for all operations.
    Useful for bots that don't require custom functions or for testing scenarios.
    """

    def __init__(self):
        """Initialize the empty functions provider."""

    async def list_functions(self) -> List[BotFunction]:
        return []

    async def get_function_schema(self, function_id: str) -> BotFunction:
        raise NotImplementedError("Functions are not implemented by base provider")

    async def invoke_function(
        self, function: FunctionInstance, inputs: FunctionInvocationInputs
    ) -> FunctionInvocationOutputs:
        return FunctionInvocationOutputs(
            output="Error running function: function implementation not found"
        )
