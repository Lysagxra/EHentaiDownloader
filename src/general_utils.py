"""General utilities module.

This module provides utilities for fetching web pages, managing directories, and
clearing the terminal screen. It includes functions to handle common tasks such as
sending HTTP requests, parsing HTML, creating download directories, and clearing the
terminal, making it reusable across projects.
"""

import logging
import os
import random
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from src.config import prepare_user_agent

# Cache cookies to avoid repeated disk reads
_cached_cookies = None


def _compact_text(value: str, limit: int = 240) -> str:
    """Normalize whitespace and shorten diagnostic text."""
    compacted = " ".join(value.split())
    return compacted[:limit] if len(compacted) <= limit else f"{compacted[:limit]}..."


def _extract_page_details(html: str) -> tuple[str, str]:
    """Extract page title and body text for diagnostics."""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""
    body_text = soup.body.get_text(" ", strip=True) if soup.body else ""
    return page_title, body_text


def _classify_page_problem(
    url: str,
    status_code: int,
    html: str,
    has_cookies: bool,
) -> str | None:
    """Return a precise human-readable diagnosis when a page indicates access issues."""
    page_title, body_text = _extract_page_details(html)
    lowered_title = page_title.lower()
    lowered_body = body_text.lower()
    lowered_html = html.lower()
    snippet_source = body_text or html
    snippet = _compact_text(snippet_source) if snippet_source else "Empty response"

    if "temporarily banned" in lowered_body or "ip address has been" in lowered_body:
        return (
            "Motivo: IP limitato o temporaneamente bannato da E-Hentai. "
            f"HTTP {status_code}. Titolo pagina: {page_title or 'N/A'}. Snippet: {snippet}"
        )

    if status_code in (429, 509) or "bandwidth exceeded" in lowered_body or "rate limit" in lowered_body:
        return (
            "Motivo: rate limit del sito raggiunto. "
            f"HTTP {status_code}. Titolo pagina: {page_title or 'N/A'}. Snippet: {snippet}"
        )

    if "sad panda" in lowered_title or "exhentai" in url.lower() and ("sad panda" in lowered_body or "sad panda" in lowered_html):
        return (
            "Motivo: accesso ExHentai negato; cookie mancanti, scaduti o non validi. "
            f"HTTP {status_code}. Titolo pagina: {page_title or 'N/A'}. Snippet: {snippet}"
        )

    if "login" in lowered_title or "please log in" in lowered_body or "you must be logged in" in lowered_body:
        return (
            "Motivo: autenticazione richiesta; cookie mancanti o scaduti. "
            f"HTTP {status_code}. Titolo pagina: {page_title or 'N/A'}. Snippet: {snippet}"
        )

    if "captcha" in lowered_body or "automated queries" in lowered_body or "check your browser" in lowered_body:
        return (
            "Motivo: protezione anti-bot o challenge del sito. "
            f"HTTP {status_code}. Titolo pagina: {page_title or 'N/A'}. Snippet: {snippet}"
        )

    if status_code == 404:
        return (
            "Motivo: URL non valido, scaduto o contenuto rimosso. "
            f"HTTP {status_code}. Titolo pagina: {page_title or 'N/A'}. Snippet: {snippet}"
        )

    if status_code == 403:
        reason = "cookie scaduti/non validi oppure accesso/IP limitato" if has_cookies else "cookie mancanti oppure accesso negato dal sito"
        return (
            f"Motivo: {reason}. "
            f"HTTP {status_code}. Titolo pagina: {page_title or 'N/A'}. Snippet: {snippet}"
        )

    if status_code >= 400:
        return (
            "Motivo: errore HTTP restituito dal sito. "
            f"HTTP {status_code}. Titolo pagina: {page_title or 'N/A'}. Snippet: {snippet}"
        )

    if "e-hentai galleries" == lowered_title and "forums" not in lowered_body and "gallery" not in lowered_body and "thumbnail" not in lowered_body:
        return (
            "Motivo: pagina anomala o incompleta restituita dal sito. "
            f"HTTP {status_code}. Titolo pagina: {page_title or 'N/A'}. Snippet: {snippet}"
        )

    return None


def _build_request_error_message(
    url: str,
    response: requests.Response | None,
    error: requests.RequestException,
    has_cookies: bool,
) -> str:
    """Build a detailed request failure message with the most likely cause."""
    if response is not None:
        diagnosis = _classify_page_problem(
            url=url,
            status_code=response.status_code,
            html=response.text,
            has_cookies=has_cookies,
        )
        if diagnosis:
            return f"Error fetching page {url}: {diagnosis}"
        return f"Error fetching page {url}: HTTP {response.status_code}: {error}"

    return f"Error fetching page {url}: network/request error: {error}"


def load_cookies() -> dict[str, str]:
    """Load cookies from cookies.json or cookies.txt if they exist."""
    global _cached_cookies
    if _cached_cookies is not None:
        return _cached_cookies

    cookies = {}

    # Try cookies.json first
    json_path = Path("cookies.json")
    if json_path.exists():
        try:
            import json
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _cached_cookies = {str(k): str(v) for k, v in data.items()}
                    return _cached_cookies
        except Exception as err:
            logging.warning(f"Error reading cookies.json: {err}")

    # Try cookies.txt
    txt_path = Path("cookies.txt")
    if txt_path.exists():
        try:
            with txt_path.open("r", encoding="utf-8") as f:
                content = f.read().strip()
                # Check if it looks like a netscape cookie file
                if "exhentai.org" in content or "e-hentai.org" in content or "# Netscape" in content:
                    for line in content.splitlines():
                        if not line.strip() or line.startswith("#"):
                            continue
                        parts = line.split("\t")
                        if len(parts) >= 7:
                            domain, flag, path, secure, expiration, name, value = parts[:7]
                            if "exhentai.org" in domain or "e-hentai.org" in domain:
                                cookies[name] = value
                else:
                    # Treat as raw Cookie header or simple key-value lines
                    if ";" in content or "=" in content:
                        pairs = content.replace("Cookie:", "").strip().split(";")
                        for pair in pairs:
                            if "=" in pair:
                                k, v = pair.strip().split("=", 1)
                                cookies[k.strip()] = v.strip()
        except Exception as err:
            logging.warning(f"Error reading cookies.txt: {err}")

    _cached_cookies = cookies
    return cookies


def create_session() -> requests.Session:
    """Create a requests Session configured with user agent and cookies."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": prepare_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
    })

    cookies = load_cookies()
    if cookies:
        session.cookies.update(cookies)

    return session


def _get_alternate_domain_url(url: str) -> str | None:
    """Return a URL with the alternate gallery domain if supported."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "e-hentai.org" in host:
        alternate_host = parsed.netloc.replace("e-hentai.org", "exhentai.org")
    elif "exhentai.org" in host:
        alternate_host = parsed.netloc.replace("exhentai.org", "e-hentai.org")
    else:
        return None

    return urlunparse(parsed._replace(netloc=alternate_host))


def _adapt_referer_to_target_domain(referer: str | None, target_url: str) -> str | None:
    """Align referer domain with target URL domain to reduce cross-domain blocking."""
    if not referer:
        return None

    target_host = urlparse(target_url).netloc
    if not target_host:
        return referer

    parsed_referer = urlparse(referer)
    if not parsed_referer.netloc:
        return referer

    if parsed_referer.netloc == target_host:
        return referer

    return urlunparse(parsed_referer._replace(netloc=target_host))


def fetch_page(
    url: str,
    timeout: int = 10,
    session: requests.Session | None = None,
    referer: str | None = None,
) -> BeautifulSoup:
    """Fetch the HTML content of a webpage with cookies and browser headers."""
    request_session = session or create_session()
    has_cookies = bool(request_session.cookies)

    def _request_page(target_url: str, target_referer: str | None) -> tuple[requests.Response, str]:
        headers = {"Referer": target_referer} if target_referer else None
        response = request_session.get(target_url, timeout=timeout, headers=headers)
        response.raise_for_status()

        if not response.text.strip():
            return response, "empty"

        diagnosis = _classify_page_problem(
            url=target_url,
            status_code=response.status_code,
            html=response.text,
            has_cookies=has_cookies,
        )
        if diagnosis:
            return response, diagnosis

        return response, "ok"

    try:
        primary_referer = _adapt_referer_to_target_domain(referer, url)
        response, primary_state = _request_page(url, primary_referer)
        fetched_url = url

        # Try domain fallback in both directions when the primary response is unusable.
        if primary_state != "ok":
            fallback_url = _get_alternate_domain_url(url)
            if fallback_url:
                fallback_referer = _adapt_referer_to_target_domain(referer, fallback_url)
                logging.warning(
                    "Primary response unusable for %s (%s). Trying fallback: %s",
                    url,
                    primary_state,
                    fallback_url,
                )
                fallback_response, fallback_state = _request_page(fallback_url, fallback_referer)
                if fallback_state == "ok":
                    response = fallback_response
                    fetched_url = fallback_url
                else:
                    raise RuntimeError(
                        f"Error fetching page {url}: primary={primary_state}; "
                        f"fallback={fallback_state}"
                    )
            else:
                raise RuntimeError(f"Error fetching page {url}: {primary_state}")

        soup = BeautifulSoup(response.text, "html.parser")
        soup.fetched_url = fetched_url
        return soup

    except requests.RequestException as req_err:
        response = req_err.response if hasattr(req_err, "response") else None
        fallback_url = _get_alternate_domain_url(url)
        if fallback_url:
            try:
                fallback_referer = _adapt_referer_to_target_domain(referer, fallback_url)
                fallback_response, fallback_state = _request_page(fallback_url, fallback_referer)
                if fallback_state == "ok":
                    soup = BeautifulSoup(fallback_response.text, "html.parser")
                    soup.fetched_url = fallback_url
                    logging.warning(
                        "Primary request failed for %s (%s). Recovered via fallback %s",
                        url,
                        req_err,
                        fallback_url,
                    )
                    return soup

                message = (
                    f"Error fetching page {url}: primary request failed ({req_err}); "
                    f"fallback unusable ({fallback_state})"
                )
                logging.exception(message)
                raise RuntimeError(message) from req_err
            except requests.RequestException as fallback_err:
                primary_message = _build_request_error_message(
                    url=url,
                    response=response,
                    error=req_err,
                    has_cookies=has_cookies,
                )
                fallback_response = (
                    fallback_err.response
                    if hasattr(fallback_err, "response")
                    else None
                )
                fallback_message = _build_request_error_message(
                    url=fallback_url,
                    response=fallback_response,
                    error=fallback_err,
                    has_cookies=has_cookies,
                )
                message = f"{primary_message}. Fallback failed too: {fallback_message}"
                logging.exception(message)
                raise RuntimeError(message) from req_err

        message = _build_request_error_message(
            url=url,
            response=response,
            error=req_err,
            has_cookies=has_cookies,
        )
        logging.exception(message)
        raise RuntimeError(message) from req_err


def clear_terminal() -> None:
    """Clear the terminal screen based on the operating system."""
    commands = {
        "nt": "cls",       # Windows
        "posix": "clear",  # macOS and Linux
    }

    command = commands.get(os.name)
    if command:
        os.system(command)  # noqa: S605
