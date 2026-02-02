"""
RAG (Retrieval-Augmented Generation) configuration service.

Manages ChromaDB vector database connections in three modes:
- Local: PersistentClient pointing to a local directory
- Server: HttpClient connecting to a ChromaDB server
- Cloud: CloudClient for managed Chroma cloud instances

Features:
- Configuration persistence to rag_config.json
- Connection testing and validation
- Collection listing and sample record fetching
"""
import os
import json
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings

from config import Config

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_RAG_CONFIG = {
    'mode': 'local',           # 'local', 'server', or 'cloud'
    'local_path': '',          # Path for PersistentClient
    'server_host': 'localhost',
    'server_port': 8000,
    'cloud_tenant': '',        # Tenant ID for CloudClient
    'cloud_database': '',      # Database name for CloudClient
    'collection': '',          # Selected collection name
    'n_results': 5,            # Number of documents to retrieve per query
    'distance_threshold': None,  # Max distance filter (None = no filtering)
}


class RagConfigService:
    """Service for managing RAG/ChromaDB configuration."""

    def __init__(self):
        self._config = None
        self._config_mtime = None

    def _get_config_path(self):
        """Get path to rag_config.json in project root."""
        return Path(__file__).parent.parent / "rag_config.json"

    def get_config(self, request_id=None):
        """Load RAG configuration from file, with caching."""
        log_prefix = f"[{request_id}] " if request_id else ""
        config_path = self._get_config_path()

        # Return default if file doesn't exist
        if not config_path.exists():
            logger.debug(f"{log_prefix}No config file, using defaults")
            return DEFAULT_RAG_CONFIG.copy()

        try:
            mtime = config_path.stat().st_mtime

            # Return cached config if file unchanged
            if self._config is not None and self._config_mtime == mtime:
                return self._config.copy()

            # Load from file
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
                self._config_mtime = mtime

            # Merge with defaults to ensure all keys exist
            merged = DEFAULT_RAG_CONFIG.copy()
            merged.update(self._config)
            self._config = merged

            logger.debug(f"{log_prefix}Loaded RAG config from {config_path}")
            return self._config.copy()

        except Exception as e:
            logger.error(f"{log_prefix}Failed to load RAG config: {e}")
            return DEFAULT_RAG_CONFIG.copy()

    def save_config(self, config_data, request_id=None):
        """Save RAG configuration to file."""
        log_prefix = f"[{request_id}] " if request_id else ""
        config_path = self._get_config_path()

        # Validate required fields based on mode
        mode = config_data.get('mode', 'local')
        if mode == 'local' and not config_data.get('local_path'):
            return {'error': 'Local path is required for local mode'}
        if mode == 'server':
            if not config_data.get('server_host'):
                return {'error': 'Host is required for server mode'}
            if not config_data.get('server_port'):
                return {'error': 'Port is required for server mode'}
        if mode == 'cloud':
            if not config_data.get('cloud_tenant'):
                return {'error': 'Tenant ID is required for cloud mode'}
            if not config_data.get('cloud_database'):
                return {'error': 'Database name is required for cloud mode'}

        # Build config object
        # Handle distance_threshold - convert to None if 0 or empty
        distance_threshold = config_data.get('distance_threshold')
        if distance_threshold is not None:
            distance_threshold = float(distance_threshold) if distance_threshold else None
            if distance_threshold == 0:
                distance_threshold = None

        config = {
            'mode': mode,
            'local_path': config_data.get('local_path', ''),
            'server_host': config_data.get('server_host', 'localhost'),
            'server_port': int(config_data.get('server_port', 8000)),
            'cloud_tenant': config_data.get('cloud_tenant', ''),
            'cloud_database': config_data.get('cloud_database', ''),
            'collection': config_data.get('collection', ''),
            'n_results': int(config_data.get('n_results', 5)),
            'distance_threshold': distance_threshold,
        }

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            # Invalidate cache
            self._config = None
            self._config_mtime = None

            logger.info(f"{log_prefix}Saved RAG config to {config_path}")
            return {'success': True, 'config': config}

        except Exception as e:
            logger.error(f"{log_prefix}Failed to save RAG config: {e}")
            return {'error': f'Failed to save config: {str(e)}'}

    def validate_local_path(self, path, request_id=None):
        """Validate that a local path contains an existing ChromaDB database."""
        log_prefix = f"[{request_id}] " if request_id else ""

        if not path:
            return {'valid': False, 'message': 'Path is required'}

        path_obj = Path(path)

        # Check if path exists
        if not path_obj.exists():
            return {
                'valid': False,
                'message': 'Path does not exist',
                'details': {'exists': False}
            }

        # Check if it's a directory
        if not path_obj.is_dir():
            return {
                'valid': False,
                'message': 'Path is not a directory',
                'details': {'exists': True, 'is_directory': False}
            }

        # Check for ChromaDB database files
        chroma_db_file = path_obj / 'chroma.sqlite3'
        if not chroma_db_file.exists():
            return {
                'valid': False,
                'message': 'No ChromaDB database found at this path',
                'details': {'exists': True, 'is_directory': True, 'has_database': False}
            }

        logger.debug(f"{log_prefix}Path validated: {path}")
        return {
            'valid': True,
            'message': 'Valid ChromaDB database',
            'details': {'exists': True, 'is_directory': True, 'has_database': True}
        }

    def discover_databases(self, request_id=None):
        """
        Discover ChromaDB databases in the ./data/ directory.

        Searches for subdirectories containing chroma.sqlite3 files and returns
        metadata about each discovered database.

        Returns:
            dict with:
                - success: bool indicating if discovery succeeded
                - databases: list of discovered databases with metadata
                - search_path: where we searched
                - current_path: currently configured database path (if any)
        """
        log_prefix = f"[{request_id}] " if request_id else ""

        databases = []

        try:
            current_config = self.get_config(request_id)
            current_path = current_config.get('local_path', '')

            # Get the data directory (relative to project root)
            project_root = Path(__file__).parent.parent
            data_dir = project_root / "data"
            if not data_dir.exists():
                logger.info(f"{log_prefix}Data directory does not exist: {data_dir}")
                return {
                    'success': True,
                    'databases': [],
                    'search_path': './data/',
                    'current_path': current_path
                }

            # Search for chroma.sqlite3 files in subdirectories
            # Skip chroma_db_sample - it's the pristine source copied to chroma_db on startup
            for subdir in data_dir.iterdir():
                if not subdir.is_dir():
                    continue
                if subdir.name == 'chroma_db_sample':
                    continue

                chroma_db_file = subdir / 'chroma.sqlite3'
                if chroma_db_file.exists():
                    try:
                        # Get database metadata
                        stat = chroma_db_file.stat()

                        # Try to get collection count (non-blocking)
                        collection_count = None
                        try:
                            client = chromadb.PersistentClient(path=str(subdir))
                            collections = client.list_collections()
                            collection_count = len(collections)
                        except Exception as e:
                            logger.debug(f"{log_prefix}Could not read collections from {subdir}: {e}")

                        database_info = {
                            'name': subdir.name,
                            'path': str(subdir),
                            'relative_path': f"./data/{subdir.name}",
                            'size_bytes': stat.st_size,
                            'size_mb': round(stat.st_size / (1024 * 1024), 2),
                            'last_modified': stat.st_mtime,
                            'collection_count': collection_count,
                            'is_current': str(subdir) == current_path or str(subdir.absolute()) == current_path
                        }
                        databases.append(database_info)
                        logger.debug(f"{log_prefix}Found database: {subdir.name}")

                    except Exception as e:
                        logger.warning(f"{log_prefix}Error reading database info from {subdir}: {e}")

            # Sort by name for consistent ordering
            databases.sort(key=lambda x: x['name'])

            logger.info(f"{log_prefix}Discovered {len(databases)} database(s) in ./data/")
            return {
                'success': True,
                'databases': databases,
                'search_path': './data/',
                'current_path': current_path
            }

        except Exception as e:
            logger.error(f"{log_prefix}Database discovery failed: {e}")
            return {
                'success': False,
                'databases': [],
                'search_path': './data/',
                'current_path': '',
                'error': str(e)
            }

    def test_connection(self, config_data, request_id=None):
        """Test ChromaDB connection with given configuration."""
        log_prefix = f"[{request_id}] " if request_id else ""
        mode = config_data.get('mode', 'local')

        try:
            if mode == 'local':
                path = config_data.get('local_path')
                if not path:
                    return {'success': False, 'message': 'Local path is required'}

                path_obj = Path(path)

                # Check if path exists
                if not path_obj.exists():
                    return {'success': False, 'message': f'Path does not exist: {path}'}

                # Check if it's a directory
                if not path_obj.is_dir():
                    return {'success': False, 'message': f'Path is not a directory: {path}'}

                # Check for ChromaDB database files (chroma.sqlite3 is the main marker)
                chroma_db_file = path_obj / 'chroma.sqlite3'
                if not chroma_db_file.exists():
                    return {
                        'success': False,
                        'message': f'No ChromaDB database found at {path}',
                        'details': 'Expected chroma.sqlite3 file not found. Ensure the path points to an existing ChromaDB database.'
                    }

                client = chromadb.PersistentClient(path=path)
                collections = client.list_collections()
                collection_names = [c.name for c in collections]

                logger.info(f"{log_prefix}Local connection successful: {path}")
                return {
                    'success': True,
                    'message': f'Connected to local ChromaDB at {path}',
                    'collections': collection_names
                }

            elif mode == 'server':
                host = config_data.get('server_host', 'localhost')
                port = int(config_data.get('server_port', 8000))

                client = chromadb.HttpClient(host=host, port=port)
                collections = client.list_collections()
                collection_names = [c.name for c in collections]

                logger.info(f"{log_prefix}Server connection successful: {host}:{port}")
                return {
                    'success': True,
                    'message': f'Connected to ChromaDB server at {host}:{port}',
                    'collections': collection_names
                }

            elif mode == 'cloud':
                tenant = config_data.get('cloud_tenant')
                database = config_data.get('cloud_database')
                api_key = Config.CHROMADB_API_KEY

                if not tenant:
                    return {'success': False, 'message': 'Tenant ID is required'}
                if not database:
                    return {'success': False, 'message': 'Database name is required'}
                if not api_key:
                    return {'success': False, 'message': 'CHROMADB_API_KEY not configured in .env'}

                client = chromadb.CloudClient(
                    tenant=tenant,
                    database=database,
                    api_key=api_key
                )
                collections = client.list_collections()
                collection_names = [c.name for c in collections]

                logger.info(f"{log_prefix}Cloud connection successful: {tenant}/{database}")
                return {
                    'success': True,
                    'message': f'Connected to ChromaDB Cloud ({tenant}/{database})',
                    'collections': collection_names
                }

            else:
                return {'success': False, 'message': f'Unknown mode: {mode}'}

        except Exception as e:
            logger.error(f"{log_prefix}Connection test failed: {e}")
            return {'success': False, 'message': str(e)}

    def get_api_key_status(self, request_id=None):
        """Check if CHROMADB_API_KEY is configured in environment."""
        api_key = Config.CHROMADB_API_KEY

        if not api_key:
            return {'configured': False, 'masked': None}

        # Mask the key (show first 4 and last 4 chars)
        if len(api_key) > 8:
            masked = api_key[:4] + '...' + api_key[-4:]
        else:
            masked = '****'

        return {'configured': True, 'masked': masked}

    def _create_client(self, config_data, request_id=None):
        """Create a ChromaDB client based on config mode."""
        log_prefix = f"[{request_id}] " if request_id else ""
        mode = config_data.get('mode', 'local')

        if mode == 'local':
            path = config_data.get('local_path')
            if not path:
                raise ValueError('Local path is required')
            return chromadb.PersistentClient(path=path)

        elif mode == 'server':
            host = config_data.get('server_host', 'localhost')
            port = int(config_data.get('server_port', 8000))
            return chromadb.HttpClient(host=host, port=port)

        elif mode == 'cloud':
            tenant = config_data.get('cloud_tenant')
            database = config_data.get('cloud_database')
            api_key = Config.CHROMADB_API_KEY

            if not tenant:
                raise ValueError('Tenant ID is required')
            if not database:
                raise ValueError('Database name is required')
            if not api_key:
                raise ValueError('CHROMADB_API_KEY not configured in .env')

            return chromadb.CloudClient(
                tenant=tenant,
                database=database,
                api_key=api_key
            )
        else:
            raise ValueError(f'Unknown mode: {mode}')

    def get_sample_records(self, config_data, collection_name, limit=5, request_id=None):
        """Fetch sample records from a ChromaDB collection."""
        log_prefix = f"[{request_id}] " if request_id else ""

        if not collection_name:
            return {'success': False, 'message': 'Collection name is required'}

        try:
            client = self._create_client(config_data, request_id)
            collection = client.get_collection(collection_name)

            # Use peek to get sample records
            results = collection.peek(limit=limit)

            # Transform into a list of record objects
            records = []
            ids = results.get('ids', [])
            documents = results.get('documents', [])
            metadatas = results.get('metadatas', [])

            for i, doc_id in enumerate(ids):
                record = {
                    'id': doc_id,
                    'document': documents[i] if i < len(documents) else None,
                    'metadata': metadatas[i] if i < len(metadatas) else None
                }
                records.append(record)

            logger.info(f"{log_prefix}Fetched {len(records)} sample records from '{collection_name}'")
            return {
                'success': True,
                'collection': collection_name,
                'count': len(records),
                'records': records
            }

        except Exception as e:
            logger.error(f"{log_prefix}Failed to fetch sample records: {e}")
            return {'success': False, 'message': str(e)}

    def query_collection(self, query_text, n_results=None, distance_threshold=None, request_id=None):
        """
        Query the configured ChromaDB collection for relevant documents.

        Uses the collection's embedding function to convert query_text to a vector
        and performs similarity search against stored documents.

        Args:
            query_text: The text to search for (typically the user's message)
            n_results: Maximum number of results to return (default from config or 5)
            distance_threshold: Maximum distance to filter results (default from config)
                               Lower values = more relevant. None = no filtering.
            request_id: Optional request ID for log correlation

        Returns:
            dict with:
                - success: bool indicating if query succeeded
                - documents: list of document texts (empty if no results)
                - metadatas: list of metadata dicts
                - distances: list of distance scores
                - ids: list of document IDs
                - collection: name of queried collection
                - message: error message if not successful
        """
        log_prefix = f"[{request_id}] " if request_id else ""

        # Load current config
        config = self.get_config(request_id)
        collection_name = config.get('collection')

        # Resolve defaults from config before any early returns
        if n_results is None:
            n_results = config.get('n_results', 5)
        if distance_threshold is None:
            distance_threshold = config.get('distance_threshold')

        if not collection_name:
            logger.debug(f"{log_prefix}RAG query skipped: no collection configured")
            return {
                'success': False,
                'message': 'No collection configured',
                'documents': [],
                'metadatas': [],
                'distances': [],
                'ids': [],
                'n_results': n_results,
                'distance_threshold': distance_threshold,
            }

        try:
            client = self._create_client(config, request_id)
            collection = client.get_collection(collection_name)

            # Query the collection
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )

            # Extract results (query returns nested lists for batch queries)
            ids = results.get('ids', [[]])[0]
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]

            # Filter by distance threshold if provided
            if distance_threshold is not None:
                filtered = [
                    (doc_id, doc, meta, dist)
                    for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances)
                    if dist <= distance_threshold
                ]
                if filtered:
                    ids, documents, metadatas, distances = zip(*filtered)
                    ids, documents, metadatas, distances = list(ids), list(documents), list(metadatas), list(distances)
                else:
                    ids, documents, metadatas, distances = [], [], [], []

            logger.info(
                f"{log_prefix}RAG query returned {len(documents)} documents "
                f"from '{collection_name}' (threshold: {distance_threshold})"
            )

            return {
                'success': True,
                'collection': collection_name,
                'documents': documents,
                'metadatas': metadatas,
                'distances': distances,
                'ids': ids,
                'n_results': n_results,
                'distance_threshold': distance_threshold,
            }

        except Exception as e:
            logger.error(f"{log_prefix}RAG query failed: {e}")
            return {
                'success': False,
                'message': str(e),
                'documents': [],
                'metadatas': [],
                'distances': [],
                'ids': [],
                'n_results': n_results,
                'distance_threshold': distance_threshold,
            }


# Singleton instance
rag_config_service = RagConfigService()
