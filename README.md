# AgentRAM

Persistent memory layer for AI coding agents. Survives session resets.

## Quick Start

```bash
# Install
pip install agentram

# Store a memory
ram-cli store "Use connection pooling for the auth DB queries" --workspace /path/to/project

# Recall memories
ram-cli recall "auth database"

# List all memories
ram-cli list --workspace /path/to/project

# Delete a memory
ram-cli forget <memory-id>

# Start MCP server (for Claude Code integration)
ram-server
```

## MCP Server Integration

Start the MCP server for integration with Claude Code:

```bash
ram-server
```

The server exposes these tools:
- `ram_store` - persist memory
- `ram_recall` - retrieve relevant memories
- `ram_list` - list all stored memories
- `ram_forget` - delete a memory

## Project Structure

```
agent-ram/
  src/agentram/
    __init__.py      # Package init
    db.py            # SQLite store
    search.py        # Memory retrieval
    git_ops.py       # Git integration
    mcp_server.py    # MCP protocol server
    cli.py           # CLI entry point
  tests/
    test_db.py       # Core DB tests
  pyproject.toml
  README.md
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Build
pip install -e .
```

## Features

- **Session memory**: store/restore conversation context per workspace
- **Codebase context**: store file summaries, key decisions, architecture notes
- **Git history**: auto-attach git diff context when storing memories
- **Semantic search**: optional embeddings-based retrieval (`pip install agentram[semantic]`)
- **Workspace isolation**: memories scoped to specific repos
