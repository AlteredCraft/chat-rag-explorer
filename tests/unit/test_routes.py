"""
Unit tests for routes.py.

Tests route-level logic: validation, error handling, response formatting.
Service calls are mocked to isolate HTTP layer behavior.
"""
import pytest
from unittest.mock import patch, MagicMock
from chat_rag_explorer.routes import generate_request_id, build_augmented_message


class TestGenerateRequestId:
    """Tests for generate_request_id function."""

    def test_returns_8_chars(self):
        """Request ID is 8 characters."""
        request_id = generate_request_id()
        assert len(request_id) == 8

    def test_returns_string(self):
        """Request ID is a string."""
        request_id = generate_request_id()
        assert isinstance(request_id, str)

    def test_unique_ids(self):
        """Multiple calls return unique IDs."""
        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100


class TestBuildAugmentedMessage:
    """Tests for build_augmented_message function."""

    def test_returns_original_if_no_documents(self):
        """Returns original message when documents list is empty."""
        result = build_augmented_message("What is X?", [])
        assert result == "What is X?"

    def test_returns_original_if_documents_none(self):
        """Returns original message when documents is None."""
        result = build_augmented_message("What is X?", None)
        assert result == "What is X?"

    def test_augments_with_single_document(self):
        """Properly formats message with single document in XML format."""
        result = build_augmented_message("What is X?", ["Document content here"])

        assert "<knowledge_base_context>" in result
        assert '<document index="1">Document content here</document>' in result
        assert "</knowledge_base_context>" in result
        assert "<original_user_message>" in result
        assert "What is X?" in result
        assert "</original_user_message>" in result

    def test_augments_with_multiple_documents(self):
        """Properly formats message with multiple documents in XML format."""
        docs = ["First doc", "Second doc", "Third doc"]
        result = build_augmented_message("Question?", docs)

        assert '<document index="1">First doc</document>' in result
        assert '<document index="2">Second doc</document>' in result
        assert '<document index="3">Third doc</document>' in result
        assert "<original_user_message>" in result
        assert "Question?" in result


class TestPageRoutes:
    """Tests for page-rendering routes."""

    def test_index_returns_html(self, client):
        """GET / returns 200 with HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data

    def test_settings_returns_html(self, client):
        """GET /settings returns 200 with HTML."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


class TestGetPrompts:
    """Tests for GET /api/prompts."""

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_returns_prompts_list(self, mock_service, client):
        """Returns list of prompts."""
        mock_service.get_prompts.return_value = [
            {"id": "test", "title": "Test Prompt"}
        ]

        response = client.get("/api/prompts")

        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert len(data["data"]) == 1

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_handles_service_error(self, mock_service, client):
        """Returns 500 on service error."""
        mock_service.get_prompts.side_effect = Exception("Service error")

        response = client.get("/api/prompts")

        assert response.status_code == 500
        assert "error" in response.get_json()


class TestGetPromptById:
    """Tests for GET /api/prompts/<id>."""

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_returns_prompt(self, mock_service, client):
        """Returns prompt data when found."""
        mock_service.get_prompt_by_id.return_value = {
            "id": "test",
            "title": "Test",
            "content": "Hello"
        }

        response = client.get("/api/prompts/test")

        assert response.status_code == 200
        assert response.get_json()["data"]["id"] == "test"

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_not_found(self, mock_service, client):
        """Returns 404 when prompt doesn't exist."""
        mock_service.get_prompt_by_id.return_value = None

        response = client.get("/api/prompts/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.get_json()["error"].lower()


class TestCreatePrompt:
    """Tests for POST /api/prompts."""

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_missing_id_returns_400(self, mock_service, client):
        """Returns 400 when prompt ID is missing."""
        response = client.post(
            "/api/prompts",
            json={"title": "Test", "content": "Hello"}
        )

        assert response.status_code == 400
        assert "id" in response.get_json()["error"].lower()

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_missing_title_returns_400(self, mock_service, client):
        """Returns 400 when title is missing."""
        response = client.post(
            "/api/prompts",
            json={"id": "test", "content": "Hello"}
        )

        assert response.status_code == 400
        assert "title" in response.get_json()["error"].lower()

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_protected_id_returns_403(self, mock_service, client):
        """Returns 403 when using protected ID."""
        mock_service.is_protected.return_value = True

        response = client.post(
            "/api/prompts",
            json={"id": "default", "title": "Test"}
        )

        assert response.status_code == 403

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_duplicate_id_returns_409(self, mock_service, client):
        """Returns 409 when ID already exists."""
        mock_service.is_protected.return_value = False
        mock_service.get_prompt_by_id.return_value = {"id": "existing"}

        response = client.post(
            "/api/prompts",
            json={"id": "existing", "title": "Test"}
        )

        assert response.status_code == 409
        assert "already exists" in response.get_json()["error"].lower()

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_success_returns_201(self, mock_service, client):
        """Returns 201 on successful creation."""
        mock_service.is_protected.return_value = False
        mock_service.get_prompt_by_id.return_value = None
        mock_service.save_prompt.return_value = {
            "id": "new",
            "title": "New Prompt"
        }

        response = client.post(
            "/api/prompts",
            json={"id": "new", "title": "New Prompt", "content": "Hello"}
        )

        assert response.status_code == 201
        assert response.get_json()["data"]["id"] == "new"


class TestUpdatePrompt:
    """Tests for PUT /api/prompts/<id>."""

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_missing_title_returns_400(self, mock_service, client):
        """Returns 400 when title is missing."""
        response = client.put(
            "/api/prompts/test",
            json={"content": "Updated"}
        )

        assert response.status_code == 400
        assert "title" in response.get_json()["error"].lower()

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_protected_returns_403(self, mock_service, client):
        """Returns 403 when editing protected prompt."""
        mock_service.is_protected.return_value = True

        response = client.put(
            "/api/prompts/default",
            json={"title": "New Title"}
        )

        assert response.status_code == 403

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_not_found_returns_404(self, mock_service, client):
        """Returns 404 when prompt doesn't exist."""
        mock_service.is_protected.return_value = False
        mock_service.get_prompt_by_id.return_value = None

        response = client.put(
            "/api/prompts/nonexistent",
            json={"title": "New Title"}
        )

        assert response.status_code == 404

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_success_returns_200(self, mock_service, client):
        """Returns 200 on successful update."""
        mock_service.is_protected.return_value = False
        mock_service.get_prompt_by_id.return_value = {"id": "test"}
        mock_service.save_prompt.return_value = {
            "id": "test",
            "title": "Updated"
        }

        response = client.put(
            "/api/prompts/test",
            json={"title": "Updated", "content": "New content"}
        )

        assert response.status_code == 200
        assert response.get_json()["data"]["title"] == "Updated"


class TestDeletePrompt:
    """Tests for DELETE /api/prompts/<id>."""

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_protected_returns_403(self, mock_service, client):
        """Returns 403 when deleting protected prompt."""
        mock_service.is_protected.return_value = True

        response = client.delete("/api/prompts/default")

        assert response.status_code == 403

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_not_found_returns_404(self, mock_service, client):
        """Returns 404 when prompt doesn't exist."""
        mock_service.is_protected.return_value = False
        mock_service.get_prompt_by_id.return_value = None

        response = client.delete("/api/prompts/nonexistent")

        assert response.status_code == 404

    @patch("chat_rag_explorer.routes.prompt_service")
    def test_success_returns_200(self, mock_service, client):
        """Returns 200 on successful deletion."""
        mock_service.is_protected.return_value = False
        mock_service.get_prompt_by_id.return_value = {"id": "test"}
        mock_service.delete_prompt.return_value = True

        response = client.delete("/api/prompts/test")

        assert response.status_code == 200
        assert response.get_json()["success"] is True


class TestChatWithRag:
    """Tests for /api/chat with RAG integration."""

    @patch("chat_rag_explorer.routes.chat_history_service")
    @patch("chat_rag_explorer.routes.chat_service")
    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_rag_enabled_augments_message(self, mock_rag, mock_chat, mock_history, client):
        """RAG enabled augments the user message with context."""
        mock_rag.query_collection.return_value = {
            "success": True,
            "documents": ["Context document 1", "Context document 2"],
            "distances": [0.5, 0.8],
            "ids": ["doc1", "doc2"],
            "collection": "test_collection"
        }

        def mock_stream(messages, *args, **kwargs):
            # Verify the last message contains augmented content in XML format
            last_msg = messages[-1]
            assert "<knowledge_base_context>" in last_msg["content"]
            assert "Context document 1" in last_msg["content"]
            assert "<original_user_message>" in last_msg["content"]
            yield "Response"
            yield "__METADATA__:{}"

        mock_chat.chat_stream.side_effect = mock_stream

        response = client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "What is X?"}],
            "model": "test-model",
            "rag_enabled": True
        })

        assert response.status_code == 200
        mock_rag.query_collection.assert_called_once()

    @patch("chat_rag_explorer.routes.chat_history_service")
    @patch("chat_rag_explorer.routes.chat_service")
    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_rag_disabled_passes_original(self, mock_rag, mock_chat, mock_history, client):
        """RAG disabled passes messages unchanged."""
        def mock_stream(messages, *args, **kwargs):
            # Verify the message is unchanged (no RAG context)
            last_msg = messages[-1]
            assert last_msg["content"] == "What is X?"
            yield "Response"
            yield "__METADATA__:{}"

        mock_chat.chat_stream.side_effect = mock_stream

        response = client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "What is X?"}],
            "model": "test-model",
            "rag_enabled": False
        })

        assert response.status_code == 200
        mock_rag.query_collection.assert_not_called()

    @patch("chat_rag_explorer.routes.chat_history_service")
    @patch("chat_rag_explorer.routes.chat_service")
    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_rag_failure_continues_without_context(self, mock_rag, mock_chat, mock_history, client):
        """RAG query failure still allows chat to proceed without context."""
        mock_rag.query_collection.return_value = {
            "success": False,
            "message": "No collection configured",
            "documents": []
        }

        def mock_stream(messages, *args, **kwargs):
            # Verify the message is unchanged (no RAG context)
            last_msg = messages[-1]
            assert last_msg["content"] == "What is X?"
            yield "Response"
            yield "__METADATA__:{}"

        mock_chat.chat_stream.side_effect = mock_stream

        response = client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "What is X?"}],
            "model": "test-model",
            "rag_enabled": True
        })

        assert response.status_code == 200
        # Chat should still work, just without context

    @patch("chat_rag_explorer.routes.chat_history_service")
    @patch("chat_rag_explorer.routes.chat_service")
    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_rag_metadata_included_in_response(self, mock_rag, mock_chat, mock_history, client):
        """RAG metadata is included in the response when context is retrieved."""
        mock_rag.query_collection.return_value = {
            "success": True,
            "documents": ["Doc 1"],
            "distances": [0.5],
            "ids": ["id1"],
            "collection": "my_collection"
        }

        collected_data = []

        def mock_stream(messages, *args, **kwargs):
            yield "Response"
            # The route builds entry_data with RAG metadata
            yield "__METADATA__:{}"

        mock_chat.chat_stream.side_effect = mock_stream

        response = client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Test?"}],
            "model": "test-model",
            "rag_enabled": True
        })

        assert response.status_code == 200
