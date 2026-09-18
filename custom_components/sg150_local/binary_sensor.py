from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, RUNTIME_MONITOR
from .monitor import SG150PortMonitor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    monitor: SG150PortMonitor = hass.data[DOMAIN][entry.entry_id][RUNTIME_MONITOR]
    async_add_entities([SG150DoorbellBinarySensor(entry, monitor)])


class SG150DoorbellBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Türruf / Videosession"
    _attr_icon = "mdi:doorbell-video"

    def __init__(self, entry: ConfigEntry, monitor: SG150PortMonitor) -> None:
        self._entry = entry
        self._monitor = monitor
        self._attr_unique_id = f"{entry.entry_id}_doorbell"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Siedle SG150",
            manufacturer="Siedle",
            model="SG 150-0",
        )
        self._remove_listener = None

    @property
    def is_on(self) -> bool:
        return self._monitor.is_open

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "host": self._monitor.host,
            "port": self._monitor.port,
            "monitor_running": self._monitor.task_running,
            "probe_count": self._monitor.probe_count,
            "last_probe_at": (
                self._monitor.last_probe_at.isoformat()
                if self._monitor.last_probe_at
                else None
            ),
            "last_opened_at": (
                self._monitor.last_opened_at.isoformat()
                if self._monitor.last_opened_at
                else None
            ),
            "last_closed_at": (
                self._monitor.last_closed_at.isoformat()
                if self._monitor.last_closed_at
                else None
            ),
        }

    async def async_added_to_hass(self) -> None:
        @callback
        def _update() -> None:
            self.async_write_ha_state()

        self._remove_listener = self._monitor.add_listener(_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
