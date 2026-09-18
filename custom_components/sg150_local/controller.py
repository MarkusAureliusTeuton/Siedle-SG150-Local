from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from urllib.parse import urljoin
from datetime import datetime, timezone
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import (
    CONF_AUTO_TABLET,
    CONF_DOOR_PATH,
    CONF_FULLY_DEVICE_ID,
    CONF_FULLY_SCREEN_ENTITY,
    CONF_HOME_PATH,
    CONF_RELOAD_COUNT,
    CONF_RELOAD_DELAY_MS,
    CONF_RETURN_DELAY_S,
    CONF_RETURN_HOME,
    CONF_WAKE_DELAY_MS,
    DEFAULT_AUTO_TABLET,
    DEFAULT_DOOR_PATH,
    DEFAULT_HOME_PATH,
    DEFAULT_RELOAD_COUNT,
    DEFAULT_RELOAD_DELAY_MS,
    DEFAULT_RETURN_DELAY_S,
    DEFAULT_RETURN_HOME,
    DEFAULT_WAKE_DELAY_MS,
)
from .monitor import SG150PortMonitor

_LOGGER = logging.getLogger(__name__)


class SG150TabletController:
    """Orchestrate the local Fully Kiosk door view."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        monitor: SG150PortMonitor,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.monitor = monitor

        self.auto_enabled = bool(
            entry.options.get(CONF_AUTO_TABLET, DEFAULT_AUTO_TABLET)
        )
        self.state = "bereit"
        self.last_action = ""
        self.last_error = ""
        self.trigger_count = 0
        self.auto_start_count = 0
        self.last_trigger_source = ""
        self.last_trigger_at: datetime | None = None
        self._last_trigger_monotonic = 0.0

        self._listeners: set[Callable[[], None]] = set()
        self._remove_monitor_listener: Callable[[], None] | None = None
        self._remove_doorbell_event: Callable[[], None] | None = None
        self._remove_video_ended_event: Callable[[], None] | None = None
        self._door_task: asyncio.Task | None = None
        self._return_task: asyncio.Task | None = None

    @property
    def configured(self) -> bool:
        return bool(self.entry.options.get(CONF_FULLY_DEVICE_ID))

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(callback)

        def remove() -> None:
            self._listeners.discard(callback)

        return remove

    def _notify(self) -> None:
        for callback in tuple(self._listeners):
            callback()

    def _set_status(
        self, state: str, action: str = "", error: str = ""
    ) -> None:
        self.state = state
        if action:
            self.last_action = action
        self.last_error = error
        self._notify()

    async def async_start(self) -> None:
        if self._remove_doorbell_event is not None:
            return

        @callback
        def _trigger_door(source: str) -> None:
            # Event bus and direct monitor callback can describe the same edge.
            # De-duplicate a single physical ring while keeping both paths as
            # independent fallbacks.
            now_mono = time.monotonic()
            if now_mono - self._last_trigger_monotonic < 1.0:
                return
            self._last_trigger_monotonic = now_mono

            self.trigger_count += 1
            self.last_trigger_source = source
            self.last_trigger_at = datetime.now(timezone.utc)
            self._cancel_return()
            self._set_status("türruf erkannt", f"Automatischer Türruf ({source})")

            if self.auto_enabled:
                self.auto_start_count += 1
                self._start_door_task()
            else:
                self._set_status(
                    "automatik aus",
                    "Automatischer Türruf",
                    "Automatische Türanzeige ist ausgeschaltet.",
                )

        @callback
        def _monitor_changed() -> None:
            if self.monitor.is_open:
                _trigger_door("monitor")
            elif self.entry.options.get(CONF_RETURN_HOME, DEFAULT_RETURN_HOME):
                self._start_return_task()

        @callback
        def _doorbell_event(event: Event) -> None:
            if (
                event.data.get("host") != self.monitor.host
                or int(event.data.get("port", -1)) != self.monitor.port
            ):
                return
            _trigger_door("event")

        @callback
        def _video_ended_event(event: Event) -> None:
            if (
                event.data.get("host") != self.monitor.host
                or int(event.data.get("port", -1)) != self.monitor.port
            ):
                return
            if self.entry.options.get(CONF_RETURN_HOME, DEFAULT_RETURN_HOME):
                self._start_return_task()

        self._remove_monitor_listener = self.monitor.add_listener(_monitor_changed)
        self._remove_doorbell_event = self.hass.bus.async_listen(
            "sg150_local_doorbell", _doorbell_event
        )
        self._remove_video_ended_event = self.hass.bus.async_listen(
            "sg150_local_video_ended", _video_ended_event
        )

    async def async_stop(self) -> None:
        if self._remove_monitor_listener is not None:
            self._remove_monitor_listener()
            self._remove_monitor_listener = None
        if self._remove_doorbell_event is not None:
            self._remove_doorbell_event()
            self._remove_doorbell_event = None
        if self._remove_video_ended_event is not None:
            self._remove_video_ended_event()
            self._remove_video_ended_event = None
        self._cancel_door()
        self._cancel_return()

    def _cancel_door(self) -> None:
        if self._door_task is not None and not self._door_task.done():
            self._door_task.cancel()
        self._door_task = None

    def _cancel_return(self) -> None:
        if self._return_task is not None and not self._return_task.done():
            self._return_task.cancel()
        self._return_task = None

    def _start_door_task(self) -> None:
        self._cancel_door()
        self._door_task = self.hass.async_create_task(
            self.async_show_door_view(), "SG150 show door view"
        )

    def _start_return_task(self) -> None:
        self._cancel_return()
        self._return_task = self.hass.async_create_task(
            self._async_delayed_return(), "SG150 return home"
        )

    async def _async_delayed_return(self) -> None:
        try:
            delay = int(
                self.entry.options.get(
                    CONF_RETURN_DELAY_S, DEFAULT_RETURN_DELAY_S
                )
            )
            await asyncio.sleep(max(0, delay))
            if not self.monitor.is_open:
                await self.async_show_home_view()
        except asyncio.CancelledError:
            raise

    def _absolute_url(self, configured_path: str) -> str:
        value = (configured_path or "").strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value

        try:
            base = get_url(
                self.hass,
                allow_external=False,
                allow_cloud=False,
                prefer_external=False,
            )
        except NoURLAvailableError as err:
            raise RuntimeError(
                "Keine lokale Home-Assistant-URL verfügbar. "
                "Bitte in den SG150-Optionen eine vollständige URL eintragen."
            ) from err

        if not value.startswith("/"):
            value = "/" + value
        return urljoin(base.rstrip("/") + "/", value.lstrip("/"))

    async def _async_turn_screen(self, on: bool) -> None:
        entity_id = self.entry.options.get(CONF_FULLY_SCREEN_ENTITY)
        if not entity_id:
            return

        await self.hass.services.async_call(
            "homeassistant",
            "turn_on" if on else "turn_off",
            {"entity_id": entity_id},
            blocking=True,
        )

    async def _async_start_fully(self) -> None:
        device_id = self.entry.options.get(CONF_FULLY_DEVICE_ID)
        if not device_id:
            raise RuntimeError("Kein Fully-Kiosk-Gerät konfiguriert.")

        if not self.hass.services.has_service("fully_kiosk", "start_application"):
            raise RuntimeError(
                "Fully-Kiosk-Integration ist nicht verfügbar."
            )

        await self.hass.services.async_call(
            "fully_kiosk",
            "start_application",
            {
                "device_id": device_id,
                "application": "de.ozerov.fully",
            },
            blocking=True,
        )

    async def _async_load_url(self, url: str) -> None:
        device_id = self.entry.options.get(CONF_FULLY_DEVICE_ID)
        if not device_id:
            raise RuntimeError("Kein Fully-Kiosk-Gerät konfiguriert.")

        if not self.hass.services.has_service("fully_kiosk", "load_url"):
            raise RuntimeError(
                "Fully-Kiosk-Integration ist nicht verfügbar."
            )

        await self.hass.services.async_call(
            "fully_kiosk",
            "load_url",
            {"device_id": device_id, "url": url},
            blocking=True,
        )

    async def async_show_door_view(self) -> None:
        if not self.configured:
            self._set_status("nicht konfiguriert", "Türansicht")
            return

        try:
            self._set_status("aktiv", "Türansicht")
            await self._async_turn_screen(True)
            await self._async_start_fully()

            wake_ms = int(
                self.entry.options.get(CONF_WAKE_DELAY_MS, DEFAULT_WAKE_DELAY_MS)
            )
            await asyncio.sleep(max(0.0, wake_ms / 1000.0))

            url = self._absolute_url(
                self.entry.options.get(CONF_DOOR_PATH, DEFAULT_DOOR_PATH)
            )
            repeat_count = max(
                1,
                min(
                    4,
                    int(
                        self.entry.options.get(
                            CONF_RELOAD_COUNT, DEFAULT_RELOAD_COUNT
                        )
                    ),
                ),
            )
            repeat_delay_ms = int(
                self.entry.options.get(
                    CONF_RELOAD_DELAY_MS, DEFAULT_RELOAD_DELAY_MS
                )
            )

            for index in range(repeat_count):
                if index:
                    await self._async_start_fully()
                await self._async_load_url(url)
                if index + 1 < repeat_count:
                    await asyncio.sleep(max(0.0, repeat_delay_ms / 1000.0))

            self._set_status("türansicht", "Türansicht")
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.exception("SG150 tablet door-view control failed")
            self._set_status("fehler", "Türansicht", str(err))

    async def async_show_home_view(self) -> None:
        if not self.configured:
            self._set_status("nicht konfiguriert", "Startseite")
            return

        try:
            self._set_status("aktiv", "Startseite")
            await self._async_turn_screen(True)
            await self._async_start_fully()
            home_path = self.entry.options.get(CONF_HOME_PATH, DEFAULT_HOME_PATH)
            # v0.3.x used this placeholder although many HA installations do
            # not have such a dashboard. Keep existing users working.
            if home_path == "/dashboard-home/0":
                home_path = "/"
            url = self._absolute_url(home_path)
            await self._async_load_url(url)
            self._set_status("startseite", "Startseite")
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.exception("SG150 tablet home-view control failed")
            self._set_status("fehler", "Startseite", str(err))

    async def async_screen_off(self) -> None:
        try:
            await self._async_turn_screen(False)
            self._set_status("display aus", "Display aus")
        except Exception as err:
            _LOGGER.exception("SG150 tablet screen-off failed")
            self._set_status("fehler", "Display aus", str(err))

    def set_auto_enabled(self, enabled: bool) -> None:
        self.auto_enabled = enabled
        self._set_status("bereit", "Automatik an" if enabled else "Automatik aus")
