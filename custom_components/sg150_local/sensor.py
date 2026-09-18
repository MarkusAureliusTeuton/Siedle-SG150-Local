from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_RETURN_HOME,
    DEFAULT_RETURN_HOME,
    DOMAIN,
    RUNTIME_CONTROLLER,
)
from .controller import SG150TabletController


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    controller: SG150TabletController = hass.data[DOMAIN][entry.entry_id][
        RUNTIME_CONTROLLER
    ]
    async_add_entities([SG150TabletStatusSensor(entry, controller)])


class SG150TabletStatusSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Tabletsteuerung"
    _attr_icon = "mdi:tablet-dashboard"

    def __init__(
        self, entry: ConfigEntry, controller: SG150TabletController
    ) -> None:
        self._entry = entry
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_tablet_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Siedle SG150",
            manufacturer="Siedle",
            model="SG 150-0",
        )
        self._remove_listener = None

    @property
    def native_value(self) -> str:
        if not self._controller.configured:
            return "nicht konfiguriert"
        return self._controller.state

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "automatic": self._controller.auto_enabled,
            "configured": self._controller.configured,
            "monitor_open": self._controller.monitor.is_open,
            "display_target": (
                "siedle_app" if self._controller.use_siedle_app else "ha_door_view"
            ),
            "siedle_app_package": self._controller.siedle_app_package,
            "return_to_fully": self._entry.options.get(
                CONF_RETURN_HOME, DEFAULT_RETURN_HOME
            ),
            "trigger_count": self._controller.trigger_count,
            "auto_start_count": self._controller.auto_start_count,
            "last_trigger_source": self._controller.last_trigger_source or None,
            "last_trigger_at": (
                self._controller.last_trigger_at.isoformat()
                if self._controller.last_trigger_at
                else None
            ),
            "last_action": self._controller.last_action,
            "last_error": self._controller.last_error or None,
        }

    async def async_added_to_hass(self) -> None:
        @callback
        def _update() -> None:
            self.async_write_ha_state()

        self._remove_listener = self._controller.add_listener(_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
