# OpenCode Example

Use this guide when you want OpenCode to inherit project memory before editing or debugging.

## Configuration

1. Install the project dependencies.
2. Run `pip install -e .` so the `project-memory-mcp` command is available.
3. Point OpenCode to the local `mcp.json` file.

## Command

```bash
opencode --mcp-config mcp.json
```

If you want to force a client label for analytics or routing, you can optionally set:

```bash
PROJECT_MEMORY_INTERFACE=opencode opencode --mcp-config mcp.json
```

OpenCode can also use the standard MCP command entry:

```json
{
  "mcpServers": {
    "project-memory-mcp": {
      "command": "project-memory-mcp"
    }
  }
}
```

## Best practices

- Call `load_unified_context` before large edits or repo-wide refactors.
- Save major architectural choices with `save_cross_interface_decision`.
- Use `sync_session_state` so another client can continue your work later.
