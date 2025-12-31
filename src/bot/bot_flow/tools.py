from loguru import logger
from bot_engine.frames.frames import EndFrame
from flows_test.manager import FlowManager
from flows_test.types import FlowArgs, FlowResult

from bot.bot_hub.functions.types import FunctionInvocationOutputs


async def get_rag_context(args: FlowArgs, flow_manager: FlowManager) -> FlowResult:
    logger.debug(f"Fetching RAG context with {args}")
    # WIll be implemented later
    return {"status": "success", "message": "RAG context fetched successfully."}


async def end_call(args: FlowArgs, flow_manager: FlowManager) -> FlowResult:
    """
    Use this tool to get the list of loans availed by the customer.
    """
    logger.debug("Ending call now")
    flow_manager.task.queue_frame(EndFrame())
    return {"status": "success"}


async def verify_user(args: dict, state: dict) -> FunctionInvocationOutputs:
    """
    Use this tool to get the list of loans availed by the customer.
    """
    logger.debug("Verifying user now")
    # Implement user verification logic here
    user_otp = args.get("otp")
    actual_otp = state.get("expected_otp") or "729"
    if user_otp != actual_otp:
        return FunctionInvocationOutputs(
            output={"status": "failure", "message": "OTP verification failed."},
            next_node="unverified_user",
        )
    return FunctionInvocationOutputs(
        output={"status": "success", "message": "User verified successfully."},
        next_node="verified_user",
    )
