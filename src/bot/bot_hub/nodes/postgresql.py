"""
PostgreSQL-based node provider implementation.

This module provides a PostgreSQL implementation of the NodeInterface
"""

from typing import Dict, List
from uuid import UUID

from loguru import logger
from sqlalchemy import delete, select

from bot.bot_hub.functions.base import EmptyFunctionsProvider
from bot.bot_hub.functions.embedded.provider import (
    EmbeddedFunctionProvider,
)
from bot.bot_hub.functions.interface import (
    FunctionProviderInterface,
)
from bot.bot_hub.functions.types import FunctionInstance
from bot.bot_hub.nodes.interface import NodeInterface
from bot.bot_hub.types import (
    BotNode,
    BotNodeMeta,
    FunctionsProviderType,
)
from bot.config import settings
from bot.deps import AsyncSession, AsyncSessionLocal
from bot.models.bot_models import FunctionMapping, Node


class PostgreSQLNodeProvider(NodeInterface):
    """
    PostgreSQL-based node provider.

    the create_bot method to automatically create initial nodes with the correct UUID.
    """

    def __init__(self):
        """Initialize the PostgreSQL node provider."""

    def _get_function_provider(self) -> FunctionProviderInterface:
        """
        Get the function provider instance based on settings.

        Returns:
            FunctionProviderInterface: The function provider instance
        """
        if (
            str(settings.hub_config.functions_provider)
            == FunctionsProviderType.EMBEDDED
        ):
            return EmbeddedFunctionProvider()
        else:
            # Default to empty provider if unknown type
            return EmptyFunctionsProvider()

    async def delete_node(self, bot_id: UUID, node_id: UUID) -> bool:
        """
        Delete a complete node by its identifier.

        Args:
            node_id: The identifier for the node

        Returns:
            bool: True if the node was deleted successfully, False otherwise
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    delete(Node).where(Node.node_id == node_id, Node.bot_id == bot_id)
                )
                await session.commit()

                deleted = result.rowcount > 0
                if deleted:
                    logger.info(f"Deleted node {node_id} for bot {bot_id}")
                return deleted

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete node {node_id} for bot {bot_id}: {e}")
                raise RuntimeError(f"Node deletion failed: {e}")

    async def list_nodes(self, bot_id: UUID) -> List[BotNodeMeta]:
        """
        List all available node IDs for the current bot.

        Args:
            bot_id: The identifier for the bot
        Returns:
            List[BotNodeMeta]: A list of nodes that are available
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Node).where(Node.bot_id == bot_id)
                )
                return [
                    BotNodeMeta(
                        bot_id=i.bot_id, node_id=i.node_id, node_name=i.node_name
                    )
                    for i in result.scalars().all()
                ]
                # Convert UUID objects to strings

            except Exception as e:
                logger.error(f"Failed to list nodes for bot {bot_id}: {e}")
                raise RuntimeError(f"Node listing failed: {e}")

    async def get_node(self, bot_id: UUID, node_id: UUID) -> BotNode:
        """
        Get a complete node with its prompt content by its identifier.

        Args:
            node_id: The identifier for the node

        Returns:
            BotNode: The complete node object with id and prompt content
        """
        async with AsyncSessionLocal() as session:
            try:
                # Query 1: Get node data (prompt)
                node_result = await session.execute(
                    select(Node).where(Node.node_id == node_id, Node.bot_id == bot_id)
                )
                node = node_result.scalar_one_or_none()

                if not node:
                    raise FileNotFoundError(f"Node not found: {node_id}")

                functions = await self._get_associated_functions(
                    session=session, bot_id=bot_id, node_id=node_id
                )
                # Return BotNode with stitched data
                return BotNode(
                    bot_id=node.bot_id,
                    node_id=node.node_id,
                    node_name=node.node_name,
                    prompt=node.prompt,
                    functions=functions,
                )

            except FileNotFoundError:
                raise
            except Exception as e:
                logger.error(f"Failed to get node {node_id} for bot {bot_id}: {e}")
                raise RuntimeError(f"Node retrieval failed: {e}")

    async def update_node(self, bot_id: UUID, node_id: UUID, prompt: str) -> BotNode:
        """
        Save a complete node with its prompt content.

        Args:
            bot_id: The id of the bot to which node belongs
            node_id: The id of the node object to update
            prompt: The updated prompt to set for the node

        Returns:
            BotNode: The saved node object
        """

        async with AsyncSessionLocal() as session:
            try:
                # Check if node exists
                result = await session.execute(
                    select(Node).where(Node.node_id == node_id, Node.bot_id == bot_id)
                )
                existing_node = result.scalar_one_or_none()

                if existing_node:
                    # Update existing node
                    existing_node.prompt = prompt
                else:
                    raise FileNotFoundError
                session.add(existing_node)
                await session.commit()
                await session.refresh(existing_node)
                logger.info(f"Saved prompt for bot {bot_id}")
                functions = await self._get_associated_functions(
                    session=session, bot_id=bot_id, node_id=node_id
                )
                return BotNode(
                    bot_id=existing_node.bot_id,
                    node_id=existing_node.node_id,
                    node_name=existing_node.node_name,
                    prompt=existing_node.prompt,
                    functions=functions,
                )

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save prompts for bot {bot_id}: {e}")
                raise RuntimeError(f"Prompt save failed: {e}")

    async def create_node(
        self, bot_id: UUID, node_name: str, prompt: str = ""
    ) -> BotNode:
        """
        Create a new node with its prompt content.

        Args:
            bot_id: The bot id to create a node for
            node_name: The display name of the created node
            prompt: Optional prompt to seed the node with

        Returns:
            BotNode: The created node object
        """

        async with AsyncSessionLocal() as session:
            try:
                new_node = Node(bot_id=bot_id, node_name=node_name, prompt=prompt)
                session.add(new_node)
                await session.commit()
                await session.refresh(new_node)
                logger.info(f"Saved prompt for bot {bot_id}")
                return BotNode(
                    bot_id=new_node.bot_id,
                    node_id=new_node.node_id,
                    node_name=new_node.node_name,
                    prompt=new_node.prompt,
                )

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save prompts for bot {bot_id}: {e}")
                raise RuntimeError(f"Prompt save failed: {e}")

    async def register_function(
        self,
        bot_id: UUID,
        node_id: UUID,
        function_id: str,
        function_label: str,
        transition_mappings: Dict[str, str],
    ) -> BotNode:
        """
        Register a new function for a specific node.

        Args:
            node_id: The identifier for the node
            function_id: The identifier for the function
            transition_mappings: The transition mappings for the function

        Returns:
            BotNode: The updated node object with the registered function

        Raises:
            ValueError: If the function does not exist in the function provider
            RuntimeError: If function registration fails
        """
        # Validate that the function exists in the function provider
        function_provider_instance = self._get_function_provider()
        try:
            await function_provider_instance.get_function_schema(function_id)
        except ValueError as e:
            logger.error(
                f"Function {function_id} is not supported by the function provider: {e}"
            )
            raise ValueError(
                f"Function '{function_id}' is not supported by the current function provider"
            ) from e
        except Exception as e:
            logger.error(
                f"Failed to validate function {function_id} in function provider: {e}"
            )
            raise ValueError(
                f"Function '{function_id}' is not supported by the current function provider"
            ) from e

        function_provider = str(settings.hub_config.functions_provider)
        async with AsyncSessionLocal() as session:
            try:
                func_mapping = FunctionMapping(
                    bot_id=bot_id,
                    node_id=node_id,
                    function_id=function_id,
                    function_label=function_label,
                    function_provider_id=function_provider,
                    transition_mappings=transition_mappings or {},
                    pre_say_config={},
                )
                session.add(func_mapping)
                await session.commit()
                logger.info(f"Registered function {function_id} to node {node_id}")
                return await self.get_node(bot_id, node_id)

            except Exception as e:
                await session.rollback()
                logger.error(
                    f"Failed to register function {function_id} to node {node_id}: {e}"
                )
                raise RuntimeError(f"Function registration failed: {e}")

    async def update_node_function(
        self, bot_id: UUID, node_id: UUID, function_id: UUID, instance: FunctionInstance
    ) -> BotNode:
        async with AsyncSessionLocal() as session:
            try:
                # Check if node exists
                result = await session.execute(
                    select(FunctionMapping).where(
                        FunctionMapping.node_id == node_id,
                        FunctionMapping.bot_id == bot_id,
                        FunctionMapping.id == function_id,
                    )
                )
                existing_function = result.scalar_one_or_none()

                if existing_function:
                    # Update existing node
                    existing_function.transition_mappings = instance.transition_mappings
                    existing_function.function_label = instance.function_label
                    existing_function.pre_say_config = instance.pre_say
                    existing_function.ack_llm_description = instance.ack_llm_description
                else:
                    raise FileNotFoundError
                session.add(existing_function)
                await session.commit()
                await session.refresh(existing_function)
                logger.info(f"Saved function for bot {bot_id} node {node_id}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save prompts for bot {bot_id}: {e}")
                raise RuntimeError(f"Prompt save failed: {e}")
        return await self.get_node(bot_id, node_id)

    async def delete_node_function(
        self, bot_id: UUID, node_id: UUID, function_id: UUID
    ) -> BotNode:
        async with AsyncSessionLocal() as session:
            try:
                # Check if node exists
                result = await session.execute(
                    select(FunctionMapping).where(
                        FunctionMapping.node_id == node_id,
                        FunctionMapping.bot_id == bot_id,
                        FunctionMapping.id == function_id,
                    )
                )
                existing_function = result.scalar_one_or_none()

                await session.delete(existing_function)
                await session.commit()
                logger.info(f"Saved function for bot {bot_id} node {node_id}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save prompts for bot {bot_id}: {e}")
                raise RuntimeError(f"Prompt save failed: {e}")
        return await self.get_node(bot_id, node_id)

    async def _get_associated_functions(
        self, session: AsyncSession, bot_id: UUID, node_id: UUID
    ) -> List[FunctionInstance]:
        """
        Register a new function for a specific node.

        Args:
            node_id: The identifier for the node
            function_id: The identifier for the function
            transition_mappings: The transition mappings for the function

        Returns:
            BotNode: The updated node object with the registered function
        """

        func_result = await session.execute(
            select(FunctionMapping).where(
                FunctionMapping.bot_id == bot_id, FunctionMapping.node_id == node_id
            )
        )
        function_mappings = func_result.scalars().all()

        # Stitch together - convert function_mappings to FunctionInstance objects
        functions = [
            FunctionInstance(
                id=fm.id,  # Use the database id
                function_id=fm.function_id,
                node_id=fm.node_id,  # Add the node_id
                bot_id=fm.bot_id,  # Add the bot_id
                transition_mappings=fm.transition_mappings or {},
                pre_say=fm.pre_say_config or {},
                ack_llm_description=fm.ack_llm_description,
            )
            for fm in function_mappings
        ]
        return functions

    async def delete_bot(self, bot_id: UUID) -> None:
        """
        Delete all node data for a specific bot.

        Args:
            bot_id: The identifier for the bot to delete

        Raises:
            ValueError: If bot_id is invalid
            RuntimeError: If bot deletion fails
            FileNotFoundError: If bot nodes don't exist
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    delete(Node).where(Node.bot_id == bot_id)
                )
                await session.commit()

                deleted = result.rowcount > 0
                if deleted:
                    logger.info(f"Deleted nodes for bot {bot_id}")
                return deleted

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete node for bot {bot_id}: {e}")
                raise RuntimeError(f"Node deletion failed: {e}")
