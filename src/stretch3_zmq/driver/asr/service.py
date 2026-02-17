"""Unified ASR service with provider abstraction and microphone streaming."""

import asyncio
import contextlib
import logging
from typing import ClassVar, Self

from .microphone import Microphone
from .providers import (
    ASRConfig,
    ASRProvider,
    BaseASRProvider,
    DeepgramProvider,
    ElevenLabsProvider,
    OpenAIProvider,
)

logger = logging.getLogger(__name__)


class ASRServiceError(Exception):
    """Base exception for ASR service errors."""

    pass


class ProviderNotFoundError(ASRServiceError):
    """Raised when an unknown provider is requested."""

    pass


class ASRService:
    """
    Unified ASR service that abstracts multiple providers.

    Usage:
        # Simple transcription from microphone
        service = ASRService.create(ASRProvider.DEEPGRAM, api_key="your-key")
        config = ASRConfig(language="en")
        transcript = await service.transcribe_microphone(config, timeout=10.0)

        # Or manual streaming control
        async with service:
            await service.connect(config)
            await service.send_audio(audio_chunk)
            transcript = await service.receive_transcript()
    """

    _PROVIDER_MAP: ClassVar[dict[ASRProvider, type[BaseASRProvider]]] = {
        ASRProvider.OPENAI: OpenAIProvider,
        ASRProvider.DEEPGRAM: DeepgramProvider,
        ASRProvider.ELEVENLABS: ElevenLabsProvider,
    }

    def __init__(self, provider: ASRProvider | str, api_key: str):
        """
        Initialize the ASR service.

        Args:
            provider: The ASR provider to use (ASRProvider enum or string).
            api_key: API key for the provider.

        Raises:
            ProviderNotFoundError: If the provider is not supported.
        """
        if isinstance(provider, str):
            try:
                provider = ASRProvider(provider)
            except ValueError as err:
                raise ProviderNotFoundError(
                    f"Unknown provider: {provider}. "
                    f"Supported providers: {[p.value for p in ASRProvider]}"
                ) from err

        provider_class = self._PROVIDER_MAP.get(provider)
        if not provider_class:
            raise ProviderNotFoundError(
                f"Provider {provider} is not implemented. "
                f"Supported providers: {[p.value for p in ASRProvider]}"
            )

        self._provider: BaseASRProvider = provider_class(api_key=api_key)

    @property
    def provider_name(self) -> ASRProvider:
        """Return the current provider name."""
        return self._provider.provider_name

    async def connect(self, config: ASRConfig) -> None:
        """Establish WebSocket connection."""
        await self._provider.connect(config)

    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send audio chunk to the ASR service."""
        await self._provider.send_audio(audio_chunk)

    async def receive_transcript(self) -> str | None:
        """Receive transcription result."""
        return await self._provider.receive_transcript()

    async def close(self) -> None:
        """Close the WebSocket connection."""
        await self._provider.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()

    async def transcribe_microphone(
        self,
        config: ASRConfig,
        timeout: float = 10.0,
    ) -> str:
        """
        Record from microphone and transcribe until a sentence is detected.

        Args:
            config: ASR configuration (language, model_id, etc.)
            timeout: Maximum seconds to wait for speech. Returns "" on timeout.

        Returns:
            Transcribed text, or empty string if timeout.
        """
        mic = Microphone()
        transcript = ""

        try:
            await self.connect(config)
            logger.info("Listening... Speak now!")

            mic.start()

            async def send_audio_loop() -> None:
                while True:
                    chunk = mic.get_audio_chunk()
                    if chunk:
                        await self.send_audio(chunk)
                    else:
                        await asyncio.sleep(0.01)

            async def receive_loop() -> str:
                while True:
                    result = await self.receive_transcript()
                    if result:
                        logger.info(f"Transcript: {result}")
                        return result

            send_task = asyncio.create_task(send_audio_loop())

            try:
                transcript = await asyncio.wait_for(receive_loop(), timeout=timeout)
            except TimeoutError:
                logger.info("Timeout - no speech detected")
                transcript = ""
            finally:
                send_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await send_task

        finally:
            mic.stop()
            await self.close()

        return transcript


__all__ = [
    "ASRConfig",
    "ASRProvider",
    "ASRService",
    "ASRServiceError",
    "ProviderNotFoundError",
]
