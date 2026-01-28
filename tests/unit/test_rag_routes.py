"""
Unit tests for RAG-related routes.

Tests the RAG configuration, database discovery, and connection endpoints.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


class TestRagConfigRoute:
    """Tests for /api/rag/config endpoint."""

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_get_config_success(self, mock_service, client):
        """GET /api/rag/config returns configuration."""
        mock_service.get_config.return_value = {
            "mode": "local",
            "local_path": "/path/to/db",
            "collection": "test_collection"
        }

        response = client.get("/api/rag/config")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["data"]["mode"] == "local"
        assert data["data"]["local_path"] == "/path/to/db"

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_get_config_error(self, mock_service, client):
        """GET /api/rag/config handles errors."""
        mock_service.get_config.side_effect = Exception("Config error")

        response = client.get("/api/rag/config")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_save_config_success(self, mock_service, client):
        """POST /api/rag/config saves configuration."""
        mock_service.save_config.return_value = {
            "success": True,
            "config": {"mode": "local", "local_path": "/new/path"}
        }

        response = client.post(
            "/api/rag/config",
            json={"mode": "local", "local_path": "/new/path"}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_save_config_validation_error(self, mock_service, client):
        """POST /api/rag/config returns 400 on validation error."""
        mock_service.save_config.return_value = {
            "error": "Local path is required"
        }

        response = client.post(
            "/api/rag/config",
            json={"mode": "local"}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


class TestDiscoverDatabasesRoute:
    """Tests for /api/rag/discover-databases endpoint."""

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_discover_databases_success(self, mock_service, client):
        """GET /api/rag/discover-databases returns discovered databases."""
        mock_service.discover_databases.return_value = {
            "success": True,
            "databases": [
                {
                    "name": "test_db",
                    "path": "/data/test_db",
                    "relative_path": "./data/test_db",
                    "size_mb": 1.5,
                    "collection_count": 2,
                    "is_current": True
                }
            ],
            "search_path": "./data/",
            "current_path": "/data/test_db"
        }

        response = client.get("/api/rag/discover-databases")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["databases"]) == 1
        assert data["databases"][0]["name"] == "test_db"
        assert data["databases"][0]["collection_count"] == 2
        assert data["databases"][0]["is_current"] is True
        assert data["search_path"] == "./data/"

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_discover_databases_empty(self, mock_service, client):
        """GET /api/rag/discover-databases handles no databases found."""
        mock_service.discover_databases.return_value = {
            "success": True,
            "databases": [],
            "search_path": "./data/",
            "current_path": ""
        }

        response = client.get("/api/rag/discover-databases")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["databases"] == []

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_discover_databases_error(self, mock_service, client):
        """GET /api/rag/discover-databases handles errors."""
        mock_service.discover_databases.side_effect = Exception("Discovery failed")

        response = client.get("/api/rag/discover-databases")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        assert "error" in data


class TestValidatePathRoute:
    """Tests for /api/rag/validate-path endpoint."""

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_validate_path_valid(self, mock_service, client):
        """POST /api/rag/validate-path validates valid path."""
        mock_service.validate_local_path.return_value = {
            "valid": True,
            "message": "Valid ChromaDB database"
        }

        response = client.post(
            "/api/rag/validate-path",
            json={"path": "/valid/path"}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["valid"] is True

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_validate_path_invalid(self, mock_service, client):
        """POST /api/rag/validate-path handles invalid path."""
        mock_service.validate_local_path.return_value = {
            "valid": False,
            "message": "Path does not exist"
        }

        response = client.post(
            "/api/rag/validate-path",
            json={"path": "/invalid/path"}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["valid"] is False


class TestTestConnectionRoute:
    """Tests for /api/rag/test-connection endpoint."""

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_test_connection_success(self, mock_service, client):
        """POST /api/rag/test-connection tests connection successfully."""
        mock_service.test_connection.return_value = {
            "success": True,
            "message": "Connected to local ChromaDB",
            "collections": ["collection1", "collection2"]
        }

        response = client.post(
            "/api/rag/test-connection",
            json={"mode": "local", "local_path": "/test/path"}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "collections" in data
        assert len(data["collections"]) == 2

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_test_connection_failure(self, mock_service, client):
        """POST /api/rag/test-connection handles connection failure."""
        mock_service.test_connection.return_value = {
            "success": False,
            "message": "Connection failed"
        }

        response = client.post(
            "/api/rag/test-connection",
            json={"mode": "local", "local_path": "/bad/path"}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is False
        assert "message" in data


class TestApiKeyStatusRoute:
    """Tests for /api/rag/api-key-status endpoint."""

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_api_key_configured(self, mock_service, client):
        """GET /api/rag/api-key-status returns configured status."""
        mock_service.get_api_key_status.return_value = {
            "configured": True,
            "masked": "abcd...efgh"
        }

        response = client.get("/api/rag/api-key-status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["configured"] is True
        assert data["masked"] == "abcd...efgh"

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_api_key_not_configured(self, mock_service, client):
        """GET /api/rag/api-key-status returns not configured."""
        mock_service.get_api_key_status.return_value = {
            "configured": False,
            "masked": None
        }

        response = client.get("/api/rag/api-key-status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["configured"] is False


class TestSampleRoute:
    """Tests for /api/rag/sample endpoint."""

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_get_sample_success(self, mock_service, client):
        """POST /api/rag/sample returns sample records."""
        mock_service.get_sample_records.return_value = {
            "success": True,
            "collection": "test_collection",
            "count": 2,
            "records": [
                {"id": "1", "document": "Sample 1"},
                {"id": "2", "document": "Sample 2"}
            ]
        }

        response = client.post(
            "/api/rag/sample",
            json={"collection": "test_collection"}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["records"]) == 2

    @patch("chat_rag_explorer.routes.rag_config_service")
    def test_get_sample_failure(self, mock_service, client):
        """POST /api/rag/sample handles failure."""
        mock_service.get_sample_records.return_value = {
            "success": False,
            "message": "Collection not found"
        }

        response = client.post(
            "/api/rag/sample",
            json={"collection": "missing"}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False