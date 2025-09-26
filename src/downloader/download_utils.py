"""HTTP request utilities with retry logic.

This module provides functions for preparing HTTP headers and fetching URLs with retry
mechanisms and exponential backoff.
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from requests.exceptions import ConnectTimeout, RequestException, Timeout

from src.config import CONNECTION_TIMEOUT, prepare_user_agent

if TYPE_CHECKING:
    from requests import Response, Session

    from src.managers.live_manager import LiveManager


def prepare_headers(url: str) -> dict:
    """Prepare a random HTTP headers with a user-agent string for making requests."""
    host = urlparse(url).netloc
    user_agent = prepare_user_agent()
    return {
        "Host": host,
        "User-Agent": user_agent,
        "Accept": (
            "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5"
        ),
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Referer": "https://e-hentai.org/",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
    }


def fetch_with_retries(
    session: Session,
    url: str,
    live_manager: LiveManager,
    retries: int = 5,
) -> Response | None:
    """Fetch a URL with retry logic and exponential backoff."""
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=CONNECTION_TIMEOUT)
            response.raise_for_status()

        except ConnectTimeout as conn_timeout:
            live_manager.update_log(
                "ConnectTimeout",
                f"Connect timeout for {url}: {conn_timeout}. "
                "Retrying ({attempt + 1}/{retries})...",
            )

        except Timeout as timeout_err:
            live_manager.update_log(
                "Timeout error",
                f"Timeout for {url}: {timeout_err}. "
                "Retrying ({attempt + 1}/{retries})...",
            )

        except RequestException as req_err:
            live_manager.update_log(
                "Request failed",
                f"Request failed for {url}: {req_err}",
            )
            break

        else:
            return response

        if attempt < retries - 1:
            live_manager.update_log(
                "Fetch attempt failed",
                f"Fetch attemp failed for {url}. Retrying ({attempt + 1}/{retries})...",
            )
            delay = 2 ** (attempt + 1) + random.uniform(1, 2)  # noqa: S311
            time.sleep(delay)

    live_manager.update_log(
        "Fetch failed",
        f"Max retries reached. Could not fetch {url}.",
    )
    return None
