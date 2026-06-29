# sub-convert

`sub-convert` is a FastAPI service that generates Mihomo subscriptions from sing-box **server** configurations. It reads `inbounds`, extracts only the requested user, converts supported inbound protocols into Mihomo proxies, merges optional remote Mihomo subscriptions, and renders the final YAML through a template.

## Features

- Python 3.12+, uv, FastAPI
- Token-isolated subscription URLs: `/sub/{token}`
- Multiple sing-box server config files
- Multiple users per inbound without leaking other users
- First-class support for:
  - VLESS Reality
  - VLESS HTTPUpgrade as Mihomo WebSocket HTTPUpgrade
- Structured YAML rendering and proxy-group injection
- Local or HTTP template and remote Mihomo subscription loading
- Per-source User-Agent support for HTTP YAML downloads
- Query parameter switch for merging or skipping remote subscriptions
- SHA-256 token hashes in config instead of plaintext tokens

## Quick Start

Install dependencies:

```bash
uv sync --extra dev
```

Run tests:

```bash
uv run pytest
```

Start the service:

```bash
uv run uvicorn sub_convert.main:app --reload
```

Open with the bundled example token:

```text
http://127.0.0.1:8000/sub/lemonjc-dev-token
```

The bundled `config.example.yaml` uses `lemonjc-dev-token` only as a development example. Copy it to `config.yaml` and replace the token before deployment.

## Configuration

By default the app loads `config.yaml` from the current working directory. Start from the safe example file:

```bash
cp config.example.yaml config.yaml
```

Or point the service directly at another config:

```bash
SUB_CONVERT_CONFIG=/path/to/config.yaml uv run uvicorn sub_convert.main:app
```

Generate a token hash:

```bash
python -c "import hashlib; print(hashlib.sha256(b'your-token').hexdigest())"
```

Minimal user entry:

```yaml
template:
  file_path: template.example.yaml
  # Or:
  # url: "https://example.com/template.yaml"
  user_agent: "sub-convert/0.1"

http_user_agent: "sub-convert/0.1"

users:
  - username: alice
    token_hash: "<sha256-token-hash>"
    allowed_servers: [us-nosla]
    remote_subscriptions:
      - name: Example Remote
        url: "https://example.com/sub.yaml"
        user_agent: "clash.meta"
```

YAML sources support exactly one of `file_path` or `url`. `user_agent` is optional per source; when omitted, the service uses global `http_user_agent`.

Local template example:

```yaml
template:
  file_path: template.example.yaml
```

Remote template example:

```yaml
template:
  url: "https://example.com/mihomo-template.yaml"
  user_agent: "clash.meta"
```

Each `server` points to a sing-box server JSON and supplies publication metadata that does not exist in sing-box itself, such as direct public IP, display name, and CDN endpoint:

```yaml
servers:
  - id: example-server
    name: "Example"
    config_path: examples/sing-box-server.example.json
    direct_server: 203.0.113.10
    inbounds:
      VLESS-REALITY-IN:
        suffix: DL
      VLESS-HTTPUPGRADE-IN:
        suffix: CF
        server: cdn.example.com
        port: 443
```

## API

- `GET /healthz`: health check
- `GET /sub/{token}`: Mihomo YAML subscription
- `GET /api/v1/subscription/{token}`: versioned equivalent

Remote subscription merge is enabled by default. Disable it per request with either query parameter:

```text
/sub/{token}?include_remote=false
/sub/{token}?merge_remote=false
```

`merge_remote` has priority when both parameters are provided.

Invalid tokens return `404` so the API does not reveal whether a token exists.

## Extending Protocols

Add a new converter by implementing `ProtocolConverter` and registering it in `default_registry()`:

```python
class MyConverter(ProtocolConverter):
    def supports(self, inbound: SingBoxInbound) -> bool: ...
    def convert(...): ...
```

Converters receive the current `SingBoxUser`, so they should never iterate all users or copy unrelated credentials into the output.
