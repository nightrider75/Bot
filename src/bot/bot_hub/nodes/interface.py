from abc import ABC, abstractmethod
from typing import Dict, List
from uuid import UUID

from bot.bot_hub.functions.types import FunctionInstance
from bot.bot_hub.types import BotNode, BotNodeMeta


class NodeInterface(ABC):
    """
    Interface for node management operations.

    This interface defines all methods related to managing nodes
    for specific nodes in the bot flow.
    """

    @abstractmethod
    async def delete_node(self, bot_id: UUID, node_id: UUID) -> bool:
        """
        Delete a complete node by its identifier.

        Args:
            bot_id: The identifier for the bot that contains the node
            node_id: The identifier for the node

        Returns:
            bool: True if the node was deleted successfully, False otherwise
        """

    @abstractmethod
    async def list_nodes(self, bot_id: UUID) -> List[BotNodeMeta]:
        """
        List all available node IDs for the current bot.
        Args:
            bot_id: The identifier for the bot to list nodes from

        Returns:
            List[BotNodeMeta]: A list of nodes that are available
        """

    @abstractmethod
    async def get_node(self, bot_id: UUID, node_id: UUID) -> BotNode:
        """
        Get a complete node with its prompt content by its identifier.

        Args:
            bot_id: The identifier for the bot
            node_id: The identifier for the node

        Returns:
            BotNode: The complete node object with id and prompt content
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
            bot_id: The identifier for the bot
            node_id: The identifier for the node
            function_id: The identifier for the function
            function_label: The label for the function
            transition_mappings: The transition mappings for the function

        Returns:
            BotNode: The updated node object with the registered function
        """

    @abstractmethod
    async def update_node_function(
        self, bot_id: UUID, node_id: UUID, function_id: UUID, instance: FunctionInstance
    ) -> BotNode:
        """
        Save a complete node with its prompt content.

        Args:
            bot_id: The id of the bot to which node belongs
            node_id: The id of the node object to update
            function_id: The id of the function integration object to update
            instance: The update object containing the state of the function

        Returns:
            BotNode: The saved node object
        """

    @abstractmethod
    async def delete_node_function(
        self, bot_id: UUID, node_id: UUID, function_id: UUID
    ) -> BotNode:
        """
        Save a complete node with its prompt content.

        Args:
            bot_id: The id of the bot to which node belongs
            node_id: The id of the node object to update
            function_id: The id of the function integration object to update
            instance: The update object containing the state of the function

        Returns:
            BotNode: The saved node object
        """

    @abstractmethod
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
