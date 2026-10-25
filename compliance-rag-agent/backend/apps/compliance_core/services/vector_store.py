"""
Primary Vector Database Service for Regulatory Standards using ChromaDB.
Features:
1. Persistent local storage in dedicated storage volume.
2. Local Sentence-Transformers embedding model (all-MiniLM-L6-v2) for full data privacy & zero external leakage.
3. Thread-safe Singleton manager for 'engineering_standards' collection.
4. Strict scalar metadata filtering (standard, regulation_number, duty_holder).
5. Hybrid retrieval combining semantic similarity with deterministic exact clause keyword recall.
"""

import os
import re
import logging
import threading
import hashlib
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path

from django.conf import settings
from pydantic import BaseModel, Field, ConfigDict

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api.types import Documents, Embeddings

from apps.compliance_core.schemas import RegulatoryChunk, DutyHolderType

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. Search Result Schema
# ==============================================================================
class RegulationSearchResult(BaseModel):
    """
    Unified result item returned from hybrid regulatory search.
    """
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    standard: str
    regulation_number: str
    sub_clause: str
    duty_holder: str
    parent_title: str
    raw_text: str
    semantic_score: float = Field(..., ge=0.0, le=1.0, description="Normalized vector similarity score")
    exact_match_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Exact clause/keyword match score")
    combined_score: float = Field(..., ge=0.0, description="Hybrid fused score used for deterministic ranking")
    is_exact_match: bool = Field(default=False, description="Flag indicating exact regulation/clause match in query")
    defense_available: bool = False
    classification_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 2. Local Privacy-Preserving Embedding Function
# ==============================================================================
class LocalSentenceTransformerEmbeddings(chromadb.EmbeddingFunction[Documents]):
    """
    Local embedding generator using sentence-transformers/all-MiniLM-L6-v2 (or BGE-small-en-v1.5).
    Operates strictly on-premise/in-container with ZERO external network transmission.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._ef = None
        self._model = None
        self._load_lock = threading.Lock()
        self.dimension = 384  # Standard embedding dimension for all-MiniLM-L6-v2 & bge-small

    @staticmethod
    def name() -> str:
        return "sentence_transformer"

    def get_config(self) -> Dict[str, Any]:
        return {"model_name": self.model_name, "dimension": self.dimension}

    @classmethod
    def build_from_config(cls, config: Dict[str, Any]) -> "LocalSentenceTransformerEmbeddings":
        return cls(model_name=config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"))

    def _get_model(self):
        if self._ef is not None:
            return self._ef

        with self._load_lock:
            if self._ef is not None:
                return self._ef

            # 1. Try native ChromaDB SentenceTransformerEmbeddingFunction
            try:
                from chromadb.utils import embedding_functions
                logger.info(f"Loading native ChromaDB SentenceTransformerEmbeddingFunction: '{self.model_name}'")
                self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.model_name
                )
                return self._ef
            except Exception as e:
                logger.debug(f"Chroma SentenceTransformerEmbeddingFunction initialization note: {e}")

            # 2. Try loading sentence-transformers directly
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading local SentenceTransformer model: '{self.model_name}' (Zero external data leakage)")
                self._model = SentenceTransformer(self.model_name)
                return self._model
            except ImportError:
                logger.debug("sentence-transformers not installed, checking langchain_community.embeddings...")

            # 3. Try LangChain HuggingFaceEmbeddings
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                logger.info(f"Loading local LangChain HuggingFaceEmbeddings: '{self.model_name}'")
                self._model = HuggingFaceEmbeddings(model_name=self.model_name)
                return self._model
            except ImportError:
                logger.debug("langchain_community not available.")

            logger.warning(
                f"SentenceTransformer library not found. Operating with deterministic local 384-dim hash embeddings "
                f"until 'pip install sentence-transformers' is run in the active Python environment."
            )
            return None

    def __call__(self, input: Documents) -> Embeddings:
        """
        Embeds a list of documents or queries into vectors.
        Conforms to Chroma's EmbeddingFunction protocol.
        """
        if not input:
            return []

        model = self._get_model()

        if model is not None:
            # 1. Native ChromaDB EmbeddingFunction
            if callable(model) and hasattr(model, "name"):
                return model(input)

            # 2. Native SentenceTransformer
            if hasattr(model, "encode"):
                embeddings = model.encode(input, normalize_embeddings=True, show_progress_bar=False)
                return [e.tolist() if hasattr(e, "tolist") else list(e) for e in embeddings]

            # 3. LangChain HuggingFaceEmbeddings
            if hasattr(model, "embed_documents"):
                return model.embed_documents(input)

        # 4. Deterministic Local Hash-Embedding Fallback (ensures 384-dim vector space offline)
        return [self._hash_text_to_384_vector(doc) for doc in input]

    def _hash_text_to_384_vector(self, text: str) -> List[float]:
        """
        Generates a deterministic normalized 384-dimensional unit vector
        for offline testing without external dependencies.
        """
        vec = []
        for i in range(self.dimension):
            h = hashlib.sha256(f"{text}_{i}".encode('utf-8')).hexdigest()
            # Map hex to float between -1.0 and 1.0
            val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
            vec.append(val)

        # Normalize to unit vector
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [round(x / norm, 6) for x in vec]


# ==============================================================================
# 3. Primary Regulation Vector Store (Singleton)
# ==============================================================================
class RegulationVectorStore:
    """
    Singleton ChromaDB vector database manager for 'engineering_standards'.
    Provides persistent local storage, scalar metadata filtering, and hybrid clause retrieval.
    """
    _instance: Optional['RegulationVectorStore'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RegulationVectorStore, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None
    ):
        if getattr(self, '_initialized', False):
            return

        # Configure directory: fallback order: explicit arg -> settings -> env -> default
        self.persist_directory = str(
            persist_dir
            or getattr(settings, 'CHROMA_PERSIST_DIR', None)
            or os.getenv('CHROMA_STORAGE_DIR')
            or os.getenv('CHROMA_PERSIST_DIR')
            or (Path(getattr(settings, 'BASE_DIR', Path('.'))).parent / 'chroma_storage')
        )
        self.collection_name = (
            collection_name
            or getattr(settings, 'CHROMA_COLLECTION_NAME', None)
            or os.getenv('CHROMA_COLLECTION_NAME')
            or 'engineering_standards'
        )
        self.embedding_model_name = (
            embedding_model
            or getattr(settings, 'EMBEDDING_MODEL_NAME', None)
            or os.getenv('EMBEDDING_MODEL_NAME')
            or 'sentence-transformers/all-MiniLM-L6-v2'
        )

        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        logger.info(f"Connecting to ChromaDB persistent vector store at: {self.persist_directory}")

        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Initialize local embedding function (Sentence-Transformers)
            self.embedding_function = LocalSentenceTransformerEmbeddings(
                model_name=self.embedding_model_name
            )

            # Initialize primary collection with cosine similarity distance
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(
                f"ChromaDB collection '{self.collection_name}' initialized successfully. "
                f"Current indexed chunks: {self.collection.count()}"
            )
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB PersistentClient: {e}", exc_info=True)
            raise e

    # --------------------------------------------------------------------------
    # Ingestion & Mutation Methods
    # --------------------------------------------------------------------------
    def add_chunks(self, chunks: List[RegulatoryChunk]) -> int:
        """
        Upserts structured RegulatoryChunk instances into ChromaDB.
        """
        if not chunks:
            return 0

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        seen_ids = set()
        for c in chunks:
            chunk_id = c.chunk_id
            if chunk_id in seen_ids:
                suffix = 2
                while f"{chunk_id}_v{suffix}" in seen_ids:
                    suffix += 1
                chunk_id = f"{chunk_id}_v{suffix}"
            seen_ids.add(chunk_id)

            ids.append(chunk_id)
            documents.append(c.raw_text)
            metadatas.append({
                "chunk_id": chunk_id,
                "standard": c.standard,
                "regulation_number": c.regulation_number,
                "sub_clause": c.sub_clause,
                "clause": c.sub_clause,  # alias for general RAG compatibility
                "duty_holder": c.duty_holder,
                "parent_title": c.parent_title,
                "document_type": c.document_type or "Statutory Regulation",
                "defense_available": bool(c.defense_available),
                "classification_code": c.classification_code or "",
                "guidance_notes": c.guidance_notes or "",
            })

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Upserted {len(ids)} chunks into '{self.collection_name}'. New total: {self.collection.count()}")
        return len(ids)

    def count(self) -> int:
        """Returns the total number of chunks currently stored in the collection."""
        return self.collection.count()

    def clear(self):
        """Clears all records in the collection (useful for re-ingestion and tests)."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Cleared ChromaDB collection '{self.collection_name}'.")

    # --------------------------------------------------------------------------
    # Metadata Filter Builder
    # --------------------------------------------------------------------------
    def build_chroma_where_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Translates a dictionary of scalar filters into a valid ChromaDB 'where' filter clause.
        Supports strict filtering by 'standard', 'regulation_number', and 'duty_holder'.
        """
        if not filters:
            return None

        allowed_keys = {'standard', 'regulation_number', 'duty_holder', 'sub_clause', 'defense_available', 'classification_code'}
        conditions: List[Dict[str, Any]] = []

        for key, value in filters.items():
            if key not in allowed_keys or value is None or value == "ALL":
                continue

            # Case-insensitive or normalized filter handling
            if isinstance(value, str):
                val_clean = value.strip()
                # Check for standard aliases
                if key == "standard" and val_clean.upper() in ("EAWR", "EAWR-1989", "ELECTRICITY AT WORK"):
                    val_clean = "Electricity at Work Regulations 1989"
                elif key == "standard" and val_clean.upper() in ("BPG4", "ESF", "ESF-BPG4"):
                    val_clean = "Electrical Safety First Best Practice Guide 4"

                conditions.append({key: val_clean})
            elif isinstance(value, bool):
                conditions.append({key: value})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    # --------------------------------------------------------------------------
    # Exact Keyword & Clause Identifier Extractor
    # --------------------------------------------------------------------------
    def extract_clause_identifiers(self, query_text: str) -> List[str]:
        """
        Extracts exact regulation/clause identifiers from engineering queries.
        Handles:
        - 'Reg 4(2)', 'Regulation 4(1)', 'Reg 16', 'Regulation 14'
        - Engineering clause numbers like '411.3.2', '7.5.1'
        - BPG4 classification codes: 'Code C1', 'Code C2', 'Code C3', 'Code FI'
        """
        identifiers: List[str] = []
        q = query_text.strip()

        # 1. Regulation numbers with optional sub-clause: e.g. 'Regulation 4(2)', 'Reg 4(1)', 'Reg 16'
        reg_pattern = re.compile(r'\b(?:Regulation|Reg\.?)\s*(\d+(?:\(\w+\))?)(?!\w)', re.IGNORECASE)
        for match in reg_pattern.finditer(q):
            num = match.group(1)
            identifiers.append(f"Regulation {num}")
            identifiers.append(num)

        # 2. Standalone sub-clause pattern: e.g. '4(1)', '4(2)', '4(4)'
        sub_pattern = re.compile(r'\b(\d{1,2}\(\d+\))(?!\w)')
        for match in sub_pattern.finditer(q):
            sub = match.group(1)
            identifiers.append(sub)
            identifiers.append(f"Regulation {sub}")

        # 3. Numeric standard clauses: e.g. '411.3.2', '411.3', '543.1'
        clause_pattern = re.compile(r'\b(\d{3}\.\d+(?:\.\d+)?)\b')
        for match in clause_pattern.finditer(q):
            identifiers.append(match.group(1))

        # 4. Classification Codes: e.g. 'Code C1', 'Code C2', 'Code C3', 'C1', 'C2'
        code_pattern = re.compile(r'\b(?:Code\s*)?(C[123]|FI)\b', re.IGNORECASE)
        for match in code_pattern.finditer(q):
            code = match.group(1).upper()
            identifiers.append(f"Code {code}")
            identifiers.append(code)

        # Deduplicate while preserving order
        seen = set()
        unique_ids = []
        for item in identifiers:
            normalized = item.lower().replace(" ", "")
            if normalized not in seen:
                seen.add(normalized)
                unique_ids.append(item)

        return unique_ids

    # --------------------------------------------------------------------------
    # 4 & 5. Hybrid Retrieval & Search Method
    # --------------------------------------------------------------------------
    def search_regulations(
        self,
        query_text: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RegulationSearchResult]:
        """
        Hybrid retrieval combining semantic vector similarity with exact clause keyword matching.
        Ensures deterministic recall when an engineer specifies an exact regulation number.

        Args:
            query_text: The user's technical question or regulation identifier.
            top_k: Maximum number of ranked results to return.
            filters: Strict scalar metadata filters (standard, regulation_number, duty_holder).

        Returns:
            List[RegulationSearchResult] sorted by hybrid combined score.
        """
        if not query_text or not query_text.strip():
            return []

        clean_query = query_text.strip()
        where_filter = self.build_chroma_where_filter(filters)
        exact_ids = self.extract_clause_identifiers(clean_query)

        # Total available items in collection
        total_items = self.collection.count()
        if total_items == 0:
            logger.warning("Search called on empty vector collection.")
            return []

        # Retrieve semantic vector candidates (fetch 2x top_k to allow hybrid fusion)
        fetch_limit = min(max(top_k * 2, 8), total_items)

        query_args: Dict[str, Any] = {
            "query_texts": [clean_query],
            "n_results": fetch_limit,
            "include": ["documents", "metadatas", "distances"]
        }
        if where_filter:
            query_args["where"] = where_filter

        try:
            results = self.collection.query(**query_args)
        except Exception as e:
            logger.error(f"ChromaDB vector query failed: {e}", exc_info=True)
            return []

        documents = results.get("documents", [[]])[0] if results.get("documents") else []
        metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
        distances = results.get("distances", [[]])[0] if results.get("distances") else []

        candidate_results: List[RegulationSearchResult] = []
        seen_chunks = set()

        # Process semantic candidates
        for idx, doc_text in enumerate(documents):
            meta = metadatas[idx] if idx < len(metadatas) else {}
            dist = distances[idx] if idx < len(distances) else 0.5
            chunk_id = meta.get("chunk_id", f"chk_{idx}")

            seen_chunks.add(chunk_id)

            # Cosine similarity conversion (1.0 = identical, 0.0 = orthogonal)
            semantic_score = max(0.0, min(1.0, round(1.0 - (dist / 2.0), 4)))

            # Calculate Exact Match score
            exact_match_score, is_exact = self._calculate_exact_match_score(
                query_identifiers=exact_ids,
                metadata=meta,
                doc_text=doc_text
            )

            # Hybrid Score Fusion:
            # 0.5 * semantic + 0.5 * exact, plus a heavy 0.75 boost if exact regulation is identified
            combined_score = round(
                (0.50 * semantic_score) + (0.50 * exact_match_score) + (0.75 if is_exact else 0.0),
                4
            )

            candidate_results.append(RegulationSearchResult(
                chunk_id=chunk_id,
                standard=meta.get("standard", "Engineering Standard"),
                regulation_number=meta.get("regulation_number", "General Provision"),
                sub_clause=meta.get("sub_clause", meta.get("clause", "N/A")),
                duty_holder=meta.get("duty_holder", DutyHolderType.NOT_APPLICABLE.value),
                parent_title=meta.get("parent_title", "Regulatory Provision"),
                raw_text=doc_text,
                semantic_score=semantic_score,
                exact_match_score=exact_match_score,
                combined_score=combined_score,
                is_exact_match=is_exact,
                defense_available=bool(meta.get("defense_available", False)),
                classification_code=meta.get("classification_code") or None,
                metadata=meta
            ))

        # If exact clause identifiers were in query, ensure chunks matching those clauses
        # are retrieved even if vector distance ranked them lower (Deterministic Recall Guarantee)
        if exact_ids:
            self._augment_with_exact_clause_matches(
                exact_ids=exact_ids,
                where_filter=where_filter,
                seen_chunks=seen_chunks,
                candidate_results=candidate_results
            )

        # Sort by combined hybrid score descending
        candidate_results.sort(key=lambda r: (r.is_exact_match, r.combined_score), reverse=True)

        return candidate_results[:top_k]

    def _calculate_exact_match_score(
        self,
        query_identifiers: List[str],
        metadata: Dict[str, Any],
        doc_text: str
    ) -> Tuple[float, bool]:
        """
        Evaluates exact keyword / clause match between query identifiers and chunk properties.
        """
        if not query_identifiers:
            return 0.0, False

        sub_clause = str(metadata.get("sub_clause", "")).lower().replace(" ", "")
        reg_num = str(metadata.get("regulation_number", "")).lower().replace(" ", "")
        parent_title = str(metadata.get("parent_title", "")).lower()
        class_code = str(metadata.get("classification_code", "")).lower()
        text_lower = doc_text.lower()

        max_score = 0.0
        is_exact = False

        for q_id in query_identifiers:
            clean_id = q_id.lower().replace(" ", "")

            # 1. Exact match on sub_clause (e.g. query 'Reg 4(2)' matches chunk 'Regulation 4(2)')
            if clean_id in sub_clause or sub_clause in clean_id:
                max_score = max(max_score, 1.0)
                is_exact = True
                continue

            # 2. Exact match on parent regulation (e.g. query 'Regulation 14' matches 'Regulation 14')
            if clean_id in reg_num or reg_num in clean_id:
                max_score = max(max_score, 0.85)
                is_exact = True
                continue

            # 3. Match on Classification Code (e.g. 'C1' or 'Code C1')
            if class_code and (clean_id == class_code or f"code{class_code}" == clean_id):
                max_score = max(max_score, 0.90)
                is_exact = True
                continue

            # 4. Match in parent title
            if clean_id in parent_title:
                max_score = max(max_score, 0.60)

            # 5. Verbatim match in raw clause text
            if q_id.lower() in text_lower:
                max_score = max(max_score, 0.40)

        return max_score, is_exact

    def _augment_with_exact_clause_matches(
        self,
        exact_ids: List[str],
        where_filter: Optional[Dict[str, Any]],
        seen_chunks: set,
        candidate_results: List[RegulationSearchResult]
    ):
        """
        Guarantees deterministic recall: queries collection for chunks that explicitly
        contain the extracted regulation number or clause if not already caught in vector top-k.
        """
        for q_id in exact_ids:
            if not q_id or len(q_id) < 2:
                continue

            # Try exact sub_clause or regulation_number lookup
            target_sub = q_id if q_id.lower().startswith("regulation") else f"Regulation {q_id}"
            
            try:
                # Query Chroma by metadata where clause
                exact_where: Dict[str, Any] = {"sub_clause": target_sub}
                if where_filter:
                    exact_where = {"$and": [exact_where, where_filter]}

                exact_data = self.collection.get(where=exact_where, limit=5)
                if exact_data and exact_data.get("ids"):
                    for idx, c_id in enumerate(exact_data["ids"]):
                        if c_id not in seen_chunks:
                            seen_chunks.add(c_id)
                            meta = exact_data["metadatas"][idx] if exact_data.get("metadatas") else {}
                            doc = exact_data["documents"][idx] if exact_data.get("documents") else ""

                            candidate_results.append(RegulationSearchResult(
                                chunk_id=c_id,
                                standard=meta.get("standard", "Engineering Standard"),
                                regulation_number=meta.get("regulation_number", "General Provision"),
                                sub_clause=meta.get("sub_clause", target_sub),
                                duty_holder=meta.get("duty_holder", DutyHolderType.ABSOLUTE.value),
                                parent_title=meta.get("parent_title", "Regulatory Provision"),
                                raw_text=doc,
                                semantic_score=0.85,
                                exact_match_score=1.0,
                                combined_score=2.25,  # Priority rank boost
                                is_exact_match=True,
                                defense_available=bool(meta.get("defense_available", False)),
                                classification_code=meta.get("classification_code") or None,
                                metadata=meta
                            ))
            except Exception as e:
                logger.debug(f"Direct clause search query for '{q_id}' yielded no results or was skipped: {e}")


# ==============================================================================
# 4. Convenience Accessor
# ==============================================================================
def get_vector_store() -> RegulationVectorStore:
    """Returns the singleton instance of the primary RegulationVectorStore."""
    return RegulationVectorStore()
