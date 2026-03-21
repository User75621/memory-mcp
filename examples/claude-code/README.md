# Claude Code CLI Example

Use this guide when you want Claude Code CLI to continue a project with the same stored memory.

## Configuration

1. Install the project dependencies.
2. Run `pip install -e .` so the `memory-mcp` command is available.
3. Register `mcp.json` in your Claude Code CLI configuration.

## Command

```bash
claude-code --mcp-config mcp.json
```

If you want to force a client label for analytics or routing, you can optionally set:

```bash
PROJECT_MEMORY_INTERFACE=claude-code claude-code --mcp-config mcp.json
```

## Best practices

- Load context with `load_unified_context` before planning or implementation.
- Persist new decisions after a design change with `save_cross_interface_decision`.
- Close sessions with `end_session` so analytics stay clean.
