MAX_REVISIONS = 3

def ingest_rss_feeds():
    """Parse RSS feeds and return dictionary of information"""
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
    feedback = None
    return feedback

def write_to_s3(final: str) -> str:
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

    while not ready_to_publish:
        draft = writer(curated_articles, feedback)
        feedback = editor(draft)
        if "LGTM" in feedback:
            ready_to_publish = True
            final = draft
        else:
            draft = writer(curated_articles, feedback)
            revisions += 1

if __name__ == "__main__":
    main()