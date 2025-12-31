from typing import List

from bot.bot_hub.functions.embedded.tools import EMBEDDED_TOOLS
from bot.bot_hub.functions.interface import (
    FunctionProviderInterface,
)
from bot.bot_hub.functions.types import (
    FunctionInstance,
    FunctionInvocationInputs,
    FunctionInvocationOutputs,
    BotFunction,
)


class EmbeddedFunctionProvider(FunctionProviderInterface):
    def __init__(self):
        super().__init__()
        self._functions = {function.name: function for function in EMBEDDED_TOOLS}

    async def list_functions(self) -> List[BotFunction]:
        """List Functions available in the provider."""
        return [function.schema for function in self._functions.values()]

    async def get_function_schema(self, function_id: str) -> BotFunction:
        """Get the schema for a specific function by its ID."""
        function = self._functions.get(function_id)
        if function:
            return function.get_schema()
        else:
            raise ValueError(f"Function with {function_id} not registered to tools")

    async def invoke_function(
        self, function: FunctionInstance, inputs: FunctionInvocationInputs
    ) -> FunctionInvocationOutputs:
        """Invoke a function with the given inputs and return the outputs."""
        embedded_tool = self._functions.get(function.function_id)
        if not embedded_tool:
            raise ValueError(
                f"Function with ID {function.function_id} not found in EmbeddedFunctionProvider."
            )

        # Execute the handler
        result = await embedded_tool.execute(inputs)
        return result
