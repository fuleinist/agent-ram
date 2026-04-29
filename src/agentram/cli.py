"""CLI for AgentRAM."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .db import MemoryDB
from .search import MemorySearch
from .git_ops import GitOps

app = typer.Typer(help="AgentRAM - Persistent memory for AI agents")
console = Console()


def get_workspace() -> str:
    """Get current workspace identifier."""
    git_ops = GitOps()
    return git_ops.get_workspace()


@app.command()
def store(
    content: str = typer.Argument(..., help="Memory content to store"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    memory_type: str = typer.Option("context", "--type", "-t", help="Memory type"),
    tags: list[str] = typer.Option([], "--tag", help="Tags for this memory"),
) -> None:
    """Store a new memory."""
    workspace = workspace or get_workspace()

    async def _store() -> None:
        db = MemoryDB()
        await db.connect()

        git_ops = GitOps(workspace)
        git_context = git_ops.get_context()

        memory_id = await db.store(
            content=content,
            workspace=workspace,
            memory_type=memory_type,
            tags=tags,
            commit_sha=git_context.commit_sha if git_context else None,
        )

        console.print(f"[green]Stored[/green]: {memory_id}")
        await db.close()

    asyncio.run(_store())


@app.command()
def recall(
    query: str = typer.Argument(..., help="Query to search memories"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    limit: int = typer.Option(5, "--limit", "-l", help="Max results"),
) -> None:
    """Recall relevant memories."""
    workspace = workspace or get_workspace()

    async def _recall() -> None:
        db = MemoryDB()
        await db.connect()
        search = MemorySearch(db)

        memories = await search.search(query=query, workspace=workspace, limit=limit)

        if not memories:
            console.print("[yellow]No memories found[/yellow]")
            await db.close()
            return

        for m in memories:
            console.print(f"\n[bold cyan][{m.id}][/bold cyan]")
            console.print(f"Type: {m.memory_type} | Created: {m.created_at.strftime('%Y-%m-%d %H:%M')}")
            if m.commit_sha:
                console.print(f"Commit: {m.commit_sha}")
            console.print(m.content)

        await db.close()

    asyncio.run(_recall())


@app.command()
def list_memories(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    memory_type: str | None = typer.Option(None, "--type", "-t", help="Filter by type"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all memories."""
    workspace = workspace or get_workspace()

    async def _list() -> None:
        db = MemoryDB()
        await db.connect()

        memories = await db.list_memories(
            workspace=workspace,
            memory_type=memory_type,
            limit=limit,
        )

        if not memories:
            if json_output:
                console.print("[]")
            else:
                console.print("[yellow]No memories[/yellow]")
            await db.close()
            return

        if json_output:
            output = [
                {
                    "id": m.id,
                    "type": m.memory_type,
                    "content": m.content,
                    "created": m.created_at.isoformat(),
                    "commit": m.commit_sha,
                    "tags": m.tags,
                }
                for m in memories
            ]
            console.print(json.dumps(output, ensure_ascii=False))
        else:
            table = Table(title="AgentRAM Memories")
            table.add_column("ID", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Content", style="white")
            table.add_column("Created")

            for m in memories:
                content = m.content[:50] + "..." if len(m.content) > 50 else m.content
                table.add_row(m.id[:8], m.memory_type, content, m.created_at.strftime("%Y-%m-%d %H:%M"))

            console.print(table)
        await db.close()

    asyncio.run(_list())


@app.command()
def forget(
    memory_id: str = typer.Argument(..., help="Memory ID to delete"),
) -> None:
    """Delete a memory."""

    async def _forget() -> None:
        db = MemoryDB()
        await db.connect()

        deleted = await db.forget(memory_id)
        if deleted:
            console.print(f"[green]Deleted[/green]: {memory_id}")
        else:
            console.print(f"[red]Not found[/red]: {memory_id}")

        await db.close()

    asyncio.run(_forget())


@app.command()
def server(
    db_path: str | None = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Start the MCP server."""
    from .mcp_server import run_server
    asyncio.run(run_server(db_path))


def main() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
