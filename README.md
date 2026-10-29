# sub-convert

`sub-convert` is a FastAPI service that generates Mihomo and sing-box subscriptions from sing-box **server** configurations. It reads `inbounds`, extracts only the requested user, converts supported protocols into client nodes, and merges them into a format-specific template.

## Features

- Python 3.12+, uv, FastAPI
- Token-isolated subscription URLs: `/sub/{token}`
- Multiple sing-box server config files
- Multiple users per inbound without leaking other users
- First-class support for:
  - VLESS Reality in Mihomo and sing-box formats
  - VLESS HTTPUpgrade in both formats
- User-Agent format negotiation
- Structured template rendering and proxy/outbound-group injection
- Local or HTTP templates and dual-format remote subscription loading
- Per-source User-Agent support for HTTP template and subscription downloads
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

Configure both output templates:

```yaml
templates:
  mihomo:
    file_path: template.example.yaml
    # Or: url: "https://example.com/mihomo.yaml"
  singbox:
    file_path: config.template.json
    # Or: url: "https://example.com/sing-box.json"

http_user_agent: "sub-convert/0.1"

users:
  - username: alice
    token_hash: "<sha256-token-hash>"
    allowed_servers: [us-nosla]
    remote_subscriptions:
      - name: Example Mihomo Remote
        type: mihomo
        url: "https://example.com/mihomo.yaml"
        user_agent: "clash.meta"
      - name: Example SingBox Remote
        type: sing-box
        url: "https://example.com/sing-box.json"
        user_agent: "sing-box"
```

YAML/JSON template sources support exactly one of `file_path` or `url`. `user_agent` is optional per source; when omitted, the service uses global `http_user_agent`. The legacy top-level `template` key is still accepted as the Mihomo template.

Local template example:

```yaml
templates:
  mihomo:
    file_path: template.example.yaml
```

Remote template example:

```yaml
templates:
  mihomo:
    url: "https://example.com/mihomo-template.yaml"
    user_agent: "clash.meta"
  singbox:
    url: "https://example.com/sing-box-template.json"
    user_agent: "sub-convert/0.1"
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
- `GET /sub/{token}`: format selected from `User-Agent`
- `GET /api/v1/subscription/{token}`: versioned equivalent

When `User-Agent` contains `sing-box` (case-insensitive), the response is sing-box JSON. `mihomo`, `clash`, and unknown clients receive Mihomo YAML. Responses set `Vary: User-Agent` and use `alice.json` or `alice.yaml` as the default filename.

The sing-box renderer appends local and remote outbounds to the template and injects their tags into every selector and URL-test group. Only remote subscriptions marked `type: sing-box` are loaded, from their `outbounds` field. Selector, URL-test, direct, block, and DNS outbounds from the remote document are not copied; the configured sing-box template remains responsible for routing policy.

Remote subscription merge applies to both formats and is enabled by default. `type: mihomo` sources read `proxies`; `type: sing-box` sources read `outbounds`. Each source uses its own URL and `user_agent`, so the remote server does not need to vary output by User-Agent. `type` defaults to `mihomo` for backward compatibility. Disable merging per request with either query parameter:

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
