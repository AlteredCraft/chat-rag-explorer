"""
LLM chat service.

Provides:
- ChatService: Streaming chat completions via the OpenAI SDK pointed at
  the active provider's OpenAI-compatible endpoint (see providers.py)
- Model listing via the provider abstraction, filtered by .models_list
- Request correlation via request_id for log tracing
- Token usage tracking and performance metrics
"""
import json
import logging
import time
from pathlib import Path
from openai import OpenAI
from flask import current_app

from chat_rag_explorer.error_messages import describe_chat_error
from chat_rag_explorer.providers import get_active_provider, list_models
from chat_rag_explorer.utils import mask_api_key

logger = logging.getLogger(__name__)


# --- Pure helper functions (easily testable without mocks) ---

def build_chat_params(model, messages, temperature=None, top_p=None):
    """Build API parameters for chat completion request.

    Args:
        model: Model identifier
        messages: List of conversation messages
        temperature: Optional sampling temperature (0-2)
        top_p: Optional nucleus sampling parameter (0-1)

    Returns:
        Dict of API parameters ready for the OpenAI client
    """
    params = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if temperature is not None:
        params["temperature"] = temperature
    if top_p is not None:
        params["top_p"] = top_p
    return params


def extract_usage_data(chunk, fallback_model):
    """Extract token usage data from a stream chunk.

    Args:
        chunk: Stream chunk object with potential usage attribute
        fallback_model: Model name to use if chunk.model is None

    Returns:
        Dict with token counts and model, or None if no usage data
    """
    if hasattr(chunk, "usage") and chunk.usage is not None:
        return {
            "prompt_tokens": chunk.usage.prompt_tokens,
            "completion_tokens": chunk.usage.completion_tokens,
            "total_tokens": chunk.usage.total_tokens,
            "model": chunk.model or fallback_model,
        }
    return None


def sort_models_by_name(models):
    """Sort model list by name (or id as fallback).

    Args:
        models: List of model dicts with 'name' and/or 'id' keys

    Returns:
        New sorted list (does not mutate input)
    """
    return sorted(models, key=lambda m: m.get("name", m.get("id", "")))


def _models_list_path():
    """Path to the optional .models_list file in the project root."""
    return Path(current_app.root_path).parent / ".models_list"


def load_models_list():
    """Load model IDs from .models_list file if it exists.

    This file contains models recommended for RAG scenarios. One model ID
    per line, lines starting with # are comments, empty lines are ignored.

    Returns:
        Set of model IDs to include, or None if file doesn't exist or is empty
    """
    models_list_path = _models_list_path()
    if not models_list_path.exists():
        return None

    models = set()
    # Read as UTF-8 explicitly so a non-ASCII comment does not break the file on
    # Windows, where the default encoding is cp1252 rather than UTF-8.
    with open(models_list_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                models.add(line)
    return models if models else None


def get_models_list_status():
    """Get status information about the .models_list file.

    Returns:
        Dict with:
            - exists: bool - Whether the file exists
            - count: int - Number of model IDs in the file (0 if doesn't exist)
            - path: str - Relative path to the file
    """
    models = load_models_list()
    return {
        "exists": _models_list_path().exists(),
        "count": len(models) if models else 0,
        "path": ".models_list"
    }


class ChatService:
    def __init__(self):
        self.client = None
        logger.debug("ChatService instance created")

    def is_configured(self):
        """Check if the active provider's API key is configured.

        Returns:
            bool: True if API key is set and non-empty, False otherwise
        """
        return bool(get_active_provider().api_key)

    def get_client(self):
        if not self.client:
            provider = get_active_provider()

            # Log initialization with masked API key
            logger.info(
                f"Initializing OpenAI client - Provider: {provider.name}, "
                f"Base URL: {provider.base_url}, API Key: {mask_api_key(provider.api_key)}"
            )

            if not provider.api_key:
                logger.error(f"API key for provider '{provider.name}' is not configured")
                raise ValueError(f"API key for provider '{provider.name}' is not configured")

            self.client = OpenAI(
                base_url=provider.base_url,
                api_key=provider.api_key,
            )
            logger.debug("OpenAI client initialized successfully")
        return self.client

    def chat_stream(self, messages, model=None, temperature=None, top_p=None, request_id=None):
        """Stream chat completion events from the LLM.

        Yields typed (kind, payload) tuples so callers can distinguish
        content from metadata without sniffing string prefixes:
        - ("content", str): a chunk of assistant response text
        - ("usage", dict): token usage data, usually once near stream end
        - ("error", str): error message; the stream ends after this

        Args:
            messages: Conversation messages to send
            model: Model identifier to use
            temperature: Sampling temperature (0-2)
            top_p: Nucleus sampling parameter (0-1)
            request_id: Optional request ID for log correlation
        """
        req_id = request_id or "no-id"
        target_model = model or current_app.config["DEFAULT_MODEL"]

        logger.info(f"[{req_id}] Starting chat stream - Model: {target_model}, temperature: {temperature}, top_p: {top_p}")
        logger.debug(f"[{req_id}] Conversation context ({len(messages)} messages): {json.dumps(messages)}")

        stream_start_time = time.time()
        first_chunk_time = None

        try:
            # Client creation happens inside the try so a misconfigured
            # provider surfaces as a clean ("error", ...) event instead of
            # an exception that breaks the HTTP stream mid-response
            client = self.get_client()

            # Build API call parameters
            api_params = build_chat_params(target_model, messages, temperature, top_p)
            stream = client.chat.completions.create(**api_params)

            chunk_count = 0
            total_content_length = 0
            full_response = []  # Accumulate response for debug logging

            for chunk in stream:
                # Track time to first chunk (TTFC)
                if first_chunk_time is None and len(chunk.choices) > 0:
                    first_chunk_time = time.time()
                    ttfc = first_chunk_time - stream_start_time
                    logger.debug(f"[{req_id}] Time to first chunk: {ttfc:.3f}s")

                # Check for usage data (usually in the final chunk when stream_options is set)
                usage_data = extract_usage_data(chunk, target_model)
                if usage_data:
                    logger.info(
                        f"[{req_id}] Token usage - Prompt: {usage_data['prompt_tokens']}, "
                        f"Completion: {usage_data['completion_tokens']}, Total: {usage_data['total_tokens']}"
                    )
                    yield ("usage", usage_data)

                if len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    if content is not None:
                        chunk_count += 1
                        total_content_length += len(content)
                        full_response.append(content)
                        yield ("content", content)

                # Log progress every 50 chunks (reduced verbosity)
                if chunk_count > 0 and chunk_count % 50 == 0:
                    logger.debug(f"[{req_id}] Streaming progress: {chunk_count} chunks, {total_content_length} chars")

            elapsed = time.time() - stream_start_time
            logger.info(
                f"[{req_id}] Stream completed - {chunk_count} chunks, "
                f"{total_content_length} chars, {elapsed:.3f}s total"
            )
            logger.debug(f"[{req_id}] LLM response:\n{''.join(full_response)}")

        except Exception as e:
            elapsed = time.time() - stream_start_time
            logger.error(f"[{req_id}] Stream error after {elapsed:.3f}s: {type(e).__name__}: {str(e)}", exc_info=True)
            # The raw error is in the log above; the user gets a message
            # that says what is misconfigured and where to fix it
            yield ("error", describe_chat_error(e, get_active_provider(), target_model))


    def get_models(self, request_id=None):
        """Fetch available models from the active provider.

        Applies the optional .models_list filter and sorts by name.

        Args:
            request_id: Optional request ID for log correlation
        """
        req_id = request_id or "no-id"
        provider = get_active_provider()
        logger.info(f"[{req_id}] Fetching models from provider '{provider.name}'")

        models = list_models(provider, req_id)

        # Filter by .models_list if it exists
        models_list = load_models_list()
        if models_list:
            models = [m for m in models if m.get("id") in models_list]
            logger.info(f"[{req_id}] Filtered to {len(models)} models from .models_list")

        models = sort_models_by_name(models)

        logger.info(f"[{req_id}] Successfully fetched {len(models)} models")
        return models


chat_service = ChatService()
