from __future__ import annotations

import yaml

from sub_convert.config import load_config
from sub_convert.mihomo.renderer import load_yaml, render_subscription


def test_render_injects_proxy_names_into_groups() -> None:
    config = load_config("config.example.yaml")
    template = load_yaml(str(config.template.file_path))

    output = render_subscription(
        template=template,
        proxies=[
            {"name": "node-a", "type": "direct"},
            {"name": "node-a", "type": "direct"},
        ],
        render_config=config.render,
    )
    data = yaml.safe_load(output)

    assert [proxy["name"] for proxy in data["proxies"]] == ["node-a", "node-a-2"]
    group_map = {group["name"]: group for group in data["proxy-groups"]}
    assert "node-a" in group_map["🌏️Main Proxy"]["proxies"]
    assert "node-a-2" in group_map["⚖Load Balance"]["proxies"]
    assert "DIRECT" in group_map["🌏️Main Proxy"]["proxies"]
