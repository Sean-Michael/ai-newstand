"""
File: config.py
Author: Sean-Michael Riesterer
Description: Global configurations definitions
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from pythonjsonlogger.json import JsonFormatter
import os

# Boolean to control wether or not the generated digest is 'published' by uploading to s3
PUBLISH = False

DATE_STR = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")

BASE_PATH = Path(__file__).parent
DRAFT_DIR = BASE_PATH / "drafts" / DATE_STR
DIGEST_DIR = BASE_PATH / "digests"
LOG_DIR = BASE_PATH / "logs"
LOG_FILE = (
    LOG_DIR / DATE_STR / f"main-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
)

RESEARCHER_MODEL = "gpt-oss:20b"
WRITER_MODEL = "gpt-oss:20b"
EDITOR_MODEL = "gpt-oss:20b"
NUM_CTX = 32768
MAX_REVISIONS = 3
TIMEFRAME_HOURS = 24
INTERESTS = [
    "AI",
    "ML",
    "MLOps",
    "LLMOps",
    "Platform Engineering",
    "AI Engineering",
    "DevOps",
    "Kubernetes",
    "NVIDIA",
    "LangChain",
    "Agents",
    "Anthropic",
    "Claude Code",
    "Codex",
    "AMD",
    "Intel",
    "Hugging Face",
    "PyTorch",
    "Ollama",
    "vLLM",
    "MCP",
    "RAG",
    "vector databases",
    "OpenAI",
    "Gemini",
    "Mistral",
    "Qwen",
    "Terraform",
    "ArgoCD",
    "GitOps",
]

S3_CONTENT_BUCKET = os.getenv("S3_CONTENT_BUCKET", "smr-webdev-content")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")


console_format = "%(asctime)s - %(levelname)s - %(message)s"
json_formatter = JsonFormatter("%(asctime)s %(levelname)s %(message)s")

LOG_LEVEL = logging.INFO
