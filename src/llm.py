"""Thin OpenAI-compatible client (NVIDIA build.nvidia.com or OpenRouter) with retry, usage capture and call counting."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"  # any tool-calling model id from https://build.nvidia.com/models
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def resolve_provider() -> dict:
    """Pick the provider from the environment: NVIDIA_API_KEY wins, then OPENROUTER_API_KEY.

    Override with LLM_BASE_URL / LLM_API_KEY for any other OpenAI-compatible endpoint.
    Model: NVIDIA_MODEL (NVIDIA) or MODEL_NAME (OpenRouter / generic). Keys are never logged.
    """
    if os.getenv("LLM_API_KEY") and os.getenv("LLM_BASE_URL"):
        return {"name": "custom", "key": os.environ["LLM_API_KEY"], "base_url": os.environ["LLM_BASE_URL"],
                "model": os.getenv("MODEL_NAME") or NVIDIA_DEFAULT_MODEL}
    if os.getenv("NVIDIA_API_KEY"):
        return {"name": "nvidia", "key": os.environ["NVIDIA_API_KEY"], "base_url": os.getenv("NVIDIA_BASE_URL", NVIDIA_BASE_URL),
                "model": os.getenv("NVIDIA_MODEL") or NVIDIA_DEFAULT_MODEL}
    if os.getenv("OPENROUTER_API_KEY"):
        return {"name": "openrouter", "key": os.environ["OPENROUTER_API_KEY"], "base_url": OPENROUTER_BASE_URL,
                "model": os.getenv("MODEL_NAME") or "anthropic/claude-sonnet-5.5"}
    return {"name": None, "key": None, "base_url": None, "model": os.getenv("NVIDIA_MODEL") or os.getenv("MODEL_NAME") or NVIDIA_DEFAULT_MODEL}


class LLMUnavailable(RuntimeError):
    """Raised when the provider cannot be used (no key, network error, repeated failure)."""


@dataclass
class LLMUsage:
    calls: int = 0
    failed_attempts: int = 0  # provider errors / empty replies that were retried (included in `calls`)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    rate_limit_wait_ms: float = 0.0  # time spent sleeping after HTTP 429; excluded from reported run latency
    stage_latency_ms: dict[str, float] = field(default_factory=dict)


class LLMClient:
    """One instance per run so that `usage` is that run's telemetry."""

    def __init__(self, client: Any = None, model: str | None = None, timeout: float = 90.0, retries: int = 1):
        self.provider = resolve_provider()
        self.model = model or self.provider["model"]
        self.retries = retries
        self.usage = LLMUsage()
        self._client = client
        self._timeout = timeout

    def _get_client(self) -> Any:
        if self._client is None:
            if not self.provider["key"]:
                raise LLMUnavailable("no LLM key set (NVIDIA_API_KEY or OPENROUTER_API_KEY)")
            from openai import OpenAI

            self._client = OpenAI(base_url=self.provider["base_url"], api_key=self.provider["key"], timeout=self._timeout, max_retries=0)
        return self._client

    def chat(self, messages: list[dict], tools: list[dict] | None = None, stage: str = "llm",
             max_tokens: int = 1800) -> Any:
        """One chat completion; returns the assistant message. Counts as one LLM call (retries count too)."""
        client = self._get_client()
        kwargs: dict[str, Any] = dict(model=self.model, messages=messages, temperature=0, max_tokens=max_tokens)
        if tools:
            kwargs["tools"] = tools
        last: Exception | None = None
        rate_limit_waits = 0
        attempt_budget = self.retries + 1
        attempt = -1
        while attempt + 1 < attempt_budget:
            attempt += 1
            start = time.perf_counter()
            self.usage.calls += 1
            try:
                response = client.chat.completions.create(**kwargs)
            except Exception as exc:
                last = exc
                self.usage.failed_attempts += 1
                self._add_latency(stage, start)
                if getattr(exc, "status_code", None) == 429 and rate_limit_waits < 4:
                    rate_limit_waits += 1  # free tiers throttle per minute: wait it out without burning a normal retry
                    time.sleep(8 * rate_limit_waits)
                    self.usage.rate_limit_wait_ms += 8000 * rate_limit_waits
                    attempt_budget += 1
                elif attempt < self.retries:
                    time.sleep(1.5 * (attempt + 1))
                continue
            self._add_latency(stage, start)
            usage = getattr(response, "usage", None)
            if usage is not None:
                self.usage.prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
                self.usage.completion_tokens += getattr(usage, "completion_tokens", 0) or 0
                cost = getattr(usage, "cost", None)
                if cost is None and getattr(usage, "model_extra", None):
                    cost = usage.model_extra.get("cost")
                self.usage.cost_usd += float(cost or 0)
            if not getattr(response, "choices", None):
                last = LLMUnavailable("empty response from provider")
                self.usage.failed_attempts += 1
                if attempt < self.retries:
                    time.sleep(1.5 * (attempt + 1))
                continue
            return response.choices[0].message
        raise LLMUnavailable(f"{type(last).__name__}: {str(last)[:200]}")

    def _add_latency(self, stage: str, start: float) -> None:
        elapsed = (time.perf_counter() - start) * 1000
        self.usage.latency_ms += elapsed
        self.usage.stage_latency_ms[stage] = self.usage.stage_latency_ms.get(stage, 0.0) + elapsed


def extract_json(text: str | None) -> dict:
    """Parse the first JSON object in a model reply (tolerates code fences and prose around it)."""
    if not text:
        raise ValueError("empty reply")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("no JSON object in reply")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("reply JSON is not an object")
    return value
