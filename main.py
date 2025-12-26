import logging

from chat_rag_explorer import create_app

logger = logging.getLogger("chat_rag_explorer")

app = create_app()

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5005

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  🚀 Server running at: http://{host}:{port}")
    logger.info("=" * 60)
    logger.info("")

    app.run(debug=True, host=host, port=port)
