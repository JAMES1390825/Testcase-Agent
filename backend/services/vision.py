"""Helpers for multimodal message construction and image preprocessing."""

from __future__ import annotations

import base64
import time
from io import BytesIO
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
import urllib3
from PIL import Image

from backend.config import IMAGE_MAX_SIZE_DEFAULT, IMAGE_QUALITY_DEFAULT

# Suppress warnings for requests made with verify=False when fetching images
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def download_and_process_image(
	url: str,
	max_size: int = IMAGE_MAX_SIZE_DEFAULT,
	quality: int = IMAGE_QUALITY_DEFAULT,
) -> str | None:
	"""Download an image, resize/compress it, and return a base64 data URL."""

	max_retries = 3
	retry_delay = 2

	for attempt in range(max_retries):
		try:
			headers = {
				"User-Agent": (
					"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
					"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
				),
				"Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
				"Accept-Encoding": "gzip, deflate, br",
				"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
				"Connection": "keep-alive",
			}

			response = requests.get(
				url,
				timeout=15,
				headers=headers,
				verify=False,
				stream=True,
			)
			response.raise_for_status()

			img = Image.open(BytesIO(response.content))

			if img.mode in ("RGBA", "LA", "P"):
				background = Image.new("RGB", img.size, (255, 255, 255))
				if img.mode == "P":
					img = img.convert("RGBA")
				mask = img.split()[-1] if img.mode == "RGBA" else None
				background.paste(img, mask=mask)
				img = background

			img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

			buffered = BytesIO()
			img.save(buffered, format="JPEG", quality=quality, optimize=True)
			img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

			return f"data:image/jpeg;base64,{img_base64}"

		except requests.exceptions.SSLError as exc:
			if attempt < max_retries - 1:
				time.sleep(retry_delay)
				continue
			print(f"处理图片失败（SSL 错误，已重试 {max_retries} 次）{url}: {exc}")
			return None
		except Exception as exc:
			if attempt < max_retries - 1:
				time.sleep(retry_delay)
				continue
			print(f"处理图片失败（已重试 {max_retries} 次）{url}: {exc}")
			return None

	return None


def build_vision_messages(
	batch: Dict,
	prompt_template: str,
	batch_index: int,
	total_batches: int,
	*,
	use_deepseek: bool = False,
	image_max_size: int = IMAGE_MAX_SIZE_DEFAULT,
	image_quality: int = IMAGE_QUALITY_DEFAULT,
	image_download_concurrency: int = 4,
) -> List[Dict]:
	"""Assemble chat messages containing text and optional images."""

	combined_text = "\n\n".join(
		[f"## {section['title']}\n{section['text']}" for section in batch["sections"]]
	)

	batch_info = ""
	if total_batches > 1:
		start_id = batch_index * 200 + 1
		batch_info = (
			f"\n\n【重要提示】这是第 {batch_index + 1}/{total_batches} 批次的 PRD 内容，"
			"请基于本批次内容生成测试用例。\n"
			f"【用例编号规则】本批次的用例 ID 必须从 {start_id:04d} 开始递增编号，"
			"格式为：TC-[模块]-[功能]-{start_id:04d}、TC-[模块]-[功能]-{start_id + 1:04d}... 依次类推。\n"
			"【严格要求】每个用例 ID 的数字部分必须唯一且连续递增，不得重复使用已出现的编号。"
		)
	else:
		batch_info = (
			"\n\n【用例编号规则】用例 ID 格式为：TC-[模块]-[功能]-[序号]，"
			"序号从 0001 开始递增（0001、0002、0003...），每个 ID 必须唯一。"
		)

	final_prompt = prompt_template.format(prd_content=combined_text) + batch_info

	all_image_urls = []
	for section in batch["sections"]:
		all_image_urls.extend(section.get("images", []))

	if use_deepseek:
		image_section = "\n\n" + "\n".join([f"![图片]({url})" for url in all_image_urls])
		messages = [
			{
				"role": "system",
				"content": "你是一名资深SQA工程师。请严格基于以下PRD（包含文本和图片）生成测试用例，使用简体中文，不得编造无关场景。",
			},
			{"role": "user", "content": final_prompt + image_section},
		]
		return messages

	content: List[Dict] = [{"type": "text", "text": final_prompt}]

	# Concurrent image processing with bounded workers
	if image_download_concurrency > 1 and len(all_image_urls) > 1:
		def task(url):
			return url, download_and_process_image(url, image_max_size, image_quality)

		with ThreadPoolExecutor(max_workers=image_download_concurrency) as ex:
			futures = [ex.submit(task, u) for u in all_image_urls]
			# Preserve order according to original URL list
			results: Dict[str, str | None] = {}
			for fut in as_completed(futures):
				url, res = fut.result()
				results[url] = res
		for img_url in all_image_urls:
			processed = results.get(img_url)
			if processed:
				content.append({"type": "image_url", "image_url": {"url": processed}})
			else:
				print(f"跳过无法处理的图片: {img_url}")
	else:
		for img_url in all_image_urls:
			processed = download_and_process_image(img_url, image_max_size, image_quality)
			if processed:
				content.append({"type": "image_url", "image_url": {"url": processed}})
			else:
				print(f"跳过无法处理的图片: {img_url}")

	messages = [
		{
			"role": "system",
			"content": "你是一名资深SQA工程师。请严格基于以下PRD（包含文本和图片）生成测试用例，使用简体中文，不得编造无关场景。",
		},
		{"role": "user", "content": content},
	]
	return messages


__all__ = ["download_and_process_image", "build_vision_messages"]
