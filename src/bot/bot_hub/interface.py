# from abc import ABC, abstractmethod
# from typing import Any, Dict, List
# from uuid import UUID

# from flows_test.manager import FlowManager
# from flows_test.types import NodeConfig

# from bot.bot_hub.config.interface import ConfigInterface
# from bot.bot_hub.functions.interface import FunctionsInterface
# from bot.bot_hub.nodes.interface import NodeInterface
# from bot.bot_hub.userdata.interface import UserDataInterface
# from bot.models.chat import ChatConversation
# from bot.types import StreamConfig


# class BotInterface(ABC):
#     """
#     Core Bot interface for initialization and workflow management.

#     This interface defines the core methods that a Bot implementation must provide
#     for initialization, flow management, and call processing operations.
#     """

#     @abstractmethod
#     def __init__(
#         self,
#         bot_identifier: UUID,
#         stream_config: StreamConfig,
#         config_provider: ConfigInterface,
#         function_provider: FunctionsInterface,
#         node_provider: NodeInterface,
#         userdata_provider: UserDataInterface,
#     ):
#         """
#         Initialize a Bot with the given stream configuration and providers.

#         Args:
#             bot_identifier: The identifier for this bot
#             stream_config: Configuration for the stream including session and user information
#             config_provider: Provider for configuration management operations
#             function_provider: Provider for node function management operations
#             node_provider: Provider for prompt management operations
#             userdata_provider: Provider for user data management operations
#         """

#     @abstractmethod
#     async def initialize(self) -> None:
#         """
#         Initialize all operations for the bot.

#         This method can be extended in the future to perform various initialization tasks.
#         Currently, it's a placeholder that just marks the bot as initialized.

#         Returns:
#             None
#         """

#     @abstractmethod
#     async def get_call_input_details(self) -> Dict[str, Any]:
#         """
#         Get the input details for the current call/session.

#         Returns:
#             Dict[str, Any]: A dictionary containing all input details for the call,
#             such as user information, call parameters, etc.
#         """

#     @abstractmethod
#     async def get_call_output_details(self) -> Dict[str, Any]:
#         """
#         Get the output details for the current call/session.

#         This method would typically be called after a call is completed to gather
#         analytics, transcripts, recording paths, etc.

#         Returns:
#             Dict[str, Any]: A dictionary containing output details from the call
#         """

#     @abstractmethod
#     async def set_flow_manager(self, flow_manager: FlowManager) -> None:
#         """
#         Set the flow manager for this bot.

#         Args:
#             flow_manager: The FlowManager instance to associate with this bot

#         Returns:
#             None
#         """

#     @abstractmethod
#     async def run_postprocessing_steps(
#         self,
#         chat_conversation: ChatConversation,
#         call_transcript_data: List[Dict[str, str]],
#     ) -> Dict[str, Any]:
#         """
#         Run postprocessing steps after a call is completed.

#         This method processes the conversation data and transcript to generate
#         call analytics, summaries, or other derived information.

#         Args:
#             chat_conversation: The ChatConversation object containing call metadata
#             call_transcript_data: List of transcript messages with role, content, and timestamp

#         Returns:
#             Dict[str, Any]: Dictionary containing postprocessing results such as:
#                 - call_summary: Summary of the conversation
#                 - sentiment_analysis: Sentiment analysis results
#                 - key_points: Important points extracted from the conversation
#                 - next_actions: Recommended follow-up actions
#                 - analytics_data: Additional analytics and metrics
#         """

#     @abstractmethod
#     async def get_node(self, node_id: UUID) -> NodeConfig:
#         """
#         Get the configuration for a specific node by its ID.

#         Args:
#             node_id: The identifier of the node to retrieve

#         Returns:
#             NodeConfig: The node configuration for the specified node_id
#         """

#     @abstractmethod
#     async def get_initial_node(self) -> NodeConfig:
#         """
#         Get the initial node configuration for the bot flow.

#         This method should return the starting node that the bot will use
#         when beginning a new conversation or flow.

#         Returns:
#             NodeConfig: The initial node configuration for the bot flow
#         """

#     @abstractmethod
#     async def list_nodes(self) -> List[BotNodeMeta]:
#         """
#         Get a list of all available nodes.

#         Returns:
#             List[BotNodeMeta]: List of node identifiers available in the bot flow
#         """

#     @abstractmethod
#     async def create_node(self, node_id: UUID) -> bool:
#         """
#         Create a new node with the specified ID.

#         Args:
#             node_id: The identifier for the new node to create

#         Returns:
#             bool: True if the node was created successfully, False otherwise
#         """
