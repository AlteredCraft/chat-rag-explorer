"""
Unit tests for routes.py.

Tests route-level logic: validation, error handling, response formatting.
Service calls are mocked to isolate HTTP layer behavior.
"""
import pytest
from unittest.mock import patch, MagicMock
from chat_rag_explorer.routes import generate_request_id


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
