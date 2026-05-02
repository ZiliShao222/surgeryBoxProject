"""Example configuration for AI Nursing Mentor.

The tracked ``ai_config_local.py`` contains the shared defaults used by the
app. Keep real API keys in environment variables whenever possible.
"""

import os

# Leave API_URL empty when using OpenAI-compatible providers via BASE_URL.
API_URL = ""

# Do not hardcode a real key in this repository.
API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

TEMPERATURE = 0.7
MAX_TOKENS = 2000
TIMEOUT = 30

# DashScope OpenAI-compatible mode by default.
MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
