"""
Flask routes and API endpoints.

Web Pages:
- / : Main chat interface
- /settings : Configuration page

API Endpoints:
- /api/chat : POST - Stream chat completions from LLM
- /api/models : GET - List available models from OpenRouter
- /api/prompts : GET/POST - List or create system prompts
- /api/prompts/<id> : GET/PUT/DELETE - Manage individual prompts
- /api/rag/* : RAG configuration and ChromaDB management

All API endpoints use request_id for log correlation and include
timing metrics for observability.
"""
import json
import logging
import time
import uuid
from flask import Blueprint, current_app, render_template, request, Response, stream_with_context, jsonify
from chat_rag_explorer.services import chat_service
from chat_rag_explorer.prompt_service import prompt_service
from chat_rag_explorer.rag_config_service import rag_config_service
from chat_rag_explorer.chat_history_service import chat_history_service

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


def generate_request_id():
    """Generate a short unique request ID for log correlation."""
    return str(uuid.uuid4())[:8]


@main_bp.route("/")
def index():
    logger.debug("Serving index page")
    return render_template("index.html")


@main_bp.route("/settings")
def settings():
    logger.debug("Serving settings page")
    return render_template("settings.html")


@main_bp.route("/api/models")
def get_models():
    request_id = generate_request_id()
    start_time = time.time()
    logger.info(f"[{request_id}] GET /api/models - Fetching available models")

    try:
        models = chat_service.get_models(request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] GET /api/models - Returned {len(models)} models ({elapsed:.3f}s)")
        return jsonify({"data": models})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] GET /api/models - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/prompts")
def get_prompts():
    request_id = generate_request_id()
    start_time = time.time()
    logger.info(f"[{request_id}] GET /api/prompts - Fetching available prompts")

    try:
        prompts = prompt_service.get_prompts(request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] GET /api/prompts - Returned {len(prompts)} prompts ({elapsed:.3f}s)")
        return jsonify({"data": prompts})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] GET /api/prompts - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/prompts/<prompt_id>")
def get_prompt(prompt_id):
    request_id = generate_request_id()
    start_time = time.time()
    logger.info(f"[{request_id}] GET /api/prompts/{prompt_id} - Fetching prompt content")

    try:
        prompt = prompt_service.get_prompt_by_id(prompt_id, request_id)
        if prompt is None:
            logger.warning(f"[{request_id}] GET /api/prompts/{prompt_id} - Not found")
            return jsonify({"error": "Prompt not found"}), 404
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] GET /api/prompts/{prompt_id} - Success ({elapsed:.3f}s)")
        return jsonify({"data": prompt})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] GET /api/prompts/{prompt_id} - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/prompts", methods=["POST"])
def create_prompt():
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    prompt_id = data.get("id", "").strip()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    content = data.get("content", "").strip()

    logger.info(f"[{request_id}] POST /api/prompts - Creating prompt: {prompt_id}")

    if not prompt_id:
        return jsonify({"error": "Prompt ID is required"}), 400
    if not title:
        return jsonify({"error": "Title is required"}), 400

    # Check if prompt ID is protected
    if prompt_service.is_protected(prompt_id):
        return jsonify({"error": "Cannot use this prompt ID"}), 403

    # Check if prompt already exists
    existing = prompt_service.get_prompt_by_id(prompt_id, request_id)
    if existing:
        return jsonify({"error": "A prompt with this ID already exists"}), 409

    try:
        prompt = prompt_service.save_prompt(prompt_id, title, description, content, request_id)
        if prompt is None:
            return jsonify({"error": "Failed to create prompt"}), 500
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] POST /api/prompts - Created ({elapsed:.3f}s)")
        return jsonify({"data": prompt}), 201
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] POST /api/prompts - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/prompts/<prompt_id>", methods=["PUT"])
def update_prompt(prompt_id):
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    content = data.get("content", "").strip()

    logger.info(f"[{request_id}] PUT /api/prompts/{prompt_id} - Updating prompt")

    if not title:
        return jsonify({"error": "Title is required"}), 400

    # Check if prompt is protected
    if prompt_service.is_protected(prompt_id):
        return jsonify({"error": "Cannot edit protected prompt"}), 403

    # Check if prompt exists
    existing = prompt_service.get_prompt_by_id(prompt_id, request_id)
    if not existing:
        return jsonify({"error": "Prompt not found"}), 404

    try:
        prompt = prompt_service.save_prompt(prompt_id, title, description, content, request_id)
        if prompt is None:
            return jsonify({"error": "Failed to update prompt"}), 500
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] PUT /api/prompts/{prompt_id} - Updated ({elapsed:.3f}s)")
        return jsonify({"data": prompt})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] PUT /api/prompts/{prompt_id} - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/prompts/<prompt_id>", methods=["DELETE"])
def delete_prompt(prompt_id):
    request_id = generate_request_id()
    start_time = time.time()

    logger.info(f"[{request_id}] DELETE /api/prompts/{prompt_id} - Deleting prompt")

    # Check if prompt is protected
    if prompt_service.is_protected(prompt_id):
        return jsonify({"error": "Cannot delete protected prompt"}), 403

    # Check if prompt exists
    existing = prompt_service.get_prompt_by_id(prompt_id, request_id)
    if not existing:
        return jsonify({"error": "Prompt not found"}), 404

    try:
        success = prompt_service.delete_prompt(prompt_id, request_id)
        if not success:
            return jsonify({"error": "Failed to delete prompt"}), 500
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] DELETE /api/prompts/{prompt_id} - Deleted ({elapsed:.3f}s)")
        return jsonify({"success": True})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] DELETE /api/prompts/{prompt_id} - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/chat", methods=["POST"])
def chat():
    # Generate full UUID for chat history, short version for app logs
    full_request_id = str(uuid.uuid4())
    request_id = full_request_id[:8]
    start_time = time.time()

    data = request.json
    messages = data.get("messages", [])
    model = data.get("model")
    temperature = data.get("temperature")
    top_p = data.get("top_p")

    # Calculate total message content length for logging
    total_content_length = sum(len(m.get("content", "")) for m in messages)

    logger.info(
        f"[{request_id}] POST /api/chat - Model: {model}, "
        f"Messages: {len(messages)}, Content length: {total_content_length} chars, "
        f"temperature: {temperature}, top_p: {top_p}"
    )
    logger.debug(f"[{request_id}] Message roles: {[m.get('role') for m in messages]}")

    if not messages:
        logger.warning(f"[{request_id}] POST /api/chat - Rejected: no messages provided")
        return {"error": "Messages are required"}, 400

    if not model:
        logger.warning(f"[{request_id}] POST /api/chat - No model specified, will use default")

    def stream_with_logging():
        """Wrapper to add logging and chat history around the stream."""
        accumulated_content = []
        chunk_count = 0
        ttfc_time = None
        token_usage = None
        error_message = None
        status = "success"
        resolved_model = model

        try:
            for chunk in chat_service.chat_stream(messages, model, temperature, top_p, request_id):
                # Track time to first content chunk
                if ttfc_time is None and not chunk.startswith("__METADATA__") and not chunk.startswith("Error:"):
                    ttfc_time = time.time()

                # Extract metadata (token usage) - don't yield to client
                if chunk.startswith("__METADATA__:"):
                    metadata_json = chunk[len("__METADATA__:"):]
                    try:
                        metadata = json.loads(metadata_json)
                        token_usage = {
                            "prompt_tokens": metadata.get("prompt_tokens"),
                            "completion_tokens": metadata.get("completion_tokens"),
                            "total_tokens": metadata.get("total_tokens"),
                        }
                        # Update model if returned in metadata
                        if metadata.get("model"):
                            resolved_model = metadata.get("model")
                    except json.JSONDecodeError:
                        pass
                    continue  # Don't yield metadata to client

                # Track errors
                if chunk.startswith("Error:"):
                    status = "error"
                    error_message = chunk
                else:
                    accumulated_content.append(chunk)

                chunk_count += 1
                yield chunk

            elapsed = time.time() - start_time
            ttfc_seconds = (ttfc_time - start_time) if ttfc_time else None

            logger.info(f"[{request_id}] POST /api/chat - Stream completed ({elapsed:.3f}s, {chunk_count} chunks)")

            # Build the entry data (used for both logging and client metadata)
            final_model = resolved_model or current_app.config.get("DEFAULT_MODEL", "unknown")
            response_content = "".join(accumulated_content)

            entry_data = {
                "request_id": full_request_id,
                "model": final_model,
                "params": {
                    "temperature": temperature,
                    "top_p": top_p,
                },
                "messages": messages,
                "response": response_content,
                "status": status,
                "error": error_message,
                "tokens": token_usage,
                "timing": {
                    "total_ms": round(elapsed * 1000, 2),
                    "ttfc_ms": round(ttfc_seconds * 1000, 2) if ttfc_seconds else None,
                },
                "chunks": chunk_count,
            }

            # Log to chat history
            chat_history_service.log_interaction(
                request_id=full_request_id,
                messages=messages,
                model=final_model,
                temperature=temperature,
                top_p=top_p,
                response_content=response_content,
                status=status,
                error=error_message,
                total_seconds=elapsed,
                ttfc_seconds=ttfc_seconds,
                chunk_count=chunk_count,
                tokens=token_usage,
            )

            # Send metadata to client for details modal
            yield f"__METADATA__:{json.dumps(entry_data)}"

        except Exception as e:
            elapsed = time.time() - start_time
            ttfc_seconds = (ttfc_time - start_time) if ttfc_time else None
            logger.error(f"[{request_id}] POST /api/chat - Stream error after {elapsed:.3f}s: {str(e)}", exc_info=True)

            # Build the entry data for error case
            final_model = resolved_model or model or current_app.config.get("DEFAULT_MODEL", "unknown")
            response_content = "".join(accumulated_content)

            entry_data = {
                "request_id": full_request_id,
                "model": final_model,
                "params": {
                    "temperature": temperature,
                    "top_p": top_p,
                },
                "messages": messages,
                "response": response_content,
                "status": "error",
                "error": str(e),
                "tokens": token_usage,
                "timing": {
                    "total_ms": round(elapsed * 1000, 2),
                    "ttfc_ms": round(ttfc_seconds * 1000, 2) if ttfc_seconds else None,
                },
                "chunks": chunk_count,
            }

            # Log failed interaction to chat history
            chat_history_service.log_interaction(
                request_id=full_request_id,
                messages=messages,
                model=final_model,
                temperature=temperature,
                top_p=top_p,
                response_content=response_content,
                status="error",
                error=str(e),
                total_seconds=elapsed,
                ttfc_seconds=ttfc_seconds,
                chunk_count=chunk_count,
                tokens=token_usage,
            )
            raise

    return Response(
        stream_with_context(stream_with_logging()),
        mimetype="text/plain",
    )


# ==================== RAG Configuration Endpoints ====================


@main_bp.route("/api/rag/config")
def get_rag_config():
    """GET - Retrieve current RAG configuration."""
    request_id = generate_request_id()
    start_time = time.time()
    logger.info(f"[{request_id}] GET /api/rag/config - Fetching RAG configuration")

    try:
        config = rag_config_service.get_config(request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] GET /api/rag/config - Success ({elapsed:.3f}s)")
        return jsonify({"data": config})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] GET /api/rag/config - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/rag/config", methods=["POST"])
def save_rag_config():
    """POST - Save RAG configuration."""
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    logger.info(f"[{request_id}] POST /api/rag/config - Saving RAG configuration (mode: {data.get('mode')})")

    try:
        result = rag_config_service.save_config(data, request_id)
        elapsed = time.time() - start_time

        if 'error' in result:
            logger.warning(f"[{request_id}] POST /api/rag/config - Validation failed: {result['error']}")
            return jsonify(result), 400

        logger.info(f"[{request_id}] POST /api/rag/config - Saved ({elapsed:.3f}s)")
        return jsonify({"data": result['config']})
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] POST /api/rag/config - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/rag/validate-path", methods=["POST"])
def validate_rag_path():
    """POST - Validate a local ChromaDB path."""
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    path = data.get("path", "")
    logger.info(f"[{request_id}] POST /api/rag/validate-path - Validating: {path}")

    try:
        result = rag_config_service.validate_local_path(path, request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] POST /api/rag/validate-path - Valid: {result['valid']} ({elapsed:.3f}s)")
        return jsonify(result)
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] POST /api/rag/validate-path - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"valid": False, "message": str(e)}), 500


@main_bp.route("/api/rag/test-connection", methods=["POST"])
def test_rag_connection():
    """POST - Test ChromaDB connection with provided config."""
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    mode = data.get("mode", "local")
    logger.info(f"[{request_id}] POST /api/rag/test-connection - Testing connection (mode: {mode})")

    try:
        result = rag_config_service.test_connection(data, request_id)
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] POST /api/rag/test-connection - Success: {result['success']} ({elapsed:.3f}s)")
        return jsonify(result)
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] POST /api/rag/test-connection - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/api/rag/api-key-status")
def get_rag_api_key_status():
    """GET - Check if CHROMADB_API_KEY is configured."""
    request_id = generate_request_id()
    logger.debug(f"[{request_id}] GET /api/rag/api-key-status - Checking API key status")

    try:
        result = rag_config_service.get_api_key_status(request_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"[{request_id}] GET /api/rag/api-key-status - Failed: {str(e)}", exc_info=True)
        return jsonify({"configured": False, "masked": None}), 500


@main_bp.route("/api/rag/sample", methods=["POST"])
def get_rag_sample():
    """POST - Fetch sample records from a ChromaDB collection."""
    request_id = generate_request_id()
    start_time = time.time()

    data = request.json
    collection = data.get("collection", "")
    logger.info(f"[{request_id}] POST /api/rag/sample - Fetching samples from '{collection}'")

    try:
        result = rag_config_service.get_sample_records(data, collection, limit=5, request_id=request_id)
        elapsed = time.time() - start_time

        if not result.get('success'):
            logger.warning(f"[{request_id}] POST /api/rag/sample - Failed: {result.get('message')}")
            return jsonify(result), 400

        logger.info(f"[{request_id}] POST /api/rag/sample - Returned {result.get('count')} records ({elapsed:.3f}s)")
        return jsonify(result)
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] POST /api/rag/sample - Failed after {elapsed:.3f}s: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500
