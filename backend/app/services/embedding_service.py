"""Embedding service: Syntax-aware chunking and sentence-transformer vector generation."""
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from app.config import get_settings
from app.parsers import ParserFactory
from app.models.analysis import ChunkType

logger = logging.getLogger("codesage.embeddings")
settings = get_settings()

_model_instance = None


def get_embedding_model():
    """Lazy load SentenceTransformer model."""
    global _model_instance
    if _model_instance is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model_instance = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("SentenceTransformer model loaded: %s", settings.EMBEDDING_MODEL)
        except Exception as e:
            logger.warning("Failed to load SentenceTransformer: %s. Using deterministic fallback embeddings.", str(e))
            _model_instance = "fallback"
    return _model_instance


class EmbeddingService:
    @classmethod
    def generate_embedding(cls, text: str) -> bytes:
        """Encode text to float32 vector and return raw binary bytes."""
        model = get_embedding_model()
        if model != "fallback" and model is not None:
            vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            return vec.astype(np.float32).tobytes()
        else:
            # Deterministic pseudo-embedding for testing or offline environments
            import hashlib
            seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            vec = rng.randn(settings.EMBEDDING_DIMENSION).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec.tobytes()

    @classmethod
    def generate_embeddings_batch(cls, texts: List[str]) -> List[bytes]:
        """Batch encode list of texts."""
        if not texts:
            return []
        model = get_embedding_model()
        if model != "fallback" and model is not None:
            vecs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            return [v.astype(np.float32).tobytes() for v in vecs]
        else:
            return [cls.generate_embedding(t) for t in texts]

    @staticmethod
    def bytes_to_vector(data: bytes) -> np.ndarray:
        """Convert binary blob back to float32 numpy vector."""
        return np.frombuffer(data, dtype=np.float32)

    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        """Compute cosine similarity between two normalized vectors."""
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))

    @classmethod
    def chunk_code_file(cls, content: str, file_path: str, language: str) -> List[Dict[str, Any]]:
        """Syntax-aware code chunking using parsed classes, functions, and sliding-window fallback."""
        lines = content.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return []

        chunks: List[Dict[str, Any]] = []
        covered_lines = set()

        parser = ParserFactory.get_parser(language)
        if parser:
            parse_result = parser.parse(content, file_path)

            # 1. Classes
            for cls_node in parse_result.classes:
                chunks.append({
                    "chunk_type": ChunkType.CLASS,
                    "name": cls_node.name,
                    "parent_name": None,
                    "start_line": cls_node.start_line,
                    "end_line": cls_node.end_line,
                    "content": cls_node.content,
                    "signature": f"class {cls_node.name}",
                    "docstring": cls_node.docstring,
                    "file_path": file_path,
                    "language": language,
                })
                for l in range(cls_node.start_line, min(cls_node.end_line + 1, total_lines + 1)):
                    covered_lines.add(l)

            # 2. Standalone Functions / Methods
            for fn in parse_result.functions:
                chunks.append({
                    "chunk_type": ChunkType.FUNCTION,
                    "name": fn.name,
                    "parent_name": None,
                    "start_line": fn.start_line,
                    "end_line": fn.end_line,
                    "content": fn.content,
                    "signature": f"{fn.name}({', '.join(fn.parameters)})",
                    "docstring": fn.docstring,
                    "file_path": file_path,
                    "language": language,
                })
                for l in range(fn.start_line, min(fn.end_line + 1, total_lines + 1)):
                    covered_lines.add(l)

        # 3. Handle uncovered blocks via sliding window
        window_size = 50
        overlap = 10
        i = 1
        while i <= total_lines:
            # Check if this range is already fully covered by structural chunks
            uncovered_in_range = [l for l in range(i, min(i + window_size, total_lines + 1)) if l not in covered_lines]
            if uncovered_in_range:
                start_l = min(uncovered_in_range)
                end_l = min(start_l + window_size, total_lines)
                block_content = "\n".join(lines[start_l - 1 : end_l])
                if block_content.strip():
                    chunks.append({
                        "chunk_type": ChunkType.BLOCK,
                        "name": f"block_{start_l}_{end_l}",
                        "parent_name": None,
                        "start_line": start_l,
                        "end_line": end_l,
                        "content": block_content,
                        "signature": None,
                        "docstring": None,
                        "file_path": file_path,
                        "language": language,
                    })
            i += window_size - overlap

        return chunks
