"""
File: publisher.py
Author: Sean-Michael Riesterer
Description: Functions for file IO and publishing newsletter to S3
"""

import boto3
from botocore.exceptions import ClientError
import logging
import os
import re

from config import (
    S3_CONTENT_BUCKET,
    AWS_REGION,
    PUBLISH,
    DIGEST_DIR,
    DATE_STR,
    RESEARCHER_MODEL,
    WRITER_MODEL,
    EDITOR_MODEL,
)


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
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
        logging.info(response)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def extract_title(newsletter_md: str) -> str:
    """Extract the H1 title from the newsletter markdown."""
    for line in newsletter_md.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return "AI Newsletter"


def make_slug(title: str) -> str:
    """Convert a title to a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug).strip("-")
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

    metadata = f"""

---
*Researcher: {RESEARCHER_MODEL} • Writer: {WRITER_MODEL} • Editor: {EDITOR_MODEL}*
"""
    full_content = frontmatter + final + metadata
    filename = DIGEST_DIR / f"{slug}.md"
    chars_written = 0

    with open(filename, "w") as file:
        try:
            chars_written = file.write(full_content)
            if chars_written < 1:
                logging.error(f"Wrote an empty file to {filename}.")
                return
        except Exception as e:
            logging.error(f"Caught exception writing digest: {e}")
            return

    if PUBLISH:
        object_name = f"digests/{filename.name}"
        uploaded = upload_file(filename, S3_CONTENT_BUCKET, object_name)
        if uploaded:
            logging.info(f"Uploaded {filename} to s3://{S3_CONTENT_BUCKET}")
        else:
            logging.error(f"Failed to upload {filename} to s3://{S3_CONTENT_BUCKET}")
