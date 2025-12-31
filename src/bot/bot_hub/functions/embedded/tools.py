import inspect
from typing import Any, Awaitable, Callable

from bot.bot_hub.functions.types import (
    FunctionInvocationInputs,
    FunctionInvocationOutputs,
    BotFunction,
)
from bot.bot_flow.tools import verify_user


class InlineEmbeddedTool:
    def __init__(
        self,
        name: str,
        description: str,
        schema: dict[str, Any],
        handler: Callable[[..., Any], Awaitable[Any]],
    ):
        self.name = name
        self.description = description
        if "name" not in schema:
            schema["name"] = name
        if "description" not in schema:
            schema["description"] = description
        if "id" not in schema:
            schema["id"] = name
        self.schema = BotFunction.model_validate(schema)
        self.param_count = self.validate_handler(handler)
        self.handler = handler
        self.transition_node_ids = {node.node for node in self.schema.transition_nodes}

    def get_schema(self) -> BotFunction:
        return self.schema

    def validate_handler(self, function: Callable) -> int:
        # Implement validation logic based on self.schema if needed
        if not inspect.iscoroutinefunction(function):
            raise ValueError("Handler must be an async function")
        params = list(inspect.signature(function).parameters.items())
        if len(params) < 1:
            raise ValueError("Handler must accept at least one parameter")
        if len(params) > 4:
            raise ValueError("Handler can accept at most 4 parameters")
        if params[0][0] != "args":
            raise ValueError("First parameter of handler must be 'args'")
        if len(params) > 1:
            if params[1][0] != "state":
                raise ValueError("Second parameter of handler must be 'state'")
        if len(params) > 2:
            if params[2][0] != "bot_id":
                raise ValueError("Third parameter of handler must be 'bot_id'")
        if len(params) > 3:
            if params[3][0] != "user_id":
                raise ValueError("Fourth parameter of handler must be 'user_id'")
        return len(params)

    async def execute(
        self, args: FunctionInvocationInputs
    ) -> FunctionInvocationOutputs:
        try:
            tool_input = args.inputs or {}
            bot_id = args.bot_id
            state = args.bot_state or {}
            if self.param_count == 1:
                output = await self.handler(tool_input)
            elif self.param_count == 2:
                output = await self.handler(tool_input, state)
            elif self.param_count == 3:
                output = await self.handler(tool_input, state, bot_id)
            else:
                user_id = args.user_id
                output = await self.handler(tool_input, state, bot_id, user_id)
            if isinstance(output, FunctionInvocationOutputs):
                return output
            if isinstance(output, dict):
                function_output = output.pop("output", None)
                next_node = output.pop("next_node", None)
                state_updates = output.get("state_updates", None)
                if isinstance(state_updates, dict):
                    del output[state_updates]
                else:
                    state_updates = {}

                if function_output is None and output:
                    function_output = output
                if next_node and next_node not in self.transition_node_ids:
                    next_node = None
                return FunctionInvocationOutputs(
                    output=function_output,
                    next_node=next_node,
                    state_updates=state_updates,
                )
            else:
                return FunctionInvocationOutputs(
                    output=output, next_node=None, state_updates={}
                )
        except Exception as e:
            # Handle exceptions that occur during function execution
            return FunctionInvocationOutputs(
                output={"success": False, "error": str(e)},
                next_node=None,
                state_updates={},
            )


EMBEDDED_TOOLS = [
    InlineEmbeddedTool(
        name="verify_user",
        description="Verify a user based on user OTP and state.",
        schema={
            "parameters": {
                "otp": {
                    "property_type": "string",
                    "required": True,
                    "description": "One Time Password sent to the user for verification.",
                },
            },
            "transition_nodes": [
                {"node": "verified_user"},
                {"node": "unverified_user"},
            ],
        },
        handler=verify_user,
    )
]
