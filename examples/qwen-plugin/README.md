# Qwen Code Example

This example shows how to attach Memory MCP to a Qwen Code workflow.

## Configuration

1. Install project dependencies.
2. Point Qwen Code to the local `mcp.json` file.

## Command

```bash
qwen --mcp-config mcp.json
```

If you want to force a client label for analytics or routing, you can optionally set:

```bash
PROJECT_MEMORY_INTERFACE=qwen-code qwen --mcp-config mcp.json
```

## Best practices

- Call `load_unified_context` before large code generation tasks.
- Save architecture decisions with `save_cross_interface_decision` after a refactor.
- Sync partial editor state with `sync_session_state` for reliable multi-interface AI continuity.
