# Claude Desktop Example

Use this guide when you want Claude Desktop to talk to the same Project Memory MCP server used by your coding tools.

## Configuration

1. Clone and install `project-memory-mcp` in a stable folder.
2. Run `pip install -e .` so the `project-memory-mcp` command is available.
3. Create `.env` with your Supabase values.
4. Edit the Claude Desktop MCP config file.

## Windows config path

```text
%APPDATA%\Claude\claude_desktop_config.json
```

## Example config

```json
{
  "mcpServers": {
    "project-memory-mcp": {
      "command": "project-memory-mcp",
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_KEY": "your-anon-key",
        "OWNER_ID": "your-owner-id",
        "DEFAULT_MODEL": "gemini-pro",
        "PROJECT_MEMORY_INTERFACE": "claude-code"
      }
    }
  }
}
```

## Best practices

- Restart Claude Desktop after saving the config.
- Ask naturally for project context and let the model call tools automatically.
- Reuse the same central server for OpenCode, Codex, and Claude Desktop.
