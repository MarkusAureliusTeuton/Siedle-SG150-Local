from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_TABLET,
    CONF_DOOR_PATH,
    CONF_FULLY_DEVICE_ID,
    CONF_FULLY_SCREEN_ENTITY,
    CONF_HOME_PATH,
    CONF_HISTORY_DELAY_S,
    CONF_HISTORY_ENABLED,
    CONF_HISTORY_MAX_IMAGES,
    CONF_HISTORY_RETENTION_DAYS,
    CONF_HISTORY_STORAGE_DIR,
    CONF_HOST,
    CONF_OFF_CONFIRMATIONS,
    CONF_POLL_INTERVAL_MS,
    CONF_PORT,
    CONF_RELOAD_COUNT,
    CONF_RELOAD_DELAY_MS,
    CONF_RETURN_DELAY_S,
    CONF_RETURN_HOME,
    CONF_SIEDLE_APP_PACKAGE,
    CONF_SIEDLE_APP_START_COUNT,
    CONF_SIEDLE_APP_START_DELAY_MS,
    CONF_USE_SIEDLE_APP,
    CONF_WAKE_DELAY_MS,
    DEFAULT_AUTO_TABLET,
    DEFAULT_DOOR_PATH,
    DEFAULT_HOME_PATH,
    DEFAULT_HISTORY_DELAY_S,
    DEFAULT_HISTORY_ENABLED,
    DEFAULT_HISTORY_MAX_IMAGES,
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_HISTORY_STORAGE_DIR,
    DEFAULT_HOST,
    DEFAULT_OFF_CONFIRMATIONS,
    DEFAULT_POLL_INTERVAL_MS,
    DEFAULT_PORT,
    DEFAULT_RELOAD_COUNT,
    DEFAULT_RELOAD_DELAY_MS,
    DEFAULT_RETURN_DELAY_S,
    DEFAULT_RETURN_HOME,
    DEFAULT_SIEDLE_APP_PACKAGE,
    DEFAULT_SIEDLE_APP_START_COUNT,
    DEFAULT_SIEDLE_APP_START_DELAY_MS,
    DEFAULT_USE_SIEDLE_APP,
    DEFAULT_WAKE_DELAY_MS,
    DOMAIN,
)


class SG150ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Siedle SG150",
                data={
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_POLL_INTERVAL_MS: user_input[CONF_POLL_INTERVAL_MS],
                    CONF_OFF_CONFIRMATIONS: user_input[CONF_OFF_CONFIRMATIONS],
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(
                    CONF_POLL_INTERVAL_MS,
                    default=DEFAULT_POLL_INTERVAL_MS,
                ): vol.All(vol.Coerce(int), vol.Range(min=50, max=2000)),
                vol.Required(
                    CONF_OFF_CONFIRMATIONS,
                    default=DEFAULT_OFF_CONFIRMATIONS,
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SG150OptionsFlow()


class SG150OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        options = dict(self.config_entry.options)

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        fully_device_marker = (
            vol.Optional(
                CONF_FULLY_DEVICE_ID,
                description={"suggested_value": options[CONF_FULLY_DEVICE_ID]},
            )
            if CONF_FULLY_DEVICE_ID in options
            else vol.Optional(CONF_FULLY_DEVICE_ID)
        )
        fully_screen_marker = (
            vol.Optional(
                CONF_FULLY_SCREEN_ENTITY,
                description={"suggested_value": options[CONF_FULLY_SCREEN_ENTITY]},
            )
            if CONF_FULLY_SCREEN_ENTITY in options
            else vol.Optional(CONF_FULLY_SCREEN_ENTITY)
        )

        schema = vol.Schema(
            {
                fully_device_marker: selector.DeviceSelector(
                    {"filter": {"integration": "fully_kiosk"}}
                ),
                fully_screen_marker: selector.EntitySelector(
                    {
                        "filter": {
                            "integration": "fully_kiosk",
                            "domain": "switch",
                        }
                    }
                ),
                vol.Required(
                    CONF_AUTO_TABLET,
                    default=options.get(CONF_AUTO_TABLET, DEFAULT_AUTO_TABLET),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_USE_SIEDLE_APP,
                    default=options.get(
                        CONF_USE_SIEDLE_APP, DEFAULT_USE_SIEDLE_APP
                    ),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_SIEDLE_APP_PACKAGE,
                    default=options.get(
                        CONF_SIEDLE_APP_PACKAGE, DEFAULT_SIEDLE_APP_PACKAGE
                    ),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_WAKE_DELAY_MS,
                    default=options.get(CONF_WAKE_DELAY_MS, DEFAULT_WAKE_DELAY_MS),
                ): selector.NumberSelector(
                    {
                        "min": 0,
                        "max": 3000,
                        "step": 50,
                        "mode": "box",
                    }
                ),
                vol.Required(
                    CONF_SIEDLE_APP_START_COUNT,
                    default=options.get(
                        CONF_SIEDLE_APP_START_COUNT,
                        DEFAULT_SIEDLE_APP_START_COUNT,
                    ),
                ): selector.NumberSelector(
                    {
                        "min": 1,
                        "max": 4,
                        "step": 1,
                        "mode": "box",
                    }
                ),
                vol.Required(
                    CONF_SIEDLE_APP_START_DELAY_MS,
                    default=options.get(
                        CONF_SIEDLE_APP_START_DELAY_MS,
                        DEFAULT_SIEDLE_APP_START_DELAY_MS,
                    ),
                ): selector.NumberSelector(
                    {
                        "min": 0,
                        "max": 3000,
                        "step": 50,
                        "mode": "box",
                    }
                ),
                vol.Required(
                    CONF_DOOR_PATH,
                    default=options.get(CONF_DOOR_PATH, DEFAULT_DOOR_PATH),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_RELOAD_COUNT,
                    default=options.get(CONF_RELOAD_COUNT, DEFAULT_RELOAD_COUNT),
                ): selector.NumberSelector(
                    {
                        "min": 1,
                        "max": 4,
                        "step": 1,
                        "mode": "box",
                    }
                ),
                vol.Required(
                    CONF_RELOAD_DELAY_MS,
                    default=options.get(
                        CONF_RELOAD_DELAY_MS, DEFAULT_RELOAD_DELAY_MS
                    ),
                ): selector.NumberSelector(
                    {
                        "min": 100,
                        "max": 3000,
                        "step": 50,
                        "mode": "box",
                    }
                ),
                vol.Required(
                    CONF_RETURN_HOME,
                    default=options.get(CONF_RETURN_HOME, DEFAULT_RETURN_HOME),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_RETURN_DELAY_S,
                    default=options.get(CONF_RETURN_DELAY_S, DEFAULT_RETURN_DELAY_S),
                ): selector.NumberSelector(
                    {
                        "min": 0,
                        "max": 300,
                        "step": 1,
                        "mode": "box",
                    }
                ),
                vol.Required(
                    CONF_HOME_PATH,
                    default=options.get(CONF_HOME_PATH, DEFAULT_HOME_PATH),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_HISTORY_ENABLED,
                    default=options.get(
                        CONF_HISTORY_ENABLED, DEFAULT_HISTORY_ENABLED
                    ),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_HISTORY_DELAY_S,
                    default=options.get(
                        CONF_HISTORY_DELAY_S, DEFAULT_HISTORY_DELAY_S
                    ),
                ): selector.NumberSelector(
                    {
                        "min": 0,
                        "max": 30,
                        "step": 0.5,
                        "mode": "box",
                    }
                ),
                vol.Required(
                    CONF_HISTORY_RETENTION_DAYS,
                    default=options.get(
                        CONF_HISTORY_RETENTION_DAYS,
                        DEFAULT_HISTORY_RETENTION_DAYS,
                    ),
                ): selector.NumberSelector(
                    {
                        "min": 1,
                        "max": 3650,
                        "step": 1,
                        "mode": "box",
                    }
                ),
                vol.Required(
                    CONF_HISTORY_MAX_IMAGES,
                    default=options.get(
                        CONF_HISTORY_MAX_IMAGES, DEFAULT_HISTORY_MAX_IMAGES
                    ),
                ): selector.NumberSelector(
                    {
                        "min": 1,
                        "max": 100000,
                        "step": 1,
                        "mode": "box",
                    }
                ),
                vol.Required(
                    CONF_HISTORY_STORAGE_DIR,
                    default=options.get(
                        CONF_HISTORY_STORAGE_DIR, DEFAULT_HISTORY_STORAGE_DIR
                    ),
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
