"""
Embedding generation service using sentence-transformers.
Converts text chunks into dense vectors for semantic search.

Model: all-MiniLM-L6-v2
- Dimensions: 384
- Speed: ~3000 sentences/second on CPU
- Quality: Good for MVP, will switch to OpenAI embeddings in production
- Size: ~80MB (small enough for local deployment)
"""

from typing import List, Dict
import logging
import asyncio
import torch
from sentence_transformers import SentenceTransformer
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton service for generating text embeddings.
    
    Uses lazy loading pattern:
    - Model is NOT loaded on import (saves memory)
    - Model loads on first .embed() call
    - Model stays in memory for subsequent calls (avoids reload overhead)
    
    Why sentence-transformers?
    - Free and open-source (no API costs)
    - Runs locally (no network latency)
    - Good quality for semantic search
    - Same library provides cross-encoder for re-ranking
    """
    
    def __init__(self):
        """Initialize service (does NOT load model yet)."""
        self._model = None
        self._device = None
        logger.info(f"EmbeddingService initialized (model will load on first use)")
    
    def _load_model(self):
        """
        Lazy load the embedding model.
        
        Why lazy loading?
        - Faster startup time (don't load if not needed)
        - Memory efficient (only load when actually embedding)
        - Allows health checks to pass before heavy model loading
        
        Device selection logic:
        - CUDA (NVIDIA GPU) if available -> fastest
        - MPS (Apple Silicon) if available -> fast on M1/M2 Macs
        - CPU as fallback -> slower but works everywhere
        """
        if self._model is not None:
            return  # Already loaded
        
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        
        # Detect best available device
        if torch.cuda.is_available():
            self._device = "cuda"
            logger.info("✅ Using CUDA (GPU) for embeddings")
        elif torch.backends.mps.is_available():
            self._device = "mps"  # Apple Silicon
            logger.info("✅ Using MPS (Apple Silicon GPU) for embeddings")
        else:
            self._device = "cpu"
            logger.info("⚠️  Using CPU for embeddings (slower, consider GPU for production)")
        
        # Load model
        # Why normalize_embeddings=True?
        # - Required for cosine similarity in Qdrant
        # - Ensures all vectors have length 1
        # - Makes similarity scores interpretable (0 to 1)
        self._model = SentenceTransformer(
            settings.embedding_model,
            device=self._device
        )
        
        # Warmup: run one embedding to compile model
        # Why? First embedding is always slower (JIT compilation, cache warmup)
        logger.info("Warming up model with test embedding...")
        _ = self._model.encode(["test"], convert_to_tensor=False, show_progress_bar=False)
        
        logger.info(f"✅ Model loaded successfully (dim={settings.embedding_dim})")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Input text to embed
        
        Returns:
            List of floats (embedding vector) with length=384
        
        Example:
            embedding = await embed_text("Software engineer with 5 years Python experience")
            # Returns: [0.123, -0.456, 0.789, ..., 0.012] (384 dimensions)
        """
        self._load_model()  # Ensure model is loaded
        
        # encode() returns numpy array, convert to Python list
        # Why convert_to_tensor=False?
        # - We need plain Python lists for JSON serialization
        # - Qdrant client accepts lists, not tensors
        # Why show_progress_bar=False?
        # - We're in async context, progress bars break logging
        embedding = self._model.encode(
            text,
            convert_to_tensor=False,
            show_progress_bar=False,
            normalize_embeddings=True  # CRITICAL: required for cosine similarity
        )
        
        return embedding.tolist()
    
    async def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (more efficient than one-by-one).
        
        Why batching?
        - GPU utilization: processes multiple texts in parallel
        - ~3x faster than sequential embedding
        - Amortizes model overhead across multiple texts
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process at once
                - 32 is good default for CPU (balances speed vs memory)
                - Can increase to 128+ for GPU
        
        Returns:
            List of embedding vectors, same order as input texts
        
        Example:
            chunks = ["chunk 1 text", "chunk 2 text", "chunk 3 text"]
            embeddings = await embed_batch(chunks)
            # Returns: [[0.1, -0.2, ...], [0.3, 0.4, ...], [-0.1, 0.5, ...]]
        """
        if not texts:
            logger.warning("Empty text list provided for embedding")
            return []
        
        self._load_model()  # Ensure model is loaded
        
        logger.info(f"Generating embeddings for {len(texts)} texts (batch_size={batch_size})")
        
        # Run encoding in thread pool to avoid blocking event loop
        # Why asyncio.to_thread?
        # - Model encoding is CPU/GPU intensive (blocking operation)
        # - Running in thread keeps FastAPI responsive
        # - Allows other requests to process while encoding
        # Batch encode: automatically splits into batches
        # Why batch_size parameter?
        # - Controls memory usage (larger batches = more memory)
        # - GPU can handle larger batches than CPU
        embeddings = await asyncio.to_thread(
            self._model.encode,
            texts,
            batch_size=batch_size,
            convert_to_tensor=False,
            show_progress_bar=len(texts) > 10,  # Show progress for large batches
            normalize_embeddings=True
        )
        
        # Convert numpy array to list of lists
        # CRITICAL: Must convert numpy arrays to native Python lists for JSON serialization
        embeddings_list = embeddings.tolist()
        
        # Debug: Verify conversion worked correctly
        logger.info(f"DEBUG: Embeddings type after tolist(): {type(embeddings_list)}")
        logger.info(f"DEBUG: First embedding type: {type(embeddings_list[0]) if embeddings_list else 'N/A'}")
        logger.info(f"DEBUG: First value type: {type(embeddings_list[0][0]) if embeddings_list and embeddings_list[0] else 'N/A'}")
        
        logger.info(f"✅ Generated {len(embeddings_list)} embeddings (dim={len(embeddings_list[0]) if embeddings_list else 0})")
        
        return embeddings_list
    
    def get_model_info(self) -> Dict[str, any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model metadata
        """
        if self._model is None:
            return {
                "loaded": False,
                "model_name": settings.embedding_model,
                "device": None,
                "embedding_dim": settings.embedding_dim
            }
        
        return {
            "loaded": True,
            "model_name": settings.embedding_model,
            "device": str(self._device),
            "embedding_dim": settings.embedding_dim,
            "max_seq_length": self._model.max_seq_length
        }


# Global singleton instance
# Why singleton?
# - Model is expensive to load (~80MB, ~2 seconds)
# - Want to share one model across all requests
# - Avoid loading multiple copies in memory
embedding_service = EmbeddingService()

