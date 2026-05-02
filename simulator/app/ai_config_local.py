"""Local AI Mentor defaults.

This file is tracked so every developer gets the same provider/model defaults.
Put the real API key in DASHSCOPE_API_KEY instead of hardcoding it here.
"""

import os

API_URL = ""
API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

TEMPERATURE = 0.7
MAX_TOKENS = 2000
TIMEOUT = 30

MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
