"""Keep the Render free-tier service from going to sleep.

Render spins a free web service down after roughly 15 minutes without inbound
HTTP traffic, and the cold start that follows takes ~50 seconds. This task calls
the service's own public URL every 14 minutes, which reaches Render's load
balancer from the outside and therefore counts as real traffic.

Two things worth knowing:

* This only *prevents* sleep. It cannot wake a service that is already asleep,
  because nothing is running to send the ping. The GitHub Actions cron in
  .github/workflows/keepalive.yml covers that case from outside.
* It is inert unless the service is running on Render (``keepalive_active``),
  so local development never sends stray requests.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

import httpx

from app.core.config import Settings

logger = logging.getLogger("app.keepalive")

KEEPALIVE_PATH = "/keepalive"


async def _ping_forever(settings: Settings) -> None:
    url = f"{settings.PUBLIC_BASE_URL}{KEEPALIVE_PATH}"
    interval = settings.KEEPALIVE_INTERVAL_SECONDS

    logger.info("Keep-alive enabled: pinging %s every %ss", url, interval)

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            # Sleep first: the service is obviously awake at startup.
            await asyncio.sleep(interval)
            try:
                response = await client.get(url)
                logger.info("Keep-alive ping -> %s", response.status_code)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # a failed ping must never kill the loop
                logger.warning("Keep-alive ping failed: %s", exc)


def start(settings: Settings) -> asyncio.Task[None] | None:
    """Start the pinger, or return None when it does not apply."""
    if not settings.keepalive_active:
        logger.debug(
            "Keep-alive inactive (enabled=%s, production=%s, public_url=%r)",
            settings.KEEPALIVE_ENABLED,
            settings.is_production,
            settings.PUBLIC_BASE_URL,
        )
        return None

    return asyncio.create_task(_ping_forever(settings), name="keepalive")


async def stop(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
