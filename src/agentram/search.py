"""Semantic search for AgentRAM memories."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .db import MemoryDB, MemoryEntry

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


_FAILED = False


class MemorySearch:
    """Memory retrieval with semantic search support."""

    def __init__(self, db: MemoryDB, model_name: str = "all-MiniLM-L6-v2"):
        self.db = db
        self.model_name = model_name
        self._model = None

    async def search(
        self,
        query: str,
        workspace: str | None = None,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """Search memories by query."""
        if SEMANTIC_AVAILABLE and not _FAILED and self._model is None:
            self._load_model()

        if SEMANTIC_AVAILABLE and not _FAILED and self._model is not None:
            return await self._semantic_search(query, workspace, limit)
        else:
            return await self.db.recall(query, workspace, limit)

    async def _semantic_search(
        self,
        query: str,
        workspace: str | None,
        limit: int,
    ) -> list[MemoryEntry]:
        """Perform semantic search using embeddings."""
        memories = await self.db.list_memories(workspace=workspace, limit=100)

        if not memories:
            return []

        contents = [m.content for m in memories]
        query_vec = self._model.encode([query], convert_to_numpy=True)[0]

        scores: list[tuple[float, MemoryEntry]] = []
        for memory in memories:
            mem_vec = self._model.encode([memory.content], convert_to_numpy=True)[0]
            sim = float(np.dot(query_vec, mem_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(mem_vec)))
            scores.append((sim, memory))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scores[:limit]]

    def _load_model(self) -> None:
        """Load sentence transformer model."""
        global _FAILED
        if SEMANTIC_AVAILABLE:
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                _FAILED = True
