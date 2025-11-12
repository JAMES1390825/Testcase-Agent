"""Prompt template loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from backend.config import (
	PROMPT_TEMPLATE_DIFF_PATH,
	PROMPT_TEMPLATE_FULL_PATH,
)


def _load_template(path: Path) -> str:
	try:
		with path.open('r', encoding='utf-8') as file:
			return file.read()
	except FileNotFoundError:
		return "错误：找不到提示模板文件。"


def load_prompt_templates() -> Tuple[str, str]:
	"""Return (full_prompt, diff_prompt) contents."""

	full_prompt = _load_template(PROMPT_TEMPLATE_FULL_PATH)
	diff_prompt = _load_template(PROMPT_TEMPLATE_DIFF_PATH)
	return full_prompt, diff_prompt


__all__ = ["load_prompt_templates"]
