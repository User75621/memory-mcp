# Contributing to Memory MCP

Thanks for helping improve Memory MCP for long-term AI project memory and Supabase persistent context.

## How to contribute

1. Fork the repository and create a feature branch.
2. Install development dependencies with `pip install -r requirements-dev.txt`.
3. Run `pytest`, `black .`, `flake8`, and `mypy src` before opening a pull request.
4. Document any user-facing change in `README.md` or `docs/`.

## Code style guidelines

- Use Python type hints in every function.
- Keep lines at 100 characters or fewer.
- Prefer small functions and explicit error handling.
- Write self-documenting code and only add comments when logic is not obvious.
- Keep docs bilingual whenever a public page or message changes.

## Pull request process

1. Explain the problem, the solution, and any schema or API impact.
2. Include screenshots or documentation updates when the docs UI changes.
3. Add or update tests for every server tool, optimizer behavior, or SQL contract you modify.
4. Wait for review and keep commits focused so maintainers can audit changes quickly.

## Issue template

Open issues with this structure:

```text
Title: Short, searchable summary

Problem
- What failed?
- Which interface was involved?

Expected behavior
- What should happen?

Environment
- Python version
- Interface: native / qwen-code / codex
- Supabase setup notes

Extra context
- Logs, screenshots, sample payloads, or schema details
```
