"""
File: main.py
Author: Sean-Michael Riesterer
Description: Agentic AI workflow for gathering RSS feed based content into a newsfeed.
Version: v1.0.2
"""

import logging
import uuid
from datetime import datetime, UTC
from time import perf_counter
import os
from ingest import ingest_rss_feeds
from publisher import write_newsletter
from config import (
    DATE_STR,
    DIGEST_DIR,
    DRAFT_DIR,
    LOG_DIR,
    LOG_FILE,
    MAX_REVISIONS,
    console_format,
    json_formatter,
    LOG_LEVEL,
    OTLP_ENDPOINT,
)
from agents import researcher, writer, editor
from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from openinference.instrumentation import using_session


def setup() -> None:
    # Setup logging
    os.makedirs(LOG_DIR / DATE_STR, exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE, mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(json_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(logging.Formatter(console_format))

    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

    # Setup current time
    current_utc_time = datetime.now(UTC)
    logging.info(f"Current UTC time {current_utc_time}")

    # Make sure output dirs exist
    for d in [DRAFT_DIR, DIGEST_DIR]:
        os.makedirs(d, exist_ok=True)

    # Setup Otel tracing
    resource = Resource(attributes={"service.name": "ai-newstand"})
    tracer_provider = trace_sdk.TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT)
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    trace_api.set_tracer_provider(tracer_provider)


def main():
    """Main execution loop"""

    setup()

    session_id = str(uuid.uuid4())
    with using_session(session_id):
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
