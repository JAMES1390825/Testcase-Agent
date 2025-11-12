"""OpenAI client factory and retry helpers with global rate limiting."""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable

from openai import OpenAI
from threading import Semaphore, Lock
from time import monotonic, sleep

from backend.config import (
	MAX_CONCURRENT_MODEL_CALLS_DEFAULT,
	MIN_CALL_INTERVAL_MS_DEFAULT,
)


def create_openai_client(api_key: str, base_url: str | None = None) -> OpenAI:
	"""Instantiate an OpenAI-compatible client with optional base URL."""

	if base_url and base_url.strip():
		return OpenAI(api_key=api_key, base_url=base_url.strip())
	return OpenAI(api_key=api_key)


_CALL_SEM = Semaphore(MAX_CONCURRENT_MODEL_CALLS_DEFAULT)
_RATE_LOCK = Lock()
_LAST_CALL_TS = 0.0
_MIN_INTERVAL_S = max(0.0, float(MIN_CALL_INTERVAL_MS_DEFAULT) / 1000.0)


def call_model_with_retries(
	client_instance: OpenAI,
	model_name: str,
	messages: Iterable[Dict[str, Any]],
	*,
	max_tokens: int = 4096,
	max_retries: int = 2,
	backoff_base: float = 0.6,
) -> str:
	"""Call chat.completions with exponential backoff and return message content."""

	attempt = 0
	delay = backoff_base
	last_err: Exception | None = None

	while attempt <= max_retries:
		try:
			# Global rate limit: bound concurrency and pace calls
			with _CALL_SEM:
				if _MIN_INTERVAL_S > 0:
					with _RATE_LOCK:
						now = monotonic()
						gap = now - globals().get('_LAST_CALL_TS', 0.0)
						if gap < _MIN_INTERVAL_S:
							sleep(_MIN_INTERVAL_S - gap)
						globals()['_LAST_CALL_TS'] = monotonic()
				completion = client_instance.chat.completions.create(
				model=model_name,
				messages=list(messages),
				max_tokens=max_tokens,
			)
			return completion.choices[0].message.content
		except Exception as exc:  # noqa: BLE001 - bubble up after retries
			last_err = exc
			if attempt == max_retries:
				break
			sleep_for = delay * (2 ** attempt)
			print(f"模型调用失败（{exc}），{sleep_for:.2f}s 后重试，第 {attempt + 1}/{max_retries} 次")
			time.sleep(sleep_for)
			attempt += 1

	raise RuntimeError(f"模型调用在重试后仍失败: {last_err}")


__all__ = ["create_openai_client", "call_model_with_retries"]
