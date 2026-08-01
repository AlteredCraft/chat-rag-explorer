"""
Flask routes and API endpoints.

Web Pages:
- / : Main chat interface
- /settings : Configuration page
- /about : About page with project information

API Endpoints:
- /api/chat : POST - Stream chat completions from LLM
- /api/models : GET - List available models from OpenRouter
- /api/prompts : GET/POST - List or create system prompts
- /api/prompts/<id> : GET/PUT/DELETE - Manage individual prompts
- /api/rag/* : RAG configuration and ChromaDB management

Cross-cutting concerns are handled once for the whole blueprint:
- before_request attaches a request ID and start time to `g` for
  log correlation and timing metrics
- errorhandler(Exception) logs unexpected failures and returns a
  JSON 500 response
"""
import json
import logging
import time
import uuid
from flask import Blueprint, current_app, g, render_template, request, Response, stream_with_context, jsonify
from werkzeug.exceptions import HTTPException
from chat_rag_explorer.services import chat_service, get_models_list_status
from chat_rag_explorer.prompt_service import prompt_service
from chat_rag_explorer.rag_config_service import rag_config_service
from chat_rag_explorer.chat_history_service import chat_history_service

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.before_request
def start_request_tracking():
    """Attach a request ID and start time to the request context (g).

    Every request gets a full UUID (used for chat history correlation)
    and a short 8-char prefix (used in application logs).
    """
    g.request_id_full = str(uuid.uuid4())
    g.request_id = g.request_id_full[:8]
    g.start_time = time.time()


@main_bp.errorhandler(Exception)
def handle_unexpected_error(e):
    """Log unexpected errors and return a JSON 500 response.

    HTTP errors (404, 405, ...) pass through so Flask renders them normally.
    """
    if isinstance(e, HTTPException):
        return e
    logger.error(
        f"[{g.request_id}] {request.method} {request.path} - "
        f"Failed after {request_elapsed():.3f}s: {e}",
        exc_info=True,
    )
    return jsonify({"error": str(e)}), 500


def request_elapsed():
    """Seconds since the current request started."""
    return time.time() - g.start_time


def escape_xml_attr(value):
    """
    Escape a string value for use in an XML attribute.

    Handles special characters: &, <, >, ", '
    """
    if not isinstance(value, str):
        value = str(value)
    return (value
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


# Metadata fields to include as attributes on document tags (if present)
METADATA_FIELDS = ['title', 'author', 'url', 'section_title', 'section_number']


def build_augmented_message(user_message, documents, metadatas=None):
    """
    Augment a user message with retrieved RAG context using XML tags.

    Wraps retrieved documents in <knowledge_base_context> and the user's
    message in <original_user_message> for clear structure. Each document
    tag includes metadata attributes (title, author, url, etc.) when available.

    Args:
        user_message: The original user message text
        documents: List of retrieved document texts
        metadatas: Optional list of metadata dicts for each document

    Returns:
        Augmented message string with context prepended in XML format
    """
    if not documents:
        return user_message

    context_parts = ["<knowledge_base_context>"]
    for i, doc in enumerate(documents, 1):
        # Build attributes list starting with index
        attrs = [f'index="{i}"']

        # Add metadata fields if available
        if metadatas and (i - 1) < len(metadatas):
            meta = metadatas[i - 1] or {}
            for key in METADATA_FIELDS:
                if key in meta and meta[key]:
                    attrs.append(f'{key}="{escape_xml_attr(meta[key])}"')

        context_parts.append(f'<document {" ".join(attrs)}>{doc}</document>')
    context_parts.append("</knowledge_base_context>")
    context_parts.append("")
    context_parts.append("<original_user_message>")
    context_parts.append(user_message)
    context_parts.append("</original_user_message>")

    return "\n".join(context_parts)


def apply_rag_context(messages, rag_enabled, request_id):
    """
    Retrieve RAG context and augment the latest user message if enabled.

    Args:
        messages: Conversation messages from the client
        rag_enabled: Whether the client requested RAG retrieval
        request_id: Request ID for log correlation

    Returns:
        Tuple of (messages_for_llm, rag_result). messages_for_llm is the
        original list unless context was retrieved, in which case the last
        user message is replaced with an augmented version. rag_result is
        the raw query_collection result, or None if no query was made.
    """
    if not rag_enabled:
        return messages, None

    user_messages = [m for m in messages if m.get("role") == "user"]
    if not user_messages:
        return messages, None

    latest_user_msg = user_messages[-1]["content"]
    rag_result = rag_config_service.query_collection(
        query_text=latest_user_msg,
        request_id=request_id,
    )

    if not rag_result.get("success"):
        logger.warning(f"[{request_id}] RAG query failed: {rag_result.get('message')}")
        return messages, rag_result

    if not rag_result.get("documents"):
        logger.debug(f"[{request_id}] RAG query returned no documents")
        return messages, rag_result

    logger.info(
        f"[{request_id}] RAG retrieved {len(rag_result['documents'])} documents "
        f"from '{rag_result.get('collection')}'"
    )

    augmented_content = build_augmented_message(
        latest_user_msg,
        rag_result["documents"],
        rag_result.get("metadatas"),
    )
    return messages[:-1] + [{"role": "user", "content": augmented_content}], rag_result


def build_rag_metadata(rag_result):
    """
    Build the RAG metadata dict for the client details modal and history log.

    Args:
        rag_result: Result dict from query_collection, or None if no query ran

    Returns:
        Metadata dict with retrieval details, or None when rag_result is None
    """
    if not rag_result:
        return None

    documents = rag_result.get("documents") or []
    return {
        "enabled": True,
        "documents_retrieved": len(documents),
        "collection": rag_result.get("collection"),
        "documents": documents,
        "metadatas": rag_result.get("metadatas") or [],
        "distances": rag_result.get("distances") or [],
        "ids": rag_result.get("ids") or [],
        "n_results": rag_result.get("n_results"),
        "distance_threshold": rag_result.get("distance_threshold"),
    }


@main_bp.route("/")
def index():
    logger.debug("Serving index page")
    return render_template("index.html")


@main_bp.route("/settings")
def settings():
    logger.debug("Serving settings page")
    return render_template("settings.html")


@main_bp.route("/about")
def about():
    logger.debug("Serving about page")
    return render_template("about.html")


@main_bp.route("/api/status")
def get_status():
    """GET - Return application status: API key state and default model.

    The default model is served here so the frontend has a single source
    of truth instead of hardcoding a copy of config.py's DEFAULT_MODEL.
    """
    logger.debug(f"[{g.request_id}] GET /api/status - Checking app status")

    return jsonify({
        "api_key_configured": chat_service.is_configured(),
        "default_model": current_app.config.get("DEFAULT_MODEL"),
    })


@main_bp.route("/api/models")
def get_models():
    logger.info(f"[{g.request_id}] GET /api/models - Fetching available models")

    models = chat_service.get_models(g.request_id)
    models_list_status = get_models_list_status()

    logger.info(f"[{g.request_id}] GET /api/models - Returned {len(models)} models ({request_elapsed():.3f}s)")
    return jsonify({
        "data": models,
        "models_list": models_list_status
    })


@main_bp.route("/api/prompts")
def get_prompts():
    logger.info(f"[{g.request_id}] GET /api/prompts - Fetching available prompts")

    prompts = prompt_service.get_prompts(g.request_id)

    logger.info(f"[{g.request_id}] GET /api/prompts - Returned {len(prompts)} prompts ({request_elapsed():.3f}s)")
    return jsonify({"data": prompts})


@main_bp.route("/api/prompts/<prompt_id>")
def get_prompt(prompt_id):
    logger.info(f"[{g.request_id}] GET /api/prompts/{prompt_id} - Fetching prompt content")

    prompt = prompt_service.get_prompt_by_id(prompt_id, g.request_id)
    if prompt is None:
        logger.warning(f"[{g.request_id}] GET /api/prompts/{prompt_id} - Not found")
        return jsonify({"error": "Prompt not found"}), 404

    logger.info(f"[{g.request_id}] GET /api/prompts/{prompt_id} - Success ({request_elapsed():.3f}s)")
    return jsonify({"data": prompt})


@main_bp.route("/api/prompts", methods=["POST"])
def create_prompt():
    data = request.json
    prompt_id = data.get("id", "").strip()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    content = data.get("content", "").strip()

    logger.info(f"[{g.request_id}] POST /api/prompts - Creating prompt: {prompt_id}")

    if not prompt_id:
        return jsonify({"error": "Prompt ID is required"}), 400
    if not title:
        return jsonify({"error": "Title is required"}), 400

    if prompt_service.is_protected(prompt_id):
        return jsonify({"error": "Cannot use this prompt ID"}), 403

    if prompt_service.get_prompt_by_id(prompt_id, g.request_id):
        return jsonify({"error": "A prompt with this ID already exists"}), 409

    prompt = prompt_service.save_prompt(prompt_id, title, description, content, g.request_id)
    if prompt is None:
        return jsonify({"error": "Failed to create prompt"}), 500

    logger.info(f"[{g.request_id}] POST /api/prompts - Created ({request_elapsed():.3f}s)")
    return jsonify({"data": prompt}), 201


@main_bp.route("/api/prompts/<prompt_id>", methods=["PUT"])
def update_prompt(prompt_id):
    data = request.json
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    content = data.get("content", "").strip()

    logger.info(f"[{g.request_id}] PUT /api/prompts/{prompt_id} - Updating prompt")

    if not title:
        return jsonify({"error": "Title is required"}), 400

    if prompt_service.is_protected(prompt_id):
        return jsonify({"error": "Cannot edit protected prompt"}), 403

    if not prompt_service.get_prompt_by_id(prompt_id, g.request_id):
        return jsonify({"error": "Prompt not found"}), 404

    prompt = prompt_service.save_prompt(prompt_id, title, description, content, g.request_id)
    if prompt is None:
        return jsonify({"error": "Failed to update prompt"}), 500

    logger.info(f"[{g.request_id}] PUT /api/prompts/{prompt_id} - Updated ({request_elapsed():.3f}s)")
    return jsonify({"data": prompt})


@main_bp.route("/api/prompts/<prompt_id>", methods=["DELETE"])
def delete_prompt(prompt_id):
    logger.info(f"[{g.request_id}] DELETE /api/prompts/{prompt_id} - Deleting prompt")

    if prompt_service.is_protected(prompt_id):
        return jsonify({"error": "Cannot delete protected prompt"}), 403

    if not prompt_service.get_prompt_by_id(prompt_id, g.request_id):
        return jsonify({"error": "Prompt not found"}), 404

    success = prompt_service.delete_prompt(prompt_id, g.request_id)
    if not success:
        return jsonify({"error": "Failed to delete prompt"}), 500

    logger.info(f"[{g.request_id}] DELETE /api/prompts/{prompt_id} - Deleted ({request_elapsed():.3f}s)")
    return jsonify({"success": True})


@main_bp.route("/api/chat", methods=["POST"])
def chat():
    # Capture request-context values as locals so the streaming generator
    # below doesn't depend on the request context staying alive
    request_id = g.request_id
    full_request_id = g.request_id_full
    start_time = g.start_time

    data = request.json
    messages = data.get("messages", [])
    model = data.get("model")
    temperature = data.get("temperature")
    top_p = data.get("top_p")
    rag_enabled = data.get("rag_enabled", False)

    # Calculate total message content length for logging
    total_content_length = sum(len(m.get("content", "")) for m in messages)

    logger.info(
        f"[{request_id}] POST /api/chat - Model: {model}, "
        f"Messages: {len(messages)}, Content length: {total_content_length} chars, "
        f"temperature: {temperature}, top_p: {top_p}, rag_enabled: {rag_enabled}"
    )
    logger.debug(f"[{request_id}] Message roles: {[m.get('role') for m in messages]}")

    if not messages:
        logger.warning(f"[{request_id}] POST /api/chat - Rejected: no messages provided")
        return {"error": "Messages are required"}, 400

    if not model:
        logger.warning(f"[{request_id}] POST /api/chat - No model specified, will use default")

    messages_for_llm, rag_result = apply_rag_context(messages, rag_enabled, request_id)

    def stream_with_logging():
        """Stream LLM chunks, then log the interaction and append metadata."""
        accumulated_content = []
        chunk_count = 0
        ttfc_time = None
        token_usage = None
        error_message = None
        status = "success"
        resolved_model = model
        stream_error = None

        try:
            for kind, payload in chat_service.chat_stream(messages_for_llm, model, temperature, top_p, request_id):
                # Usage data is kept for the final metadata payload, not streamed
                if kind == "usage":
                    token_usage = {
                        "prompt_tokens": payload.get("prompt_tokens"),
                        "completion_tokens": payload.get("completion_tokens"),
                        "total_tokens": payload.get("total_tokens"),
                    }
                    if payload.get("model"):
                        resolved_model = payload["model"]
                    continue

                if kind == "error":
                    status = "error"
                    error_message = payload
                    chunk_count += 1
                    yield f"Error: {payload}"
                    continue

                # Content chunk
                if ttfc_time is None:
                    ttfc_time = time.time()
                accumulated_content.append(payload)
                chunk_count += 1
                yield payload

        except Exception as e:
            stream_error = e
            status = "error"
            error_message = str(e)
            logger.error(
                f"[{request_id}] POST /api/chat - Stream error after "
                f"{time.time() - start_time:.3f}s: {str(e)}", exc_info=True
            )

        # Single finalize path for success, in-band errors, and exceptions:
        # assemble the metadata payload once, log it, then either re-raise
        # (exception case) or append it to the stream for the client.
        elapsed = time.time() - start_time
        ttfc_seconds = (ttfc_time - start_time) if ttfc_time else None

        entry_data = {
            "request_id": full_request_id,
            "model": resolved_model or current_app.config.get("DEFAULT_MODEL", "unknown"),
            "params": {
                "temperature": temperature,
                "top_p": top_p,
            },
            "messages": messages_for_llm,  # Send augmented messages for transparency
            "messages_original": messages,  # Also include original for reference
            "response": "".join(accumulated_content),
            "status": status,
            "error": error_message,
            "tokens": token_usage,
            "timing": {
                "total_ms": round(elapsed * 1000, 2),
                "ttfc_ms": round(ttfc_seconds * 1000, 2) if ttfc_seconds else None,
            },
            "chunks": chunk_count,
            "rag": build_rag_metadata(rag_result),
        }

        chat_history_service.log_interaction(entry_data)

        if stream_error:
            raise stream_error

        logger.info(f"[{request_id}] POST /api/chat - Stream completed ({elapsed:.3f}s, {chunk_count} chunks)")

        # Send metadata to client for details modal
        yield f"__METADATA__:{json.dumps(entry_data)}"

    return Response(
        stream_with_context(stream_with_logging()),
        mimetype="text/plain",
    )


# ==================== RAG Configuration Endpoints ====================


@main_bp.route("/api/rag/config")
def get_rag_config():
    """GET - Retrieve current RAG configuration."""
    logger.info(f"[{g.request_id}] GET /api/rag/config - Fetching RAG configuration")

    config = rag_config_service.get_config(g.request_id)

    logger.info(f"[{g.request_id}] GET /api/rag/config - Success ({request_elapsed():.3f}s)")
    return jsonify({"data": config})


@main_bp.route("/api/rag/config", methods=["POST"])
def save_rag_config():
    """POST - Save RAG configuration."""
    data = request.json
    logger.info(f"[{g.request_id}] POST /api/rag/config - Saving RAG configuration (mode: {data.get('mode')})")

    result = rag_config_service.save_config(data, g.request_id)
    if 'error' in result:
        logger.warning(f"[{g.request_id}] POST /api/rag/config - Validation failed: {result['error']}")
        return jsonify(result), 400

    logger.info(f"[{g.request_id}] POST /api/rag/config - Saved ({request_elapsed():.3f}s)")
    return jsonify(result)


@main_bp.route("/api/rag/validate-path", methods=["POST"])
def validate_rag_path():
    """POST - Validate a local ChromaDB path."""
    path = request.json.get("path", "")
    logger.info(f"[{g.request_id}] POST /api/rag/validate-path - Validating: {path}")

    result = rag_config_service.validate_local_path(path, g.request_id)

    logger.info(f"[{g.request_id}] POST /api/rag/validate-path - Valid: {result['valid']} ({request_elapsed():.3f}s)")
    return jsonify(result)


@main_bp.route("/api/rag/test-connection", methods=["POST"])
def test_rag_connection():
    """POST - Test ChromaDB connection with provided config."""
    data = request.json
    logger.info(f"[{g.request_id}] POST /api/rag/test-connection - Testing connection (mode: {data.get('mode', 'local')})")

    result = rag_config_service.test_connection(data, g.request_id)

    logger.info(f"[{g.request_id}] POST /api/rag/test-connection - Success: {result['success']} ({request_elapsed():.3f}s)")
    return jsonify(result)


@main_bp.route("/api/rag/api-key-status")
def get_rag_api_key_status():
    """GET - Check if CHROMADB_API_KEY is configured."""
    logger.debug(f"[{g.request_id}] GET /api/rag/api-key-status - Checking API key status")

    return jsonify(rag_config_service.get_api_key_status(g.request_id))


@main_bp.route("/api/rag/discover-databases")
def discover_rag_databases():
    """GET - Discover ChromaDB databases in ./data/ directory."""
    logger.info(f"[{g.request_id}] GET /api/rag/discover-databases - Discovering databases")

    result = rag_config_service.discover_databases(g.request_id)

    logger.info(
        f"[{g.request_id}] GET /api/rag/discover-databases - "
        f"Found {len(result.get('databases', []))} database(s) ({request_elapsed():.3f}s)"
    )
    return jsonify(result)


@main_bp.route("/api/rag/sample", methods=["POST"])
def get_rag_sample():
    """POST - Fetch sample records from a ChromaDB collection."""
    data = request.json
    collection = data.get("collection", "")
    logger.info(f"[{g.request_id}] POST /api/rag/sample - Fetching samples from '{collection}'")

    result = rag_config_service.get_sample_records(data, collection, limit=5, request_id=g.request_id)
    if not result.get('success'):
        logger.warning(f"[{g.request_id}] POST /api/rag/sample - Failed: {result.get('message')}")
        return jsonify(result), 400

    logger.info(f"[{g.request_id}] POST /api/rag/sample - Returned {result.get('count')} records ({request_elapsed():.3f}s)")
    return jsonify(result)
