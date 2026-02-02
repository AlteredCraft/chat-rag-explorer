"""
Unit tests for rag_config_service.py.

Tests configuration persistence, path validation, and API key status.
ChromaDB client creation is mocked to avoid network calls.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from chat_rag_explorer.rag_config_service import RagConfigService, DEFAULT_RAG_CONFIG


class TestGetConfig:
    """Tests for get_config() method."""

    def test_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        """Returns default config when no file exists."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        config = service.get_config()

        assert config["mode"] == "local"
        assert config["server_host"] == "localhost"
        assert config["server_port"] == 8000

    def test_loads_from_file(self, tmp_path, monkeypatch):
        """Loads configuration from existing file."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        # Write test config
        config_path.write_text(json.dumps({
            "mode": "server",
            "server_host": "chroma.example.com",
            "server_port": 9000,
        }))

        config = service.get_config()

        assert config["mode"] == "server"
        assert config["server_host"] == "chroma.example.com"
        assert config["server_port"] == 9000

    def test_merges_with_defaults(self, tmp_path, monkeypatch):
        """Missing keys are filled from defaults."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        # Write partial config
        config_path.write_text(json.dumps({"mode": "cloud"}))

        config = service.get_config()

        assert config["mode"] == "cloud"
        assert config["server_host"] == "localhost"  # From defaults

    def test_caches_by_mtime(self, tmp_path, monkeypatch):
        """Config is cached based on file mtime."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        config_path.write_text(json.dumps({"mode": "server"}))

        # First load
        config1 = service.get_config()
        assert config1["mode"] == "server"

        # Second load uses cache (same mtime)
        config2 = service.get_config()
        assert config2["mode"] == "server"
        assert service._config is not None


class TestSaveConfig:
    """Tests for save_config() method."""

    def test_save_local_config(self, tmp_path, monkeypatch):
        """Can save local mode configuration."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        result = service.save_config({
            "mode": "local",
            "local_path": "/path/to/chroma"
        })

        assert "error" not in result
        assert config_path.exists()
        saved = json.loads(config_path.read_text())
        assert saved["mode"] == "local"
        assert saved["local_path"] == "/path/to/chroma"

    def test_save_server_config(self, tmp_path, monkeypatch):
        """Can save server mode configuration."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        result = service.save_config({
            "mode": "server",
            "server_host": "chroma.example.com",
            "server_port": 8080
        })

        assert "error" not in result
        saved = json.loads(config_path.read_text())
        assert saved["mode"] == "server"
        assert saved["server_host"] == "chroma.example.com"
        assert saved["server_port"] == 8080

    def test_save_cloud_config(self, tmp_path, monkeypatch):
        """Can save cloud mode configuration."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        result = service.save_config({
            "mode": "cloud",
            "cloud_tenant": "my-tenant",
            "cloud_database": "my-db"
        })

        assert "error" not in result
        saved = json.loads(config_path.read_text())
        assert saved["mode"] == "cloud"
        assert saved["cloud_tenant"] == "my-tenant"
        assert saved["cloud_database"] == "my-db"

    def test_local_requires_path(self, tmp_path, monkeypatch):
        """Local mode requires local_path."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        result = service.save_config({"mode": "local"})

        assert "error" in result
        assert "path" in result["error"].lower()

    def test_server_requires_host(self, tmp_path, monkeypatch):
        """Server mode requires server_host."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        result = service.save_config({
            "mode": "server",
            "server_host": "",
            "server_port": 8000
        })

        assert "error" in result
        assert "host" in result["error"].lower()

    def test_cloud_requires_tenant(self, tmp_path, monkeypatch):
        """Cloud mode requires cloud_tenant."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        result = service.save_config({
            "mode": "cloud",
            "cloud_database": "db"
        })

        assert "error" in result
        assert "tenant" in result["error"].lower()

    def test_save_invalidates_cache(self, tmp_path, monkeypatch):
        """Saving invalidates config cache."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        # Pre-populate cache
        service._config = {"mode": "old"}
        service._config_mtime = 12345

        service.save_config({
            "mode": "local",
            "local_path": "/new/path"
        })

        assert service._config is None
        assert service._config_mtime is None


class TestValidateLocalPath:
    """Tests for validate_local_path() method."""

    def test_empty_path_invalid(self):
        """Empty path is invalid."""
        service = RagConfigService()

        result = service.validate_local_path("")

        assert result["valid"] is False

    def test_nonexistent_path_invalid(self, tmp_path):
        """Nonexistent path is invalid."""
        service = RagConfigService()
        fake_path = tmp_path / "does_not_exist"

        result = service.validate_local_path(str(fake_path))

        assert result["valid"] is False
        assert "not exist" in result["message"].lower()

    def test_file_not_directory_invalid(self, tmp_path):
        """File (not directory) is invalid."""
        service = RagConfigService()
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        result = service.validate_local_path(str(file_path))

        assert result["valid"] is False
        assert "not a directory" in result["message"].lower()

    def test_directory_without_db_invalid(self, tmp_path):
        """Directory without ChromaDB files is invalid."""
        service = RagConfigService()

        result = service.validate_local_path(str(tmp_path))

        assert result["valid"] is False
        assert "no chromadb" in result["message"].lower()

    def test_valid_chromadb_directory(self, tmp_path):
        """Directory with chroma.sqlite3 is valid."""
        service = RagConfigService()
        (tmp_path / "chroma.sqlite3").write_text("fake db")

        result = service.validate_local_path(str(tmp_path))

        assert result["valid"] is True
        assert "valid" in result["message"].lower()


class TestGetApiKeyStatus:
    """Tests for get_api_key_status() method."""

    def test_no_api_key(self, monkeypatch):
        """Returns not configured when no API key."""
        service = RagConfigService()
        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Config.CHROMADB_API_KEY", None)

        result = service.get_api_key_status()

        assert result["configured"] is False
        assert result["masked"] is None

    def test_api_key_configured(self, monkeypatch):
        """Returns masked key when configured."""
        service = RagConfigService()
        monkeypatch.setattr(
            "chat_rag_explorer.rag_config_service.Config.CHROMADB_API_KEY",
            "abcd1234efgh5678"
        )

        result = service.get_api_key_status()

        assert result["configured"] is True
        assert result["masked"] == "abcd...5678"

    def test_short_api_key_masked(self, monkeypatch):
        """Short API keys are fully masked."""
        service = RagConfigService()
        monkeypatch.setattr(
            "chat_rag_explorer.rag_config_service.Config.CHROMADB_API_KEY",
            "short"
        )

        result = service.get_api_key_status()

        assert result["configured"] is True
        assert result["masked"] == "****"


class TestTestConnection:
    """Tests for test_connection() method with mocked ChromaDB."""

    def test_local_missing_path(self):
        """Local mode without path returns error."""
        service = RagConfigService()

        result = service.test_connection({"mode": "local"})

        assert result["success"] is False
        assert "path" in result["message"].lower()

    def test_local_nonexistent_path(self, tmp_path):
        """Local mode with nonexistent path returns error."""
        service = RagConfigService()
        fake_path = tmp_path / "does_not_exist"

        result = service.test_connection({
            "mode": "local",
            "local_path": str(fake_path)
        })

        assert result["success"] is False
        assert "not exist" in result["message"].lower()

    def test_local_no_database(self, tmp_path):
        """Local mode with empty directory returns error."""
        service = RagConfigService()

        result = service.test_connection({
            "mode": "local",
            "local_path": str(tmp_path)
        })

        assert result["success"] is False
        assert "no chromadb" in result["message"].lower()

    @patch("chat_rag_explorer.rag_config_service.chromadb.PersistentClient")
    def test_local_success(self, mock_client_class, tmp_path):
        """Local mode success with mocked client."""
        service = RagConfigService()
        (tmp_path / "chroma.sqlite3").write_text("fake")

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_client.list_collections.return_value = [mock_collection]
        mock_client_class.return_value = mock_client

        result = service.test_connection({
            "mode": "local",
            "local_path": str(tmp_path)
        })

        assert result["success"] is True
        assert "test_collection" in result["collections"]

    @patch("chat_rag_explorer.rag_config_service.chromadb.HttpClient")
    def test_server_success(self, mock_client_class):
        """Server mode success with mocked client."""
        service = RagConfigService()

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = "server_collection"
        mock_client.list_collections.return_value = [mock_collection]
        mock_client_class.return_value = mock_client

        result = service.test_connection({
            "mode": "server",
            "server_host": "localhost",
            "server_port": 8000
        })

        assert result["success"] is True
        assert "server_collection" in result["collections"]

    def test_cloud_missing_tenant(self):
        """Cloud mode without tenant returns error."""
        service = RagConfigService()

        result = service.test_connection({
            "mode": "cloud",
            "cloud_database": "db"
        })

        assert result["success"] is False
        assert "tenant" in result["message"].lower()

    def test_unknown_mode(self):
        """Unknown mode returns error."""
        service = RagConfigService()

        result = service.test_connection({"mode": "invalid"})

        assert result["success"] is False
        assert "unknown" in result["message"].lower()


class TestDiscoverDatabases:
    """Tests for discover_databases() method."""

    def test_no_data_directory(self, tmp_path, monkeypatch):
        """Returns empty list when data directory doesn't exist."""
        service = RagConfigService()
        # Make data directory not exist
        fake_project = tmp_path / "fake_project"
        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Path",
                          lambda x: fake_project / Path(x).name)

        result = service.discover_databases()

        assert result["success"] is True
        assert result["databases"] == []
        assert result["search_path"] == "./data/"

    def test_empty_data_directory(self, tmp_path, monkeypatch):
        """Returns empty list when data directory is empty."""
        service = RagConfigService()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Mock the path resolution to use our temp directory
        def mock_path(path_str):
            p = Path(path_str)
            if p.name == "rag_config_service.py":
                return tmp_path / "chat_rag_explorer" / "rag_config_service.py"
            return p

        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Path", mock_path)

        result = service.discover_databases()

        assert result["success"] is True
        assert result["databases"] == []

    def test_discovers_single_database(self, tmp_path, monkeypatch):
        """Discovers a single ChromaDB database."""
        service = RagConfigService()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create a fake ChromaDB database
        db_dir = data_dir / "test_db"
        db_dir.mkdir()
        (db_dir / "chroma.sqlite3").write_text("fake db content")

        # Mock path resolution
        def mock_path(path_str):
            p = Path(path_str)
            if p.name == "rag_config_service.py":
                return tmp_path / "chat_rag_explorer" / "rag_config_service.py"
            return p

        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Path", mock_path)

        result = service.discover_databases()

        assert result["success"] is True
        assert len(result["databases"]) == 1
        db = result["databases"][0]
        assert db["name"] == "test_db"
        assert "test_db" in db["path"]
        assert db["relative_path"] == "./data/test_db"
        assert db["size_bytes"] > 0

    def test_discovers_multiple_databases(self, tmp_path, monkeypatch):
        """Discovers multiple ChromaDB databases."""
        service = RagConfigService()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create multiple fake ChromaDB databases
        for name in ["db1", "db2", "db3"]:
            db_dir = data_dir / name
            db_dir.mkdir()
            (db_dir / "chroma.sqlite3").write_text(f"fake {name}")

        # Create a non-database directory (should be ignored)
        (data_dir / "not_a_db").mkdir()

        # Mock path resolution
        def mock_path(path_str):
            p = Path(path_str)
            if p.name == "rag_config_service.py":
                return tmp_path / "chat_rag_explorer" / "rag_config_service.py"
            return p

        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Path", mock_path)

        result = service.discover_databases()

        assert result["success"] is True
        assert len(result["databases"]) == 3
        names = [db["name"] for db in result["databases"]]
        assert "db1" in names
        assert "db2" in names
        assert "db3" in names
        assert "not_a_db" not in names

    def test_ignores_files_in_data_dir(self, tmp_path, monkeypatch):
        """Ignores files (non-directories) in data directory."""
        service = RagConfigService()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create a file (should be ignored)
        (data_dir / "readme.txt").write_text("not a directory")

        # Create a valid database
        db_dir = data_dir / "valid_db"
        db_dir.mkdir()
        (db_dir / "chroma.sqlite3").write_text("fake db")

        # Mock path resolution
        def mock_path(path_str):
            p = Path(path_str)
            if p.name == "rag_config_service.py":
                return tmp_path / "chat_rag_explorer" / "rag_config_service.py"
            return p

        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Path", mock_path)

        result = service.discover_databases()

        assert result["success"] is True
        assert len(result["databases"]) == 1
        assert result["databases"][0]["name"] == "valid_db"

    def test_excludes_chroma_db_sample(self, tmp_path, monkeypatch):
        """Excludes chroma_db_sample directory (pristine source, not for user access)."""
        service = RagConfigService()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create the sample directory (should be excluded)
        sample_dir = data_dir / "chroma_db_sample"
        sample_dir.mkdir()
        (sample_dir / "chroma.sqlite3").write_text("pristine sample")

        # Create the working copy (should be included)
        working_dir = data_dir / "chroma_db"
        working_dir.mkdir()
        (working_dir / "chroma.sqlite3").write_text("working copy")

        # Mock path resolution
        def mock_path(path_str):
            p = Path(path_str)
            if p.name == "rag_config_service.py":
                return tmp_path / "chat_rag_explorer" / "rag_config_service.py"
            return p

        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Path", mock_path)

        result = service.discover_databases()

        assert result["success"] is True
        assert len(result["databases"]) == 1
        assert result["databases"][0]["name"] == "chroma_db"
        # Verify sample is not in results
        names = [db["name"] for db in result["databases"]]
        assert "chroma_db_sample" not in names

    @patch("chat_rag_explorer.rag_config_service.chromadb.PersistentClient")
    def test_includes_collection_count(self, mock_client_class, tmp_path, monkeypatch):
        """Includes collection count when accessible."""
        service = RagConfigService()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        db_dir = data_dir / "test_db"
        db_dir.mkdir()
        (db_dir / "chroma.sqlite3").write_text("fake db")

        # Mock ChromaDB client
        mock_client = MagicMock()
        mock_collection1 = MagicMock()
        mock_collection1.name = "collection1"
        mock_collection2 = MagicMock()
        mock_collection2.name = "collection2"
        mock_client.list_collections.return_value = [mock_collection1, mock_collection2]
        mock_client_class.return_value = mock_client

        # Mock path resolution
        def mock_path(path_str):
            p = Path(path_str)
            if p.name == "rag_config_service.py":
                return tmp_path / "chat_rag_explorer" / "rag_config_service.py"
            return p

        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Path", mock_path)

        result = service.discover_databases()

        assert result["success"] is True
        assert len(result["databases"]) == 1
        assert result["databases"][0]["collection_count"] == 2

    def test_marks_current_database(self, tmp_path, monkeypatch):
        """Marks the currently configured database."""
        service = RagConfigService()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create databases
        current_db = data_dir / "current_db"
        current_db.mkdir()
        (current_db / "chroma.sqlite3").write_text("current")

        other_db = data_dir / "other_db"
        other_db.mkdir()
        (other_db / "chroma.sqlite3").write_text("other")

        # Mock path resolution
        def mock_path(path_str):
            p = Path(path_str)
            if p.name == "rag_config_service.py":
                return tmp_path / "chat_rag_explorer" / "rag_config_service.py"
            return p

        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Path", mock_path)

        # Mock get_config to return current_db as configured
        monkeypatch.setattr(service, "get_config",
                          lambda request_id=None: {"local_path": str(current_db)})

        result = service.discover_databases()

        assert result["success"] is True
        current_marked = [db for db in result["databases"] if db["is_current"]]
        assert len(current_marked) == 1
        assert current_marked[0]["name"] == "current_db"

    def test_handles_discovery_error(self, tmp_path, monkeypatch):
        """Handles errors during discovery gracefully."""
        service = RagConfigService()

        # Mock to raise an exception
        def mock_path(path_str):
            raise PermissionError("Access denied")

        monkeypatch.setattr("chat_rag_explorer.rag_config_service.Path", mock_path)

        result = service.discover_databases()

        assert result["success"] is False
        assert "error" in result
        assert result["databases"] == []


class TestQueryCollection:
    """Tests for query_collection() method."""

    def test_no_collection_configured(self, tmp_path, monkeypatch):
        """Returns error when no collection is configured."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        config_path.write_text(json.dumps({
            "mode": "local",
            "local_path": str(tmp_path),
            "collection": ""
        }))
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        result = service.query_collection("test query")

        assert result["success"] is False
        assert "no collection" in result["message"].lower()
        assert result["documents"] == []

    @patch("chat_rag_explorer.rag_config_service.chromadb.PersistentClient")
    def test_successful_query(self, mock_client_class, tmp_path, monkeypatch):
        """Returns documents on successful query."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        (tmp_path / "chroma.sqlite3").write_text("fake")
        config_path.write_text(json.dumps({
            "mode": "local",
            "local_path": str(tmp_path),
            "collection": "test_collection",
            "n_results": 5
        }))
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc content 1", "doc content 2"]],
            "metadatas": [[{"source": "a"}, {"source": "b"}]],
            "distances": [[0.5, 0.8]]
        }
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        result = service.query_collection("test query", n_results=2)

        assert result["success"] is True
        assert len(result["documents"]) == 2
        assert result["documents"][0] == "doc content 1"
        assert result["distances"][0] == 0.5
        assert result["collection"] == "test_collection"

    @patch("chat_rag_explorer.rag_config_service.chromadb.PersistentClient")
    def test_distance_threshold_filtering(self, mock_client_class, tmp_path, monkeypatch):
        """Documents above threshold are filtered out."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        (tmp_path / "chroma.sqlite3").write_text("fake")
        config_path.write_text(json.dumps({
            "mode": "local",
            "local_path": str(tmp_path),
            "collection": "test_collection"
        }))
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1", "id2", "id3"]],
            "documents": [["close doc", "medium doc", "far doc"]],
            "metadatas": [[{}, {}, {}]],
            "distances": [[0.3, 0.7, 1.5]]
        }
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        result = service.query_collection("test query", distance_threshold=1.0)

        assert result["success"] is True
        # Only docs with distance <= 1.0 should be included
        assert len(result["documents"]) == 2
        assert "far doc" not in result["documents"]

    @patch("chat_rag_explorer.rag_config_service.chromadb.PersistentClient")
    def test_query_failure_returns_error(self, mock_client_class, tmp_path, monkeypatch):
        """Query failure returns error with empty lists."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        (tmp_path / "chroma.sqlite3").write_text("fake")
        config_path.write_text(json.dumps({
            "mode": "local",
            "local_path": str(tmp_path),
            "collection": "test_collection"
        }))
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        mock_client_class.side_effect = Exception("Connection failed")

        result = service.query_collection("test query")

        assert result["success"] is False
        assert "connection failed" in result["message"].lower()
        assert result["documents"] == []

    @patch("chat_rag_explorer.rag_config_service.chromadb.PersistentClient")
    def test_uses_config_defaults(self, mock_client_class, tmp_path, monkeypatch):
        """Uses n_results and distance_threshold from config when not provided."""
        service = RagConfigService()
        config_path = tmp_path / "rag_config.json"
        (tmp_path / "chroma.sqlite3").write_text("fake")
        config_path.write_text(json.dumps({
            "mode": "local",
            "local_path": str(tmp_path),
            "collection": "test_collection",
            "n_results": 3,
            "distance_threshold": 0.5
        }))
        monkeypatch.setattr(service, "_get_config_path", lambda: config_path)

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{}, {}]],
            "distances": [[0.2, 0.8]]  # Only first should pass 0.5 threshold
        }
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        result = service.query_collection("test query")

        # Should use n_results=3 from config
        mock_collection.query.assert_called_once()
        call_kwargs = mock_collection.query.call_args[1]
        assert call_kwargs["n_results"] == 3

        # Should filter by distance_threshold=0.5 from config
        assert len(result["documents"]) == 1
        assert result["documents"][0] == "doc1"
