"""Utilities for parsing PRD markdown content into structured data."""

from __future__ import annotations

from typing import Dict, List, Tuple
import re

from backend.config import (
	MAX_IMAGES_PER_BATCH_DEFAULT,
	MAX_SECTION_CHARS_DEFAULT,
)


def extract_images_from_markdown(markdown_text: str) -> List[Tuple[str, int]]:
	"""Return all image URLs with their position in the markdown."""

	pattern = r"!\[.*?\]\((.*?)\)"
	matches: List[Tuple[str, int]] = []
	for match in re.finditer(pattern, markdown_text):
		url = match.group(1).strip()
		if url:
			matches.append((url, match.start()))
	return matches


def parse_prd_sections(markdown_text: str) -> List[Dict]:
	"""Split markdown into sections and attach images to each section."""

	sections: List[Dict] = []
	lines = markdown_text.split('\n')

	current_section = {"title": "前言", "text": "", "images": [], "start_pos": 0, "end_pos": 0}
	current_pos = 0

	for line in lines:
		line_len = len(line) + 1  # include newline

		if line.startswith('# ') or line.startswith('## '):
			if current_section["text"].strip():
				current_section["end_pos"] = current_pos
				current_section["text"] = current_section["text"].strip()
				sections.append(current_section)

			title = line.lstrip('#').strip()
			current_section = {
				"title": title or "无标题章节",
				"text": "",
				"images": [],
				"start_pos": current_pos,
				"end_pos": 0,
			}
		else:
			current_section["text"] += line + '\n'

		current_pos += line_len

	if current_section["text"].strip():
		current_section["end_pos"] = current_pos
		current_section["text"] = current_section["text"].strip()
		sections.append(current_section)

	all_images = extract_images_from_markdown(markdown_text)
	for section in sections:
		section["images"] = [
			img_url for img_url, pos in all_images if section["start_pos"] <= pos < section["end_pos"]
		]

	return sections


def create_batches_from_sections(
	sections: List[Dict],
	max_images: int = MAX_IMAGES_PER_BATCH_DEFAULT,
	max_section_chars: int = MAX_SECTION_CHARS_DEFAULT,
) -> List[Dict]:
	"""Group sections into batches respecting image and text thresholds.

	Notes:
	- Enforces the image cap strictly: if a single section contains more
	  images than ``max_images``, the section will be split into multiple
	  pseudo-sections, each carrying the same text but only a slice of the
	  image URLs so that no batch ever exceeds the cap due to one large section.
	"""

	if max_images <= 0:
		max_images = MAX_IMAGES_PER_BATCH_DEFAULT

	# Expand sections so that any section with too many images is split
	# into multiple smaller pseudo-sections with sliced image arrays.
	expanded_sections: List[Dict] = []
	for section in sections:
		images = list(section.get("images", []))
		if len(images) <= max_images or not images:
			expanded_sections.append(section)
			continue

		# Split images into chunks of size max_images
		for i in range(0, len(images), max_images):
			chunk_imgs = images[i : i + max_images]
			expanded_sections.append(
				{
					"title": section.get("title", "无标题章节"),
					"text": section.get("text", ""),
					"images": chunk_imgs,
					# position values are not used beyond parsing stage
					"start_pos": section.get("start_pos", 0),
					"end_pos": section.get("end_pos", 0),
				}
			)

	batches: List[Dict] = []
	current_batch = {"sections": [], "total_images": 0, "total_chars": 0}

	for section in expanded_sections:
		section_images = len(section.get("images", []))
		section_chars = len(section.get("text", ""))

		if current_batch["sections"] and (
			current_batch["total_images"] + section_images > max_images
			or current_batch["total_chars"] + section_chars > max_section_chars
		):
			batches.append(current_batch)
			current_batch = {"sections": [], "total_images": 0, "total_chars": 0}

		current_batch["sections"].append(section)
		current_batch["total_images"] += section_images
		current_batch["total_chars"] += section_chars

	if current_batch["sections"]:
		batches.append(current_batch)

	return batches


__all__ = [
	"extract_images_from_markdown",
	"parse_prd_sections",
	"create_batches_from_sections",
]
