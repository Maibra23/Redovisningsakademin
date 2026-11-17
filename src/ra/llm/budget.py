"""Budget for model calls (architecture section 10).

Adapted from utils/llm_budget.py in the owner's ekonomistyrning repository.
A session may make 30 calls; the whole app may make LLM_DAILY_CAP calls a day.
The service keeps the session count in session state and the daily count in
the database (table llm_usage), so reloading the page does not reset it. A
cached answer costs nothing.
"""

import logging
from enum import StrEnum

from ra.llm.client import setting

logger = logging.getLogger(__name__)

SESSION_CAP = 30
DAILY_CAP_KEY = "LLM_DAILY_CAP"
DEFAULT_DAILY_CAP = 200


class Verdict(StrEnum):
    OK = "ok"
    SESSION_FULL = "session_full"
    DAILY_FULL = "daily_full"


def daily_cap() -> int:
    """LLM_DAILY_CAP from the environment or secrets; the default when missing or unreadable."""
    raw = setting(DAILY_CAP_KEY)
    if raw is None:
        return DEFAULT_DAILY_CAP
    try:
        return max(0, int(raw.strip()))
    except ValueError:
        logger.warning("LLM_DAILY_CAP %r is not a whole number; using %d", raw, DEFAULT_DAILY_CAP)
        return DEFAULT_DAILY_CAP


def verdict(session_calls: int, daily_calls: int, cap: int) -> Verdict:
    """Whether one more call is allowed."""
    if session_calls >= SESSION_CAP:
        return Verdict.SESSION_FULL
    if daily_calls >= cap:
        return Verdict.DAILY_FULL
    return Verdict.OK
