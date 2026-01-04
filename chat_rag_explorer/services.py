"""
LLM chat service using OpenRouter API.

Provides:
- ChatService: Handles streaming chat completions via OpenAI-compatible API
- Model listing from the OpenRouter API
- Request correlation via request_id for log tracing
- Token usage tracking and performance metrics

The service uses the OpenAI SDK configured to point at OpenRouter,
making it compatible with any OpenAI-compatible backend.
"""
import json
import logging
import time
import requests
from openai import OpenAI
from flask import current_app

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self):
        self.client = None
        logger.debug("ChatService instance created")

    def get_client(self):
        if not self.client:
            base_url = current_app.config["OPENROUTER_BASE_URL"]
            api_key = current_app.config["OPENROUTER_API_KEY"]

            # Log initialization with masked API key
            masked_key = f"{api_key[:8]}...{api_key[-4:]}" if api_key and len(api_key) > 12 else "[MISSING]"
            logger.info(f"Initializing OpenAI client - Base URL: {base_url}, API Key: {masked_key}")

            if not api_key:
                logger.error("OPENROUTER_API_KEY is not configured")
                raise ValueError("OPENROUTER_API_KEY is not configured")

            self.client = OpenAI(
                base_url=base_url,
                api_key=api_key,
            )
            logger.debug("OpenAI client initialized successfully")
        return self.client

    def chat_stream(self, messages, model=None, temperature=None, top_p=None, request_id=None):
        """Stream chat completions from the LLM.

        Args:
            messages: Conversation messages to send
            model: Model identifier to use
            temperature: Sampling temperature (0-2)
            top_p: Nucleus sampling parameter (0-1)
            request_id: Optional request ID for log correlation
        """
        req_id = request_id or "no-id"
        client = self.get_client()
        target_model = model or current_app.config["DEFAULT_MODEL"]

        logger.info(f"[{req_id}] Starting chat stream - Model: {target_model}, temperature: {temperature}, top_p: {top_p}")
        logger.debug(f"[{req_id}] Conversation context ({len(messages)} messages): {json.dumps(messages)}")

        stream_start_time = time.time()
        first_chunk_time = None

        try:
            # Build API call parameters
            api_params = {
                "model": target_model,
                "messages": messages,
                "stream": True,
                "stream_options": {"include_usage": True},
            }

            # Add optional parameters if provided
            if temperature is not None:
                api_params["temperature"] = temperature
            if top_p is not None:
                api_params["top_p"] = top_p

            # Note: stream_options={"include_usage": True} is required for token counts in streams
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
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    usage_data = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                        "model": chunk.model or target_model,
                    }
                    logger.info(
                        f"[{req_id}] Token usage - Prompt: {usage_data['prompt_tokens']}, "
                        f"Completion: {usage_data['completion_tokens']}, Total: {usage_data['total_tokens']}"
                    )
                    # Send as a special metadata marker
                    yield f"__METADATA__:{json.dumps(usage_data)}"

                if len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    if content is not None:
                        chunk_count += 1
                        total_content_length += len(content)
                        full_response.append(content)
                        yield content

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
            yield f"Error: {str(e)}"


    def get_models(self, request_id=None):
        """Fetch available models from OpenRouter API.

        Args:
            request_id: Optional request ID for log correlation
        """
        req_id = request_id or "no-id"
        logger.info(f"[{req_id}] Fetching models from OpenRouter API")

        start_time = time.time()

        try:
            url = f"{current_app.config['OPENROUTER_BASE_URL']}/models"
            headers = {
                "Authorization": f"Bearer {current_app.config['OPENROUTER_API_KEY']}"
            }

            logger.debug(f"[{req_id}] GET {url}")
            response = requests.get(url, headers=headers, timeout=30)

            elapsed = time.time() - start_time
            logger.debug(f"[{req_id}] OpenRouter API response: {response.status_code} ({elapsed:.3f}s)")

            response.raise_for_status()

            data = response.json()
            models = data.get("data", [])

            # Sort models by name for better UX
            models.sort(key=lambda m: m.get("name", m.get("id", "")))

            logger.info(f"[{req_id}] Successfully fetched {len(models)} models ({elapsed:.3f}s)")
            return models

        except requests.RequestException as e:
            elapsed = time.time() - start_time
            # Log more details about the HTTP error
            status_code = getattr(e.response, 'status_code', 'N/A') if hasattr(e, 'response') else 'N/A'
            logger.error(
                f"[{req_id}] Failed to fetch models - Status: {status_code}, "
                f"Error: {type(e).__name__}: {str(e)} ({elapsed:.3f}s)",
                exc_info=True
            )
            raise


chat_service = ChatService()
