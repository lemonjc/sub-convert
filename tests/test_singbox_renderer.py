from __future__ import annotations

import json

from sub_convert.config import load_config
from sub_convert.mihomo.renderer import load_yaml
from sub_convert.singbox.renderer import render_subscription


def test_render_merges_outbounds_and_injects_selectors() -> None:
    config = load_config("config.example.yaml")
    template = load_yaml(str(config.templates.singbox.file_path))

    output = render_subscription(
        template=template,
        outbounds=[
            {"type": "vless", "tag": "node-a", "server": "198.51.100.1"},
            {"type": "vless", "tag": "node-a", "server": "198.51.100.2"},
        ],
    )
    data = json.loads(output)
    outbounds = {outbound["tag"]: outbound for outbound in data["outbounds"]}

    assert outbounds["node-a"]["server"] == "198.51.100.1"
    assert outbounds["node-a-2"]["server"] == "198.51.100.2"
    assert "node-a" in outbounds["🌏️Main Proxy"]["outbounds"]
    assert "node-a-2" in outbounds["♾️Auto Select"]["outbounds"]
    assert data["outbounds"][-1]["tag"] == "node-a-2"
