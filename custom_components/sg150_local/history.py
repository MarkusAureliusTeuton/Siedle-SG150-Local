from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import hashlib
import logging
from pathlib import Path
import sqlite3

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HISTORY_DELAY_S,
    CONF_HISTORY_ENABLED,
    CONF_HISTORY_MAX_IMAGES,
    CONF_HISTORY_RETENTION_DAYS,
    CONF_HISTORY_STORAGE_DIR,
    DEFAULT_HISTORY_DELAY_S,
    DEFAULT_HISTORY_ENABLED,
    DEFAULT_HISTORY_MAX_IMAGES,
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_HISTORY_STORAGE_DIR,
)
from .mjpeg import async_fetch_first_jpeg
from .monitor import SG150PortMonitor

_LOGGER = logging.getLogger(__name__)

DB_FILENAME = "history.sqlite3"


class SG150HistoryRecorder:
    """Store one visitor image per SG150 video session with SQLite metadata."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        monitor: SG150PortMonitor,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.monitor = monitor
        self._listeners: set[Callable[[], None]] = set()
        self._remove_monitor_listener: Callable[[], None] | None = None
        self._capture_task: asyncio.Task | None = None

        self.image_count = 0
        self.latest_path: str | None = None
        self.latest_timestamp: datetime | None = None
        self.last_capture_source = ""
        self.last_error = ""

    @property
    def enabled(self) -> bool:
        return bool(
            self.entry.options.get(
                CONF_HISTORY_ENABLED, DEFAULT_HISTORY_ENABLED
            )
        )

    @property
    def capture_delay(self) -> float:
        return float(
            self.entry.options.get(CONF_HISTORY_DELAY_S, DEFAULT_HISTORY_DELAY_S)
        )

    @property
    def retention_days(self) -> int:
        return int(
            self.entry.options.get(
                CONF_HISTORY_RETENTION_DAYS, DEFAULT_HISTORY_RETENTION_DAYS
            )
        )

    @property
    def max_images(self) -> int:
        return int(
            self.entry.options.get(
                CONF_HISTORY_MAX_IMAGES, DEFAULT_HISTORY_MAX_IMAGES
            )
        )

    @property
    def storage_root(self) -> Path:
        raw = str(
            self.entry.options.get(
                CONF_HISTORY_STORAGE_DIR, DEFAULT_HISTORY_STORAGE_DIR
            )
        ).strip()
        parts = [part for part in raw.replace("\\", "/").split("/") if part]
        if not parts or any(part == ".." for part in parts):
            parts = [DEFAULT_HISTORY_STORAGE_DIR]
        return Path(self.hass.config.path(*parts))

    @property
    def database_path(self) -> Path:
        return self.storage_root / DB_FILENAME

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(listener)

        def remove() -> None:
            self._listeners.discard(listener)

        return remove

    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            try:
                listener()
            except Exception:
                _LOGGER.exception("SG150 history listener failed")

    async def async_start(self, entry: ConfigEntry) -> None:
        await self.hass.async_add_executor_job(self._init_database)

        @callback
        def _monitor_changed() -> None:
            if self.monitor.is_open and self.enabled:
                self._schedule_automatic_capture()

        self._remove_monitor_listener = self.monitor.add_listener(_monitor_changed)

    async def async_stop(self) -> None:
        if self._remove_monitor_listener is not None:
            self._remove_monitor_listener()
            self._remove_monitor_listener = None
        if self._capture_task is not None and not self._capture_task.done():
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
        self._capture_task = None

    def _schedule_automatic_capture(self) -> None:
        if self._capture_task is not None and not self._capture_task.done():
            return
        self._capture_task = self.hass.async_create_task(
            self._async_delayed_capture(), "SG150 visitor image capture"
        )

    async def _async_delayed_capture(self) -> None:
        try:
            await asyncio.sleep(max(0.0, self.capture_delay))
            if self.monitor.is_open:
                await self.async_capture("automatic")
        except asyncio.CancelledError:
            raise

    async def async_capture(self, source: str = "manual") -> bool:
        """Capture and archive one JPEG while the SG150 video session is active."""

        if not self.enabled:
            self.last_error = "Bildhistorie ist deaktiviert."
            self._notify()
            return False
        if not self.monitor.is_open:
            self.last_error = "Keine aktive SG150-Videosession."
            self._notify()
            return False

        url = f"http://{self.monitor.host}:{self.monitor.port}/"
        jpeg: bytes | None = None
        for attempt in range(3):
            jpeg = await async_fetch_first_jpeg(self.hass, url, timeout=3)
            if jpeg:
                break
            if attempt < 2:
                await asyncio.sleep(0.25)

        if not jpeg:
            self.last_error = "Kein vollständiges JPEG aus dem SG150-Stream empfangen."
            self._notify()
            return False

        captured_at = datetime.now(timezone.utc)
        try:
            result = await self.hass.async_add_executor_job(
                self._save_image,
                jpeg,
                captured_at,
                source,
            )
        except Exception as err:
            _LOGGER.exception("Saving SG150 visitor image failed")
            self.last_error = str(err)
            self._notify()
            return False

        self.latest_path = result["path"]
        self.latest_timestamp = captured_at
        self.image_count = result["count"]
        self.last_capture_source = source
        self.last_error = ""
        self._notify()
        return True

    async def async_latest_image(self) -> bytes | None:
        path = self.latest_path
        if not path:
            return None
        file_path = Path(path)
        if not file_path.is_file():
            return None
        try:
            return await self.hass.async_add_executor_job(file_path.read_bytes)
        except OSError:
            return None

    def _init_database(self) -> None:
        root = self.storage_root
        root.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as db:
            self._ensure_schema(db)
            row = db.execute(
                "SELECT captured_at, path FROM images ORDER BY captured_at DESC LIMIT 1"
            ).fetchone()
            self.image_count = int(
                db.execute("SELECT COUNT(*) FROM images").fetchone()[0]
            )
        if row:
            self.latest_timestamp = datetime.fromisoformat(row[0])
            self.latest_path = row[1]

    def _ensure_schema(self, db: sqlite3.Connection) -> None:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL,
                local_time TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_images_captured_at ON images(captured_at)"
        )
        db.commit()

    def _save_image(
        self,
        jpeg: bytes,
        captured_at: datetime,
        source: str,
    ) -> dict[str, object]:
        root = self.storage_root
        root.mkdir(parents=True, exist_ok=True)
        local_time = dt_util.as_local(captured_at)
        folder = (
            root
            / local_time.strftime("%Y")
            / local_time.strftime("%m")
            / local_time.strftime("%d")
        )
        folder.mkdir(parents=True, exist_ok=True)
        filename = local_time.strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3] + ".jpg"
        path = folder / filename
        temp_path = path.with_suffix(".jpg.tmp")
        temp_path.write_bytes(jpeg)
        temp_path.replace(path)
        digest = hashlib.sha256(jpeg).hexdigest()

        with sqlite3.connect(self.database_path) as db:
            self._ensure_schema(db)
            db.execute(
                """
                INSERT INTO images (
                    captured_at, local_time, path, size_bytes, sha256, source
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    captured_at.isoformat(),
                    local_time.isoformat(),
                    str(path),
                    len(jpeg),
                    digest,
                    source,
                ),
            )
            self._prune(db, captured_at)
            count = int(db.execute("SELECT COUNT(*) FROM images").fetchone()[0])
            db.commit()

        return {"path": str(path), "count": count}

    def _prune(self, db: sqlite3.Connection, now: datetime) -> None:
        retention_days = max(1, min(3650, self.retention_days))
        cutoff = (now - timedelta(days=retention_days)).isoformat()
        old_rows = db.execute(
            "SELECT id, path FROM images WHERE captured_at < ? ORDER BY captured_at ASC",
            (cutoff,),
        ).fetchall()
        self._delete_rows(db, old_rows)

        max_images = max(1, min(100000, self.max_images))
        count = int(db.execute("SELECT COUNT(*) FROM images").fetchone()[0])
        excess = max(0, count - max_images)
        if excess:
            rows = db.execute(
                "SELECT id, path FROM images ORDER BY captured_at ASC LIMIT ?",
                (excess,),
            ).fetchall()
            self._delete_rows(db, rows)

    @staticmethod
    def _delete_rows(db: sqlite3.Connection, rows: list[tuple[int, str]]) -> None:
        for row_id, path in rows:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                _LOGGER.warning("Could not delete expired SG150 image %s", path)
            db.execute("DELETE FROM images WHERE id = ?", (row_id,))
