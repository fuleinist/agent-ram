"""Tests for AgentRAM database operations."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from agentram.db import MemoryDB, MemoryEntry


@pytest_asyncio.fixture
async def db() -> MemoryDB:
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        database = MemoryDB(db_path)
        await database.connect()
        yield database
        await database.close()


@pytest.mark.asyncio
async def test_store_and_recall(db: MemoryDB) -> None:
    """Test storing and retrieving a memory."""
    memory_id = await db.store(
        content="This is a test memory about the auth system",
        workspace="/test/workspace",
        memory_type="context",
    )

    assert memory_id is not None
    assert len(memory_id) == 36  # UUID

    memories = await db.recall("auth system", workspace="/test/workspace")
    assert len(memories) == 1
    assert memories[0].content == "This is a test memory about the auth system"
    assert memories[0].memory_type == "context"


@pytest.mark.asyncio
async def test_store_with_git_context(db: MemoryDB) -> None:
    """Test storing a memory with git commit info."""
    memory_id = await db.store(
        content="Fixed the login bug",
        workspace="/test/workspace",
        commit_sha="abc1234",
    )

    memory = await db.get(memory_id)
    assert memory is not None
    assert memory.commit_sha == "abc1234"


@pytest.mark.asyncio
async def test_list_memories(db: MemoryDB) -> None:
    """Test listing memories with filters."""
    await db.store(content="First memory", workspace="/test", memory_type="session")
    await db.store(content="Second memory", workspace="/test", memory_type="context")
    await db.store(content="Other workspace", workspace="/other", memory_type="context")

    all_memories = await db.list_memories(workspace="/test")
    assert len(all_memories) == 2

    session_only = await db.list_memories(workspace="/test", memory_type="session")
    assert len(session_only) == 1
    assert session_only[0].content == "First memory"


@pytest.mark.asyncio
async def test_forget(db: MemoryDB) -> None:
    """Test deleting a memory."""
    memory_id = await db.store(
        content="Temporary memory",
        workspace="/test",
    )

    deleted = await db.forget(memory_id)
    assert deleted is True

    memory = await db.get(memory_id)
    assert memory is None

    not_deleted = await db.forget("nonexistent-id")
    assert not_deleted is False


@pytest.mark.asyncio
async def test_recall_no_results(db: MemoryDB) -> None:
    """Test recall with no matching results."""
    await db.store(content="Something about the database", workspace="/test")

    memories = await db.recall("python async", workspace="/test")
    assert len(memories) == 0


@pytest.mark.asyncio
async def test_tags(db: MemoryDB) -> None:
    """Test storing memories with tags."""
    memory_id = await db.store(
        content="Auth middleware implementation",
        workspace="/test",
        tags=["auth", "middleware", "security"],
    )

    memory = await db.get(memory_id)
    assert memory is not None
    assert "auth" in memory.tags
    assert "middleware" in memory.tags
    assert "security" in memory.tags


@pytest.mark.asyncio
async def test_multiple_workspaces(db: MemoryDB) -> None:
    """Test memories are isolated by workspace."""
    await db.store(content="Workspace A secret", workspace="/workspace/a")
    await db.store(content="Workspace B secret", workspace="/workspace/b")

    a_memories = await db.recall("secret", workspace="/workspace/a")
    b_memories = await db.recall("secret", workspace="/workspace/b")

    assert len(a_memories) == 1
    assert len(b_memories) == 1
    assert "A" in a_memories[0].content
    assert "B" in b_memories[0].content
