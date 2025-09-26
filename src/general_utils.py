"""General utilities module.

This module provides utilities for fetching web pages, managing directories, and
clearing the terminal screen. It includes functions to handle common tasks such as
sending HTTP requests, parsing HTML, creating download directories, and clearing the
terminal, making it reusable across projects.
"""

import logging
import os
import sys

import requests
from bs4 import BeautifulSoup


def fetch_page(url: str, timeout: int = 10) -> BeautifulSoup:
    """Fetch the HTML content of a webpage."""
    # Create a new session per worker
    session = requests.Session()

    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    except requests.RequestException as req_err:
        message = f"Error fetching page {url}: {req_err}"
        logging.exception(message)
        sys.exit(1)


def clear_terminal() -> None:
    """Clear the terminal screen based on the operating system."""
    commands = {
        "nt": "cls",       # Windows
        "posix": "clear",  # macOS and Linux
    }

    command = commands.get(os.name)
    if command:
        os.system(command)  # noqa: S605
