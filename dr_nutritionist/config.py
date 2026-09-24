"""
Settings, read from the environment.

Nothing here has a default that would let the app run with a missing
key and fail later in a confusing way. If a key is needed and absent,
the code that needs it says so.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral/mistral-small-latest")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini/gemini-3.6-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
USDA_API_KEY = os.environ.get("USDA_API_KEY", "")


def providers() -> list[tuple[str, str]]:
    """
    The models to try, in order, as (model, key) pairs.

    Mistral is the default. A second provider is here because the free
    tier rate limits hard: during development a single call returned 429
    while the quota for the day was fine, and one throttled provider
    should not decide whether the app works. Whichever answers first is
    used, and the result records which one it was.
    """
    chain = []
    if MISTRAL_API_KEY:
        chain.append((MISTRAL_MODEL, MISTRAL_API_KEY))
    if GEMINI_API_KEY:
        chain.append((GEMINI_MODEL, GEMINI_API_KEY))
    return chain

# The crew calls a model three times, once per task. Each call is a round
# trip, so this is not a fast pipeline and it is not meant to be: nobody
# is waiting on a phone line.
MAX_MEALS = 10


def model_available() -> bool:
    """Whether the crew can run at all, or the deterministic path is needed."""
    return bool(providers())
