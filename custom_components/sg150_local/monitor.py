from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import EVENT_DOORBELL, EVENT_VIDEO_ENDED

_LOGGER = logging.getLogger(__name__)


class SG150PortMonitor:
    """Fast local monitor for the SG150 transient MJPEG port."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        poll_interval_ms: int,
        off_confirmations: int,
    ) -> None:
        self.hass = hass
        self.host = host
        self.port = port
        self.poll_interval = max(0.05, poll_interval_ms / 1000.0)
        self.off_confirmations = max(1, off_confirmations)

        self.is_open = False
        self.last_opened_at: datetime | None = None
        self.last_closed_at: datetime | None = None
        self.last_probe_at: datetime | None = None
        self.probe_count = 0
        self._failures = 0
        self._listeners: set[Callable[[], None]] = set()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    @property
    def task_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(callback)

        def remove() -> None:
            self._listeners.discard(callback)

        return remove

    async def async_start(self, entry: ConfigEntry) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = entry.async_create_background_task(
            self.hass,
            self._run(),
            "SG150 local port monitor",
        )

    async def async_stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _probe(self) -> bool:
        writer = None
        try:
            # The SG150 MJPEG port only exists during the transient door-video
            # session. A refused connection is therefore the normal idle state.
            async with asyncio.timeout(min(0.2, max(0.08, self.poll_interval))):
                _reader, writer = await asyncio.open_connection(self.host, self.port)
            return True
        except (TimeoutError, OSError):
            return False
        finally:
            if writer is not None:
                # Important: never let a diagnostic TCP probe block the monitor
                # while waiting for the SG150 to finish the TCP close handshake.
                # Some SG150 video sessions keep the socket teardown pending.
                writer.close()
                try:
                    async with asyncio.timeout(0.05):
                        await writer.wait_closed()
                except (TimeoutError, OSError):
                    pass

    def _notify(self) -> None:
        for callback in tuple(self._listeners):
            try:
                callback()
            except Exception:
                # One entity/listener must never be able to terminate the
                # long-running port monitor.
                _LOGGER.exception("SG150 monitor listener failed")

    def _set_open(self, value: bool) -> None:
        if value == self.is_open:
            return

        self.is_open = value
        now = datetime.now(timezone.utc)

        if value:
            self.last_opened_at = now
            self.hass.bus.async_fire(
                EVENT_DOORBELL,
                {
                    "host": self.host,
                    "port": self.port,
                    "detected_at": now.isoformat(),
                },
            )
            _LOGGER.info("SG150 video session detected on %s:%s", self.host, self.port)
        else:
            self.last_closed_at = now
            self.hass.bus.async_fire(
                EVENT_VIDEO_ENDED,
                {
                    "host": self.host,
                    "port": self.port,
                    "ended_at": now.isoformat(),
                },
            )
            _LOGGER.info("SG150 video session ended on %s:%s", self.host, self.port)

        self._notify()

    async def _run(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    self.probe_count += 1
                    self.last_probe_at = datetime.now(timezone.utc)
                    open_now = await self._probe()

                    if open_now:
                        self._failures = 0
                        self._set_open(True)
                    elif self.is_open:
                        self._failures += 1
                        if self._failures >= self.off_confirmations:
                            self._failures = 0
                            self._set_open(False)
                    else:
                        self._failures = 0
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # A transient unexpected error must not permanently kill
                    # doorbell detection. Log it and continue with the next probe.
                    _LOGGER.exception("Unexpected SG150 port-monitor probe error")

                try:
                    await asyncio.wait_for(
                        self._stop.wait(), timeout=self.poll_interval
                    )
                except TimeoutError:
                    pass
        except asyncio.CancelledError:
            raise
