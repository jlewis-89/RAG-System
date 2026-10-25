"""
ChromaDB Persistent Client and Vector Store Service.
Manages connection to persistent vector storage for compliance standards and documents.
"""

import os
import logging
import threading
from typing import List, Dict, Any, Optional
from django.conf import settings
import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)


class ChromaDBService:
    """
    Singleton service managing the persistent ChromaDB client and collections.
    """
    _instance: Optional['ChromaDBService'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ChromaDBService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return

        self.persist_directory = str(settings.CHROMA_PERSIST_DIR)
        self.collection_name = getattr(settings, 'CHROMA_COLLECTION_NAME', 'engineering_compliance_standards')
        
        # Ensure persistence directory exists
        os.makedirs(self.persist_directory, exist_ok=True)

        logger.info(f"Initializing ChromaDB PersistentClient at: {self.persist_directory}")
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            # Default collection with cosine similarity
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Connected to ChromaDB collection '{self.collection_name}'. Current count: {self.collection.count()}")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB PersistentClient: {e}", exc_info=True)
            raise e

    def get_collection(self, name: Optional[str] = None):
        """Returns the primary or requested ChromaDB collection."""
        if name and name != self.collection_name:
            return self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
        return self.collection

    def add_chunks(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        collection_name: Optional[str] = None
    ) -> int:
        """
        Upsert chunked text and metadata into the ChromaDB collection.
        """
        target_collection = self.get_collection(collection_name)
        target_collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas  # type: ignore
        )
        return len(ids)

    def query_similar(
        self,
        query_text: str,
        n_results: int = 4,
        where_filter: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> Any:
        """
        Query vector store for the most relevant document chunks based on semantic similarity.
        """
        target_collection = self.get_collection(collection_name)
        
        query_args: Dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": min(n_results, max(1, target_collection.count() or 1)),
            "include": ["documents", "metadatas", "distances"]
        }
        
        if where_filter:
            query_args["where"] = where_filter

        results = target_collection.query(**query_args)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Returns health and collection statistics."""
        return {
            "persist_directory": self.persist_directory,
            "collection_name": self.collection_name,
            "total_items": self.collection.count(),
            "status": "healthy"
        }


# Convenience accessor
def get_chroma_service() -> ChromaDBService:
    return ChromaDBService()
