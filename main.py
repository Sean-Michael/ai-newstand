"""
File: main.py
Author: Sean-Michael Riesterer
Description: Agentic AI workflow for gathering RSS feed based content into a newsfeed.
Version: v1.0.1
"""

import logging
from datetime import datetime, UTC
from time import perf_counter
import json
import re
from ollama import chat, ChatResponse
import os
from requests import RequestException
import concurrent.futures


from prompts import (
    RESEARCHER_SYSTEM_PROMPT,
    RESEARCHER_USER_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_PROMPT,
    WRITER_SYSTEM_PROMPT,
    WRITER_USER_PROMPT,
    EDITOR_SYSTEM_PROMPT,
    EDITOR_USER_PROMPT,
)

from article_processor import (
    fetch_article,
    ingest_rss_feeds,
)

from publisher import (
    write_newsletter,
)

from config import (
    DATE_STR,
    DIGEST_DIR,
    DRAFT_DIR,
    LOG_DIR,
    LOG_FILE,
    RESEARCHER_MODEL,
    WRITER_MODEL,
    EDITOR_MODEL,
    NUM_CTX,
    MAX_REVISIONS,
    INTERESTS,
    console_format,
    json_formatter,
    LOG_LEVEL,
)


os.makedirs(LOG_DIR / DATE_STR, exist_ok=True)
file_handler = logging.FileHandler(LOG_FILE, mode="a")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(json_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(logging.Formatter(console_format))

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

current_utc_time = datetime.now(UTC)
logging.info(f"Current UTC time {current_utc_time}")


def chat_with_ollama(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    think: bool = False,
    options=None,
    tools=None,
) -> ChatResponse:
    """Sends a chat to a model with a prompt"""
    message = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    start = perf_counter()

    response = chat(
        model=model_name,
        messages=message,
        think=think,
        options=options or {"num_ctx": NUM_CTX},
        tools=tools,
    )

    finish = perf_counter()
    logging.debug(f"Response from Ollama: {response}")
    logging.debug(f"Chat finished in {finish - start}s")
    return response


def summarize_article(article: dict):
    """Uses LLM to summarize an article given trimmed content, returns JSON with summary and metadata"""
    body = {re.sub(r"<[^>]+>", "", article.get("content", "NO CONTENT"))}
    response = chat_with_ollama(
        RESEARCHER_MODEL,
        SUMMARY_SYSTEM_PROMPT.template,
        SUMMARY_USER_PROMPT.render(article=body),
        think=False,
    )

    summary = response.message.content
    logging.debug(f"Summary of {article.get('title')}\n\t{summary}")

    summarized = {
        "source": article.get("source", "NO SOURCE"),
        "title": article.get("title", "NO TITLE"),
        "summary": summary,
        "link": article.get("link", "NO LINK"),
    }
    return summarized


def researcher(raw_articles: dict[str, list]) -> list[dict] | None:
    """Researcher Agent, refines article results into best candidates and summarizes"""
    logging.info(
        f"Ingested {sum(len(v) for v in raw_articles.values())} total articles from {len(raw_articles)} feeds"
    )
    trimmed = [
        {
            "source": source,
            "title": entry.get("title", "NO TITLE"),
            "summary": entry.get("summary", "NO SUMMARY"),
            "content": (
                entry.get("content", [{}])[0].get("value", "")
                or entry.get("summary", "NO CONTENT")
            )[:3000],
            "link": entry.get("link", "NO LINK"),
        }
        for source, entries in raw_articles.items()
        for entry in entries
    ]

    thin_articles = [
        a
        for a in trimmed
        if (len(a.get("content", "")) < 200 or "NO CONTENT" in a.get("content", ""))
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_article = {
            executor.submit(fetch_article, a.get("link", "")): a for a in thin_articles
        }

        for future in concurrent.futures.as_completed(future_to_article):
            try:
                a = future_to_article[future]
                logging.info(
                    f"RSS got no content for '{a.get('title', 'unknown')}', fetching article"
                )
                a["content"] = future.result() or "NO CONTENT"
                logging.debug(f"Fetched content length: {len(a['content'])}")
                if a["content"] == "NO CONTENT":
                    logging.info(
                        f"Could not fetch article content for '{a.get('title', 'unknown')}"
                    )
            except RequestException as e:
                logging.error(f"Exception caught in task future: {e}")
            except Exception as e:
                logging.error(f"Exception caught in task future: {e}")

    trimmed_for_curation = [
        {k: a[k] for k in ("source", "title", "summary", "link")} for a in trimmed
    ]
    researcher_prompt = RESEARCHER_USER_PROMPT.render(
        interests=INTERESTS, articles=json.dumps(trimmed_for_curation)
    )
    response = ""

    try:
        response = chat_with_ollama(
            RESEARCHER_MODEL,
            RESEARCHER_SYSTEM_PROMPT.template,
            researcher_prompt,
            think=False,
        )
    except Exception as e:
        logging.error(f"Caught Exception: {e}")
        return None

    try:
        curated_links = list(set(json.loads(response.message.content or "[]")))
        logging.info(f"Researcher selected {len(curated_links)} unique links")
        logging.debug(f"researcher links: {curated_links}")
        curated_articles = [a for a in trimmed if a.get("link") in curated_links]
        logging.debug(f"curated_articles: {curated_articles}")
        logging.info(f"Researcher curated {len(curated_articles)} articles")

        summarized_articles = [summarize_article(a) for a in curated_articles]
        logging.info(f"Researcher summarized {len(summarized_articles)} articles")
        logging.info(f"Article sources: {[a['source'] for a in summarized_articles]}")
        return summarized_articles
    except Exception as e:
        logging.error(f"Caught exception: {e}")
        return None


def writer(
    articles: list[dict[str, str]], previous_draft: str | None, feedback: str | None
) -> str | None:
    """Writer Agent, takes curated articles and generates a newsletter"""
    logging.info(f"Writer recieved {len(articles)} articles.")
    newsletter = ""
    if feedback is None:
        feedback = ""

    response = chat_with_ollama(
        WRITER_MODEL,
        WRITER_SYSTEM_PROMPT.template,
        WRITER_USER_PROMPT.render(
            date_str=DATE_STR,
            articles=articles,
            feedback=feedback,
            draft=previous_draft,
        ),
        think=False,
    )
    newsletter = response.message.content
    logging.info("Writer generated draft.")
    return newsletter


def editor(draft: str) -> str | None:
    """Editor Agent, takes draft newsletter and provides feedback, if no edits, returns 'LGTM'"""

    response = chat_with_ollama(
        EDITOR_MODEL,
        EDITOR_SYSTEM_PROMPT.template,
        EDITOR_USER_PROMPT.render(date_str=DATE_STR, draft=draft),
        think=False,
    )
    feedback = response.message.content
    logging.info("Editor generated feedback.")
    return feedback


def main():
    """Main execution loop"""

    for d in [DRAFT_DIR, DIGEST_DIR]:
        os.makedirs(d, exist_ok=True)

    start_main = perf_counter()
    ready_to_publish = False
    final = ""
    draft = ""
    feedback = ""
    revisions = 0
    raw_articles = ingest_rss_feeds()
    curated_articles = researcher(raw_articles)

    if not curated_articles:
        logging.error(
            f"Researcher returned no articles - or no valid JSON, got: {curated_articles}"
        )
        return
    logging.info(
        f"Passing {len(curated_articles)} articles to writer: {[a['source'] + ' - ' + a['title'][:40] for a in curated_articles]}"
    )

    while not ready_to_publish and revisions < MAX_REVISIONS:
        start_revision = perf_counter()
        draft = writer(curated_articles, draft, feedback)
        if not draft:
            revisions += 1
            continue

        draft_filename = DRAFT_DIR / f"draft-{revisions}"
        with open(draft_filename, "w") as draft_file:
            draft_file.write(draft)

        feedback = editor(draft)
        if not feedback:
            revisions += 1
            continue

        edit_filename = DRAFT_DIR / f"edits-{revisions}"
        with open(edit_filename, "w") as edit_file:
            edit_file.write(feedback)

        if feedback.strip() == "LGTM":
            ready_to_publish = True
            final = draft
            end_revision = perf_counter()
            logging.info(
                f"Editorial loop {revisions} finished in {end_revision - start_revision}s"
            )
            logging.info("Editor approved the draft, print it!")

        revisions += 1
        end_revision = perf_counter()
        logging.info(
            f"Editorial loop {revisions} finished in {end_revision - start_revision}s"
        )

    final = final or draft
    logging.info(f"Agent loop finished in {revisions} iterations.")

    if final:
        write_newsletter(final)
    else:
        logging.error(f"Failed to write, no final or draft, final:{final}")
        exit(1)
    end_main = perf_counter()
    logging.info(f"Finished main execution in {end_main - start_main}s")
    exit(0)


if __name__ == "__main__":
    main()
