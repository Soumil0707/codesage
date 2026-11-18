"""RAG Service: MySQL-backed indexing, embedding storage, and hybrid retrieval."""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_, delete

from app.models.repository import Repository, RepositoryVersion, SourceFile, IndexingStatus
from app.models.analysis import CodeChunk, CodeEmbedding
from app.services.embedding_service import EmbeddingService
from app.services.dependency_service import DependencyService
from app.config import get_settings

logger = logging.getLogger("codesage.rag")
settings = get_settings()


class RAGService:
    @classmethod
    async def index_version(cls, version_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Index all files in a RepositoryVersion: chunking, embedding generation, and dependency analysis."""
        # Clean previous chunks & embeddings for this version
        await db.execute(delete(CodeChunk).where(CodeChunk.version_id == version_id))

        stmt = select(SourceFile).where(SourceFile.version_id == version_id)
        files = (await db.execute(stmt)).scalars().all()

        total_chunks = 0
        all_chunk_texts = []
        chunk_models: List[CodeChunk] = []

        for f in files:
            if not f.content:
                continue

            raw_chunks = EmbeddingService.chunk_code_file(f.content, f.file_path, f.language)
            for rc in raw_chunks:
                chunk = CodeChunk(
                    version_id=version_id,
                    file_path=rc["file_path"],
                    chunk_type=rc["chunk_type"],
                    name=rc["name"],
                    content=rc["content"],
                    start_line=rc["start_line"],
                    end_line=rc["end_line"],
                    language=rc["language"],
                    parent_name=rc.get("parent_name"),
                    signature=rc.get("signature"),
                    docstring=rc.get("docstring"),
                    token_count=len(rc["content"].split()),
                )
                chunk_models.append(chunk)
                all_chunk_texts.append(f"{chunk.name or ''}\n{chunk.content}")

        # Bulk save chunks
        for c in chunk_models:
            db.add(c)
        await db.flush()

        # Generate embeddings in batches of 64
        batch_size = 64
        for i in range(0, len(all_chunk_texts), batch_size):
            batch_texts = all_chunk_texts[i : i + batch_size]
            batch_chunks = chunk_models[i : i + batch_size]
            embeddings = EmbeddingService.generate_embeddings_batch(batch_texts)

            for chunk, emb_bytes in zip(batch_chunks, embeddings):
                embedding_record = CodeEmbedding(
                    chunk_id=chunk.id,
                    embedding_vector=emb_bytes,
                    embedding_model=settings.EMBEDDING_MODEL,
                    dimension=settings.EMBEDDING_DIMENSION,
                )
                db.add(embedding_record)

        total_chunks = len(chunk_models)

        # Build dependencies graph
        dep_result = await DependencyService.build_and_save_dependencies(version_id, db)

        # Update repository version and status
        v_stmt = select(RepositoryVersion).where(RepositoryVersion.id == version_id)
        version = (await db.execute(v_stmt)).scalars().first()
        if version:
            await db.execute(
                update(Repository)
                .where(Repository.id == version.repository_id)
                .values(indexing_status=IndexingStatus.COMPLETED)
            )

        await db.commit()
        logger.info(
            "Version %s indexed: %d chunks created, %d dependencies mapped.",
            version_id, total_chunks, dep_result["total_dependencies"]
        )

        return {
            "version_id": version_id,
            "total_chunks": total_chunks,
            "dependency_metrics": dep_result,
        }

    @classmethod
    async def hybrid_search(
        cls,
        query: str,
        version_id: str,
        db: AsyncSession,
        top_k: int = 8,
        language: Optional[str] = None,
        file_path_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining MySQL keyword filtering with application-side cosine similarity."""
        # 1. Fetch chunks & embeddings for the target version
        query_stmt = (
            select(CodeChunk, CodeEmbedding)
            .join(CodeEmbedding, CodeChunk.id == CodeEmbedding.chunk_id)
            .where(CodeChunk.version_id == version_id)
        )

        if language:
            query_stmt = query_stmt.where(CodeChunk.language == language)
        if file_path_filter:
            query_stmt = query_stmt.where(CodeChunk.file_path.like(f"%{file_path_filter}%"))

        results = (await db.execute(query_stmt)).all()
        if not results:
            return []

        # 2. Encode search query
        query_vec_bytes = EmbeddingService.generate_embedding(query)
        query_vec = EmbeddingService.bytes_to_vector(query_vec_bytes)

        query_tokens = [w.lower() for w in query.split() if len(w) > 2]
        scored_chunks = []

        for chunk, emb in results:
            emb_vec = EmbeddingService.bytes_to_vector(emb.embedding_vector)
            semantic_score = EmbeddingService.cosine_similarity(query_vec, emb_vec)

            # Keyword lexical match score
            content_lower = chunk.content.lower()
            name_lower = (chunk.name or "").lower()
            keyword_hits = sum(1 for tok in query_tokens if tok in content_lower or tok in name_lower)
            lexical_score = min(keyword_hits / max(len(query_tokens), 1), 1.0)

            # Hybrid weighted score: 70% vector + 30% keyword
            hybrid_score = (0.7 * semantic_score) + (0.3 * lexical_score)

            scored_chunks.append({
                "chunk_id": chunk.id,
                "file_path": chunk.file_path,
                "name": chunk.name,
                "chunk_type": chunk.chunk_type.value if hasattr(chunk.chunk_type, "value") else str(chunk.chunk_type),
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "language": chunk.language,
                "content": chunk.content,
                "score": float(hybrid_score),
            })

        # Rank and return top_k
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]
