"""Hugging Face Inference Providers client (architecture section 10).

Adapted from utils/llm.py in the owner's ekonomistyrning repository: token,
model and provider from the environment or Streamlit secrets, Qwen3 as the
default with its thinking switched off and any thinking block removed, a
timeout, and a cache so an identical prompt is sent only once per process.
Every failure is raised as ModelUnavailable, so callers handle one error type.
"""

import hashlib
import os
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass

import streamlit as st

TOKEN_KEY = "HF_TOKEN"
MODEL_KEY = "LLM_MODEL"
PROVIDER_KEY = "LLM_PROVIDER"
# Qwen3-8B, the ekonomistyrning default, is served only by featherless-ai, which
# the owner's token has not enabled; Qwen3-14B is served by deepinfra.
DEFAULT_MODEL = "Qwen/Qwen3-14B"
DEFAULT_PROVIDER = "auto"
TIMEOUT_SECONDS = 30
DEFAULT_MAX_TOKENS = 500
TEMPERATURE = 0.2
CACHE_SIZE = 256
NO_THINK = "/no_think"

# Qwen3 writes its reasoning in <think> blocks before the answer.
THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", flags=re.DOTALL)


class ModelUnavailable(RuntimeError):
    """The model cannot answer: no token, no library, network error or a refused call."""


def setting(key: str) -> str | None:
    """A setting from the environment, then Streamlit secrets (as storage/db.py)."""
    value = os.environ.get(key)
    if value:
        return value
    try:
        value = st.secrets.get(key)
    except FileNotFoundError:
        return None
    return str(value) if value else None


@dataclass(frozen=True)
class ModelConfig:
    token: str | None
    model: str
    provider: str


def load_config() -> ModelConfig:
    return ModelConfig(
        token=setting(TOKEN_KEY),
        model=setting(MODEL_KEY) or DEFAULT_MODEL,
        provider=setting(PROVIDER_KEY) or DEFAULT_PROVIDER,
    )


def is_configured() -> bool:
    """True when a token is set. Does not call the model."""
    return load_config().token is not None


def strip_thinking(text: str) -> str:
    """Remove thinking blocks; an unclosed one (the token limit was hit) removes the rest."""
    cleaned = THINK_BLOCK.sub("", text)
    return cleaned.split("<think>", 1)[0].strip()


def _with_no_think(user_prompt: str, model: str) -> str:
    """Switch off Qwen3's reasoning so the whole token budget goes to the answer."""
    if "qwen3" not in model.lower() or NO_THINK in user_prompt:
        return user_prompt
    return f"{user_prompt}\n{NO_THINK}"


def prompt_key(config: ModelConfig, system_prompt: str, user_prompt: str,
               max_tokens: int, temperature: float = TEMPERATURE) -> str:
    """Cache key: the model and everything sent to it."""
    payload = "\n||\n".join((config.model, config.provider, str(max_tokens), str(temperature),
                             system_prompt, user_prompt))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_cache: OrderedDict[str, str] = OrderedDict()
_cache_lock = threading.Lock()


def cached(key: str) -> str | None:
    """The stored answer for an identical earlier prompt, if any."""
    with _cache_lock:
        if key not in _cache:
            return None
        _cache.move_to_end(key)
        return _cache[key]


def remember(key: str, answer: str) -> None:
    with _cache_lock:
        _cache[key] = answer
        _cache.move_to_end(key)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)


def chat(config: ModelConfig, system_prompt: str, user_prompt: str,
         max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = TEMPERATURE) -> str:
    """One chat completion; the answer without thinking blocks."""
    if not config.token:
        raise ModelUnavailable("no token")
    try:
        from huggingface_hub import InferenceClient
    except ImportError as error:
        raise ModelUnavailable("huggingface_hub is not installed") from error
    client = InferenceClient(provider=config.provider, api_key=config.token,
                             timeout=TIMEOUT_SECONDS)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": _with_no_think(user_prompt, config.model)},
    ]
    try:
        response = client.chat_completion(messages=messages, model=config.model,
                                          max_tokens=max_tokens, temperature=temperature)
        raw = response.choices[0].message.content or ""
    except Exception as error:  # every library or network failure means the model is off
        raise ModelUnavailable(f"{type(error).__name__}: {error}") from error
    return strip_thinking(raw)
