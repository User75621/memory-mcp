# Codex Example

Use this guide to connect Codex to the same persistent memory backend used by your other AI clients.

## Configuration

1. Export Supabase credentials from `.env`.
2. Run `pip install -e .` so the `memory-mcp` command is available.
3. Start the server with `memory-mcp` if you want to test it manually.
4. Load `mcp.json` inside your Codex plugin or CLI settings.

## Command

```bash
codex --config mcp.json
```

## Best practices

- Save blockers with `add_warning` so every interface sees the same risk state.
- Close sessions with `end_session` to improve `get_interface_analytics` data.
- Keep tasks synchronized with `update_task_status` during delegated coding work.
