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
from .kb import save_doc as kb_save_doc, load_doc as kb_load_doc, list_docs as kb_list_docs, create_doc_from_sections as kb_create_doc_from_sections, search_similar_sections as kb_search_similar_sections
from .prompts import load_prompt_templates
from .cache import make_key, get as cache_get, set as cache_set
from .uploads import (
    save_testcases as uploads_save_testcases,
    list_testcases as uploads_list_testcases,
    get_testcases as uploads_get_testcases,
    save_prd as uploads_save_prd,
    list_prds as uploads_list_prds,
    get_prd as uploads_get_prd,
)

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
    "kb_save_doc",
    "kb_load_doc",
    "kb_list_docs",
    "kb_create_doc_from_sections",
    "kb_search_similar_sections",
    "uploads_save_testcases",
    "uploads_list_testcases",
    "uploads_get_testcases",
    "uploads_save_prd",
    "uploads_list_prds",
    "uploads_get_prd",
]
