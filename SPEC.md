# AgentRAM — Specification

## What it does
AgentRAM is a persistent memory layer for AI coding agents (Claude Code, Codex, etc.) that survives session resets. It stores codebase context, design decisions, architecture rationale, and conversation history so agents always know where they left off.

## Core Features

### 1. Memory Store (SQLite-backed)
- **Session memory**: store/restore conversation context per workspace
- **Codebase context**: store file summaries, key decisions, architecture notes
- **Git history awareness**: track commit-level context
- **Queryable**: semantic search over stored memories

### 2. MCP Server Interface
- Standard Model Context Protocol server
- `ram_store(context)` — persist memory
- `ram_recall(query)` — retrieve relevant memories
- `ram_list()` — list all stored memories
- `ram_forget(memory_id)` — delete a memory

### 3. Git Integration
- Auto-attach git diff context when storing memories
- Track file-change history per workspace
- Link memories to specific commits/blobs

### 4. Agent Hook
- `ram-agent` CLI tool that wraps Claude Code
- Pre-fetches relevant memories before each session
- Auto-summarizes session and stores on exit
- Workspace-aware: remembers which repo you're in

## Tech Stack
- Python 3.11+ with `aiosqlite` for async DB
- MCP SDK (`mcp` Python package)
- `gitpython` for git integration
- `numpy`/`sentence-transformers` for semantic search (optional, falls back to keyword)
- `typer` CLI framework

## Project Structure
```
agent-ram/
  src/
    agentram/
      __init__.py
      db.py           # SQLite store
      mcp_server.py   # MCP protocol server
      git_ops.py      # Git integration
      search.py       # Memory retrieval
      cli.py          # CLI entry point
  tests/
  pyproject.toml
  README.md
```

## Acceptance Criteria
1. `ram-server` starts an MCP server on stdio
2. `ram-cli store <text>` persists a memory entry
3. `ram-cli recall <query>` returns relevant memories
4. MCP `tools` expose store/recall/list/forget
5. SQLite DB stores memories with workspace, timestamp, content
6. Git integration captures diff context when storing
7. Basic test suite covers core DB operations
8. README shows quick-start in < 5 commands
