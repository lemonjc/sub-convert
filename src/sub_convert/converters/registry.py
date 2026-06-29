from __future__ import annotations

import logging

from sub_convert.config.models import InboundPublishOptions, ServerSource
from sub_convert.converters.base import ConversionError, ProtocolConverter
from sub_convert.converters.vless import VlessHttpUpgradeConverter, VlessRealityConverter
from sub_convert.mihomo.models import MihomoProxy
from sub_convert.singbox.models import SingBoxInbound

logger = logging.getLogger(__name__)


class ConverterRegistry:
    def __init__(self, converters: list[ProtocolConverter]) -> None:
        self._converters = converters

    def convert(
        self,
        *,
        server: ServerSource,
        inbound: SingBoxInbound,
        username: str,
        strict: bool,
    ) -> MihomoProxy | None:
        user = inbound.user_by_name(username)
        if user is None:
            return None

        publish = server.inbounds.get(inbound.tag, InboundPublishOptions())
        converter = next(
            (candidate for candidate in self._converters if candidate.supports(inbound)), None
        )
        if converter is None:
            message = f"unsupported inbound type={inbound.type!r} tag={inbound.tag!r}"
            if strict:
                raise ConversionError(message)
            logger.warning(message)
            return None

        return converter.convert(server=server, inbound=inbound, user=user, publish=publish)


def default_registry() -> ConverterRegistry:
    return ConverterRegistry([VlessRealityConverter(), VlessHttpUpgradeConverter()])

