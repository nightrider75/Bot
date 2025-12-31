"""
Firestore-based bot store implementation with in-memory caching.

This module provides the FireStoreBotStore class that implements the BotStoreInterface
using Google Cloud Firestore as the backend storage with 5-minute in-memory caching.
"""

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from google.cloud import firestore
from google.cloud.firestore import AsyncClient
from google.oauth2 import service_account
from loguru import logger

from bot.bot_hub.types import BotNode, BotUserData, BotNodeMeta
from bot.config import settings
from bot.store.bot_store.interface import BotStoreInterface
from bot.types import BotConfig


@dataclass
class CacheEntry:
    """Cache entry with timestamp for expiration."""

    value: Any
    timestamp: float


class CacheManager:
    """Simple in-memory cache with time-based expiration."""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache manager.

        Args:
            ttl_seconds: Time to live in seconds (default: 300 = 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() - entry.timestamp > self.ttl_seconds:
            # Entry expired, remove it
            del self._cache[key]
            return None

        return entry.value

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = CacheEntry(value=value, timestamp=time.time())

    def invalidate(self, key: str) -> None:
        """
        Remove specific key from cache.

        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]

    def invalidate_pattern(self, pattern: str) -> None:
        """
        Remove all keys matching a pattern from cache.

        Args:
            pattern: String pattern to match in keys
        """
        keys_to_delete = [k for k in self._cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()


class FireStoreBotStore(BotStoreInterface):
    """
    Firestore implementation of the BotStoreInterface with in-memory caching.

    This class provides Firestore-based storage and retrieval operations
    for all bot-related data including prompts, functions, configuration, and user data.
    Implements 5-minute in-memory caching for read operations.
    """

    def __init__(self, bot_id: UUID, cache_ttl: int = 300):
        """
        Initialize the Firestore bot store with a specific bot ID.

        Args:
            bot_id: The identifier for the bot this store will serve
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.bot_id = bot_id
        self.config = settings.store_config.firestore_config
        self._client: Optional[AsyncClient] = None
        self._cache = CacheManager(ttl_seconds=cache_ttl)

    def _make_cache_key(self, operation: str, *args) -> str:
        """
        Create a cache key from operation and arguments.

        Args:
            operation: Operation name (e.g., 'node', 'functions', 'config')
            *args: Additional arguments to include in key

        Returns:
            Cache key string
        """
        parts = [self.bot_id, operation] + [str(arg) for arg in args]
        return ":".join(parts)

    async def _get_client(self) -> AsyncClient:
        """Get or create the Firestore async client."""
        if self._client is None:
            credentials = None

            if self.config.credentials:
                # Load credentials from JSON string
                credential_info = json.loads(self.config.credentials)
                credentials = service_account.Credentials.from_service_account_info(
                    credential_info
                )
            elif self.config.credentials_path:
                # Load credentials from file
                credentials = service_account.Credentials.from_service_account_file(
                    self.config.credentials_path
                )

            self._client = firestore.AsyncClient(
                project=self.config.project_id,
                credentials=credentials,
                database=self.config.database_id,
            )

        return self._client

    def _get_collection_ref(self, collection_type: str) -> str:
        """Get collection reference for a specific data type."""
        collection_names = {
            "nodes": self.config.nodes_collection,
            "functions": self.config.functions_collection,
            "configs": self.config.configs_collection,
            "users": self.config.users_collection,
        }

        if collection_type not in collection_names:
            raise ValueError(f"Unknown collection type: {collection_type}")

        return collection_names[collection_type]

    async def get_node(self, node_id: UUID) -> BotNode:
        """
        Get the specific node with its complete data (cached).

        Args:
            node_id: The identifier of the node to get

        Returns:
            BotNode: The complete node object with id and prompt content

        Raises:
            ValueError: If node_id is invalid
            FileNotFoundError: If the node doesn't exist
        """
        if not node_id:
            raise ValueError("node_id cannot be empty")

        # Check cache first
        cache_key = self._make_cache_key("node", node_id)
        cached_node = self._cache.get(cache_key)
        if cached_node is not None:
            logger.debug(f"Cache hit for node {node_id}")
            return cached_node

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("nodes")

            # Query for the specific node for this bot
            # query = client.collection(collection_name).where("bot_id", "==", self.bot_id).where("node_id", "==", node_id)
            # TODO: For now assuming single node, update it later
            query = client.collection(collection_name).where("id", "==", self.bot_id)
            docs = [doc async for doc in query.stream()]

            if not docs:
                raise FileNotFoundError(
                    f"Node {node_id} not found for bot {self.bot_id}"
                )

            doc_data = docs[0].to_dict()
            node = BotNode(
                # node_id=doc_data["node_id"],
                node_id="initial",
                prompt=doc_data.get("prompt", {}).get("template"),
            )

            # Cache the result
            self._cache.set(cache_key, node)
            logger.debug(f"Cached node {node_id}")

            return node

        except Exception as e:
            logger.error(f"Error retrieving node {node_id} for bot {self.bot_id}: {e}")
            raise

    async def get_config(self) -> BotConfig:
        """
        Get the complete bot configuration (cached).

        Returns:
            BotConfig: The complete bot configuration including all components

        Raises:
            RuntimeError: If configuration retrieval fails
        """
        # Check cache first
        cache_key = self._make_cache_key("config")
        cached_config = self._cache.get(cache_key)
        if cached_config is not None:
            logger.debug("Cache hit for bot config")
            return cached_config

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("configs")

            query = client.collection(collection_name).where(
                "bot_identifier", "==", self.bot_id
            )
            docs = [doc async for doc in query.stream()]

            if not docs:
                raise FileNotFoundError(
                    f"Configuration not found for bot {self.bot_id}"
                )

            doc_data = docs[0].to_dict()
            config = BotConfig(**doc_data)

            # Cache the result
            self._cache.set(cache_key, config)
            logger.debug("Cached bot config")

            return config

        except Exception as e:
            logger.error(f"Error retrieving config for bot {self.bot_id}: {e}")
            raise RuntimeError(f"Failed to retrieve configuration: {e}") from e

    async def get_user_data(self, user_id: str) -> BotUserData:
        """
        Get user data for a specific user (cached).

        Args:
            user_id: The identifier for the user

        Returns:
            BotUserData: Structured user data object

        Raises:
            ValueError: If user_id is invalid
            FileNotFoundError: If user data doesn't exist
        """
        if not user_id:
            raise ValueError("user_id cannot be empty")

        # Check cache first
        cache_key = self._make_cache_key("user", user_id)
        cached_user_data = self._cache.get(cache_key)
        if cached_user_data is not None:
            logger.debug(f"Cache hit for user {user_id}")
            return cached_user_data

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("users")

            query = (
                client.collection(collection_name)
                .where("bot_id", "==", self.bot_id)
                .where("user_id", "==", user_id)
            )
            docs = [doc async for doc in query.stream()]

            if not docs:
                raise FileNotFoundError(
                    f"User data not found for user {user_id} and bot {self.bot_id}"
                )

            doc_data = docs[0].to_dict()
            user_data = BotUserData(
                user_id=doc_data["user_id"], data=doc_data.get("data", {})
            )

            # Cache the result
            self._cache.set(cache_key, user_data)
            logger.debug(f"Cached user data for {user_id}")

            return user_data

        except Exception as e:
            logger.error(
                f"Error retrieving user data for user {user_id} and bot {self.bot_id}: {e}"
            )
            raise

    async def save_prompts(self, prompts: List[BotNode]) -> bool:
        """
        Save multiple node prompts and invalidate cache.

        Args:
            prompts: List of BotNode objects containing node data

        Returns:
            bool: True if all prompts were saved successfully

        Raises:
            ValueError: If prompt data is invalid
            RuntimeError: If saving fails
        """
        if not prompts:
            return True

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("nodes")
            batch = client.batch()

            for prompt in prompts:
                if not prompt.node_id or not prompt.prompt:
                    raise ValueError(f"Invalid prompt data: {prompt}")

                doc_data = {
                    "bot_id": self.bot_id,
                    "node_id": prompt.node_id,
                    "prompt": prompt.prompt,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }

                doc_id = f"{self.bot_id}_{prompt.node_id}"
                doc_ref = client.collection(collection_name).document(doc_id)
                batch.set(doc_ref, doc_data)

                # Invalidate cache for this node
                cache_key = self._make_cache_key("node", prompt.node_id)
                self._cache.invalidate(cache_key)

            await batch.commit()

            # Invalidate all nodes cache
            self._cache.invalidate_pattern("all_nodes")

            logger.info(
                f"Successfully saved {len(prompts)} prompts for bot {self.bot_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error saving prompts for bot {self.bot_id}: {e}")
            raise RuntimeError(f"Failed to save prompts: {e}") from e

    async def save_config(self, configs: List[BotConfig]) -> bool:
        """
        Save bot configurations and invalidate cache.

        Args:
            configs: List of BotConfig objects to save

        Returns:
            bool: True if all configurations were saved successfully

        Raises:
            ValueError: If config data is invalid
            RuntimeError: If saving fails
        """
        if not configs:
            return True

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("configs")
            batch = client.batch()

            for config in configs:
                if not config.bot_identifier:
                    raise ValueError(f"Invalid config data: {config}")

                doc_data = config.model_dump()
                doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

                # Use bot_identifier as document ID
                doc_ref = client.collection(collection_name).document(
                    config.bot_identifier
                )
                batch.set(doc_ref, doc_data)

            await batch.commit()

            # Invalidate config cache
            cache_key = self._make_cache_key("config")
            self._cache.invalidate(cache_key)

            logger.info(f"Successfully saved {len(configs)} configurations")
            return True

        except Exception as e:
            logger.error(f"Error saving configurations: {e}")
            raise RuntimeError(f"Failed to save configurations: {e}") from e

    async def save_user_data(self, user_data_list: List[BotUserData]) -> bool:
        """
        Save user data for multiple users and invalidate cache.

        Args:
            user_data_list: List of BotUserData objects containing structured user data

        Returns:
            bool: True if all user data was saved successfully

        Raises:
            ValueError: If user data is invalid
            RuntimeError: If saving fails
        """
        if not user_data_list:
            return True

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("users")
            batch = client.batch()

            for user_data in user_data_list:
                if not user_data.user_id:
                    raise ValueError(f"Invalid user data: {user_data}")

                doc_data = {
                    "bot_id": self.bot_id,
                    "user_id": user_data.user_id,
                    "data": user_data.data,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }

                # Use bot_id + user_id as document ID for uniqueness
                doc_id = f"{self.bot_id}_{user_data.user_id}"
                doc_ref = client.collection(collection_name).document(doc_id)
                batch.set(doc_ref, doc_data)

                # Invalidate cache for this user
                cache_key = self._make_cache_key("user", user_data.user_id)
                self._cache.invalidate(cache_key)

            await batch.commit()
            logger.info(
                f"Successfully saved user data for {len(user_data_list)} users in bot {self.bot_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error saving user data for bot {self.bot_id}: {e}")
            raise RuntimeError(f"Failed to save user data: {e}") from e

    async def list_nodes(self) -> List[BotNodeMeta]:
        """
        List all available nodes for this bot (cached).

        Returns:
            List[BotNodeMeta]: List of nodes available for this bot

        Raises:
            RuntimeError: If listing nodes fails
        """
        # Check cache first
        cache_key = self._make_cache_key("list_nodes")
        cached_nodes = self._cache.get(cache_key)
        if cached_nodes is not None:
            logger.debug("Cache hit for list_nodes")
            return cached_nodes

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("nodes")

            query = client.collection(collection_name).where("id", "==", self.bot_id)
            docs = [doc async for doc in query.stream()]

            node_ids = [doc.to_dict()["id"] for doc in docs]

            # Cache the result
            self._cache.set(cache_key, node_ids)
            logger.debug("Cached list_nodes")

            return node_ids

        except Exception as e:
            logger.error(f"Error listing nodes for bot {self.bot_id}: {e}")
            raise RuntimeError(f"Failed to list nodes: {e}") from e

    async def get_all_nodes(self) -> List[BotNode]:
        """
        Get all nodes with their complete data for this bot (cached).

        Returns:
            List[BotNode]: List of complete node objects for this bot

        Raises:
            RuntimeError: If retrieving nodes fails
        """
        # Check cache first
        cache_key = self._make_cache_key("all_nodes")
        cached_nodes = self._cache.get(cache_key)
        if cached_nodes is not None:
            logger.debug("Cache hit for all_nodes")
            return cached_nodes

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("nodes")

            query = client.collection(collection_name).where(
                "bot_id", "==", self.bot_id
            )
            docs = [doc async for doc in query.stream()]

            nodes = []
            for doc in docs:
                doc_data = doc.to_dict()
                nodes.append(
                    BotNode(node_id=doc_data["node_id"], prompt=doc_data["prompt"])
                )

            # Cache the result
            self._cache.set(cache_key, nodes)
            logger.debug("Cached all_nodes")

            return nodes

        except Exception as e:
            logger.error(f"Error retrieving all nodes for bot {self.bot_id}: {e}")
            raise RuntimeError(f"Failed to retrieve nodes: {e}") from e

    async def list_users(self) -> List[str]:
        """
        List all users that have data for this bot (cached).

        Returns:
            List[str]: List of user IDs that have data for this bot

        Raises:
            RuntimeError: If listing users fails
        """
        # Check cache first
        cache_key = self._make_cache_key("list_users")
        cached_users = self._cache.get(cache_key)
        if cached_users is not None:
            logger.debug("Cache hit for list_users")
            return cached_users

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("users")

            query = client.collection(collection_name).where(
                "bot_id", "==", self.bot_id
            )
            docs = [doc async for doc in query.stream()]

            user_ids = [doc.to_dict()["user_id"] for doc in docs]

            # Cache the result
            self._cache.set(cache_key, user_ids)
            logger.debug("Cached list_users")

            return user_ids

        except Exception as e:
            logger.error(f"Error listing users for bot {self.bot_id}: {e}")
            raise RuntimeError(f"Failed to list users: {e}") from e

    async def get_all_user_data(self) -> List[BotUserData]:
        """
        Get all user data for this bot (cached).

        Returns:
            List[BotUserData]: List of all user data objects for this bot

        Raises:
            RuntimeError: If retrieving user data fails
        """
        # Check cache first
        cache_key = self._make_cache_key("all_users")
        cached_user_data = self._cache.get(cache_key)
        if cached_user_data is not None:
            logger.debug("Cache hit for all_users")
            return cached_user_data

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("users")

            query = client.collection(collection_name).where(
                "bot_id", "==", self.bot_id
            )
            docs = [doc async for doc in query.stream()]

            user_data_list = []
            for doc in docs:
                doc_data = doc.to_dict()
                user_data_list.append(
                    BotUserData(
                        user_id=doc_data["user_id"], data=doc_data.get("data", {})
                    )
                )

            # Cache the result
            self._cache.set(cache_key, user_data_list)
            logger.debug("Cached all_users")

            return user_data_list

        except Exception as e:
            logger.error(f"Error retrieving all user data for bot {self.bot_id}: {e}")
            raise RuntimeError(f"Failed to retrieve user data: {e}") from e

    async def delete_prompt(self, node_id: UUID) -> bool:
        """
        Delete prompt for a specific node and invalidate cache.

        Args:
            node_id: The identifier of the node to delete the prompt for

        Returns:
            bool: True if prompt was deleted successfully

        Raises:
            ValueError: If node_id is invalid
            FileNotFoundError: If prompt doesn't exist
        """
        if not node_id:
            raise ValueError("node_id cannot be empty")

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("nodes")

            doc_id = f"{self.bot_id}_{node_id}"
            doc_ref = client.collection(collection_name).document(doc_id)

            doc = await doc_ref.get()
            if not doc.exists:
                raise FileNotFoundError(
                    f"Prompt for node {node_id} not found in bot {self.bot_id}"
                )

            await doc_ref.delete()

            # Invalidate cache
            cache_key = self._make_cache_key("node", node_id)
            self._cache.invalidate(cache_key)
            self._cache.invalidate_pattern("all_nodes")

            logger.info(
                f"Successfully deleted prompt for node {node_id} in bot {self.bot_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error deleting prompt for node {node_id} in bot {self.bot_id}: {e}"
            )
            raise

    async def delete_functions(self, node_id: UUID) -> bool:
        """
        Delete all functions for a specific node and invalidate cache.

        Args:
            node_id: The identifier of the node to delete functions for

        Returns:
            bool: True if functions were deleted successfully

        Raises:
            ValueError: If node_id is invalid
        """
        if not node_id:
            raise ValueError("node_id cannot be empty")

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("functions")

            query = (
                client.collection(collection_name)
                .where("bot_id", "==", self.bot_id)
                .where("node_id", "==", node_id)
            )
            docs = [doc async for doc in query.stream()]

            if not docs:
                logger.info(
                    f"No functions found for node {node_id} in bot {self.bot_id}"
                )
                return True

            batch = client.batch()
            for doc in docs:
                batch.delete(doc.reference)

            await batch.commit()

            # Invalidate cache
            cache_key = self._make_cache_key("functions", node_id)
            self._cache.invalidate(cache_key)

            logger.info(
                f"Successfully deleted {len(docs)} functions for node {node_id} in bot {self.bot_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error deleting functions for node {node_id} in bot {self.bot_id}: {e}"
            )
            raise

    async def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all data for a specific user and invalidate cache.

        Args:
            user_id: The identifier for the user

        Returns:
            bool: True if user data was deleted successfully

        Raises:
            ValueError: If user_id is invalid
            FileNotFoundError: If user data doesn't exist
        """
        if not user_id:
            raise ValueError("user_id cannot be empty")

        try:
            client = await self._get_client()
            collection_name = self._get_collection_ref("users")

            doc_id = f"{self.bot_id}_{user_id}"
            doc_ref = client.collection(collection_name).document(doc_id)

            doc = await doc_ref.get()
            if not doc.exists:
                raise FileNotFoundError(
                    f"User data for user {user_id} not found in bot {self.bot_id}"
                )

            await doc_ref.delete()

            # Invalidate cache
            cache_key = self._make_cache_key("user", user_id)
            self._cache.invalidate(cache_key)
            self._cache.invalidate_pattern("all_users")

            logger.info(
                f"Successfully deleted user data for user {user_id} in bot {self.bot_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error deleting user data for user {user_id} in bot {self.bot_id}: {e}"
            )
            raise
