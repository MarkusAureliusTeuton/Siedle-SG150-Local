from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HOST,
    CONF_OFF_CONFIRMATIONS,
    CONF_POLL_INTERVAL_MS,
    CONF_PORT,
    DEFAULT_OFF_CONFIRMATIONS,
    DEFAULT_POLL_INTERVAL_MS,
    DEFAULT_PORT,
    DOMAIN,
    RUNTIME_CONTROLLER,
    RUNTIME_MONITOR,
)
from .controller import SG150TabletController
from .monitor import SG150PortMonitor

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    poll_ms = entry.data.get(CONF_POLL_INTERVAL_MS, DEFAULT_POLL_INTERVAL_MS)
    off_confirmations = entry.data.get(
        CONF_OFF_CONFIRMATIONS, DEFAULT_OFF_CONFIRMATIONS
    )

    monitor = SG150PortMonitor(
        hass,
        host,
        port,
        poll_ms,
        off_confirmations,
    )
    controller = SG150TabletController(hass, entry, monitor)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        RUNTIME_MONITOR: monitor,
        RUNTIME_CONTROLLER: controller,
    }

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await monitor.async_start(entry)
    await controller.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        runtime = hass.data[DOMAIN].pop(entry.entry_id)
        await runtime[RUNTIME_CONTROLLER].async_stop()
        await runtime[RUNTIME_MONITOR].async_stop()
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
