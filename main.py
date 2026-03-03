"""
File: main.py
Author: Sean-Michael Riesterer
Description: Agentic AI workflow for gathering RSS feed based content into a newsfeed.
Version:
"""


"""
TODO:
- [ ] Add timings to functions 
- [ ] Add traces to all calls
- [ ] Trim summaries to help token limits/truncation
- [ ] Speedup ingest_rss_feeds
"""

import feedparser
import logging
from datetime import datetime, timedelta, UTC
from time import mktime
import json
import ollama

CURATOR_MODEL = "qwen2.5:3b"
MAX_REVISIONS = 3
INTERESTS = ["AI", "ML", "MLOps", "AI Engineering", "DevOps", "Kubernetes", "NVIDIA", "LangChain", "Agents", "Anthropic", "Claude Code"]

FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.DEBUG

logging.basicConfig(format=FORMAT,level=LOG_LEVEL)

current_utc_time = datetime.now(UTC)
logging.info(f"Current UTC time {current_utc_time}")

def build_curator_prompt(interests: list[str], articles: list[dict[str]]) -> str:
    prompt = f"""You are a curator of news stories for an AI / ML Ops professional interested in the following topics: {interests}. 
    Specifically focus on new technology or product releases, workflows, techniques, or otherwise 'technical' content rather than social or political.
    Given a list of articles in the following format:
            "source": source,
            "title": entry.title,
            "summary": entry.summary,
            "link": entry.link
    
    Please return the links to articles that you have selected based on the criteria. 
    Return ONLY a JSON array of selected article links, nothing else. Example format:
["https://...", "https://..."]
    
    ARTICLES:
    {articles}
    """
    return prompt

def chat_with_ollama(model_name: str, system_prompt:str, user_prompt:str) -> dict | None:
    """Sends a chat to a model with a prompt"""
    message = [
        {
            "role": "system", 
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]
    response = ollama.chat(model=model_name, messages=message)
    logging.debug(f"Response from Ollama: {response}")
    return response


def ingest_rss_feeds() -> dict:
    """Parse RSS feeds and return dictionary of information"""
    """TODO: Add some try/except timeout/rate limit handling"""
    feeds = None
    with open("feeds.json", "r") as json_file:
        feeds = json.load(json_file)
    results = {}
    for name, url in feeds.items():
        results[name] = []
        feed = feedparser.parse(url)
        for entry in feed.entries:
            date = entry.get('published_parsed') or entry.get('updated_parsed')
            if date:
                timestamp = mktime(date)
                datetime_obj = datetime.fromtimestamp(timestamp, UTC)
                if  datetime_obj > current_utc_time - timedelta(hours=12):
                    results[name].append(entry)
        if results.get(name, []):
            logging.debug(f"Got {len(results.get(name))} recent entries for {name}")    
    return results


def curator(raw_articles: dict) -> str:
    """Refine article results into best candidates"""
    trimmed = [
        {
            "source": source,
            "title": entry.get('title', 'NO TITLE'),
            "summary": entry.get('summary','NO SUMMARY'),
            "link": entry.get('link', 'NO LINK')
        } 
        for source, entries in raw_articles.items()
        for entry in entries 
    ]
    curator_prompt = build_curator_prompt(INTERESTS, json.dumps(trimmed))
    system_prompt = "You are a precise newsletter curator. Follow instructions exactly. Return only what is asked."
    #logging.debug(f"Curator Prompt: {curator_prompt}")
    response = ""
    try:
        response = chat_with_ollama(CURATOR_MODEL, system_prompt, curator_prompt)
    except Exception as e:
        logging.error(f"Caught Exception: {e}")

    curated_articles = response.message.content
    logging.debug(f"Curator response content: {curated_articles}")
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