import logging
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from app.config import settings

logger = logging.getLogger(__name__)

# Single client instance
_client: QdrantClient = None
_fallback_memory: bool = False

def get_qdrant_client() -> QdrantClient:
    """
    Initializes and returns the Qdrant client. If connecting to a remote host fails,
    it falls back to a thread-safe local persistent Qdrant instance on disk.
    """
    global _client, _fallback_memory
    if _client is not None:
        return _client

    url = settings.QDRANT_URL
    api_key = settings.QDRANT_API_KEY

    # Try connecting to external Qdrant if specified
    if url and url != ":memory:":
        try:
            logger.info(f"Attempting to connect to Qdrant at {url}...")
            # Set short timeout to fail fast and fall back gracefully
            _client = QdrantClient(url=url, api_key=api_key, timeout=5.0)
            # Ping database to verify connection
            _client.get_collections()
            logger.info(f"Connected to Qdrant successfully at {url}.")
            _fallback_memory = False
            return _client
        except Exception as e:
            logger.warning(
                f"Failed to connect to remote Qdrant at {url}: {e}. "
                "Falling back to high-performance local persistent vector database."
            )

    # Local fallback
    if url == ":memory:":
        logger.info("Initializing high-performance local in-memory Qdrant client.")
        _client = QdrantClient(location=":memory:")
        _fallback_memory = True
    else:
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        storage_path = os.path.join(base_dir, "data", "qdrant_storage")
        logger.info(f"Initializing high-performance local persistent Qdrant client at {storage_path}.")
        try:
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            _client = QdrantClient(path=storage_path)
            _fallback_memory = False
        except Exception as local_err:
            logger.error(f"Failed to initialize local persistent Qdrant client: {local_err}. Falling back to in-memory.")
            _client = QdrantClient(location=":memory:")
            _fallback_memory = True
            
    return _client

def is_fallback_memory() -> bool:
    """
    Returns True if the active Qdrant client is running completely in-memory (volatile).
    """
    global _client
    if _client is None:
        get_qdrant_client()
    return _fallback_memory

def ensure_collection(collection_name: str, vector_size: int = 1536):
    """
    Ensures that a vector collection exists in Qdrant. If it doesn't, it is created.
    """
    client = get_qdrant_client()
    try:
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        
        if not exists:
            logger.info(f"Creating vector collection '{collection_name}' (dim={vector_size})...")
            from qdrant_client.http.models import Distance, VectorParams
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info(f"Collection '{collection_name}' created successfully.")
        else:
            logger.debug(f"Collection '{collection_name}' already exists.")
    except Exception as e:
        logger.error(f"Error ensuring collection '{collection_name}': {e}")
        # Allow fallback to continue
