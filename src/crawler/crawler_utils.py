"""Utility functions for processing picture pages and generating reloaded URLs.

This module provides helper functions for extracting picture page URLs and modifying
them to include reloaded parameters.
"""

from urllib.parse import parse_qs, urlencode, urlparse

from bs4 import Tag


def get_picture_pages(containers: list[Tag]) -> list[str]:
    """Extract picture page URLs from a list of container elements."""
    return [
        container.get("href")
        for container in containers if "/s/" in container.get("href")
    ]


def generate_reloaded_page(picture_page: str, nl_value: str) -> str:
    """Generate a reloaded version of a picture page URL with an 'nl' parameter."""
    parsed_url = urlparse(picture_page)
    query_params = parse_qs(parsed_url.query)
    query_params["nl"] = nl_value
    return parsed_url._replace(query=urlencode(query_params, doseq=True)).geturl()
