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

MAX_REVISIONS = 3

FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.DEBUG

logging.basicConfig(format=FORMAT,level=LOG_LEVEL)

current_utc_time = datetime.now(UTC)
logging.info(f"Curren UTC time {current_utc_time}")


def ingest_rss_feeds():
    """Parse RSS feeds and return dictionary of information"""
    feed_urls = {
        'Docker Blog': 'https://www.docker.com/blog/feed/',
        'Hugging Face Blog': 'https://huggingface.co/blog/feed.xml',
    }
    daily_results = {}
    for name, url in feed_urls.items():
        feed = feedparser.parse(url)
        logging.info(f"Feed Title: {feed.feed.title}")
        logging.info(f"Feed Link: {feed.feed.link}")
        for entry in feed.entries:
            #logging.debug(f"Processing entry: {entry.title}...")
            date = entry.get('published_parsed')
            if date:
                timestamp = mktime(date)
                datetime_obj = datetime.fromtimestamp(timestamp, UTC)
                logging.debug(datetime_obj)
                if  datetime_obj > current_utc_time - timedelta(hours=100):
                    daily_results[name] = entry
                    logging.debug(f"Got {len(daily_results[name])} recent entries for {name}")

            
    articles = None
    return articles


def curator(raw_articles: str) -> str:
    """Refine article results into best candidates"""
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