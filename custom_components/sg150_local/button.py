from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, RUNTIME_CONTROLLER, RUNTIME_HISTORY
from .controller import SG150TabletController
from .history import SG150HistoryRecorder


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    controller: SG150TabletController = runtime[RUNTIME_CONTROLLER]
    history: SG150HistoryRecorder = runtime[RUNTIME_HISTORY]
    async_add_entities(
        [
            SG150TabletButton(
                entry,
                controller,
                "Türansicht anzeigen",
                "mdi:doorbell-video",
                "show_door",
                controller.async_show_door_view,
            ),
            SG150TabletButton(
                entry,
                controller,
                "Startseite anzeigen",
                "mdi:home",
                "show_home",
                controller.async_show_home_view,
            ),
            SG150TabletButton(
                entry,
                controller,
                "Tablet Display aus",
                "mdi:tablet-off",
                "screen_off",
                controller.async_screen_off,
            ),
            SG150HistoryCaptureButton(entry, history),
        ]
    )


class SG150TabletButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        controller: SG150TabletController,
        name: str,
        icon: str,
        key: str,
        action: Callable[[], Awaitable[None]],
    ) -> None:
        self._controller = controller
        self._action = action
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Siedle SG150",
            manufacturer="Siedle",
            model="SG 150-0",
        )

    @property
    def available(self) -> bool:
        return self._controller.configured

    async def async_press(self) -> None:
        await self._action()


class SG150HistoryCaptureButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Besucherbild jetzt speichern"
    _attr_icon = "mdi:camera-plus"

    def __init__(self, entry: ConfigEntry, history: SG150HistoryRecorder) -> None:
        self._history = history
        self._attr_unique_id = f"{entry.entry_id}_capture_visitor_image"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Siedle SG150",
            manufacturer="Siedle",
            model="SG 150-0",
        )

    @property
    def available(self) -> bool:
        return self._history.enabled and self._history.monitor.is_open

    async def async_press(self) -> None:
        await self._history.async_capture("manual")
