"""HTTP request utilities with retry logic.

This module provides functions for preparing HTTP headers and fetching URLs with retry
mechanisms and exponential backoff.
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from requests.exceptions import ConnectTimeout, HTTPError, RequestException, Timeout

from src.config import CONNECTION_TIMEOUT, RATE_LIMIT_SLEEPING_TIME, prepare_user_agent

if TYPE_CHECKING:
    from requests import Response, Session

    from src.managers.live_manager import LiveManager


def prepare_headers(url: str) -> dict:
    """Prepare a random HTTP headers with a user-agent string for making requests."""
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    referer_base = f"{parsed_url.scheme}://{host}/" if parsed_url.scheme and host else "https://e-hentai.org/"
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
        "Referer": referer_base,
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
    }


def fetch_with_retries(
    session: Session,
    url: str,
    live_manager: LiveManager,
    retries: int = 5,
    headers: dict | None = None,
) -> Response | None:
    """Fetch a URL with retry logic and exponential backoff/rate-limit handling."""
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=CONNECTION_TIMEOUT, headers=headers)
            response.raise_for_status()

        except HTTPError as http_err:
            status_code = (
                http_err.response.status_code
                if http_err.response is not None
                else 0
            )
            if status_code in (429, 509):
                live_manager.update_log(
                    "Rate limit",
                    f"Rate limit ({status_code}) hit for {url}. "
                    f"Sleeping for {RATE_LIMIT_SLEEPING_TIME} seconds...",
                )
                time.sleep(RATE_LIMIT_SLEEPING_TIME)
                continue
            else:
                live_manager.update_log(
                    "Request failed",
                    f"HTTP error {status_code} for {url}: {http_err}",
                )
                break

        except ConnectTimeout as conn_timeout:
            live_manager.update_log(
                "ConnectTimeout",
                f"Connect timeout for {url}: {conn_timeout}. "
                f"Retrying ({attempt + 1}/{retries})...",
            )

        except Timeout as timeout_err:
            live_manager.update_log(
                "Timeout error",
                f"Timeout for {url}: {timeout_err}. "
                f"Retrying ({attempt + 1}/{retries})...",
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
                f"Fetch attempt failed for {url}. Retrying ({attempt + 1}/{retries})...",
            )
            delay = 2 ** (attempt + 1) + random.uniform(1, 2)  # noqa: S311
            time.sleep(delay)

    live_manager.update_log(
        "Fetch failed",
        f"Max retries reached. Could not fetch {url}.",
    )
    return None
