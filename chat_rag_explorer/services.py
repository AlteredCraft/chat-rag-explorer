import json
import logging
from openai import OpenAI
from flask import current_app

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self):
        self.client = None

    def get_client(self):
        if not self.client:
            logger.debug("Initializing OpenAI client for OpenRouter")
            self.client = OpenAI(
                base_url=current_app.config["OPENROUTER_BASE_URL"],
                api_key=current_app.config["OPENROUTER_API_KEY"],
            )
        return self.client

    def chat_stream(self, messages, model=None):
        client = self.get_client()
        target_model = model or current_app.config["DEFAULT_MODEL"]

        logger.info(f"Starting chat stream for model: {target_model}")
        logger.debug(f"Conversation context: {json.dumps(messages)}")

        try:
            # Note: stream_options={"include_usage": True} is required for token counts in streams
            stream = client.chat.completions.create(
                model=target_model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
            )

            chunk_count = 0
            for chunk in stream:
                # Log raw LLM response in debug mode
                logger.debug(f"Raw chunk: {chunk.model_dump_json()}")

                # Check for usage data (usually in the final chunk when stream_options is set)
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    usage_data = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                        "model": chunk.model or target_model,
                    }
                    # Send as a special metadata marker
                    yield f"__METADATA__:{json.dumps(usage_data)}"

                if len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    if content is not None:
                        chunk_count += 1
                        yield content

            logger.info(f"Stream completed successfully with {chunk_count} chunks")

        except Exception as e:
            logger.error(f"Error in chat_stream: {str(e)}", exc_info=True)
            yield f"Error: {str(e)}"


chat_service = ChatService()
