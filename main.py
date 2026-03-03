"""
File: main.py
Author: Sean-Michael Riesterer
Description: Agentic AI workflow for gathering RSS feed based content into a newsfeed.
Version:
"""

import feedparser
import logging
from datetime import datetime, timedelta, UTC
from time import mktime
import json
import ollama

MAX_REVISIONS = 3

FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.DEBUG

logging.basicConfig(format=FORMAT,level=LOG_LEVEL)

current_utc_time = datetime.now(UTC)
logging.info(f"Curren UTC time {current_utc_time}")


def ingest_rss_feeds() -> dict:
    """Parse RSS feeds and return dictionary of information"""
    feeds = None
    with open("feeds.json", "r") as json_file:
        feeds = json.load(json_file)
    results = {}
    for name, url in feeds.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            date = entry.get('published_parsed') or entry.get('updated_parsed')
            if date:
                timestamp = mktime(date)
                datetime_obj = datetime.fromtimestamp(timestamp, UTC)
                if  datetime_obj > current_utc_time - timedelta(hours=24*7):
                    results[name] = entry
        if results.get(name) is not None:
            logging.debug(f"Got {len(results.get(name))} recent entries for {name}")    
    return results


def curator(raw_articles: dict) -> str:
    """Refine article results into best candidates"""
    for entry in raw_articles.values():
        logging.info(entry.get('summary'))

    curated_articles = None
    return curated_articles


def writer(curated_articles: str, feedback:str | None) -> str:
    """Take curated articles and generate a Newsletter.MD"""
    newsletter_draft = None
    return newsletter_draft


def editor(draft: str) -> str:
    """Take draft newsletter and provide feedback, if no edits, return LGTM!"""
    feedback = "LGTM"
    logging.info("Editor approved the draft, print it!")
    return feedback


def write_to_s3(final: str) -> None:
    """
    Save a dated article with a generated title to S3
    On failure, write to a local file for backup.
    """
    return


def main():
    """Main execution loop"""
    ready_to_publish = False

    final = None
    feedback = None
    revisions = 0
    raw_articles = ingest_rss_feeds()
    curated_articles = curator(raw_articles)

    while not ready_to_publish and revisions < MAX_REVISIONS:
        draft = writer(curated_articles, feedback)
        feedback = editor(draft)
        if "LGTM" in feedback:
            ready_to_publish = True
            final = draft
        revisions += 1
    logging.info(f"Agent loop finished in {revisions} iterations.")


if __name__ == "__main__":
    main()