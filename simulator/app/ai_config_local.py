"""Local AI Mentor defaults used by the project."""

import os

API_URL = ""
API_KEY = "sk-99b958b0a12442fab5cf06ee6b7e6d76"

TEMPERATURE = 0.7
MAX_TOKENS = 2000
TIMEOUT = 30

MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
