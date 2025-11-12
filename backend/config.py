"""Backend configuration values and default limits."""

from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_TEMPLATE_FULL_PATH = BASE_DIR / "prompt_template.md"
PROMPT_TEMPLATE_DIFF_PATH = BASE_DIR / "prompt_template_diff.md"


# Vision-related defaults (still overridable by frontend payload)
DISABLE_VISION_DEFAULT = os.environ.get("DISABLE_VISION", "1") == "1"
MAX_IMAGES_PER_BATCH_DEFAULT = int(os.environ.get("MAX_IMAGES_PER_BATCH", "10"))
IMAGE_MAX_SIZE_DEFAULT = int(os.environ.get("IMAGE_MAX_SIZE", "1024"))
IMAGE_QUALITY_DEFAULT = int(os.environ.get("IMAGE_QUALITY", "85"))
MAX_SECTION_CHARS_DEFAULT = int(os.environ.get("MAX_SECTION_CHARS", "60000"))

# Concurrency defaults
BATCH_INFERENCE_CONCURRENCY_DEFAULT = int(os.environ.get("BATCH_INFERENCE_CONCURRENCY", "2"))
IMAGE_DOWNLOAD_CONCURRENCY_DEFAULT = int(os.environ.get("IMAGE_DOWNLOAD_CONCURRENCY", "4"))

# Global rate limiter for model calls
MAX_CONCURRENT_MODEL_CALLS_DEFAULT = int(os.environ.get("MAX_CONCURRENT_MODEL_CALLS", "3"))
MIN_CALL_INTERVAL_MS_DEFAULT = int(os.environ.get("MIN_CALL_INTERVAL_MS", "0"))


__all__ = [
	"BASE_DIR",
	"PROMPT_TEMPLATE_FULL_PATH",
	"PROMPT_TEMPLATE_DIFF_PATH",
	"DISABLE_VISION_DEFAULT",
	"MAX_IMAGES_PER_BATCH_DEFAULT",
	"IMAGE_MAX_SIZE_DEFAULT",
	"IMAGE_QUALITY_DEFAULT",
	"MAX_SECTION_CHARS_DEFAULT",
	"BATCH_INFERENCE_CONCURRENCY_DEFAULT",
	"IMAGE_DOWNLOAD_CONCURRENCY_DEFAULT",
	"MAX_CONCURRENT_MODEL_CALLS_DEFAULT",
	"MIN_CALL_INTERVAL_MS_DEFAULT",
]
