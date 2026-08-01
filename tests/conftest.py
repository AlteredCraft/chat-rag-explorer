"""
Pytest configuration and shared fixtures.

Provides:
- Flask app and test client fixtures
- Temporary directory fixtures for file-based tests
- Mock configuration for testing without real API keys
"""
import os
import pytest

# Set test environment before importing app. LLM_PROVIDER is required
# and has no default, so the fixture models a correctly configured app;
# tests that need the unset state override it on app.config directly.
os.environ["LLM_API_KEY"] = "test-api-key-for-testing"
os.environ.setdefault("LLM_PROVIDER", "openrouter")


@pytest.fixture
def app():
    """Create Flask application for testing.

    create_app() reads the real Config, which loads the developer's .env,
    so every setting a test asserts a default for is pinned here. Without
    that, a perfectly reasonable .env (CHAT_HISTORY_ENABLED=true, say)
    fails tests on one machine and passes on another - and passes in CI
    only because CI has no .env at all. Tests that need a different value
    override app.config themselves.
    """
    from chat_rag_explorer import create_app

    app = create_app()
    app.config.update({
        "TESTING": True,
        "LLM_API_KEY": "test-api-key-for-testing",
        "LLM_PROVIDER": "openrouter",
        "CHAT_HISTORY_ENABLED": False,
    })
    yield app


@pytest.fixture
def client(app):
    """Flask test client for making requests."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Flask application context for testing services."""
    with app.app_context():
        yield app
