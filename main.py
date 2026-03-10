"""
File: main.py
Author: Sean-Michael Riesterer
Description: Agentic AI workflow for gathering RSS feed based content into a newsfeed.
Version:
"""


"""
TODO:
- [x] Add timings to functions 
- [ ] Add traces to all calls
- [x] Trim summaries to help token limits/truncation
- [ ] Speedup ingest_rss_feeds
- [ ] Experiment tracking for different models/prompts
- [ ] Map reduce for articles researcher needs to summarize them for the writer
- [ ] Refactor ingest_rss_feeds to return a list[dict] directly instead of dict[str, list]
- [ ] DRY
- [ ] Logging to file and formatted
- [ ] Pull in system logs with some orchestrator script or something like journalctl ollama and nvidia
- [ ] Change environment vars to click CLI options
"""

import feedparser
import logging
from datetime import datetime, timedelta, UTC
from time import mktime, perf_counter
import json
import re
from ollama import chat, ChatResponse
from zoneinfo import ZoneInfo
import boto3
from pathlib import Path
from botocore.exceptions import ClientError
import os


DATE_STR = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")

BASE_PATH = Path(__file__).parent
DRAFT_DIR = os.path.join(BASE_PATH, 'drafts', DATE_STR + '/')
DIGEST_DIR = os.path.join(BASE_PATH, 'digests/')

for d in [DRAFT_DIR, DIGEST_DIR]:
    os.makedirs(d, exist_ok=True)

# Boolean to control wether or not the generated newsletter is 'published' by uploading to s3
PUBLISH = False


RESEARCHER_MODEL = "qwen3.5:9b"
WRITER_MODEL = "qwen3.5:9b"
EDITOR_MODEL = "qwen3.5:9b"
NUM_CTX = 32768
MAX_REVISIONS = 3
TIMEFRAME_HOURS = 24
INTERESTS = [
    "AI", "ML", "MLOps", "LLMOps", "Platform Engineering", "AI Engineering",
    "DevOps", "Kubernetes", "NVIDIA", "LangChain", "Agents", "Anthropic", "Claude Code", "Codex",
    "AMD", "Intel", "Hugging Face", "PyTorch", "Ollama", "vLLM", "MCP", "RAG", "vector databases",
    "OpenAI", "Gemini", "Mistral", "Qwen", "Terraform", "ArgoCD", "GitOps"
]

S3_CONTENT_BUCKET = os.getenv("S3_CONTENT_BUCKET", "smr-webdev-content")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")


FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.DEBUG

logging.basicConfig(format=FORMAT,level=LOG_LEVEL)

current_utc_time = datetime.now(UTC)
logging.info(f"Current UTC time {current_utc_time}")


def chat_with_ollama(model_name: str, system_prompt:str, user_prompt:str, think:bool = False, options={"num_ctx":NUM_CTX}) -> ChatResponse:
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
    start = perf_counter()
    response = chat(model=model_name, messages=message, think=think, options=options)
    finish = perf_counter()
    logging.debug(f"Response from Ollama: {response}")
    logging.info(f"Chat finished in {finish - start}s")
    return response


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
            date = entry.get('published_parsed') or entry.get('updated_parsed')
            if date:
                timestamp = mktime(date)
                datetime_obj = datetime.fromtimestamp(timestamp, UTC)
                if  datetime_obj > current_utc_time - timedelta(hours=TIMEFRAME_HOURS):
                    results[name].append(entry)
        if results.get(name, []):
            logging.debug(f"Got {len(results.get(name))} recent entries for {name}") 
    end = perf_counter()
    logging.info(f"RSS parser finished in {end - start}s")   
    return results


def build_researcher_prompt(interests: list[str], articles: list[dict[str]]) -> str:
    prompt = f"""You are a researcher of news stories for an AI / ML Ops professional interested in the following topics: {interests}. 
    Specifically focus on new technology or product releases, workflows, techniques, or otherwise 'technical' content rather than social or political.
    Given a list of articles in the following format:
            "source": source,
            "title": entry.title,
            "summary": entry.summary,
            "link": entry.link
    
    1. Select no more than 10 articles that best match the interest topics and criteria.
        - Try to use a mixture of sources to capture a variety of topics.
        - Prioritize content from: Hugging Face Blog, MLOps Community, CNCF Blog when available
    2. Gather the UNIQUE links for each article 
    3. Return ONLY a JSON array of selected article links, nothing else. Example format:
["https://...", "https://..."]
    
    ARTICLES:
    {articles}
    """
    return prompt


def summarize_article(article: dict):
    system_prompt = """
    You are a research assistant summarizing articles for a senior DevOps engineer 
    interested in AI and MLOps. They build on Kubernetes, work with self-hosted LLMs, 
    and care about practical tooling. Summarize only what is in the article. 
    If the content is thin, say so briefly.
    """
    user_prompt = f"""
        Summarize this article in one or two paragraphs. Cover: what it is, the key technical 
        insight or announcement, one concrete detail (metric, example, or comparison), 
        and why it matters to someone building ML infrastructure.

        ARTICLE: 
        {re.sub(r'<[^>]+>', '', article.get('content'))}
    """
    response = chat_with_ollama(RESEARCHER_MODEL, system_prompt, user_prompt, think=False)

    summary = response.message.content
    logging.debug(f"Summary of {article.get('title')}\n\t{summary}")

    summarized = {
        "source": article.get('source', 'NO SOURCE'),
        "title": article.get('title', 'NO TITLE'),
        "summary": summary,
        "link": article.get('link', 'NO LINK')
    }
    return summarized


def researcher(raw_articles: list[dict]) -> list[dict] | None:
    """Refine article results into best candidates"""
    logging.info(f"Ingested {sum(len(v) for v in raw_articles.values())} total articles from {len(raw_articles)} feeds")
    trimmed = [
        {
            "source": source,
            "title": entry.get('title', 'NO TITLE'),
            "summary": entry.get('summary','NO SUMMARY'),
            "content": (entry.get('content', [{}])[0].get('value', '') or entry.get('summary', 'NO CONTENT'))[:3000],
            "link": entry.get('link', 'NO LINK')
        } 
        for source, entries in raw_articles.items()
        for entry in entries 
    ]

    trimmed_for_curation = [{k: a[k] for k in ('source','title','summary','link')} for a in trimmed]
    researcher_prompt = build_researcher_prompt(INTERESTS, json.dumps(trimmed_for_curation))
    system_prompt = "You are a precise newsletter researcher. Follow instructions exactly. Return only what is asked."
    response = ""
    try:
        response = chat_with_ollama(RESEARCHER_MODEL, system_prompt, researcher_prompt, think=False)
    except Exception as e:
        logging.error(f"Caught Exception: {e}")

    try: 
        curated_links = list(set(json.loads(response.message.content)))
        logging.info(f"Researcher selected {len(curated_links)} unique links")
        logging.debug(f"researcher links: {curated_links}")
        curated_articles = [a for a in trimmed if a.get('link') in curated_links]
        logging.debug(f"curated_articles: {curated_articles}")
        logging.info(f"Researcher curated {len(curated_articles)} articles")
        

        summarized_articles = [summarize_article(a) for a in curated_articles]
        logging.info(f"Researcher summarized {len(summarized_articles)} articles")
        logging.info(f"Article sources: {[a['source'] for a in summarized_articles]}")
        return summarized_articles
    except Exception as e:
        logging.error(f"Caught exception: {e}")
        return None


def writer(articles: str, previous_draft:str | None, feedback:str | None) -> str:
    """Take curated articles and generate a Newsletter.MD"""
    logging.info(f"Writer recieved {len(articles)} articles.")
    newsletter = ""
    if feedback is None:
        feedback = ""

    system_prompt = """
        You are writing a personal knowledge digest for a senior DevOps engineer 
        interested in AI and MLOps. Write like a knowledgeable colleague sharing 
        what they learned today, not a marketer. Be specific and technical.

        The editor will provide feedback, if given follow it exactly and update your previous draft.
    """
    user_prompt = f"""
        Write a markdown newsletter for {DATE_STR} using the articles below.

        Format:
        # [Thematic title] | {DATE_STR}

        ## 🔥 Story of the Day
        ### [Title](link) — Source
        3-4 paragraphs. Cover what happened, why it matters, and one concrete 
        technical detail worth remembering.

        ## ⚡ Quick Hits
        ### [Title](link) — Source
        1 - 2 paragraphs of actual substance. No filler phrases like "in this article 
        the author discusses". Just the information.

        (repeat for each article)

        Rules:
        - Only use articles from the provided list, do not invent stories
        - Every title must be a markdown link of the exac format: [Title](link) for proper hyperlink
        - No marketing language or filler phrases
        - If an article has thin content, keep it short rather than padding it
        - For title links, enclose the link text in square brackets [] and immediately follow it with the URL in parentheses ()

        ARTICLES:
        {articles}

        FEEDBACK:
        {feedback}

        PREVIOUS DRAFT:
        {previous_draft}

        Return ONLY the markdown.
    """

    response = chat_with_ollama(WRITER_MODEL, system_prompt, user_prompt, think=False)
    newsletter = response.message.content
    logging.info(f"Newsletter draft: {newsletter}")
    return newsletter


def editor(draft: str) -> str:
    """Take draft newsletter and provide feedback, if no edits, return LGTM!"""

    system_prompt = """
        You are editing a personal technical digest. Respond with LGTM if the draft 
        is solid. Otherwise give specific actionable feedback only — no examples, 
        no rewrites, just clear instructions for the writer. 
        
        Do NOT include 'LGTM' anywhere in your response if you have feedback. 
        Only respond with LGTM if the draft is ready to print.
    """
    user_prompt = f"""
        Today's date is {DATE_STR}
        Review this newsletter draft for a DevOps/MLOps engineer. Check:
        - Does every story have a markdown link? Do not fact check URL content just that they exist and are of the correct format 
        - Links should be in this format for proper MD hyperlink (LINK_TEXT)[URL]
        - Is the Story of the Day substantively deeper than the Quick Hits?
        - Are there any filler phrases like "in this article the author discusses"?
        - Does any story appear to be invented rather than sourced from real content?
        - Is it worth reading over morning coffee?

        Respond with LGTM or specific feedback only. Do not mix 'LGTM' in with feedback.

        DRAFT:
        {draft}
    """

    response = chat_with_ollama(EDITOR_MODEL, system_prompt, user_prompt, think=False)
    feedback = response.message.content
    logging.info(f"Editor feedback: {feedback}")

    return feedback


# Below function taken from AWS documentation for boto3 sdk docs
def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def extract_title(newsletter_md: str) -> str:
    """Extract the H1 title from the newsletter markdown."""
    for line in newsletter_md.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return "AI Newsletter"


def make_slug(title: str) -> str:
    """Convert a title to a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug).strip('-')
    return slug


def write_newsletter(final: str) -> None:
    """
    Add frontmatter, save locally, and upload to S3.
    """

    title = extract_title(final)
    slug = make_slug(title)

    frontmatter = f"""---
title: "{title}"
date: {DATE_STR}
---
"""
    full_content = frontmatter + final
    filename = DIGEST_DIR + slug + ".md"

    with open(filename, "w") as file:
        written = file.write(full_content)
    if written > 0 and PUBLISH:
        object_name = "digests/" + filename
        uploaded = upload_file(filename, S3_CONTENT_BUCKET, object_name)
        if uploaded:
            logging.info(f"Uploaded {object_name} to s3://{S3_CONTENT_BUCKET}")
        else:
            logging.error(f"Failed to upload {object_name} to s3://{S3_CONTENT_BUCKET}")
    else:
        if not PUBLISH:
            logging.info("Publish to s3 disabled")
            return
        logging.error("Wrote an empty file, no upload to s3..")
        exit(1)


def main():
    """Main execution loop"""
    start_main = perf_counter()
    ready_to_publish = False
    final = ""
    draft = ""
    feedback = ""
    revisions = 0
    raw_articles = ingest_rss_feeds()    
    curated_articles = researcher(raw_articles)
    
    if not curated_articles:
        logging.error(f"Researcher returned no articles - or no valid JSON, got: {curated_articles}")
        return
    logging.info(f"Passing {len(curated_articles)} articles to writer: {[a['source'] + ' - ' + a['title'][:40] for a in curated_articles]}")
    
    while not ready_to_publish and revisions < MAX_REVISIONS:
        start_revision = perf_counter()
        draft = writer(curated_articles, draft, feedback)
        draft_filename = DRAFT_DIR + 'draft-' + str(revisions)
        
        with open(draft_filename, "w") as draft_file:
            draft_file.write(draft)
        feedback = editor(draft)
        edit_filename = DRAFT_DIR + 'edits-' + str(revisions)
        
        with open(edit_filename, "w") as edit_file:
            edit_file.write(feedback)
        
        if feedback.strip() == "LGTM":
            ready_to_publish = True
            final = draft
            end_revision = perf_counter()
            logging.info(f"Editorial loop {revisions} finished in {end_revision - start_revision}s")
            logging.info("Editor approved the draft, print it!")
        
        revisions += 1
        end_revision = perf_counter()
        logging.info(f"Editorial loop {revisions} finished in {end_revision - start_revision}s")
    
    final = final or draft
    logging.info(f"Agent loop finished in {revisions} iterations.")

    metadata = f"""

---
*Researcher: {RESEARCHER_MODEL} • Writer: {WRITER_MODEL} • Editor: {EDITOR_MODEL}*
"""
    final_copy = final + metadata
    write_newsletter(final_copy)

    end_main = perf_counter()
    logging.info(f"Finished main execution in {end_main - start_main}s")


if __name__ == "__main__":
    main()