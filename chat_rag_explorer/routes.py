import logging
from flask import Blueprint, render_template, request, Response, stream_with_context, jsonify
from chat_rag_explorer.services import chat_service

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


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
    logger.debug("Fetching available models")
    try:
        models = chat_service.get_models()
        return jsonify({"data": models})
    except Exception as e:
        logger.error(f"Failed to fetch models: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])
    model = data.get("model")

    logger.info(
        f"Received chat request. Context length: {len(messages)}, Model: {model}"
    )

    if not messages:
        logger.warning("Chat request received without messages")
        return {"error": "Messages are required"}, 400

    return Response(
        stream_with_context(chat_service.chat_stream(messages, model)),
        mimetype="text/plain",
    )
