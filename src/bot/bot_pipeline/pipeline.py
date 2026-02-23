import io
from typing import Any

from fastapi import WebSocket
from loguru import logger
from pydub import AudioSegment
from bot_engine.frames.frames import (
    LLMMessagesAppendFrame,
    LLMMessagesUpdateFrame,
    OutputAudioRawFrame,
    TTSSpeakFrame,
)
from bot_engine.pipeline.pipeline import Pipeline
from bot_engine.pipeline.runner import PipelineRunner
from bot_engine.pipeline.task import PipelineParams, PipelineTask
from bot_engine.processors.aggregators.llm_response import (
    LLMUserAggregatorParams,
)
from bot_engine.processors.aggregators.openai_llm_context import (
    OpenAILLMContext,
)
from bot_engine.processors.audio.audio_buffer_processor import (
    AudioBufferProcessor,
)
from bot_engine.processors.filters.stt_mute_filter import (
    STTMuteConfig,
    STTMuteFilter,
)
from bot_engine.processors.transcript_processor import TranscriptProcessor
from bot_engine.processors.user_idle_processor import UserIdleProcessor
from bot_engine.utils.base_object import BaseObject
from flows_test.manager import FlowManager

from bot.bot_hub.node_template_utils import templatize
from bot.bot_pipeline.llm_provider import LLMProvider
from bot.bot_pipeline.stt_provider import TranscriberProvider
from bot.bot_pipeline.transport_provider import TransportProvider
from bot.bot_pipeline.tts_provider import SynthesizerProvider
from bot.config import settings
from bot.deps import AsyncSessionLocal
from bot.processors.interruption_converter import InterruptionConverterProcessor
from bot.store.asset_store.postgres import PostgresAssetStore
from bot.store.file_store.store import FileStore
from bot.types import BotConfig, StreamConfig


class BotPipeline(BaseObject):
    def __init__(
        self,
        config: BotConfig,
        stream_config: StreamConfig,
        connection: WebSocket | Any,
        **kwargs,
    ):
        super().__init__()
        self.config = config
        self.stream_config = stream_config
        self.connection = connection

        self.transport = TransportProvider.get_provider(
            config.transport, stream_config, connection
        )
        self.stt = TranscriberProvider.get_provider(config.stt, config.pipeline_config)
        self.llm = LLMProvider.get_provider(config.llm)
        self.tts = SynthesizerProvider.get_provider(config.tts)

        self.transcript = TranscriptProcessor()
        self.context = OpenAILLMContext()
        self.context_aggregator = self.llm.create_context_aggregator(
            self.context,
            user_params=LLMUserAggregatorParams(
                enable_emulated_vad_interruptions=True,
                aggregation_timeout=config.pipeline_config.llm_aggregation_timeout,
            ),
        )
        pipeline_components = []
        self._register_event_handler("user_idle_disconnect")

        pipeline_components.append(self.transport.input())

        # Add interruption converter processor to handle user speech interruptions
        # This converts UserStartedSpeakingFrame to InterruptionTaskFrame for TTS interruption
        self.interruption_converter = InterruptionConverterProcessor()
        pipeline_components.append(self.interruption_converter)

        if config.pipeline_config.user_idle_enabled:

            async def handle_idle(
                processor: UserIdleProcessor, retry_count: int
            ) -> bool:
                logger.info(f" user idle retry_count : [{retry_count}]")

                def render(prompt):
                    return templatize(prompt, self.flow_manager.state)

                pipeline_config = config.pipeline_config

                if retry_count <= pipeline_config.user_idle_retries:
                    if pipeline_config.user_idle_llm_nudge:
                        nudge = render(pipeline_config.user_idle_llm_nudge)
                        self.context.messages.append(
                            {"role": "system", "content": nudge}
                        )
                        await processor.push_frame(
                            LLMMessagesUpdateFrame(
                                messages=self.context.messages, run_llm=True
                            )
                        )
                    else:
                        await processor.push_frame(
                            TTSSpeakFrame(render(pipeline_config.user_idle_nudge))
                        )
                    return True
                else:
                    if pipeline_config.user_idle_llm_goodbye:
                        goodbye = render(pipeline_config.user_idle_llm_goodbye)
                        self.context.messages.append(
                            {"role": "system", "content": goodbye}
                        )
                        await processor.push_frame(
                            LLMMessagesUpdateFrame(
                                messages=self.context.messages, run_llm=True
                            )
                        )
                    else:
                        await processor.push_frame(
                            TTSSpeakFrame(render(pipeline_config.user_idle_goodbye))
                        )
                    await self._call_event_handler("user_idle_disconnect")
                    return False

            self.user_idle = UserIdleProcessor(
                timeout=config.pipeline_config.user_idle_timeout, callback=handle_idle
            )
            pipeline_components.append(self.user_idle)

        pipeline_components.append(self.stt)
        stt_mute_processor = STTMuteFilter(
            config=STTMuteConfig(
                strategies={
                    i.to_internal() for i in config.pipeline_config.stt_mute_strategy
                }
            ),
        )
        pipeline_components.append(stt_mute_processor)
        pipeline_components.append(self.transcript.user())
        pipeline_components.append(self.context_aggregator.user())
        pipeline_components.append(self.llm)
        pipeline_components.append(self.tts)
        pipeline_components.append(self.transport.output())
        if config.pipeline_config.audio_recording:
            self.audio_buffer_processor = AudioBufferProcessor(
                num_channels=2,
                buffer_size=0,
            )
            pipeline_components.append(self.audio_buffer_processor)
        pipeline_components.append(self.transcript.assistant())
        pipeline_components.append(self.context_aggregator.assistant())

        self.pipeline = Pipeline(pipeline_components)
        self.task = PipelineTask(
            self.pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                report_only_initial_ttfb=True,
            ),
            cancel_on_max_ttl=config.pipeline_config.max_ttl_enabled,
            max_ttl_secs=config.pipeline_config.max_ttl_timeout,
        )

        self.flow_manager = FlowManager(
            task=self.task,
            llm=self.llm,
            context_aggregator=self.context_aggregator,
            tts=self.tts,
        )
        self.runner = PipelineRunner(handle_sigint=False, force_gc=True)
        self.file_store = FileStore(
            config=config.file_store,
            scoped_prefix=str(config.bot_identifier),
        )

    async def play_initial_audio(self):
        """Play initial audio from asset store or phrase if configured.

        This method should be called right after the pipeline is created
        but before it starts running, to ensure the initial audio/phrase is
        the very first thing processed.

        If initial_audio_id is configured:
        - Fetches the audio file from asset store using the ID
        - Plays the audio file with the configured initial_audio_rate
        - Adds initial_audio_phrase to the transcript as an assistant message for LLM processing
        If only initial_audio_phrase is configured (without initial_audio_id):
        - Uses TTS to speak the phrase (existing behavior)
        """
        pipeline_config = self.config.pipeline_config

        # If initial_audio_id is configured, fetch and play the audio file
        if pipeline_config.initial_audio_id:
            try:
                logger.info(
                    f"Playing initial audio from asset store with ID: '{pipeline_config.initial_audio_id}'"
                )
                audio_bytes = None
                # Get database session and create asset store
                async with AsyncSessionLocal() as session:
                    asset_store = PostgresAssetStore(
                        file_store_config=settings.store_config.file_storage_config,
                        session=session,
                    )

                    # Fetch audio file bytes from asset store
                    audio_bytes = await asset_store.get_file(
                        pipeline_config.initial_audio_id
                    )
                    if audio_bytes is None:
                        logger.error(
                            f"Failed to fetch audio file with ID: '{pipeline_config.initial_audio_id}' from asset store"
                        )
                        return

                    logger.debug(
                        f"Fetched audio file from asset store, size: {len(audio_bytes)} bytes"
                    )
                if audio_bytes:
                    # Load audio from bytes using pydub
                    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))

                    # Get source sample rate
                    source_sample_rate = audio_segment.frame_rate

                    target_sample_rate = (
                        pipeline_config.initial_audio_rate or source_sample_rate
                    )

                    # Convert to mono if needed
                    if audio_segment.channels > 1:
                        audio_segment = audio_segment.set_channels(1)

                    # Resample if needed
                    if source_sample_rate != target_sample_rate:
                        logger.debug(
                            f"Resampling audio from {source_sample_rate}Hz to {target_sample_rate}Hz"
                        )
                        audio_segment = audio_segment.set_frame_rate(target_sample_rate)

                    # Export to raw PCM bytes (16-bit signed integers)
                    raw_audio = audio_segment.raw_data

                    # Queue the audio frame for playback
                    audio_frame = OutputAudioRawFrame(
                        audio=raw_audio,
                        sample_rate=target_sample_rate,
                        num_channels=1,
                    )
                    await self.task.queue_frame(audio_frame)

                    logger.info(
                        f"Initial audio queued successfully (sample rate: {target_sample_rate}Hz)"
                    )

                if pipeline_config.initial_audio_phrase:
                    logger.info(
                        f"Adding initial audio phrase to transcript as assistant message: '{pipeline_config.initial_audio_phrase}'"
                    )

                    # Queue the assistant message as a frame so it is appended
                    # AFTER the LLMMessagesUpdateFrame (from flow_manager.initialize)
                    # is processed.  Using context.add_message() directly would be
                    # overwritten when set_messages() runs for the update frame.
                    await self.task.queue_frame(
                        LLMMessagesAppendFrame(
                            messages=[
                                {
                                    "role": "assistant",
                                    "content": pipeline_config.initial_audio_phrase,
                                }
                            ]
                        )
                    )

            except Exception as e:
                logger.error(f"Failed to play initial audio from asset store: {e}")

        elif pipeline_config.initial_audio_phrase:
            try:
                templatized = templatize(
                    pipeline_config.initial_audio_phrase, self.flow_manager.state
                )
                logger.info(f"Playing initial audio phrase via TTS: '{templatized}'")

                # Queue the TTS speak frame with the configured phrase
                # This will be processed before any other frames
                await self.task.queue_frame(TTSSpeakFrame(templatized))

                logger.info("Initial audio phrase queued successfully")

                # Queue the assistant message as a frame so it is appended
                # AFTER the LLMMessagesUpdateFrame (from flow_manager.initialize)
                # is processed.  Using context.add_message() directly would be
                # overwritten when set_messages() runs for the update frame.
                await self.task.queue_frame(
                    LLMMessagesAppendFrame(
                        messages=[
                            {
                                "role": "assistant",
                                "content": templatized,
                            }
                        ]
                    )
                )

            except Exception as e:
                logger.error(f"Failed to play initial audio phrase: {e}")
        else:
            logger.debug("No initial audio configured")

    async def run(self):
        return await self.runner.run(self.task)
