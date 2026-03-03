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
- [x] Trim summaries to help token limits/truncation
- [ ] Speedup ingest_rss_feeds
- [ ] Experiment tracking for different models/prompts
- [ ] Map reduce for articles researcher needs to summarize them for the writer
- [ ] Refactor ingest_rss_feeds to return a list[dict] directly instead of dict[str, list]
"""

import feedparser
import logging
from datetime import datetime, timedelta, UTC
from time import mktime
import json
import re
import ollama
from zoneinfo import ZoneInfo

RESEARCHER_MODEL = "mistral:7b-instruct-v0.3-q8_0"
WRITER_MODEL = "mistral:7b-instruct-v0.3-q8_0"
EDITOR_MODEL = "mistral:7b-instruct-v0.3-q8_0"
MAX_REVISIONS = 3
TIMEFRAME_HOURS = 24
INTERESTS = [
    "AI", "ML", "MLOps", "LLMOps", "Platform Engineering", "AI Engineering",
    "DevOps", "Kubernetes", "NVIDIA", "LangChain", "Agents", "Anthropic", "Claude Code", "Codex",
    "AMD", "Intel", "Hugging Face", "PyTorch", "Ollama", "vLLM", "MCP", "RAG", "vector databases",
    "OpenAI", "Gemini", "Mistral", "Qwen", "Terraform", "ArgoCD", "GitOps"
]

FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.DEBUG

logging.basicConfig(format=FORMAT,level=LOG_LEVEL)

current_utc_time = datetime.now(UTC)
logging.info(f"Current UTC time {current_utc_time}")


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
                if  datetime_obj > current_utc_time - timedelta(hours=TIMEFRAME_HOURS):
                    results[name].append(entry)
        if results.get(name, []):
            logging.debug(f"Got {len(results.get(name))} recent entries for {name}")    
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
    system_prompt = "You are a precise newsletter researcher. Follow instructions exactly. Return only what is asked."
    user_prompt = f"""
        Read the following article content and generate a thorough research summary of what you read.
        Include key details and learnings that might interest an AI/ML Engineer.
        Only use information from within the article, do not make anything up. If there is no information in the article,
        indicate that.
        
        ARTICLE: 
        {re.sub(r'<[^>]+>', '', article.get('content'))}
    """
    response = chat_with_ollama(RESEARCHER_MODEL, system_prompt, user_prompt)

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
        response = chat_with_ollama(RESEARCHER_MODEL, system_prompt, researcher_prompt)
    except Exception as e:
        logging.error(f"Caught Exception: {e}")

    try: 
        curated_links = json.loads(response.message.content)
        logging.debug(f"researcher links: {curated_links}")
        curated_articles = [a for a in trimmed if a.get('link') in curated_links]
        logging.debug(f"curated_articles: {curated_articles}")
        logging.info(f"Researcher curated {len(curated_articles)} articles")
        
        summarized_articles = [summarize_article(a) for a in curated_articles]
        logging.info(f"Researcher summarized {len(summarized_articles)} articles")
        return summarized_articles
    except Exception as e:
        logging.error(f"Caught exception: {e}")
        return None


def writer(articles: str, feedback:str | None) -> str:
    """Take curated articles and generate a Newsletter.MD"""
    now_pacific = datetime.now(ZoneInfo("America/Los_Angeles"))
    pacific_string_formatted = now_pacific.strftime("%Y-%m-%d")
    newsletter = ""
    if feedback is None:
        feedback = ""

    system_prompt = "You are a technical newsletter writer, be precise and follow instructions exactly."
    user_prompt = f"""
        Given a list of summarized articles and the date, write a markdown formatted newsletter in the following format:
        - Header with the {pacific_string_formatted} and some title relating to a key story or theme
        - One highlighted story that goes into some more depth
        - Several minor stories
        - Each story should have a link in the title like [Title](link/to/source)
        
        ARTICLES:
        {articles}

        if feedback is provided then use it to refine your draft:
        {feedback}

        Return ONLY the markdown formatted newsletter you wrote.
    """

    response = chat_with_ollama(WRITER_MODEL, system_prompt, user_prompt)
    newsletter = response.message.content
    logging.info(f"Newsletter draft: {newsletter}")
    return newsletter


def editor(draft: str) -> str:
    """Take draft newsletter and provide feedback, if no edits, return LGTM!"""
    system_prompt = """
        You are a technical newsletter editor, be precise and follow instructions exactly. 
        If the draft looks good enough without glaring omissions or issues, simply respond with 'LGTM'.
        Otherwise respond ONLY with the feedback for the writer.
    """
    user_prompt = f"""
        Given a draft of a newsletter focused on AI / ML and DevOps, provide critical feedback that improves the form and
        readability of the newsletter. Make sure it's good for a 'coffee read' in the morning for a DevOps Engineer wanting to
        keep up to date on the latest trends and releases in AI.

        DRAFT:
        {draft}
    """

    response = chat_with_ollama(EDITOR_MODEL, system_prompt, user_prompt)
    feedback = response.message.content
    logging.info(f"Editor feedback: {feedback}")

    return feedback


def write_newsletter(final: str) -> None:
    """
    Save a dated article with a generated title to S3
    On failure, write to a local file for backup.
    """
    now_pacific = datetime.now(ZoneInfo("America/Los_Angeles"))
    pacific_string_formatted = now_pacific.strftime("%Y-%m-%d")
    with open(f"{pacific_string_formatted}-Newsletter.md", "w") as file:
        file.write(final)
    return


def main():
    """Main execution loop"""
    ready_to_publish = False

    final = ""
    draft = ""
    feedback = None
    revisions = 0
    raw_articles = ingest_rss_feeds()
    curated_articles = researcher(raw_articles)

    while not ready_to_publish and revisions < MAX_REVISIONS:
        draft = writer(curated_articles, feedback)
        feedback = editor(draft)
        if feedback.strip() == "LGTM":
            ready_to_publish = True
            final = draft
            logging.info("Editor approved the draft, print it!")
        revisions += 1
    final = draft
    logging.info(f"Agent loop finished in {revisions} iterations.")
    write_newsletter(final)


if __name__ == "__main__":
    main()