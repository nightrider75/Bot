"""
Local file prompt provider implementation.

This module provides a local file-based implementation of the NodeInterface
that stores prompts as text files in a directory structure organized by bot and node.
"""

import json
from pathlib import Path
from typing import Dict, List
from uuid import UUID, uuid4

import aiofiles
from loguru import logger

from bot.bot_hub.functions.types import FunctionInstance
from bot.bot_hub.nodes.interface import NodeInterface
from bot.bot_hub.types import BotNode, BotNodeMeta
from bot.config import settings


class LocalFileNodeProvider(NodeInterface):
    """
    Local file-based prompt provider.

    This provider stores prompts as text files in the filesystem using the structure:
    base_path/bot_id/node_id.txt

    The base_path is configured via settings.hub_config.data_base_path.
    """

    def __init__(self):
        """Initialize the local file prompt provider."""
        self.base_path = Path(settings.hub_config.data_base_path) / "nodes"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.bot_path: Path = Path("")

    def _get_node_file_path(self, bot_id: UUID, node_id: UUID) -> Path:
        """
        Get the file path for a specific node's prompt.

        Args:
            node_id: The identifier for the node

        Returns:
            Path: The file path for the node's prompt
        """
        bot_path = self.base_path / str(bot_id)
        bot_path.mkdir(parents=True, exist_ok=True)
        return bot_path / f"{node_id}.json"

    async def delete_node(self, bot_id: UUID, node_id: UUID) -> bool:
        """
        Delete a complete node by its identifier.

        Args:
            bot_id: The identifier for the bot
            node_id: The identifier for the node

        Returns:
            bool: True if the node was deleted successfully, False otherwise
        """
        node_file = self._get_node_file_path(node_id)

        if not node_file.exists():
            logger.warning(
                f"Attempted to delete non-existent prompt file for node '{node_id}' in bot '{bot_id}'"
            )
            return False

        try:
            node_file.unlink()
            logger.info(
                f"Successfully deleted prompt for node '{node_id}' in bot '{bot_id}'"
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting prompt file {node_file}: {e}")
            return False

    async def _list_node_ids(self, bot_id: UUID) -> List[BotNodeMeta]:
        """
        List all available node IDs for the current bot.

        Args:
            bot_id: The identifier for the bot
        Returns:
            List[BotNodeMeta]: A list of nodes that are available
        """
        bot_path = self.base_path / str(bot_id)
        if not bot_path.exists():
            logger.debug(
                f"Bot directory does not exist for bot '{bot_id}' at {bot_path}"
            )
            return []

        try:
            node_ids = []
            for file_path in bot_path.glob("*.json"):
                node_id = file_path.stem  # filename without extension
                node_ids.append(UUID(node_id))
            logger.debug(f"Found {len(node_ids)} node files for bot '{bot_id}'")
            return sorted(node_ids)
        except Exception as e:
            logger.error(f"Error listing node files in {bot_path}: {e}")
            return []

    async def list_nodes(self, bot_id: UUID) -> List[BotNodeMeta]:
        """
        List all available node IDs for the current bot.

        Args:
            bot_id: The identifier for the bot
        Returns:
            List[BotNodeMeta]: A list of nodes that are available
        """
        ids = await self._list_node_ids(bot_id)
        node_metas = []
        for i in ids:
            node = await self.get_node(bot_id, i)
            node_metas.append(
                BotNodeMeta(
                    bot_id=node.bot_id, node_id=node.node_id, node_name=node.node_name
                )
            )
        return node_metas

    async def get_node(self, bot_id: UUID, node_id: UUID) -> BotNode:
        """
        Get a complete node with its prompt content by its identifier.

        Args:
            node_id: The identifier for the node

        Returns:
            BotNode: The complete node object with id and prompt content
        """
        node_file = self._get_node_file_path(bot_id, node_id)

        try:
            async with aiofiles.open(node_file, "r", encoding="utf-8") as f:
                content = await f.read()
                node_data = json.loads(content)
                return BotNode(**node_data)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error reading node file {node_file}: {e}")
            raise FileNotFoundError from e

    async def _save_node(self, node: BotNode) -> BotNode:
        """
        Save a complete node with its prompt content.

        Args:
            node: The BotNode object to save

        Returns:
            BotNode: The saved node object
        """
        node_file = self._get_node_file_path(node.bot_id, node.node_id)

        try:
            # Ensure the bot directory exists
            self.bot_path.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(node_file, "w", encoding="utf-8") as f:
                await f.write(node.model_dump_json(indent=2))

            logger.info(
                f"Successfully saved prompt for node '{node.node_id}' in bot '{node.bot_id}'"
            )
        except Exception as e:
            logger.error(f"Error saving prompt file {node_file}: {e}")
            raise

        return node

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
        existing_node = await self.get_node(bot_id, node_id=node_id)
        existing_node.prompt = prompt
        node = await self._save_node(existing_node)
        return node

    async def create_node(
        self, bot_id: UUID, node_name: str, prompt: str = ""
    ) -> BotNode:
        """
        Create a new node with its prompt content.

        Args:
            node: The BotNode object to create

        Returns:
            BotNode: The created node object
        """
        node = BotNode(
            bot_id=bot_id, node_id=uuid4(), prompt=prompt, node_name=node_name
        )
        return await self._save_node(node)

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
            function_label: The label for the function
            transition_mappings: The transition mappings for the function

        Returns:
            BotNode: The updated node object with the registered function
        """
        node = await self.get_node(bot_id, node_id)
        # Validate transition mappings against functions transitions if needed
        function_instance = FunctionInstance(
            id=uuid4(),
            function_id=function_id,
            function_label=function_label,
            node_id=node_id,
            bot_id=bot_id,
            transition_mappings=transition_mappings,
            pre_say=dict(),
            ack_llm_description=None,
        )
        node.functions.append(function_instance)
        node = await self._save_node(node)
        return node

    async def update_node_function(
        self, bot_id: UUID, node_id: UUID, function_id: UUID, instance: FunctionInstance
    ) -> BotNode:
        node = await self.get_node(bot_id, node_id)
        for function in node.functions:
            if function.id == function_id:
                function.transition_mappings = instance.transition_mappings
                function.function_label = instance.function_label
                function.pre_say = instance.pre_say
                function.ack_llm_description = instance.ack_llm_description
                updated_node = await self._save_node(node)
                return updated_node
        raise ValueError(
            f"No Function {function_id} found for node {node_id} and bot_id: {bot_id}"
        )

    async def delete_node_function(
        self, bot_id: UUID, node_id: UUID, function_id: UUID
    ) -> BotNode:
        node = await self.get_node(bot_id, node_id)
        node.functions = [i for i in node.functions if i.id != function_id]
        updated_node = await self._save_node(node)
        return updated_node
        raise ValueError(
            f"No Function {function_id} found for node {node_id} and bot_id: {bot_id}"
        )

    @classmethod
    async def delete_bot(cls, bot_id: UUID) -> None:
        """
        Delete all node data for a specific bot.

        Args:
            bot_id: The identifier for the bot to delete

        Raises:
            ValueError: If bot_id is invalid (empty or None)
            FileNotFoundError: If the bot's prompt directory doesn't exist
            RuntimeError: If deletion fails
        """
        if not bot_id or not bot_id.strip():
            raise ValueError("Bot ID cannot be empty")

        try:
            import shutil

            base_path = Path(settings.hub_config.data_base_path) / "nodes"
            bot_path = base_path / bot_id

            if not bot_path.exists():
                raise FileNotFoundError(
                    f"Prompt directory for bot '{bot_id}' does not exist at {bot_path}"
                )

            shutil.rmtree(bot_path)
            logger.info(f"Deleted prompt directory for bot '{bot_id}' at {bot_path}")

        except (OSError, PermissionError) as e:
            logger.error(f"Error deleting bot prompts for '{bot_id}': {e}")
            raise RuntimeError(
                f"Failed to delete bot prompts for '{bot_id}': {e}"
            ) from e
