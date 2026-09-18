from __future__ import annotations

DOMAIN = "sg150_local"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_POLL_INTERVAL_MS = "poll_interval_ms"
CONF_OFF_CONFIRMATIONS = "off_confirmations"

CONF_FULLY_DEVICE_ID = "fully_device_id"
CONF_FULLY_SCREEN_ENTITY = "fully_screen_entity"
CONF_DOOR_PATH = "door_path"
CONF_HOME_PATH = "home_path"
CONF_AUTO_TABLET = "auto_tablet"
CONF_WAKE_DELAY_MS = "wake_delay_ms"
CONF_RELOAD_COUNT = "reload_count"
CONF_RELOAD_DELAY_MS = "reload_delay_ms"
CONF_RETURN_HOME = "return_home"
CONF_RETURN_DELAY_S = "return_delay_s"

CONF_USE_SIEDLE_APP = "use_siedle_app"
CONF_SIEDLE_APP_PACKAGE = "siedle_app_package"
CONF_SIEDLE_APP_START_COUNT = "siedle_app_start_count"
CONF_SIEDLE_APP_START_DELAY_MS = "siedle_app_start_delay_ms"

DEFAULT_HOST = "192.168.178.97"
DEFAULT_PORT = 20502
DEFAULT_POLL_INTERVAL_MS = 200
DEFAULT_OFF_CONFIRMATIONS = 5

DEFAULT_DOOR_PATH = "/dashboard-tuersprechanlage/live"
DEFAULT_HOME_PATH = "/"
DEFAULT_AUTO_TABLET = True
DEFAULT_WAKE_DELAY_MS = 300
DEFAULT_RELOAD_COUNT = 2
DEFAULT_RELOAD_DELAY_MS = 700
DEFAULT_RETURN_HOME = True
DEFAULT_RETURN_DELAY_S = 2

DEFAULT_USE_SIEDLE_APP = True
DEFAULT_SIEDLE_APP_PACKAGE = "de.siedle.sus"
DEFAULT_SIEDLE_APP_START_COUNT = 2
DEFAULT_SIEDLE_APP_START_DELAY_MS = 500

EVENT_DOORBELL = "sg150_local_doorbell"
EVENT_VIDEO_ENDED = "sg150_local_video_ended"

RUNTIME_MONITOR = "monitor"
RUNTIME_CONTROLLER = "controller"
