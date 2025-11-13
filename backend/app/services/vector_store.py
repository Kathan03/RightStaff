"""
Qdrant vector database client for candidate embeddings.
Handles vector storage, similarity search, and metadata filtering.
"""

from typing import List, Dict, Optional
import logging
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct, 
    Filter,
    FieldCondition,
    MatchValue
)

from app.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Qdrant vector database client.
    
    Collection Schema:
    - Vector size: 384 (all-MiniLM-L6-v2 embedding dimension)
    - Distance: Cosine (normalized vectors, score 0-1)
    - Payload schema:
        {
            "candidate_id": str (UUID),
            "chunk_index": int,
            "chunk_text": str,
            "start_char": int,
            "end_char": int,
            "char_count": int,
            "filename": str,
            "created_at": str (ISO timestamp)
        }
    """

    def __init__(self):
        """Initialize Qdrant client."""
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=30
        )
        self.collection_name = settings.qdrant_collection
        logger.info(f"Qdrant client initialized: {settings.qdrant_host}:{settings.qdrant_port}")

    def create_collection(self, vector_size: int = 384):
        """
        Create Qdrant collection for candidate embeddings.
        
        This operation is idempotent:
        - If collection exists, does nothing
        - If collection doesn't exist, creates it
        - Safe to call multiple times
        
        Why Cosine distance?
        - Works with normalized vectors (all-MiniLM-L6-v2 normalizes)
        - Scores are interpretable: 1.0 = identical, 0.0 = orthogonal
        - Fast computation (single dot product after normalization)
        
        Args:
            vector_size: Embedding dimension (384 for all-MiniLM-L6-v2)
        
        Raises:
            Exception: If collection creation fails
        """
        try:
            # Check if collection already exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name in collection_names:
                logger.info(f"✅ Collection '{self.collection_name}' already exists")
                # Verify vector size matches
                collection_info = self.client.get_collection(self.collection_name)
                actual_size = collection_info.config.params.vectors.size
                if actual_size != vector_size:
                    logger.warning(
                        f"⚠️  Collection vector size mismatch: expected {vector_size}, got {actual_size}"
                    )
                return
            
            # Create new collection
            logger.info(f"Creating collection '{self.collection_name}' with vector_size={vector_size}")
            
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"✅ Created collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"❌ Error creating collection: {e}")
            raise

    def upsert_vectors(
        self,
        vectors: List[List[float]],
        payloads: List[Dict],
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        Insert or update vectors in collection.
        
        This is the main method for storing resume chunk embeddings.
        
        Why "upsert" instead of "insert"?
        - If vector with same ID exists, it updates (no duplicate error)
        - If vector doesn't exist, it inserts
        - Idempotent: safe to run multiple times for same candidate
        
        How IDs work:
        - Format: "{candidate_id}_chunk_{chunk_index}"
        - Example: "a1b2c3d4-...-uuid_chunk_0"
        - Allows querying by candidate (filter by prefix)
        - Allows deletion by candidate (delete all chunks)
        
        Args:
            vectors: List of embedding vectors [[0.1, 0.2, ...], ...]
            payloads: List of metadata dicts (must match vectors length)
            ids: Optional list of IDs (auto-generated if None)
        
        Returns:
            True if successful
        
        Raises:
            ValueError: If vectors/payloads length mismatch
            Exception: If upsert operation fails
        
        Example:
            vectors = [[0.1, 0.2, ...], [0.3, 0.4, ...]]
            payloads = [
                {"candidate_id": "uuid1", "chunk_index": 0, "chunk_text": "..."},
                {"candidate_id": "uuid1", "chunk_index": 1, "chunk_text": "..."}
            ]
            success = upsert_vectors(vectors, payloads)
        """
        if len(vectors) != len(payloads):
            raise ValueError(
                f"Vectors and payloads length mismatch: {len(vectors)} != {len(payloads)}"
            )
        
        if not vectors:
            logger.warning("Empty vectors list provided for upsert")
            return False
        
        # Generate IDs if not provided
        if ids is None:
            ids = []
            for payload in payloads:
                candidate_id = payload.get("candidate_id", str(uuid.uuid4()))
                chunk_index = payload.get("chunk_index", 0)
                
                # CRITICAL FIX: Qdrant requires integer IDs (not strings) for upsert operations
                # Solution: Generate deterministic integer ID from candidate_id + chunk_index
                # Why hash?
                # - Converts string to deterministic integer
                # - Same input always gives same ID (idempotent)
                # - Allows re-indexing without ID conflicts
                point_id_str = f"{candidate_id}_chunk_{chunk_index}"
                # Use hash() and mask to get positive 64-bit integer
                point_id = hash(point_id_str) & 0x7FFFFFFFFFFFFFFF  # Positive 64-bit int
                
                # Store the string ID in payload for debugging/querying
                payload["point_id_str"] = point_id_str
                
                ids.append(point_id)
        
        logger.info(f"Upserting {len(vectors)} vectors to collection '{self.collection_name}'")
        
        try:
            # Create PointStruct objects
            # Why PointStruct?
            # - Qdrant's native format for vector points
            # - Combines ID, vector, and metadata (payload)
            points = [
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
                for point_id, vector, payload in zip(ids, vectors, payloads)
            ]
            
            # Upsert to Qdrant
            # Why upsert instead of insert?
            # - Handles re-indexing gracefully (no "already exists" errors)
            # - Idempotent operation
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True  # Wait for operation to complete (ensures consistency)
            )
            
            logger.info(f"✅ Successfully upserted {len(vectors)} vectors")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error upserting vectors: {e}")
            raise

    def delete_by_candidate_id(self, candidate_id: str) -> bool:
        """
        Delete all vectors for a candidate (all resume chunks).
        
        Why delete?
        - Re-indexing: when candidate uploads new resume
        - Compliance: when candidate requests data deletion
        - Cleanup: when candidate is removed from system
        
        How deletion works:
        - Uses metadata filter on candidate_id field
        - Deletes all vectors matching the filter
        - Idempotent: no error if candidate has no vectors
        
        Args:
            candidate_id: Candidate UUID (string)
        
        Returns:
            True if successful (even if no vectors found)
        
        Example:
            delete_by_candidate_id("a1b2c3d4-1234-5678-90ab-cdef12345678")
            # Deletes all chunk vectors for this candidate
        """
        logger.info(f"Deleting all vectors for candidate: {candidate_id}")
        
        try:
            # Delete using filter
            # Why filter instead of ID list?
            # - Don't need to query first to get all IDs
            # - More efficient (single operation)
            # - Works even if we don't know chunk count
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="candidate_id",
                            match=MatchValue(value=candidate_id)
                        )
                    ]
                ),
                wait=True  # Wait for deletion to complete
            )
            
            logger.info(f"✅ Deleted vectors for candidate: {candidate_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting vectors for candidate {candidate_id}: {e}")
            # Don't raise - deletion failure shouldn't break the pipeline
            # Candidate data in PostgreSQL is still authoritative
            return False

    async def upsert_points(
        self,
        points: List[Dict],
        collection_name: Optional[str] = None
    ) -> bool:
        """
        Upsert points in dictionary format (alternative to upsert_vectors).

        This method accepts points as list of dicts (used by job_embeddings service).

        Args:
            points: List of point dicts with structure:
                [
                    {
                        "id": str or int,
                        "vector": List[float],
                        "payload": Dict
                    },
                    ...
                ]
            collection_name: Collection to upsert to (default: self.collection_name)

        Returns:
            True if successful

        Example:
            points = [
                {
                    "id": "job_123_profile",
                    "vector": [0.1, 0.2, ...],
                    "payload": {"job_id": "123", "kind": "profile"}
                }
            ]
            success = await vector_store.upsert_points(points)
        """
        if not points:
            logger.warning("Empty points list provided for upsert")
            return False

        collection = collection_name or self.collection_name

        try:
            logger.info(f"Upserting {len(points)} points to collection '{collection}'")

            # Convert dict format to PointStruct objects
            point_structs = []
            for point in points:
                point_id = point["id"]

                # Convert string IDs to deterministic integers
                if isinstance(point_id, str):
                    point_id = hash(point_id) & 0x7FFFFFFFFFFFFFFF

                point_structs.append(
                    PointStruct(
                        id=point_id,
                        vector=point["vector"],
                        payload=point.get("payload", {})
                    )
                )

            # Upsert to Qdrant
            self.client.upsert(
                collection_name=collection,
                points=point_structs,
                wait=True
            )

            logger.info(f"✅ Successfully upserted {len(points)} points")
            return True

        except Exception as e:
            logger.error(f"❌ Error upserting points: {e}")
            raise

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        filter_dict: Optional[Dict] = None,
        collection_name: Optional[str] = None,
        with_payload: bool = True
    ) -> List:
        """
        Search for similar vectors (semantic search).

        Used for:
        - Finding candidates similar to job description
        - Dense retrieval in ranking pipeline
        - Answering chatbot questions (Days 11-12)

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score (0-1, cosine distance)
            filter_dict: Qdrant filter dictionary for metadata filtering
            collection_name: Collection to search (default: self.collection_name)
            with_payload: Whether to include payload in results

        Returns:
            List of Qdrant ScoredPoint objects with:
                - id: Point ID
                - score: Similarity score (0-1, higher is better)
                - payload: Metadata dict (if with_payload=True)

        Example:
            results = vector_store.search(
                query_vector=[0.1, 0.2, ...],
                top_k=20,
                filter_dict={
                    "must": [
                        {"key": "candidate_id", "match": {"any": ["uuid1", "uuid2"]}}
                    ]
                }
            )
        """
        try:
            collection = collection_name or self.collection_name

            # Build search query
            search_params = {
                "collection_name": collection,
                "query_vector": query_vector,
                "limit": top_k,
                "with_payload": with_payload
            }

            # Add score threshold if specified
            if score_threshold is not None:
                search_params["score_threshold"] = score_threshold

            # Add filter if specified
            if filter_dict:
                search_params["query_filter"] = Filter(**filter_dict)

            # Execute search
            results = self.client.search(**search_params)

            logger.info(
                f"Search returned {len(results)} results from '{collection}' "
                f"(top_k={top_k}, filtered={filter_dict is not None})"
            )

            return results

        except Exception as e:
            logger.error(f"Error searching vectors: {e}")
            raise

    def get_collection_info(self) -> Dict:
        """
        Get collection statistics (vector count, config, etc.).
        
        Useful for:
        - Health checks
        - Monitoring
        - Debugging
        
        Returns:
            {
                "vectors_count": int,
                "points_count": int,
                "status": str,
                "vector_size": int
            }
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "vectors_count": info.vectors_count or 0,
                "points_count": info.points_count or 0,
                "status": info.status,
                "vector_size": info.config.params.vectors.size
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {
                "vectors_count": 0,
                "points_count": 0,
                "status": "error",
                "error": str(e)
            }

    def health_check(self) -> bool:
        """
        Check if Qdrant is responsive.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False


# Global vector store instance
vector_store = VectorStore()
