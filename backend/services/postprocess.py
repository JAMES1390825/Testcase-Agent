"""Helpers for cleaning and merging AI-generated tables (Markdown/CSV),
plus validation utilities for strict CSV enforcement.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple
import csv
import re
import io


def sanitize_table_rows(markdown_text: str) -> str:
	"""Ensure table rows are single-line by replacing cell newlines."""

	lines: List[str] = []
	for line in markdown_text.splitlines():
		if line.strip().startswith('|'):
			cells = line.split('|')
			sanitized = []
			for cell in cells:
				clean = cell.replace('\n', '；').replace('\r', '').strip()
				clean = ' '.join(clean.split())
				sanitized.append(clean)
			lines.append('|'.join(sanitized))
		else:
			lines.append(line)
	return '\n'.join(lines)


def deduplicate_test_case_ids(markdown_text: str) -> str:
	"""Detect duplicate test case IDs and reassign unique identifiers."""

	lines = markdown_text.splitlines()
	seen_ids = set()
	result_lines: List[str] = []
	counter = 1

	id_pattern = re.compile(r'(TC-[A-Z]+-[A-Z]+)-(\d+)')

	for line in lines:
		if not line.strip().startswith('|'):
			result_lines.append(line)
			continue

		cells = [cell.strip() for cell in line.split('|')]

		if len(cells) > 2 and ('用例ID' in cells[1] or ':---' in cells[1]):
			result_lines.append(line)
			continue

		if len(cells) > 1 and cells[1]:
			original_id = cells[1]
			if original_id.startswith('TC-'):
				if original_id in seen_ids:
					match = id_pattern.match(original_id)
					prefix = match.group(1) if match else 'TC-AUTO'

					new_id = f"{prefix}-{counter:04d}"
					while new_id in seen_ids:
						counter += 1
						new_id = f"{prefix}-{counter:04d}"

					cells[1] = new_id
					seen_ids.add(new_id)
				else:
					seen_ids.add(original_id)
				counter += 1

		result_lines.append('|'.join(cells))

	return '\n'.join(result_lines)


def merge_markdown_tables(responses: Iterable[str]) -> str:
	"""Combine multiple markdown tables keeping only the first header."""

	combined_lines: List[str] = []
	header_seen = False
	sep_seen = False

	for chunk in responses:
		if not chunk:
			continue
		lines = chunk.splitlines()
		for idx, line in enumerate(lines):
			if not line.strip().startswith('|'):
				continue

			is_separator = '|' in line and ('---' in line or '—' in line)
			if not header_seen and is_separator:
				if idx - 1 >= 0 and lines[idx - 1].strip().startswith('|'):
					combined_lines.append(lines[idx - 1])
				combined_lines.append(line)
				header_seen = True
				sep_seen = True
				continue

			if header_seen and sep_seen and is_separator:
				continue

			combined_lines.append(line)

	return '\n'.join(combined_lines).strip()


__all__ = [
	"sanitize_table_rows",
	"deduplicate_test_case_ids",
	"merge_markdown_tables",
]


# --- CSV helpers ---

def merge_csv_texts(chunks: Iterable[str]) -> str:
	"""Merge multiple CSV texts keeping the first header only.

	Assumes each chunk is plain CSV text with first line as header.
	"""
	header: str | None = None
	rows: List[str] = []

	for chunk in chunks:
		if not chunk:
			continue
		lines = [ln for ln in chunk.replace("\r\n", "\n").replace("\r", "\n").split("\n") if ln != ""]
		if not lines:
			continue
		if header is None:
			header = lines[0]
			rows.extend(lines[1:])
		else:
			# Skip header line of subsequent chunks if identical or not
			# We conservatively drop only the first line, assuming it's header.
			rows.extend(lines[1:] if len(lines) > 1 else [])

	if header is None:
		return ""
	return "\r\n".join([header] + rows)


__all__.append("merge_csv_texts")


# --- CSV validation ---

EXPECTED_HEADER = [
	"用例ID",
	"模块",
	"子模块",
	"测试项",
	"前置条件",
	"操作步骤",
	"预期结果",
	"用例类型",
]


def _strip_code_fences(text: str) -> str:
	s = text.strip()
	if s.startswith("```") and s.endswith("```"):
		# remove first and last fence lines
		lines = s.splitlines()
		if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
			return "\n".join(lines[1:-1]).strip()
	return text


def validate_strict_csv(csv_text: str) -> Tuple[bool, str]:
	"""Validate CSV content strictly against EXPECTED_HEADER schema.

	Returns (ok, reason). When ok is False, reason contains a brief message.
	"""
	if not csv_text or not csv_text.strip():
		return False, "输出为空"

	csv_text = _strip_code_fences(csv_text)
	normalized = csv_text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
	reader = csv.reader(normalized.split("\n"))

	try:
		rows = list(reader)
	except Exception as exc:  # noqa: BLE001
		return False, f"CSV 解析失败: {exc}"

	if not rows:
		return False, "没有任何行"

	header = [col.strip() for col in rows[0]]
	if header != EXPECTED_HEADER:
		return False, (
			"表头不符合规范，应为：" + ",".join(EXPECTED_HEADER)
		)

	if len(rows) < 2:
		return False, "没有数据行"

	# Ensure every row has the same number of columns
	expected_len = len(EXPECTED_HEADER)
	for idx, r in enumerate(rows[1:], start=2):
		if len(r) != expected_len:
			return False, f"第 {idx} 行列数不一致，应为 {expected_len} 列"

	return True, ""


__all__.extend(["validate_strict_csv", "EXPECTED_HEADER"])


# --- CSV auto-repair (best-effort) ---

def coerce_to_strict_csv(csv_text: str) -> str:
	"""Best-effort repair to produce a valid 8-column CSV.

	Strategy:
	- Strip surrounding code fences/BOM and normalize newlines
	- Locate a header line that matches EXPECTED_HEADER either with ',' or '，'
	- If the header uses Chinese comma, convert delimiters to ',' for the whole text
	- Parse rows with csv.reader; for each row:
	  * If len(row) > 8: merge tail into the last cell with commas
	  * If len(row) < 8: right-pad empty strings
	  * Skip blank-only lines
	- Rebuild CSV with the exact expected header

	This does not try to be perfect; it aims to avoid trivial 500s caused by
	model outputs like a trailing explanation line or a stray comma.
	"""

	if not csv_text:
		return ""

	text = _strip_code_fences(csv_text).lstrip("\ufeff")
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	lines = [ln for ln in text.split("\n") if ln.strip() != ""]
	if not lines:
		return ""

	# Find header line index and detect delimiter
	head_idx = -1
	uses_cn_comma = False
	for i, ln in enumerate(lines):
		# Exact English comma header
		if [c.strip() for c in ln.split(',')] == EXPECTED_HEADER:
			head_idx = i
			break
		# Chinese comma variant
		if [c.strip() for c in ln.split('，')] == EXPECTED_HEADER:
			head_idx = i
			uses_cn_comma = True
			break

	if head_idx == -1:
		# Try a fuzzy match: line contains most header tokens and at least 7 commas
		for i, ln in enumerate(lines):
			comma = ln.count(',')
			cncomma = ln.count('，')
			if ("用例ID" in ln and "用例类型" in ln) and (comma >= 7 or cncomma >= 7):
				head_idx = i
				uses_cn_comma = cncomma > comma
				break

	if head_idx == -1:
		# No recognizable header; nothing we can do safely
		return csv_text

	payload_lines = lines[head_idx:]
	joined = "\n".join(payload_lines)
	if uses_cn_comma:
		joined = joined.replace('，', ',')

	# Feed to CSV reader and coerce row widths
	reader = csv.reader(io.StringIO(joined))
	rows = list(reader)
	if not rows:
		return csv_text

	expected_len = len(EXPECTED_HEADER)
	result_io = io.StringIO()
	writer = csv.writer(result_io, lineterminator="\r\n")
	writer.writerow(EXPECTED_HEADER)

	for r in rows[1:]:
		# Skip completely empty rows
		if not any(cell.strip() for cell in r):
			continue
		if len(r) > expected_len:
			merged_last = ",".join(r[expected_len - 1:]).strip()
			r = r[: expected_len - 1] + [merged_last]
		elif len(r) < expected_len:
			r = r + [""] * (expected_len - len(r))
		writer.writerow([cell.strip() for cell in r])

	return result_io.getvalue()


__all__.append("coerce_to_strict_csv")
