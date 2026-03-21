# Native Chat Example

Use this flow when your client runs in a native MCP chat interface and you want a stable memory layer.

## Commands

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -e .
memory-mcp
```

## Example MCP request

```json
{
  "tool": "load_unified_context",
  "arguments": {
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "interface": "native"
  }
}
```

## Expected output

- Returns project memory, active warnings, tasks, decisions, and a recommended model.
- Optimizes context for the native interface token budget.
- Preserves shared memory for future OpenCode, Claude Code CLI, Qwen Code, or Codex handoffs.
