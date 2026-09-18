from __future__ import annotations

import asyncio

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

BUFFER_SIZE = 102400
CONNECT_TIMEOUT = 3
MAX_BUFFER_SIZE = 2_000_000


async def async_fetch_first_jpeg(
    hass: HomeAssistant,
    url: str,
    *,
    timeout: float = CONNECT_TIMEOUT,
) -> bytes | None:
    """Read the first complete JPEG from the SG150 MJPEG stream."""

    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(timeout):
            async with session.get(url) as response:
                response.raise_for_status()
                data = b""
                async for chunk in response.content.iter_chunked(BUFFER_SIZE):
                    data += chunk
                    jpg_end = data.find(b"\xff\xd9")
                    if jpg_end == -1:
                        if len(data) > MAX_BUFFER_SIZE:
                            return None
                        continue
                    jpg_start = data.find(b"\xff\xd8")
                    if jpg_start == -1:
                        continue
                    return data[jpg_start : jpg_end + 2]
    except (TimeoutError, aiohttp.ClientError, OSError):
        return None
    return None
