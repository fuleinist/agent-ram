"""MCP server implementation for AgentRAM."""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from .db import MemoryDB
from .search import MemorySearch
from .git_ops import GitOps


class MCPServer:
    """Model Context Protocol server for AgentRAM."""

    def __init__(self, db_path: str | None = None):
        self.db = MemoryDB(db_path)
        self.search = MemorySearch(self.db)
        self.git_ops = GitOps()
        self._running = False

    async def start(self) -> None:
        """Start the MCP server on stdio."""
        await self.db.connect()
        self._running = True

        while self._running:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break

                request = line.strip()
                if not request:
                    continue

                try:
                    import json
                    req_data = json.loads(request)
                    response = await self._handle_request(req_data)
                    print(json.dumps(response), flush=True)
                except json.JSONDecodeError:
                    print(json.dumps({"error": "invalid json"}), flush=True)
            except Exception as e:
                print(json.dumps({"error": str(e)}), flush=True)

    async def _handle_request(self, request: dict[str Any]) -> dict[str Any]:
        """Handle an MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "agentram", "version": "0.1.0"},
            }

        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "ram_store",
                        "description": "Store a new memory",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "workspace": {"type": "string"},
                                "memory_type": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["content", "workspace"],
                        },
                    },
                    {
                        "name": "ram_recall",
                        "description": "Recall relevant memories",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "workspace": {"type": "string"},
                                "limit": {"type": "integer", "default": 5},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "ram_list",
                        "description": "List all memories",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "workspace": {"type": "string"},
                                "memory_type": {"type": "string"},
                                "limit": {"type": "integer", "default": 50},
                            },
                        },
                    },
                    {
                        "name": "ram_forget",
                        "description": "Delete a memory",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "memory_id": {"type": "string"},
                            },
                            "required": ["memory_id"],
                        },
                    },
                ]
            }

        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})

            if tool_name == "ram_store":
                git_context = self.git_ops.get_context()
                memory_id = await self.db.store(
                    content=tool_args["content"],
                    workspace=tool_args["workspace"],
                    memory_type=tool_args.get("memory_type", "context"),
                    tags=tool_args.get("tags", []),
                    commit_sha=git_context.commit_sha if git_context else None,
                )
                return {"content": [{"type": "text", "text": f"Stored: {memory_id}"}]}

            elif tool_name == "ram_recall":
                memories = await self.search.search(
                    query=tool_args["query"],
                    workspace=tool_args.get("workspace"),
                    limit=tool_args.get("limit", 5),
                )
                text = "\n".join(
                    f"[{m.id}] {m.content[:200]}..." if len(m.content) > 200 else f"[{m.id}] {m.content}"
                    for m in memories
                )
                return {"content": [{"type": "text", "text": text or "No memories found"}]}

            elif tool_name == "ram_list":
                memories = await self.db.list_memories(
                    workspace=tool_args.get("workspace"),
                    memory_type=tool_args.get("memory_type"),
                    limit=tool_args.get("limit", 50),
                )
                text = "\n".join(
                    f"[{m.id}] {m.memory_type}: {m.content[:100]}..."
                    for m in memories
                )
                return {"content": [{"type": "text", "text": text or "No memories"}]}

            elif tool_name == "ram_forget":
                deleted = await self.db.forget(tool_args["memory_id"])
                return {"content": [{"type": "text", "text": "Deleted" if deleted else "Not found"}]}

            return {"error": f"Unknown tool: {tool_name}"}

        if method == "shutdown":
            self._running = False
            await self.db.close()
            return {"ok": True}

        return {"error": f"Unknown method: {method}"}


async def run_server(db_path: str | None = None) -> None:
    """Run the MCP server."""
    server = MCPServer(db_path)
    await server.start()
