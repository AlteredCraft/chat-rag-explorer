"""
Small shared helpers used across services.

Currently holds API key masking, which is needed by the chat service,
the RAG config service, and startup logging.
"""


def mask_api_key(api_key):
    """Mask an API key for safe logging and display.

    Args:
        api_key: The API key string to mask

    Returns:
        "sk-abc12...xyz9" style excerpt for keys long enough to excerpt
        safely, "****" for short keys, "[MISSING]" when unset
    """
    if not api_key:
        return "[MISSING]"
    if len(api_key) <= 12:
        return "****"
    return f"{api_key[:8]}...{api_key[-4:]}"
