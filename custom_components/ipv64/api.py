"""HTTP helper utilities for interacting with the IPv64 API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import RETRY_ATTEMPTS, RETRY_DELAY, TIMEOUT

_LOGGER = logging.getLogger(__name__)


async def request_json(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    log_context: str | None = None,
    retry_attempts: int | None = None,
    retry_delay: float | None = None,
    timeout: float = TIMEOUT,
) -> dict[str, Any]:
    """Perform an IPv64 API request and return the parsed JSON response."""
    context = log_context or url
    last_error: Exception | None = None

    attempts = retry_attempts or RETRY_ATTEMPTS
    delay = retry_delay if retry_delay is not None else RETRY_DELAY

    for attempt in range(1, attempts + 1):
        try:
            async with session.request(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                json=json,
                timeout=timeout,
            ) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except aiohttp.ClientResponseError as error:  # pragma: no cover - requires API access
            last_error = error
            if attempt == attempts:
                raise
            _LOGGER.warning(
                "API request %s failed with status %s. Retrying (%d/%d)",
                context,
                error.status,
                attempt,
                attempts,
            )
        except (TimeoutError, aiohttp.ClientError) as error:  # pragma: no cover - requires API access
            last_error = error
            if attempt == attempts:
                raise
            _LOGGER.warning(
                "API request %s failed: %s. Retrying (%d/%d)",
                context,
                error,
                attempt,
                attempts,
            )

        await asyncio.sleep(delay)

    assert last_error is not None
    raise last_error
