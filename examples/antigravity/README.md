# Antigravity Example

Use this guide when your Antigravity build supports external MCP servers and you want to attach Memory MCP.

## Configuration

1. Clone and install `memory-mcp` once in a stable folder.
2. Run `pip install -e .` so the `memory-mcp` command is available.
3. Create a private `.env` with your Supabase values.
4. Run `schema.sql` in Supabase SQL Editor.
5. Register the server in Antigravity MCP settings using the same command as `mcp.json`.

## Command

```bash
memory-mcp
```

## Verified Windows MCP path

```text
%USERPROFILE%\.gemini\antigravity\mcp_config.json
```

## Best practices

- Load project memory before planning or long coding sessions.
- Save decisions when architecture changes.
- Sync session state before switching to another client.
