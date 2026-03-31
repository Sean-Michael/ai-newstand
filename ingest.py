"""
File: ingest.py
Author: Sean-Michael Riesterer
Description: Functions to gather articles from RSS Feeds and parse content with bs4
"""

import logging
import requests
from requests import RequestException, Response
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta, UTC
from time import mktime, perf_counter
from config import TIMEFRAME_HOURS
import json

current_utc_time = datetime.now(UTC)


def fetch_article(url: str) -> str | None:
    """Requests a page from URL via HTTP"""

    logging.info(f"Fetching URL: {url}\n")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
    except RequestException as e:
        logging.error(f"Caught Request Exception {e}")
        return None

    if response.status_code == 200 and "text/html" in content_type:
        return parse_article(response)
    else:
        return None


def parse_article(response: Response) -> str | None:
    """Parses page to extract text content."""

    soup = BeautifulSoup(response.content, "html.parser")
    noise_tags = [
        "nav",
        "footer",
        "header",
        "aside",
        "script",
        "meta",
        "style",
        "form",
        "svg",
        "noscript",
        "iframe",
        "button",
    ]

    noise_selectors = [
        '[role="navigation"]',
        '[role="complementary"]',
        '[role="banner"]',
        ".comments",
        ".comment-section",
        "#comments",
        ".sidebar",
        "#sidebar",
        ".social-share",
        ".share-buttons",
        ".sharing",
        ".related-posts",
        ".recommended",
        ".read-next",
        ".newsletter-signup",
        ".subscribe",
        ".cookie-banner",
        ".cookie-consent",
        ".author-bio",
        ".author-card",
        ".table-of-contents",
        ".toc",
        ".breadcrumb",
        ".breadcrumbs",
        ".pagination",
        ".ad",
        ".advertisement",
        ".sponsored",
    ]

    for selector in noise_selectors:
        for el in soup.select(selector):
            el.decompose()

    for tag_noise in soup.find_all(noise_tags):
        tag_noise.decompose()

    content = soup.find("article") or soup.find("main") or soup.find("body")

    if content:
        text = content.get_text(separator="\n", strip=True)
        if len(text) < 200:
            return None
        logging.info(f"Extracted {len(text)} chars from content.")
        return text


def ingest_rss_feeds() -> dict:
    """Parse RSS feeds and return dictionary of information"""
    """TODO: Add some try/except timeout/rate limit handling"""
    feeds = None
    with open("feeds.json", "r") as json_file:
        feeds = json.load(json_file)
    results = {}

    start = perf_counter()
    for name, url in feeds.items():
        results[name] = []
        feed = feedparser.parse(url)
        for entry in feed.entries:
            date = entry.get("published_parsed", None) or entry.get(
                "updated_parsed", None
            )
            if date:
                timestamp = mktime(date)  # type: ignore[arg-type]
                datetime_obj = datetime.fromtimestamp(timestamp, UTC)
                if datetime_obj > current_utc_time - timedelta(hours=TIMEFRAME_HOURS):
                    results[name].append(entry)
        if results.get(name, []):
            logging.debug(f"Got {len(results.get(name, ''))} recent entries for {name}")
    end = perf_counter()
    logging.debug(f"RSS parser finished in {end - start}s")
    return results
