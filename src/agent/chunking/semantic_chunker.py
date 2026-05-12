"""规则语义切片器。

本文件把解析层 ParsedDocument 切成审阅前 chunk，保证硬长度上限并保留源文档定位。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.agent.contracts.document import DocumentBlock, ParsedDocument, SourceLocation

DEFAULT_CHUNK_MAX_CHARS = 4000
SEMANTIC_ENDINGS = "。！？；.!?;"


@dataclass(frozen=True)
class _SourceSegment:
    """切片前的最小合并片段，通常对应解析层块或超长块的一段。"""

    text: str
    source_block: DocumentBlock
    local_start: int = 0
    local_end: int = 0


def chunk_parsed_document(
    parsed_document: ParsedDocument,
    *,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
) -> list[DocumentBlock]:
    """按 Markdown 结构和句末符号切分解析文档。"""

    _validate_max_chars(max_chars)
    source_blocks = _get_source_blocks(parsed_document)
    segments = _build_source_segments(source_blocks, max_chars)
    grouped_segments = _group_segments_by_limit(segments, max_chars)
    return [
        _make_chunk_block(parsed_document, chunk_index, group, max_chars)
        for chunk_index, group in enumerate(grouped_segments, start=1)
    ]


def _validate_max_chars(max_chars: int) -> None:
    """校验 chunk 硬上限配置。"""

    if max_chars <= 0:
        raise ValueError("max_chars_must_be_positive")


def _get_source_blocks(parsed_document: ParsedDocument) -> list[DocumentBlock]:
    """优先使用解析层结构块，缺失时退回合同 Markdown 全文。"""

    blocks = [block for block in parsed_document.blocks if block.text.strip()]
    if blocks:
        return blocks
    content = (parsed_document.contract_content or "").strip()
    if not content:
        return []
    return [_build_fallback_source_block(parsed_document, content)]


def _build_fallback_source_block(parsed_document: ParsedDocument, content: str) -> DocumentBlock:
    """为只有全文没有结构块的解析结果构造来源块。"""

    file_part = _document_file_part(parsed_document)
    location = SourceLocation(
        file_path=parsed_document.file_path,
        block_index=1,
        layout_index=1,
        start_offset=0,
        end_offset=len(content),
        element_type="document",
    )
    return DocumentBlock(
        block_id=f"{file_part}-raw-block-1",
        text=content,
        normalized_text=content,
        source_location=location,
        block_index=1,
        char_count=len(content),
        metadata={"element_type": "document", "content_format": "markdown"},
    )


def _build_source_segments(source_blocks: list[DocumentBlock], max_chars: int) -> list[_SourceSegment]:
    """把解析层块转换为可合并片段，超长块按语义边界拆小。"""

    segments: list[_SourceSegment] = []
    for block in source_blocks:
        text = block.text.strip()
        if len(text) <= max_chars:
            segments.append(_SourceSegment(text=text, source_block=block, local_start=0, local_end=len(text)))
        else:
            segments.extend(_split_oversized_block(block, text, max_chars))
    return segments


def _split_oversized_block(block: DocumentBlock, text: str, max_chars: int) -> list[_SourceSegment]:
    """拆分单个超长来源块，优先回退到 Markdown 或语义结束符。"""

    segments: list[_SourceSegment] = []
    start = 0
    while start < len(text):
        end = _find_split_end(text, start, max_chars)
        segment_text = text[start:end].strip()
        if segment_text:
            segments.append(_SourceSegment(text=segment_text, source_block=block, local_start=start, local_end=end))
        start = _skip_leading_space(text, end)
    return segments


def _find_split_end(text: str, start: int, max_chars: int) -> int:
    """寻找不超过硬上限的最佳切分点。"""

    hard_end = min(start + max_chars, len(text))
    if hard_end >= len(text):
        return len(text)
    candidate = _find_markdown_boundary(text, start, hard_end)
    if candidate is None:
        candidate = _find_semantic_boundary(text, start, hard_end)
    if candidate is None:
        candidate = _find_line_boundary(text, start, hard_end)
    if candidate is None or candidate <= start:
        return hard_end
    return candidate


def _find_markdown_boundary(text: str, start: int, end: int) -> int | None:
    """优先回退到 Markdown 结构边界。"""

    window = text[start:end]
    candidates = [
        window.rfind("\n\n"),
        window.rfind("\n#"),
        window.rfind("\n|"),
    ]
    best = max(candidates)
    if best <= 0:
        return None
    return start + best


def _find_semantic_boundary(text: str, start: int, end: int) -> int | None:
    """回退到中文或英文句末符号。"""

    for index in range(end - 1, start, -1):
        if text[index] in SEMANTIC_ENDINGS:
            return index + 1
    return None


def _find_line_boundary(text: str, start: int, end: int) -> int | None:
    """兜底回退到最近换行。"""

    index = text.rfind("\n", start, end)
    if index <= start:
        return None
    return index


def _skip_leading_space(text: str, start: int) -> int:
    """跳过切分点后的空白字符。"""

    while start < len(text) and text[start].isspace():
        start += 1
    return start


def _group_segments_by_limit(segments: list[_SourceSegment], max_chars: int) -> list[list[_SourceSegment]]:
    """按硬长度上限合并片段，超限时回退到上一片段边界。"""

    groups: list[list[_SourceSegment]] = []
    current: list[_SourceSegment] = []
    current_length = 0
    for segment in segments:
        projected = current_length + _joiner_length(current) + len(segment.text)
        if current and projected > max_chars:
            groups.append(current)
            current = [segment]
            current_length = len(segment.text)
        else:
            current.append(segment)
            current_length = projected
    if current:
        groups.append(current)
    return groups


def _joiner_length(current: list[_SourceSegment]) -> int:
    """计算追加片段时需要的 Markdown 空行长度。"""

    return 2 if current else 0


def _make_chunk_block(
    parsed_document: ParsedDocument,
    chunk_index: int,
    segments: list[_SourceSegment],
    max_chars: int,
) -> DocumentBlock:
    """把一组来源片段聚合为 chunk 块。"""

    text = "\n\n".join(segment.text for segment in segments)
    metadata = _build_chunk_metadata(segments, max_chars)
    location = _build_chunk_location(segments, chunk_index)
    return DocumentBlock(
        block_id=f"{_document_file_part(parsed_document)}-chunk-{chunk_index}",
        text=text,
        normalized_text=text,
        source_location=location,
        section_title=_first_section_title(segments),
        page_number=location.page_number if location else None,
        block_index=chunk_index,
        char_count=len(text),
        metadata=metadata,
    )


def _build_chunk_metadata(segments: list[_SourceSegment], max_chars: int) -> dict[str, Any]:
    """构造 chunk 级定位和修改参数元数据。"""

    source_locations = [_segment_location_dump(segment) for segment in segments]
    page_numbers = _unique_not_none(item.get("page_number") for item in source_locations)
    layout_indices = _unique_not_none(item.get("layout_index") for item in source_locations)
    source_block_ids = [segment.source_block.block_id for segment in segments]
    return {
        "element_type": "chunk",
        "chunking_strategy": "markdown_semantic_v1",
        "hard_max_chars": max_chars,
        "source_block_ids": source_block_ids,
        "source_locations": source_locations,
        "page_numbers": page_numbers,
        "layout_indices": layout_indices,
        "edit_locator": _build_edit_locator(source_block_ids, source_locations, page_numbers, layout_indices),
    }


def _segment_location_dump(segment: _SourceSegment) -> dict[str, Any]:
    """生成片段级来源定位。"""

    location = segment.source_block.source_location
    if location is None:
        return {"block_id": segment.source_block.block_id}
    adjusted = _adjust_segment_location(location, segment)
    data = adjusted.model_dump(mode="json")
    data["block_id"] = segment.source_block.block_id
    return data


def _adjust_segment_location(location: SourceLocation, segment: _SourceSegment) -> SourceLocation:
    """根据超长块内局部偏移修正来源定位。"""

    start_offset = _offset_with_delta(location.start_offset, segment.local_start)
    end_offset = _offset_with_delta(location.start_offset, segment.local_end)
    return SourceLocation(
        file_path=location.file_path,
        contract_content_path=location.contract_content_path,
        page_number=location.page_number,
        block_index=location.block_index,
        layout_index=location.layout_index,
        start_offset=start_offset,
        end_offset=end_offset,
        element_type=location.element_type,
    )


def _offset_with_delta(base: int | None, delta: int) -> int | None:
    """按局部偏移推导源文本偏移。"""

    if base is None:
        return None
    return base + delta


def _build_edit_locator(
    source_block_ids: list[str],
    source_locations: list[dict[str, Any]],
    page_numbers: list[int],
    layout_indices: list[int],
) -> dict[str, Any]:
    """构造后续修改工具调用可用的定位参数。"""

    return {
        "source_block_ids": source_block_ids,
        "page_numbers": page_numbers,
        "layout_indices": layout_indices,
        "start_offset": _min_not_none(item.get("start_offset") for item in source_locations),
        "end_offset": _max_not_none(item.get("end_offset") for item in source_locations),
    }


def _build_chunk_location(segments: list[_SourceSegment], chunk_index: int) -> SourceLocation | None:
    """构造 chunk 聚合定位，跨页时页码留空并在 metadata 保留全部页码。"""

    dumps = [_segment_location_dump(segment) for segment in segments]
    file_path = _first_not_none(item.get("file_path") for item in dumps)
    if file_path is None:
        return None
    page_numbers = _unique_not_none(item.get("page_number") for item in dumps)
    layout_indices = _unique_not_none(item.get("layout_index") for item in dumps)
    return SourceLocation(
        file_path=file_path,
        page_number=page_numbers[0] if len(page_numbers) == 1 else None,
        block_index=chunk_index,
        layout_index=layout_indices[0] if layout_indices else None,
        start_offset=_min_not_none(item.get("start_offset") for item in dumps),
        end_offset=_max_not_none(item.get("end_offset") for item in dumps),
        element_type="chunk",
    )


def _document_file_part(parsed_document: ParsedDocument) -> str:
    """生成 chunk ID 使用的文件标识。"""

    name = parsed_document.file_path or parsed_document.filename
    return Path(name).stem.replace(" ", "_")


def _first_section_title(segments: list[_SourceSegment]) -> str | None:
    """提取 chunk 内第一个章节标题。"""

    for segment in segments:
        if segment.source_block.section_title:
            return segment.source_block.section_title
    return None


def _unique_not_none(values: Any) -> list[int]:
    """返回保持顺序的非空整数列表。"""

    result: list[int] = []
    for value in values:
        if isinstance(value, int) and value not in result:
            result.append(value)
    return result


def _first_not_none(values: Any) -> Any:
    """返回第一个非空值。"""

    for value in values:
        if value is not None:
            return value
    return None


def _min_not_none(values: Any) -> int | None:
    """返回非空最小整数。"""

    numbers = [value for value in values if isinstance(value, int)]
    return min(numbers) if numbers else None


def _max_not_none(values: Any) -> int | None:
    """返回非空最大整数。"""

    numbers = [value for value in values if isinstance(value, int)]
    return max(numbers) if numbers else None


def _main_test_semantic_chunker() -> None:
    """执行规则语义切片器的本文件自检。"""

    parsed = ParsedDocument(
        filename="合同.md",
        file_type="md",
        contract_content="第一句。" * 20,
    )
    chunks = chunk_parsed_document(parsed, max_chars=50)
    assert chunks
    assert all(len(chunk.text) <= 50 for chunk in chunks)
    assert chunks[0].metadata["chunking_strategy"] == "markdown_semantic_v1"


if __name__ == "__main__":
    _main_test_semantic_chunker()
