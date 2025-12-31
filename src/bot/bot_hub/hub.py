"""
Bot Hub class for the bot orchestration system.

This module provides the BotHub class that manages all provider instances
for a specific bot.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union
from uuid import UUID

from google.cloud import pubsub_v1
from google.oauth2 import service_account
from loguru import logger
from flows_test.manager import FlowManager
from flows_test.types import (
    ContextStrategy,
    ContextStrategyConfig,
    FlowArgs,
    FlowResult,
    FlowsFunctionSchema,
    NodeConfig,
)

from bot.bot_hub.bots import (
    Bot,
    FileBotProvider,
    PostgreSQLBotProvider,
)

# Import provider implementations
from bot.bot_hub.config.base import DefaultSettingsConfigProvider
from bot.bot_hub.config.local import LocalFileConfigProvider
from bot.bot_hub.config.postgresql import PostgreSQLConfigProvider
from bot.bot_hub.functions.base import EmptyFunctionsProvider
from bot.bot_hub.functions.embedded.provider import (
    EmbeddedFunctionProvider,
)
from bot.bot_hub.functions.types import (
    FunctionInstance,
    FunctionInvocationInputs,
    BotFunction,
)
from bot.bot_hub.node_template_utils import templatize
from bot.bot_hub.nodes.base import LocalFileNodeProvider
from bot.bot_hub.nodes.postgresql import PostgreSQLNodeProvider

# Import interfaces
from bot.bot_hub.nodes.store import StoreNodeProvider

# Import provider type enums
from bot.bot_hub.types import (
    BotNodeMeta,
    BotProviderType,
    ConfigProviderType,
    FunctionsProviderType,
    NodeProviderType,
    UserDataProviderType,
)
from bot.bot_hub.userdata.base import LocalCSVUserDataProvider
from bot.bot_hub.userdata.memory import InMemoryUserDataProvider
from bot.bot_hub.userdata.postgresql import (
    PostgreSQLUserDataProvider,
)
from bot.config import settings

# Import types for BotSession
from bot.models.chat import ChatConversation
from bot.store.bot_store.firestore import FireStoreBotStore
from bot.types import (
    AgentConfig,
    BotConfig,
    PipelineConfig,
    StreamConfig,
    SynthesizerConfig,
    TranscriberConfig,
    TransportConfig,
    TransportType,
)

if TYPE_CHECKING:
    pass


class BotHub:
    """
    Bot Hub class that manages all provider instances for a specific bot.

    This class serves as the central hub that coordinates all the different
    provider types (config, functions, prompt, userdata) for a bot.
    """

    def __init__(self, bot_identifier: UUID):
        """
        Initialize the bot hub with all providers for a specific bot.

        Args:
            bot_identifier: The identifier for the bot this hub will serve
        """
        self.bot_identifier = bot_identifier
        self.config = settings.hub_config
        # Initialize all providers based on configuration
        if self.config.bot_provider == BotProviderType.LOCAL_FILE:
            self.bot_provider = FileBotProvider()
        elif self.config.bot_provider == BotProviderType.POSTGRESQL:
            self.bot_provider = PostgreSQLBotProvider()

        if self.config.config_provider == ConfigProviderType.DEFAULT_SETTINGS:
            self.config_provider = DefaultSettingsConfigProvider()
        elif self.config.config_provider == ConfigProviderType.LOCAL_FILE:
            self.config_provider = LocalFileConfigProvider()
        elif self.config.config_provider == ConfigProviderType.POSTGRESQL:
            self.config_provider = PostgreSQLConfigProvider()

        if self.config.functions_provider == FunctionsProviderType.EMPTY:
            self.functions_provider = EmptyFunctionsProvider()
        elif self.config.functions_provider == FunctionsProviderType.EMBEDDED:
            self.functions_provider = EmbeddedFunctionProvider()

        if self.config.node_provider == NodeProviderType.LOCAL_FILE:
            self.node_provider = LocalFileNodeProvider()
        elif self.config.node_provider == NodeProviderType.DB_FIRESTORE:
            store = FireStoreBotStore(self.bot_identifier)
            self.node_provider = StoreNodeProvider(store)
        elif self.config.node_provider == NodeProviderType.POSTGRESQL:
            self.node_provider = PostgreSQLNodeProvider()

        if self.config.userdata_provider == UserDataProviderType.LOCAL_CSV:
            self.userdata_provider = LocalCSVUserDataProvider(bot_identifier)
        elif self.config.userdata_provider == UserDataProviderType.IN_MEMORY:
            self.userdata_provider = InMemoryUserDataProvider()
        elif self.config.userdata_provider == UserDataProviderType.POSTGRESQL:
            self.userdata_provider = PostgreSQLUserDataProvider(bot_identifier)

    async def list_nodes(self) -> List[BotNodeMeta]:
        """
        List all available nodes for the current bot.

        This method uses the prompt provider to discover all available nodes
        since prompts are typically associated with flow nodes.

        Returns:
            List[BotNodeMeta]: A list of nodes that have prompts available
        """
        return await self.node_provider.list_nodes(self.bot_identifier)

    @classmethod
    async def create_bot(cls, name: str) -> Bot:
        """
        Create a new bot with all providers initialized.

        Args:
            name: The name for the new bot

        Returns:
            Bot: The newly created bot instance

        Raises:
            RuntimeError: If bot creation fails in any provider
        """
        # Create bot using bot provider
        bot_provider_class = cls._get_bot_provider_class(
            settings.hub_config.bot_provider
        )
        bot_provider = bot_provider_class()
        bot = await bot_provider.create_bot(name)
        logger.debug(f"Created bot: {bot}")

        hub = BotHub(bot.id)

        # Create initial node
        default_config = BotConfig(
            bot_identifier=bot.id,
            pipeline_config=settings.pipeline_config,
            tts=settings.synthesizer_config,
            stt=settings.transcriber_config,
            llm=settings.agent_config,
            transport=settings.transport_config,
            file_store=settings.store_config.file_storage_config,
        )

        await hub.config_provider.set_config(bot.id, default_config)

        node = await hub.node_provider.create_node(bot.id, "Initial Node")

        bot = await hub.bot_provider.update_bot(bot.id, node.node_id)

        # Initialize user data storage for the bot
        await hub.userdata_provider.create_bot(bot.id)
        logger.debug(f"Initialized user data storage for bot {bot.id}")

        return bot

    @classmethod
    async def list_bots(cls) -> List[Bot]:
        """
        List all available bots.

        Returns:
            List[Bot]: List of all bot instances with their IDs and names

        Raises:
            RuntimeError: If listing bots fails in the bot provider
        """
        bot_provider_class = cls._get_bot_provider_class(
            settings.hub_config.bot_provider
        )
        bot_provider = bot_provider_class()
        logger.debug("Listing bots via hub")

        # Get bots from bot provider
        bots = await bot_provider.list_bots()
        logger.debug(f"Available bots: {bots}")
        return bots

    @classmethod
    async def delete_bot(cls, bot_id: UUID) -> None:
        """
        Delete a bot and all its associated data across all providers.

        Args:
            bot_id (UUID): The unique identifier of the bot to delete

        Raises:
            FileNotFoundError: If bot with given ID doesn't exist
            RuntimeError: If deletion fails in any provider
        """

        # Then clean up in all other providers
        config_provider_class = cls._get_config_provider_class(
            settings.hub_config.config_provider
        )
        node_provider_class = cls._get_node_provider_class(
            settings.hub_config.node_provider
        )
        userdata_provider_class = cls._get_userdata_provider_class(
            settings.hub_config.userdata_provider
        )

        # Delete bot from all providers
        await config_provider_class.delete_bot_config(bot_id)
        await node_provider_class.delete_bot(bot_id)
        await userdata_provider_class.delete_bot_userdata(bot_id)
        # Delete bot using bot provider first
        bot_provider_class = cls._get_bot_provider_class(
            settings.hub_config.bot_provider
        )
        bot_provider = bot_provider_class()
        await bot_provider.delete_bot(bot_id)
        logger.debug(f"Deleted bot {bot_id} from bot provider")

    @classmethod
    async def get_bot(cls, bot_id: UUID) -> Bot:
        """
        Get a bot instance by its ID.

        Args:
            bot_id (UUID): The unique identifier of the bot to retrieve

        Returns:
            Bot: The bot instance if found

        Raises:
            FileNotFoundError: If bot with given ID doesn't exist
        """
        bot_provider_class = cls._get_bot_provider_class(
            settings.hub_config.bot_provider
        )
        bot_provider = bot_provider_class()
        return await bot_provider.get_bot(bot_id)

    @classmethod
    def _get_config_provider_class(cls, provider_type: ConfigProviderType):
        """
        Get the config provider class for the given type.

        Args:
            provider_type: The type of config provider to get

        Returns:
            The config provider class corresponding to the provider type

        Raises:
            ValueError: If the provider_type is not supported
        """
        provider_map = {
            ConfigProviderType.DEFAULT_SETTINGS: DefaultSettingsConfigProvider,
            ConfigProviderType.LOCAL_FILE: LocalFileConfigProvider,
            ConfigProviderType.POSTGRESQL: PostgreSQLConfigProvider,
        }

        provider_class = provider_map.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unknown config provider type: {provider_type}")

        return provider_class

    @classmethod
    def _get_node_provider_class(cls, provider_type: NodeProviderType):
        """
        Get the prompt provider class for the given type.

        Args:
            provider_type: The type of prompt provider to get

        Returns:
            The prompt provider class corresponding to the provider type

        Raises:
            ValueError: If the provider_type is not supported
        """
        provider_map = {
            NodeProviderType.LOCAL_FILE: LocalFileNodeProvider,
            # TODO: For now this works because the static methods are same
            # But this needs to be enforced either by moving the static methods to a dedicated interface
            NodeProviderType.DB_FIRESTORE: FireStoreBotStore,
            NodeProviderType.POSTGRESQL: PostgreSQLNodeProvider,
        }

        provider_class = provider_map.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unknown prompt provider type: {provider_type}")

        return provider_class

    @classmethod
    def _get_userdata_provider_class(cls, provider_type: UserDataProviderType):
        """
        Get the userdata provider class for the given type.

        Args:
            provider_type: The type of userdata provider to get

        Returns:
            The userdata provider class corresponding to the provider type

        Raises:
            ValueError: If the provider_type is not supported
        """
        provider_map = {
            UserDataProviderType.LOCAL_CSV: LocalCSVUserDataProvider,
            UserDataProviderType.IN_MEMORY: InMemoryUserDataProvider,
            UserDataProviderType.POSTGRESQL: PostgreSQLUserDataProvider,
        }

        provider_class = provider_map.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unknown userdata provider type: {provider_type}")

        return provider_class

    @classmethod
    def _get_bot_provider_class(cls, provider_type: BotProviderType):
        """
        Get the bot provider class for the given type.

        Args:
            provider_type: The type of bot provider to get

        Returns:
            The bot provider class corresponding to the provider type

        Raises:
            ValueError: If the provider_type is not supported
        """
        provider_map = {
            BotProviderType.LOCAL_FILE: FileBotProvider,
            BotProviderType.POSTGRESQL: PostgreSQLBotProvider,
        }

        provider_class = provider_map.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unknown bot provider type: {provider_type}")

        return provider_class


class BotSession:
    """
    Bot Session class that manages a session between a specific bot and user.

    This class provides a session-aware interface to bot operations by maintaining
    the context of bot ID, user ID, and transport type along with an initialized BotHub instance.
    """

    def __init__(self, bot_id: UUID, user_id: str, transport_type: TransportType):
        """
        Initialize a bot session for a specific bot, user, and transport type.

        Args:
            bot_id: The identifier for the bot
            user_id: The identifier for the user
            transport_type: The type of transport being used for this session
        """
        self.bot_id = bot_id
        self.user_id = user_id
        self._transport_type = transport_type
        self.bot_hub = BotHub(bot_id)
        self._initialized = False

        # Initialize cached config attributes as None
        self._bot_config: Optional[BotConfig] = None
        self._pipeline_config: Optional[PipelineConfig] = None
        self._agent_config: Optional[AgentConfig] = None
        self._synthesizer_config: Optional[SynthesizerConfig] = None
        self._transcriber_config: Optional[TranscriberConfig] = None
        self._transport_config: Optional[TransportConfig] = None
        self._user_data: Optional[dict] = {}

    async def initialize(self) -> None:
        """
        Initialize the bot hub providers and preload all configuration and user data for this session.

        This method must be called before using any other session methods.
        It will preload all configuration data and user data to ensure fast access during the session.
        """
        if not self._initialized:
            # Initialize all providers
            # Preload all configuration data
            # Get the complete bot configuration
            bot_config = await self.bot_hub.config_provider.get_config(self.bot_id)

            # Extract individual configs from BotConfig
            self._pipeline_config = bot_config.pipeline_config
            self._agent_config = bot_config.llm
            self._synthesizer_config = bot_config.tts
            self._transcriber_config = bot_config.stt
            self._transport_config = bot_config.transport
            self._transport_config.provider = self._transport_type

            # Store the complete bot config
            self._bot_config = BotConfig(
                bot_identifier=self.bot_id,
                pipeline_config=self._pipeline_config,
                tts=self._synthesizer_config,
                stt=self._transcriber_config,
                llm=self._agent_config,
                transport=self._transport_config,
                file_store=bot_config.file_store,
            )

            # Preload user data (if available)
            try:
                user_data = await self.bot_hub.userdata_provider.get_user_data(
                    self.user_id
                )
                if user_data:
                    self._user_data = user_data.data
            except (ValueError, RuntimeError, FileNotFoundError):
                # User data might not exist yet, that's okay
                self._user_data = {}

            self._initialized = True

    async def get_config(self) -> BotConfig:
        """
        Get the complete bot configuration for this session.

        Returns:
            BotConfig: The complete bot configuration including all components

        Raises:
            RuntimeError: If the session has not been initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "Session must be initialized before accessing configuration"
            )

        return self._bot_config

    def get_user_data(self) -> Optional[dict]:
        """
        Get the preloaded user data for this session.

        Returns the user data that was loaded during session initialization.
        This data is cached for performance and consistency during the session.

        Returns:
            Optional[dict]: The user data dictionary if available, None if no user data exists

        Raises:
            RuntimeError: If the session has not been initialized
        """
        if not self._initialized:
            raise RuntimeError("Session must be initialized before accessing user data")
        return self._user_data

    def _normalize_functions(
        self, function_instance: FunctionInstance, function_def: BotFunction
    ) -> List[FlowsFunctionSchema]:
        """
        Normalize a list of FunctionInstance objects to FlowsFunctionSchema format.

        This method converts the internal FunctionInstance representations to the
        FlowsFunctionSchema format expected by the flows-test library.

        Args:
            functions: List of FunctionInstance objects to normalize

        Returns:
            List[FlowsFunctionSchema]: The normalized list of functions
        """
        properties_dict = {}
        required_list = []
        for param_name, param in function_def.parameters.items():
            properties_dict[param_name] = {
                "type": param.property_type,
                "description": param.description,
            }
            if param.enum:
                properties_dict[param_name]["enum"] = param.enum
            if param.required:
                required_list.append(param_name)
        if function_instance.ack_llm_description:
            properties_dict["acknowledgement_message"] = {
                "type": "string",
                "description": function_instance.ack_llm_description,
            }
            required_list.append("acknowledgement_message")

        async def handler(
            args: FlowArgs, flow_manager: FlowManager
        ) -> Tuple[Optional[FlowResult], Optional[Union["NodeConfig", str]]]:
            try:
                input_params = FunctionInvocationInputs(
                    bot_id=self.bot_id,
                    user_id=self.user_id,
                    inputs=args,
                    bot_state=flow_manager.state,
                )
                output = await self.bot_hub.functions_provider.invoke_function(
                    function_instance, input_params
                )
                next_node = None
                if output.next_node:
                    actual_node = function_instance.transition_mappings.get(
                        output.next_node
                    )
                    if actual_node:
                        next_node = await self.get_node(actual_node, flow_manager.state)
                if output.state_updates:
                    for key, value in output.state_updates.items():
                        flow_manager.state[key] = value
                return FlowResult(status="success", output=output.output), next_node
            except Exception as e:
                logger.error(f"Error running function {function_def.name}: {e}")
                return {
                    "status": "error",
                    "error": f" Failed to run function {str(e)}",
                }, None

        return FlowsFunctionSchema(
            name=function_instance.function_label
            if function_instance.function_label
            else function_def.name,
            description=function_def.description,
            properties=properties_dict,
            required=required_list,
            handler=handler,
            pre_say_config=function_instance.pre_say,
            ack_llm_field="acknowledgement_message"
            if function_instance.ack_llm_description
            else None,
        )

    async def get_node(
        self, node_id: UUID, state: Dict[str, str], is_initial_node: bool = False
    ) -> NodeConfig:
        """
        Get a configured node for the current bot session.

        This method retrieves and configures a node by combining user data, prompts,
        and functions for the specified node ID. The prompt is formatted with user data
        and the node is configured with appropriate role messages and functions.

        Args:
            node_id: The identifier of the node to retrieve
            state: The state containing variables used for templatization
            is_initial_node: Whether this is the initial node of the conversation.
                When True and initial_audio_phrase is configured, respond_immediately
                will be set to False to avoid duplicate greetings.

        Returns:
            NodeConfig: A configured node with formatted prompts, functions, and settings

        Raises:
            ValueError: If the node_id doesn't exist or user data is invalid
            RuntimeError: If there's an error retrieving node components
        """
        if not self._initialized:
            raise RuntimeError("Session must be initialized before accessing user data")
        prompt_variables = state
        node = await self.bot_hub.node_provider.get_node(
            bot_id=self.bot_id, node_id=node_id
        )
        node_functions = []
        for func_instance in node.functions:
            func_def = await self.bot_hub.functions_provider.get_function_schema(
                func_instance.function_id
            )
            if func_def:
                normalized_func = self._normalize_functions(func_instance, func_def)
                node_functions.append(normalized_func)
            else:
                logger.warning(
                    f"Function definition not found for function ID: {func_instance.function_id}"
                )
        prompt = templatize(node.prompt, prompt_variables)

        # For initial node with initial_audio_phrase configured, disable respond_immediately
        # to avoid duplicate greetings (initial_audio_phrase + LLM response)
        respond_immediately = True
        if is_initial_node and self._pipeline_config and self._pipeline_config.initial_audio_phrase:
            respond_immediately = False
            logger.debug(
                "Disabling respond_immediately for initial node since initial_audio_phrase is configured"
            )

        return NodeConfig(
            role_messages=[{"role": "system", "content": prompt}],
            task_messages=[],
            functions=node_functions,
            pre_actions=[],
            post_actions=[],
            context_strategy=ContextStrategyConfig(strategy=ContextStrategy.APPEND),
            respond_immediately=respond_immediately,
        )

    async def get_initial_node(self, state: Dict[str, str]) -> NodeConfig:
        """
        Get the initial node configuration for starting a bot conversation.

        This method fetches the bot object to get the dynamic start_node_id,
        which replaces the hardcoded "initial" node ID. For PostgreSQL provider,
        it uses the UUID stored in bots.start_node_id. For other providers,
        it falls back to "initial" for backward compatibility.
        Args:
            state: The state containing variables used for templatization

        Returns:
            NodeConfig: The configured initial node for this bot session

        Raises:
            ValueError: If the initial node doesn't exist
            RuntimeError: If there's an error retrieving the initial node or bot metadata
        """
        try:
            bot = await self.bot_hub.bot_provider.get_bot(self.bot_id)
            start_node_id = bot.initial_node_id
        except Exception as e:
            # Any other error, fallback to "initial" to maintain service
            logger.warning(f"Error fetching start_node_id: {e}, using 'initial' node")
            raise e

        return await self.get_node(start_node_id, state, is_initial_node=True)

    @property
    def is_initialized(self) -> bool:
        """
        Check if the session has been initialized.

        Returns:
            bool: True if the session has been initialized, False otherwise
        """
        return self._initialized

    async def run_postcall_analysis(
        self,
        chat: ChatConversation,
        call_transcript_data: List[Dict[str, str]],
        stream_config: StreamConfig,
    ):
        """Run Post call analysis for the session"""
        postcall_config = self._bot_config.pipeline_config.postcall_config
        trimmed_audio_path = chat.recording_audio_path
        if trimmed_audio_path:
            trimmed_audio_path = trimmed_audio_path.replace(
                f"gs://{self._bot_config.file_store.store_location}", ""
            )
        postcall_bot_id = stream_config.bot_assistant_id or str(chat.bot_identifier)
        if postcall_config.gcs_pubsub_topics:
            gcs_data = {
                "call_id": str(chat.call_id),
                "bot_id": postcall_bot_id,
                "orchestration_bot_id": str(self.bot_id),
                "orchestration_user_id": self.user_id,
                "transcripts": call_transcript_data,
                "session_id": str(chat.session_id),
                "utc_created_at": datetime.utcnow().isoformat() + "Z",
                "call_recording_path": trimmed_audio_path,
                "call_end_time": chat.end_time.isoformat(),
                "call_start_time": chat.start_time.isoformat(),
                "total_call_seconds": chat.call_duration_secs,
            }
            logger.debug(
                f"Posting GCS data: {gcs_data} to topic {postcall_config.gcs_pubsub_topics}"
            )
            try:
                if postcall_config.credentials:
                    # Load credentials from JSON string
                    credential_info = json.loads(postcall_config.credentials)
                    credentials = service_account.Credentials.from_service_account_info(
                        credential_info
                    )
                elif postcall_config.credentials_path:
                    # Load credentials from file
                    credentials = service_account.Credentials.from_service_account_file(
                        postcall_config.credentials_path
                    )
                else:
                    credentials = None  # Use default credentials
                publisher = pubsub_v1.PublisherClient(credentials=credentials)
                for topic in postcall_config.gcs_pubsub_topics:
                    topic_path = publisher.topic_path(
                        postcall_config.gcs_pubsub_project_id,
                        topic,
                    )
                    data = json.dumps(gcs_data, ensure_ascii=False).encode("utf8")
                    res = publisher.publish(topic_path, data)
                    logger.debug(
                        f"Published message ID: {res.result()} to topic: {topic}"
                    )
            except Exception as e:
                logger.error(f"Error pushing data to Pub/Sub publisher client: {e}")
                return
