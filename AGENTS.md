# Repository Guidelines

## Project Structure & Module Organization

Application code lives in `src/sub_convert/`:

- `api/`: FastAPI routes and error handling.
- `config/`: YAML loading and Pydantic configuration models.
- `converters/`: sing-box protocol converters and registry.
- `singbox/`: sing-box input models, readers, and output rendering.
- `mihomo/`: Mihomo rendering and output models.
- `subscriptions/`: subscription orchestration, token lookup, and YAML loading.

Tests mirror these areas in `tests/test_<module>.py`. Tracked examples belong in `examples/`, `config.example.yaml`, `config.template.json`, and the template examples; do not commit local `config.yaml` or generated subscription data.

## Build, Test, and Development Commands

```bash
uv sync --extra dev                              # Install runtime and test dependencies
uv run pytest                                    # Run the full test suite
uv run pytest tests/test_converters.py -q        # Run one focused test module
uv run uvicorn sub_convert.main:app --reload     # Start the development server
uv build                                         # Build source and wheel artifacts
```

Copy `config.example.yaml` to `config.yaml` and replace its development token before starting the service at `http://127.0.0.1:8000`. Set `SUB_CONVERT_CONFIG` to use another config.

## Coding Style & Naming Conventions

Target Python 3.12+ with four-space indentation, type hints, and `from __future__ import annotations`. Use `snake_case` for functions, variables, and modules; `PascalCase` for classes and Pydantic models. Group imports as standard library, third-party, then local. Keep module responsibilities intact. No formatter or linter is configured, so match surrounding style.

## Testing Guidelines

Tests use pytest and are named `tests/test_*.py` with `test_*` functions. Cover converter, rendering, configuration, privacy, and HTTP changes. Prefer tracked examples and `TestClient`; avoid live network calls. Run `uv run pytest` before submission. No coverage threshold is enforced.

## Commit & Pull Request Guidelines

Use short, imperative subject lines, following examples such as `Add subscription filename response header`. Avoid conventional-commit prefixes.

Pull requests should explain the behavioral change, list verification commands, and link related issues. Include sanitized YAML for output changes and note configuration or API compatibility impacts.

## Security & Configuration

Keep `config.yaml`, credentials, private keys, and subscription snapshots out of Git. Configure users with SHA-256 `token_hash` values rather than plaintext tokens. Preserve token-isolation guarantees: converters must emit only the requested user's credentials, and invalid tokens must remain indistinguishable from missing ones.
