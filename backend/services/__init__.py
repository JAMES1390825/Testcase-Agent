"""Service layer helpers for the Testcase Agent backend."""

from .client_factory import create_openai_client, call_model_with_retries
from .parsing import extract_images_from_markdown, parse_prd_sections, create_batches_from_sections
from .postprocess import (
    sanitize_table_rows,
    deduplicate_test_case_ids,
    merge_markdown_tables,
    merge_csv_texts,
    validate_strict_csv,
    coerce_to_strict_csv,
    EXPECTED_HEADER,
)
from .vision import download_and_process_image, build_vision_messages
from .prompts import load_prompt_templates
from .cache import make_key, get as cache_get, set as cache_set

__all__ = [
    "create_openai_client",
    "call_model_with_retries",
    "extract_images_from_markdown",
    "parse_prd_sections",
    "create_batches_from_sections",
    "sanitize_table_rows",
    "deduplicate_test_case_ids",
    "merge_markdown_tables",
    "merge_csv_texts",
    "validate_strict_csv",
    "coerce_to_strict_csv",
    "EXPECTED_HEADER",
    "download_and_process_image",
    "build_vision_messages",
    "load_prompt_templates",
    "make_key",
    "cache_get",
    "cache_set",
]
