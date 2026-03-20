"""LLM client abstraction layer.

Provides a ``LLMClient`` protocol and concrete implementations for Anthropic
and OpenAI-compatible APIs (including Ollama via ``base_url``).

All implementations convert between the provider-agnostic ``Message`` /
``LLMResponse`` types and the provider-specific API formats.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import structlog

from saludai_agent.exceptions import LLMError, LLMResponseError
from saludai_agent.types import LLMResponse, Message, TokenUsage, ToolCall

if TYPE_CHECKING:
    from saludai_agent.config import AgentConfig

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic interface for LLM generation."""

    async def generate(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            system: System prompt.
            messages: Conversation history.
            tools: Tool definitions in provider-specific format.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            A provider-agnostic ``LLMResponse``.

        Raises:
            LLMError: On communication failures.
            LLMResponseError: On malformed responses.
        """
        ...


# ---------------------------------------------------------------------------
# Anthropic implementation
# ---------------------------------------------------------------------------


class AnthropicLLMClient:
    """LLM client for Anthropic's Claude API.

    Args:
        model: Model identifier (e.g. ``"claude-sonnet-4-20250514"``).
        api_key: Anthropic API key. Falls back to ``ANTHROPIC_API_KEY`` env var.
    """

    def __init__(self, model: str, api_key: str | None = None) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise LLMError(
                "anthropic package is required for AnthropicLLMClient. "
                "Install it with: uv add anthropic"
            ) from exc

        self._model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response via Anthropic API.

        Uses prompt caching on the system prompt and tool definitions to reduce
        input token costs on repeated calls with the same prompt.
        """
        anthropic_messages = _messages_to_anthropic(messages)

        # Prompt caching: wrap system as content block with cache_control
        system_blocks: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        kwargs: dict[str, Any] = {
            "model": self._model,
            "system": system_blocks,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            # Cache tool definitions: mark the last tool with cache_control
            cached_tools = _add_cache_control_to_tools(tools)
            kwargs["tools"] = cached_tools

        try:
            import anthropic

            response = await self._client.messages.create(**kwargs)
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling Anthropic API: {exc}") from exc

        return _anthropic_response_to_llm_response(response)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()


# ---------------------------------------------------------------------------
# OpenAI-compatible implementation (OpenAI + Ollama)
# ---------------------------------------------------------------------------


class OpenAILLMClient:
    """LLM client for OpenAI-compatible APIs (including Ollama).

    Args:
        model: Model identifier.
        api_key: API key. For Ollama, use any non-empty string.
        base_url: Base URL override. Required for Ollama
            (e.g. ``"http://localhost:11434/v1"``).
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        try:
            import openai
        except ImportError as exc:
            raise LLMError(
                "openai package is required for OpenAILLMClient. Install it with: uv add openai"
            ) from exc

        self._model = model
        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response via OpenAI-compatible API."""
        openai_messages = _messages_to_openai(system, messages)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = _tools_to_openai(tools)

        try:
            import openai

            response = await self._client.chat.completions.create(**kwargs)
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling OpenAI API: {exc}") from exc

        return _openai_response_to_llm_response(response)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_llm_client(config: AgentConfig) -> LLMClient:
    """Create an LLM client from agent configuration.

    Args:
        config: Agent configuration with LLM provider settings.

    Returns:
        A configured ``LLMClient`` instance.

    Raises:
        LLMError: If the provider is unsupported.
    """
    if config.llm_provider == "anthropic":
        return AnthropicLLMClient(
            model=config.llm_model,
            api_key=config.llm_api_key,
        )

    if config.llm_provider in ("openai", "ollama"):
        base_url = config.llm_base_url
        api_key = config.llm_api_key
        if config.llm_provider == "ollama":
            base_url = base_url or "http://localhost:11434/v1"
            api_key = api_key or "ollama"
        return OpenAILLMClient(
            model=config.llm_model,
            api_key=api_key,
            base_url=base_url,
        )

    raise LLMError(f"Unsupported LLM provider: {config.llm_provider!r}")


# ---------------------------------------------------------------------------
# Anthropic format converters
# ---------------------------------------------------------------------------


def _add_cache_control_to_tools(
    tools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add cache_control to the last tool definition for prompt caching.

    Anthropic caches everything up to and including the block with
    ``cache_control``, so marking the last tool caches the entire
    tool definition list.
    """
    if not tools:
        return tools
    cached = [dict(t) for t in tools]
    cached[-1] = {**cached[-1], "cache_control": {"type": "ephemeral"}}
    return cached


def _messages_to_anthropic(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert provider-agnostic messages to Anthropic API format."""
    result: list[dict[str, Any]] = []

    for msg in messages:
        if msg.role == "system":
            continue

        if msg.role == "assistant":
            content: list[dict[str, Any]] = []
            if msg.content:
                content.append({"type": "text", "text": msg.content})
            for tc in msg.tool_calls:
                content.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                )
            result.append({"role": "assistant", "content": content})

        elif msg.role == "tool":
            result.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content or "",
                        }
                    ],
                }
            )

        elif msg.role == "user":
            result.append({"role": "user", "content": msg.content or ""})

    return result


def _anthropic_response_to_llm_response(response: Any) -> LLMResponse:
    """Convert an Anthropic API response to provider-agnostic format."""
    content: str | None = None
    tool_calls: list[ToolCall] = []

    for block in response.content:
        if block.type == "text":
            content = block.text
        elif block.type == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=dict(block.input) if block.input else {},
                )
            )

    usage = TokenUsage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cache_creation_input_tokens=getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
    )

    return LLMResponse(
        content=content,
        tool_calls=tuple(tool_calls),
        stop_reason=response.stop_reason or "",
        usage=usage,
    )


# ---------------------------------------------------------------------------
# OpenAI format converters
# ---------------------------------------------------------------------------


def _messages_to_openai(system: str, messages: list[Message]) -> list[dict[str, Any]]:
    """Convert provider-agnostic messages to OpenAI chat format."""
    result: list[dict[str, Any]] = [{"role": "system", "content": system}]

    for msg in messages:
        if msg.role == "system":
            continue

        if msg.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant"}
            if msg.content:
                entry["content"] = msg.content
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            result.append(entry)

        elif msg.role == "tool":
            result.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content or "",
                }
            )

        elif msg.role == "user":
            result.append({"role": "user", "content": msg.content or ""})

    return result


def _tools_to_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic-style tool definitions to OpenAI function calling format."""
    result: list[dict[str, Any]] = []
    for tool in tools:
        result.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            }
        )
    return result


def _openai_response_to_llm_response(response: Any) -> LLMResponse:
    """Convert an OpenAI API response to provider-agnostic format."""
    choice = response.choices[0]
    message = choice.message

    content = message.content
    tool_calls: list[ToolCall] = []

    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                arguments = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError) as exc:
                raise LLMResponseError(f"Failed to parse tool call arguments: {exc}") from exc
            tool_calls.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments,
                )
            )

    usage = TokenUsage()
    if response.usage:
        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens or 0,
            output_tokens=response.usage.completion_tokens or 0,
        )

    return LLMResponse(
        content=content,
        tool_calls=tuple(tool_calls),
        stop_reason=choice.finish_reason or "",
        usage=usage,
    )
