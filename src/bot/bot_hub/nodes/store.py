"""
Store-based prompt provider implementation.

This module provides a store-based implementation of the NodeInterface
that uses a BotStoreInterface instance to manage prompts and node data.
"""

from typing import List
from uuid import UUID

from loguru import logger

from bot.bot_hub.nodes.interface import NodeInterface
from bot.bot_hub.types import BotNode
from bot.store.bot_store.interface import BotStoreInterface


class StoreNodeProvider(NodeInterface):
    """
    Store-based prompt provider.

    This provider uses a BotStoreInterface instance to manage prompts and node data,
    providing a unified interface for accessing bot nodes through various storage backends.
    """

    def __init__(self, bot_store: BotStoreInterface):
        """
        Initialize the store-based prompt provider.

        Args:
            bot_store: BotStoreInterface instance for data operations
        """
        self.bot_store = bot_store
        self.bot_id: UUID = bot_store.bot_id
        logger.info(f"Initialized StoreNodeProvider for bot '{self.bot_id}'")

    async def delete_node(self, node_id: UUID) -> bool:
        """
        Delete a complete node by its identifier.

        Args:
            node_id: The identifier for the node

        Returns:
            bool: True if the node was deleted successfully, False otherwise
        """
        try:
            result = await self.bot_store.delete_prompt(node_id)
            if result:
                logger.info(
                    f"Successfully deleted node '{node_id}' for bot '{self.bot_id}'"
                )
            else:
                logger.warning(
                    f"Failed to delete node '{node_id}' for bot '{self.bot_id}'"
                )
            return result
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            logger.error(
                f"Error deleting node '{node_id}' for bot '{self.bot_id}': {e}"
            )
            return False

    async def list_node_ids(self) -> List[str]:
        """
        List all available node IDs for the current bot.

        Returns:
            List[str]: A list of node IDs that are available
        """
        try:
            node_ids = await self.bot_store.list_nodes()
            logger.debug(f"Found {len(node_ids)} nodes for bot '{self.bot_id}'")
            return sorted(node_ids)
        except RuntimeError as e:
            logger.error(f"Error listing nodes for bot '{self.bot_id}': {e}")
            return []

    async def get_node(self, node_id: UUID) -> BotNode:
        """
        Get a complete node with its prompt content by its identifier.

        Args:
            node_id: The identifier for the node

        Returns:
            BotNode: The complete node object with id and prompt content
        """
        try:
            node = await self.bot_store.get_node(node_id)
            logger.debug(f"Retrieved node '{node_id}' for bot '{self.bot_id}'")
            return node
        except FileNotFoundError:
            # Return an empty node if not found
            logger.warning(
                f"Node '{node_id}' not found for bot '{self.bot_id}', returning empty node"
            )
            return BotNode(node_id=node_id, prompt="")
        except (ValueError, RuntimeError) as e:
            logger.error(
                f"Error retrieving node '{node_id}' for bot '{self.bot_id}': {e}"
            )
            return BotNode(node_id=node_id, prompt="")

    async def _save_node(self, node: BotNode) -> BotNode:
        """
        Save a complete node with its prompt content.

        Args:
            node: The BotNode object to save

        Returns:
            BotNode: The saved node object
        """
        try:
            # Save the node using the store interface
            success = await self.bot_store.save_prompts([node])
            if not success:
                raise RuntimeError(
                    f"Failed to save node '{node.node_id}' for bot '{self.bot_id}'"
                )

            logger.info(
                f"Successfully saved node '{node.node_id}' for bot '{self.bot_id}'"
            )
            return node
        except (ValueError, RuntimeError) as e:
            logger.error(
                f"Error saving node '{node.node_id}' for bot '{self.bot_id}': {e}"
            )
            raise

    async def create_node(self, node: BotNode) -> BotNode:
        """
        Create a new node with its prompt content.

        Args:
            node: The BotNode object to create

        Returns:
            BotNode: The created node object
        """
        return await self._save_node(node)

    @classmethod
    async def delete_bot(cls, bot_id: UUID) -> None:
        """
        Delete all node data for a specific bot.

        Args:
            bot_id: The identifier for the bot to delete

        Raises:
            ValueError: If bot_id is invalid
            RuntimeError: If bot deletion fails
            FileNotFoundError: If bot nodes don't exist
        """
        raise NotImplementedError(
            "StoreNodeProvider does not support class method operations"
        )
