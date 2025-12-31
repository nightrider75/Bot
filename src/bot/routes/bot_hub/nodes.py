"""
Bot Hub Nodes (Prompts) routes.

This module provides API endpoints for managing node prompts in the bot hub.
"""

from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bot_engine.services.llm_service import PreSayMap

from bot.bot_hub.functions.types import (
    FunctionInstance,
    BotFunction,
)
from bot.bot_hub.hub import BotHub
from bot.bot_hub.node_template_utils import templatize

router = APIRouter()


class NodeRequest(BaseModel):
    """Request model for prompt operations."""

    node_name: str
    prompt: str


class PromptRequest(BaseModel):
    """Request model for prompt operations."""

    prompt: str


class FunctionIntegration(BaseModel):
    id: UUID
    function_id: str
    function_label: str
    function_schema: BotFunction
    node_id: UUID
    bot_id: UUID
    transition_mappings: Dict[str, str] = dict()
    pre_say: PreSayMap = dict()
    ack_llm_description: Optional[str] = None


class NodeResponse(BaseModel):
    """Response model for node operations."""

    node_id: UUID
    prompt: str
    functions: List[FunctionIntegration]


class FunctionInstanceRequest(BaseModel):
    function_id: str
    function_label: Optional[str] = None
    transition_mappings: Dict[str, str] = dict()
    pre_say: PreSayMap = dict()
    ack_llm_description: Optional[str] = None


class NodeBaseData(BaseModel):
    """Response model for listing nodes."""

    node_id: UUID
    bot_id: UUID
    node_name: str


class NodesListResponse(BaseModel):
    """Response model for listing nodes."""

    nodes: List[NodeBaseData]


@router.get("/{bot_id}/nodes", response_model=NodesListResponse)
async def list_nodes(bot_id: UUID):
    """
    List all available nodes for a bot.

    Args:
        bot_id: The identifier for the bot

    Returns:
        NodesListResponse: List of available node IDs
    """
    try:
        hub = BotHub(bot_id)
        nodes = await hub.list_nodes()
        return NodesListResponse(
            nodes=[
                NodeBaseData(node_id=i.node_id, bot_id=i.bot_id, node_name=i.node_name)
                for i in nodes
            ]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list nodes: {str(e)}"
        ) from e


@router.get("/{bot_id}/nodes/{node_id}", response_model=NodeResponse)
async def get_node(bot_id: UUID, node_id: UUID):
    """
    Get a specific node.

    Args:
        bot_id: The identifier for the bot
        node_id: The identifier for the node

    Returns:
        NodeResponse: The content response for the node
    """
    try:
        hub = BotHub(bot_id)

        node = await hub.node_provider.get_node(bot_id, node_id)
        functions = [
            FunctionIntegration(
                id=func.id,
                function_id=func.function_id,
                function_label=func.function_label or func.function_id,
                function_schema=await hub.functions_provider.get_function_schema(
                    func.function_id
                ),
                node_id=func.node_id,
                bot_id=func.bot_id,
                transition_mappings=func.transition_mappings,
                pre_say=func.pre_say,
                ack_llm_description=func.ack_llm_description,
            )
            for func in node.functions
        ]
        return NodeResponse(
            node_id=node.node_id, prompt=node.prompt, functions=functions
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get prompt: {str(e)}"
        ) from e


@router.post("/{bot_id}/nodes/", response_model=NodeResponse)
@router.put("/{bot_id}/nodes/", response_model=NodeResponse)
async def create_node(bot_id: UUID, request: NodeRequest):
    """
    Save a prompt for a specific node.

    Args:
        bot_id: The identifier for the bot
        node_id: The identifier for the node
        request: The prompt content to save

    Returns:
        NodeResponse: Confirmation of the saved prompt
    """
    try:
        hub = BotHub(bot_id)

        try:
            templatize(request.prompt, {})
        except Exception as e:
            return HTTPException(
                status_code=400, detail=f"Incorrectly templatized prompt: {e}"
            )

        node = await hub.node_provider.create_node(
            bot_id=bot_id, node_name=request.node_name, prompt=request.prompt
        )
        functions = [
            FunctionIntegration(
                id=func.id,
                function_id=func.function_id,
                function_label=func.function_label or func.function_id,
                function_schema=await hub.functions_provider.get_function_schema(
                    func.function_id
                ),
                node_id=func.node_id,
                bot_id=func.bot_id,
                transition_mappings=func.transition_mappings,
                pre_say=func.pre_say,
                ack_llm_description=func.ack_llm_description,
            )
            for func in node.functions
        ]
        return NodeResponse(
            node_id=node.node_id, prompt=node.prompt, functions=functions
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save prompt: {str(e)}"
        ) from e


@router.post("/{bot_id}/nodes/{node_id}/prompt", response_model=NodeResponse)
@router.put("/{bot_id}/nodes/{node_id}/prompt", response_model=NodeResponse)
async def save_node_prompt(bot_id: UUID, node_id: UUID, request: PromptRequest):
    """
    Save a prompt for a specific node.

    Args:
        bot_id: The identifier for the bot
        node_id: The identifier for the node
        request: The prompt content to save

    Returns:
        NodeResponse: Confirmation of the saved prompt
    """
    try:
        hub = BotHub(bot_id)

        try:
            templatize(request.prompt, {})
        except Exception as e:
            return HTTPException(
                status_code=400, detail=f"Incorrectly templatized prompt: {e}"
            )

        node = await hub.node_provider.update_node(
            bot_id=bot_id, node_id=node_id, prompt=request.prompt
        )
        functions = [
            FunctionIntegration(
                id=func.id,
                function_id=func.function_id,
                function_label=func.function_label or func.function_id,
                function_schema=await hub.functions_provider.get_function_schema(
                    func.function_id
                ),
                node_id=func.node_id,
                bot_id=func.bot_id,
                transition_mappings=func.transition_mappings,
                pre_say=func.pre_say,
                ack_llm_description=func.ack_llm_description,
            )
            for func in node.functions
        ]
        return NodeResponse(
            node_id=node.node_id, prompt=node.prompt, functions=functions
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save prompt: {str(e)}"
        ) from e


@router.delete("/{bot_id}/nodes/{node_id}")
async def delete_node(bot_id: UUID, node_id: UUID):
    """
    Delete the prompt for a specific node.

    Args:
        bot_id: The identifier for the bot
        node_id: The identifier for the node

    Returns:
        dict: Confirmation of deletion
    """
    try:
        hub = BotHub(bot_id)

        success = await hub.node_provider.delete_node(node_id)
        if success:
            return {"message": f"Prompt for node '{node_id}' deleted successfully"}
        else:
            raise HTTPException(
                status_code=404, detail=f"Prompt for node '{node_id}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete prompt: {str(e)}"
        ) from e


@router.post("/{bot_id}/nodes/{node_id}/function", response_model=NodeResponse)
@router.put("/{bot_id}/nodes/{node_id}/function", response_model=NodeResponse)
async def create_node_function(
    bot_id: UUID, node_id: UUID, request: FunctionInstanceRequest
):
    """
    Save a function for a specific node.

    Args:
        bot_id: The identifier for the bot
        node_id: The identifier for the node
        request: The function instance request to save

    Returns:
        NodeResponse: Confirmation of the saved function
    """
    try:
        hub = BotHub(bot_id)

        node = await hub.node_provider.register_function(
            bot_id,
            node_id,
            request.function_id,
            request.function_label or request.function_id,
            request.transition_mappings,
        )
        functions = [
            FunctionIntegration(
                id=func.id,
                function_id=func.function_id,
                function_label=func.function_label or func.function_id,
                function_schema=await hub.functions_provider.get_function_schema(
                    func.function_id
                ),
                node_id=func.node_id,
                bot_id=func.bot_id,
                transition_mappings=func.transition_mappings,
                pre_say=func.pre_say,
                ack_llm_description=func.ack_llm_description,
            )
            for func in node.functions
        ]
        return NodeResponse(
            node_id=node.node_id, prompt=node.prompt, functions=functions
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save function: {str(e)}"
        ) from e


@router.post(
    "/{bot_id}/nodes/{node_id}/function/{function_id}", response_model=NodeResponse
)
@router.put(
    "/{bot_id}/nodes/{node_id}/function/{function_id}", response_model=NodeResponse
)
async def update_node_function(
    bot_id: UUID, node_id: UUID, function_id: UUID, request: FunctionInstanceRequest
):
    """
    Save a function for a specific node.

    Args:
        bot_id: The identifier for the bot
        node_id: The identifier for the node
        request: The function instance request to save

    Returns:
        NodeResponse: Confirmation of the saved function
    """
    try:
        hub = BotHub(bot_id)

        node = await hub.node_provider.update_node_function(
            bot_id,
            node_id,
            function_id,
            FunctionInstance(
                id=function_id,
                function_id=request.function_id,
                function_label=request.function_label or request.function_id,
                node_id=node_id,
                bot_id=bot_id,
                transition_mappings=request.transition_mappings,
                pre_say=request.pre_say,
                ack_llm_description=request.ack_llm_description,
            ),
        )
        functions = [
            FunctionIntegration(
                id=func.id,
                function_id=func.function_id,
                function_label=func.function_label or func.function_id,
                function_schema=await hub.functions_provider.get_function_schema(
                    func.function_id
                ),
                node_id=func.node_id,
                bot_id=func.bot_id,
                transition_mappings=func.transition_mappings,
                pre_say=func.pre_say,
                ack_llm_description=func.ack_llm_description,
            )
            for func in node.functions
        ]
        return NodeResponse(
            node_id=node.node_id, prompt=node.prompt, functions=functions
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save function: {str(e)}"
        ) from e


@router.delete(
    "/{bot_id}/nodes/{node_id}/function/{function_id}", response_model=NodeResponse
)
async def delete_node_function(bot_id: UUID, node_id: UUID, function_id: UUID):
    """
    Save a function for a specific node.

    Args:
        bot_id: The identifier for the bot
        node_id: The identifier for the node
        request: The function instance request to save

    Returns:
        NodeResponse: Confirmation of the saved function
    """
    try:
        hub = BotHub(bot_id)

        node = await hub.node_provider.delete_node_function(
            bot_id, node_id, function_id
        )
        functions = [
            FunctionIntegration(
                id=func.id,
                function_id=func.function_id,
                function_label=func.function_label or func.function_id,
                function_schema=await hub.functions_provider.get_function_schema(
                    func.function_id
                ),
                node_id=func.node_id,
                bot_id=func.bot_id,
                transition_mappings=func.transition_mappings,
                pre_say=func.pre_say,
            )
            for func in node.functions
        ]
        return NodeResponse(
            node_id=node.node_id, prompt=node.prompt, functions=functions
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save function: {str(e)}"
        ) from e
