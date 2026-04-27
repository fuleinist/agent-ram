"""SQLite-backed memory store for AgentRAM."""

from __future__ import annotations

import aiosqlite
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    """A stored memory entry."""
    id: str
    workspace: str
    content: str
    memory_type: str  # "session" | "context" | "decision" | "architecture"
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    commit_sha: Optional[str] = None
    tags: list[str] = field(default_factory=list)


class MemoryDB:
    """Async SQLite-backed memory store."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path or Path.home() / ".agentram" / "memory.db"
        self._db_path = self.db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Initialize database connection and create tables."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self._db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def _create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                workspace TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL DEFAULT 'context',
                created_at TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                commit_sha TEXT,
                tags TEXT NOT NULL DEFAULT '[]'
            )
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workspace ON memories(workspace)
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)
        """)
        await self._conn.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def store(
        self,
        content: str,
        workspace: str,
        memory_type: str = "context",
        metadata: Optional[dict[str, Any]] = None,
        commit_sha: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """Store a new memory entry."""
        memory_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            """
            INSERT INTO memories (id, workspace, content, memory_type, created_at, metadata, commit_sha, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                workspace,
                content,
                memory_type,
                now,
                _json_dumps(metadata or {}),
                commit_sha,
                _json_dumps(tags or []),
            ),
        )
        await self._conn.commit()
        return memory_id

    async def recall(
        self,
        query: str,
        workspace: Optional[str] = None,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """Retrieve memories matching a query (keyword fallback)."""
        memories = await self._search_keyword(query, workspace, limit)
        return [self._row_to_entry(row) for row in memories]

    async def _search_keyword(
        self,
        query: str,
        workspace: Optional[str] = None,
        limit: int = 5,
    ) -> list[aiosqlite.Row]:
        """Simple keyword search."""
        conditions = ["content LIKE ?"]
        params: list[Any] = [f"%{query}%"]

        if workspace:
            conditions.append("workspace = ?")
            params.append(workspace)

        sql = f"""
            SELECT * FROM memories
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)

        async with self._conn.execute(sql, params) as cursor:
            return await cursor.fetchall()

    async def list_memories(
        self,
        workspace: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        """List all memories, optionally filtered."""
        conditions = []
        params: list[Any] = []

        if workspace:
            conditions.append("workspace = ?")
            params.append(workspace)
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM memories {where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]

    async def forget(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        cursor = await self._conn.execute(
            "DELETE FROM memories WHERE id = ?", (memory_id,)
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a single memory by ID."""
        async with self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            return self._row_to_entry(row)
        return None

    def _row_to_entry(self, row: aiosqlite.Row) -> MemoryEntry:
        """Convert a database row to a MemoryEntry."""
        return MemoryEntry(
            id=row["id"],
            workspace=row["workspace"],
            content=row["content"],
            memory_type=row["memory_type"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=_json_loads(row["metadata"]),
            commit_sha=row["commit_sha"],
            tags=_json_loads(row["tags"]),
        )


def _json_dumps(obj: Any) -> str:
    """Serialize object to JSON string."""
    import json
    return json.dumps(obj, ensure_ascii=False)


def _json_loads(s: str) -> Any:
    """Deserialize JSON string to object."""
    import json
    if not s or s == "{}":
        return {}
    return json.loads(s)
