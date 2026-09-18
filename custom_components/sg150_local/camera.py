from __future__ import annotations

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

from .const import DOMAIN, RUNTIME_HISTORY, RUNTIME_MONITOR
from .history import SG150HistoryRecorder
from .mjpeg import async_fetch_first_jpeg
from .monitor import SG150PortMonitor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    monitor: SG150PortMonitor = runtime[RUNTIME_MONITOR]
    history: SG150HistoryRecorder = runtime[RUNTIME_HISTORY]
    async_add_entities(
        [
            SG150Camera(entry, monitor),
            SG150LatestVisitorImageCamera(entry, history),
        ]
    )


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
        return await async_fetch_first_jpeg(self.hass, self._url)

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


class SG150LatestVisitorImageCamera(Camera):
    _attr_has_entity_name = True
    _attr_name = "Letztes Besucherbild"
    _attr_is_on = True

    def __init__(self, entry: ConfigEntry, history: SG150HistoryRecorder) -> None:
        super().__init__()
        self._history = history
        self._attr_unique_id = f"{entry.entry_id}_latest_visitor_image"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Siedle SG150",
            manufacturer="Siedle",
            model="SG 150-0",
        )
        self._remove_listener = None

    @property
    def available(self) -> bool:
        return self._history.latest_path is not None

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        return await self._history.async_latest_image()

    async def async_added_to_hass(self) -> None:
        @callback
        def _update() -> None:
            self.async_write_ha_state()

        self._remove_listener = self._history.add_listener(_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
