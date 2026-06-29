from __future__ import annotations

from abc import ABC, abstractmethod

from sub_convert.config.models import InboundPublishOptions, ServerSource
from sub_convert.mihomo.models import MihomoProxy
from sub_convert.singbox.models import SingBoxInbound, SingBoxUser


class ConversionError(RuntimeError):
    """Raised when an inbound cannot be converted safely."""


class ProtocolConverter(ABC):
    @abstractmethod
    def supports(self, inbound: SingBoxInbound) -> bool:
        """Return whether this converter can handle the inbound."""

    @abstractmethod
    def convert(
        self,
        *,
        server: ServerSource,
        inbound: SingBoxInbound,
        user: SingBoxUser,
        publish: InboundPublishOptions,
    ) -> MihomoProxy:
        """Convert a sing-box inbound/user pair into a Mihomo proxy."""


def build_proxy_name(server: ServerSource, publish: InboundPublishOptions) -> str:
    if publish.suffix:
        return f"{server.name}-{publish.suffix}"
    return f"{server.name}-{publish.server or 'node'}"

