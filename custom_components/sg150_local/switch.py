from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, RUNTIME_CONTROLLER
from .controller import SG150TabletController


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    controller: SG150TabletController = hass.data[DOMAIN][entry.entry_id][
        RUNTIME_CONTROLLER
    ]
    async_add_entities([SG150AutoTabletSwitch(entry, controller)])


class SG150AutoTabletSwitch(SwitchEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_name = "Automatische Türanzeige"
    _attr_icon = "mdi:tablet-cellphone"

    def __init__(
        self, entry: ConfigEntry, controller: SG150TabletController
    ) -> None:
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_auto_tablet"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Siedle SG150",
            manufacturer="Siedle",
            model="SG 150-0",
        )
        self._remove_listener = None

    @property
    def is_on(self) -> bool:
        return self._controller.auto_enabled

    async def async_turn_on(self, **kwargs) -> None:
        self._controller.set_auto_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._controller.set_auto_enabled(False)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        last = await self.async_get_last_state()
        if last is not None:
            self._controller.set_auto_enabled(last.state == "on")

        @callback
        def _update() -> None:
            self.async_write_ha_state()

        self._remove_listener = self._controller.add_listener(_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
