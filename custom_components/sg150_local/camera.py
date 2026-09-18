from __future__ import annotations

import asyncio
from contextlib import suppress

import aiohttp
from aiohttp import web

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import (
    async_aiohttp_proxy_web,
    async_get_clientsession,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, RUNTIME_MONITOR
from .monitor import SG150PortMonitor

BUFFER_SIZE = 102400
CONNECT_TIMEOUT = 3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    monitor: SG150PortMonitor = hass.data[DOMAIN][entry.entry_id][RUNTIME_MONITOR]
    async_add_entities([SG150Camera(entry, monitor)])


class SG150Camera(Camera):
    _attr_has_entity_name = True
    _attr_name = "Haustür"
    _attr_is_on = True

    def __init__(self, entry: ConfigEntry, monitor: SG150PortMonitor) -> None:
        super().__init__()
        self._entry = entry
        self._monitor = monitor
        self._url = f"http://{monitor.host}:{monitor.port}/"
        self._attr_unique_id = f"{entry.entry_id}_camera"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Siedle SG150",
            manufacturer="Siedle",
            model="SG 150-0",
        )
        self._remove_listener = None

    @property
    def available(self) -> bool:
        return self._monitor.is_open

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        if not self._monitor.is_open:
            return None

        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT):
                async with session.get(self._url) as response:
                    response.raise_for_status()
                    data = b""
                    async for chunk in response.content.iter_chunked(BUFFER_SIZE):
                        data += chunk
                        jpg_end = data.find(b"\xff\xd9")
                        if jpg_end == -1:
                            if len(data) > 2_000_000:
                                return None
                            continue
                        jpg_start = data.find(b"\xff\xd8")
                        if jpg_start == -1:
                            continue
                        return data[jpg_start : jpg_end + 2]
        except (TimeoutError, aiohttp.ClientError, OSError):
            return None
        return None

    async def handle_async_mjpeg_stream(
        self, request: web.Request
    ) -> web.StreamResponse | None:
        if not self._monitor.is_open:
            return None

        session = async_get_clientsession(self.hass)
        stream_coro = session.get(self._url)
        try:
            return await async_aiohttp_proxy_web(self.hass, request, stream_coro)
        except (aiohttp.ClientError, OSError, ConnectionResetError):
            # Port 20502 only exists while a door-video session is active.
            # A closed port outside a ring is expected and must not start HA's
            # generic stream worker or be treated as a persistent camera error.
            return None

    async def async_added_to_hass(self) -> None:
        @callback
        def _update() -> None:
            self.async_write_ha_state()

        self._remove_listener = self._monitor.add_listener(_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
