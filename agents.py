"""
File: agents.py
Author: Sean-Michael Riesterer
Description: Functions for LLM agent operations
"""

from requests import RequestException
import concurrent.futures
import json
import re
from ollama import chat, ChatResponse
import logging
from ingest import fetch_article
from config import (
    DATE_STR,
    RESEARCHER_MODEL,
    WRITER_MODEL,
    EDITOR_MODEL,
    NUM_CTX,
    INTERESTS,
)
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
from opentelemetry import trace
from openinference.instrumentation import using_prompt_template

tracer = trace.get_tracer(__name__)


def chat_with_ollama(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    think: bool = False,
    options=None,
    tools=None,
) -> ChatResponse:
    """Sends a chat to a model with a prompt"""
    with tracer.start_as_current_span("llm.chat") as span:
        span.set_attribute("llm.model_name", model_name)
        span.set_attribute("input.value", user_prompt)
        span.set_attribute("llm.system", system_prompt)

        response = chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            think=think,
            options=options or {"num_ctx": NUM_CTX},
            tools=tools,
        )

        # token counts
        prompt_tokens = response.prompt_eval_count or 0
        output_tokens = response.eval_count or 0
        span.set_attribute("llm.token_count.prompt", prompt_tokens)
        span.set_attribute("llm.token_count.completion", output_tokens)
        span.set_attribute("llm.token_count.total", prompt_tokens + output_tokens)

        # latency timings in ms (duration is in nanoseconds so divide by 1e+6)
        span.set_attribute("llm.latency.total_ms", (response.total_duration or 0) / 1e6)
        span.set_attribute(
            "llm.latency.prompt_eval_ms", (response.prompt_eval_duration or 0) / 1e6
        )
        span.set_attribute(
            "llm.latency.generation_ms", (response.eval_duration or 0) / 1e6
        )
        span.set_attribute("llm.latency.load_ms", (response.load_duration or 0) / 1e6)

        # token throughput
        if response.eval_duration and response.eval_count:
            tokens_per_second = response.eval_count / (response.eval_duration / 1e9)
            span.set_attribute("llm.throughput.tokens_per_second", tokens_per_second)

        span.set_attribute("llm.num_ctx", (options or {}).get("num_ctx", NUM_CTX))

        output = response.message.content or ""
        span.set_attribute("output.value", output)
        logging.debug(f"Response from Ollama: {response}")
        logging.debug(f"Chat finished in {(response.eval_duration or 0)}s")
        return response


def summarize_article(article: dict):
    """Uses LLM to summarize an article given trimmed content, returns JSON with summary and metadata"""
    body = re.sub(r"<[^>]+>", "", article.get("content", "NO CONTENT"))
    with tracer.start_as_current_span("summarize.agent") as span:
        span.set_attribute("llm.system_prompt.template", SUMMARY_SYSTEM_PROMPT.template)
        span.set_attribute("llm.system_prompt.version", SUMMARY_SYSTEM_PROMPT.version)
        with using_prompt_template(
            template=SUMMARY_USER_PROMPT.template,
            version=SUMMARY_USER_PROMPT.version,
            variables={"article": body[:200]},
        ):
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

    try:
        with tracer.start_as_current_span("researcher.agent") as span:
            span.set_attribute(
                "llm.system_prompt.template", RESEARCHER_SYSTEM_PROMPT.template
            )
            span.set_attribute(
                "llm.system_prompt.version", RESEARCHER_SYSTEM_PROMPT.version
            )
            with using_prompt_template(
                template=RESEARCHER_USER_PROMPT.template,
                version=RESEARCHER_USER_PROMPT.version,
            ):
                response = chat_with_ollama(
                    RESEARCHER_MODEL,
                    RESEARCHER_SYSTEM_PROMPT.template,
                    RESEARCHER_USER_PROMPT.render(
                        interests=INTERESTS, articles=json.dumps(trimmed_for_curation)
                    ),
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
    if feedback is None:
        feedback = ""

    with tracer.start_as_current_span("writer.agent") as span:
        span.set_attribute("llm.system_prompt.template", WRITER_SYSTEM_PROMPT.template)
        span.set_attribute("llm.system_prompt.version", WRITER_SYSTEM_PROMPT.version)
        with using_prompt_template(
            template=WRITER_USER_PROMPT.template,
            version=WRITER_USER_PROMPT.version,
        ):
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
    with tracer.start_as_current_span("editor.agent") as span:
        span.set_attribute("llm.system_prompt.template", EDITOR_SYSTEM_PROMPT.template)
        span.set_attribute("llm.system_prompt.version", EDITOR_SYSTEM_PROMPT.version)
        with using_prompt_template(
            template=EDITOR_USER_PROMPT.template,
            version=EDITOR_USER_PROMPT.version,
        ):
            response = chat_with_ollama(
                EDITOR_MODEL,
                EDITOR_SYSTEM_PROMPT.template,
                EDITOR_USER_PROMPT.render(date_str=DATE_STR, draft=draft),
                think=False,
            )
    feedback = response.message.content
    logging.info("Editor generated feedback.")
    return feedback
