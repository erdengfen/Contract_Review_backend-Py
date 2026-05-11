"""普通 PDF 解析 pipeline。

本文件负责普通 PDF 的本地 text layer 提取、可选 MinerU Markdown 融合和 ParsedDocument 输出。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from src.agent.contracts.document import DocumentBlock, ParsedDocument, SourceLocation
from src.agent.parsers.mineru_light_client import MinerULightResult
from src.agent.parsers.pdf_text_layer import PdfTextLayerError, PdfTextPage, extract_pdf_text_layer


class MinerULightParser(Protocol):
    """普通 PDF 解析所需的 MinerU 轻量客户端协议。"""

    def parse_file(self, file_path: str, *, language: str = "ch") -> MinerULightResult:
        """解析文件并返回 Markdown。"""


def parse_text_pdf_file(
    file_path: str,
    *,
    filename: str | None = None,
    file_id: int | None = None,
    original_file_path: str | None = None,
    mineru_client: MinerULightParser | None = None,
) -> ParsedDocument:
    """解析普通 PDF，优先融合 MinerU Markdown，失败时使用本地 text layer。"""

    path = Path(file_path).expanduser().resolve()
    source_path = original_file_path or str(path)
    pages, warnings = _safe_extract_text_layer(str(path))
    mineru_result, mineru_warnings = _safe_parse_mineru(str(path), mineru_client)
    warnings.extend(mineru_warnings)
    if mineru_result and mineru_result.markdown:
        return _document_from_mineru(filename or path.name, source_path, file_id, pages, mineru_result, warnings)
    return _document_from_text_layer(filename or path.name, source_path, file_id, pages, warnings)


def _safe_extract_text_layer(file_path: str) -> tuple[list[PdfTextPage], list[str]]:
    """提取本地 text layer，失败时保留可追踪告警。"""

    try:
        pages = extract_pdf_text_layer(file_path)
    except PdfTextLayerError as error:
        return [], [str(error)]
    if not pages:
        return [], ["pdf_text_layer_empty"]
    return pages, []


def _safe_parse_mineru(
    file_path: str,
    mineru_client: MinerULightParser | None,
) -> tuple[MinerULightResult | None, list[str]]:
    """调用可选 MinerU 客户端，失败时回退到本地 text layer。"""

    if mineru_client is None:
        return None, ["mineru_light_not_configured"]
    try:
        result = mineru_client.parse_file(file_path, language="ch")
    except Exception:
        return None, ["mineru_light_failed"]
    if result.state != "done" or not result.markdown:
        return result, [*result.warnings, f"mineru_light_state:{result.state}"]
    return result, result.warnings


def _document_from_mineru(
    filename: str,
    source_path: str,
    file_id: int | None,
    pages: list[PdfTextPage],
    mineru_result: MinerULightResult,
    warnings: list[str],
) -> ParsedDocument:
    """使用 MinerU Markdown 作为主视图，并用本地 text layer 辅助页码回填。"""

    markdown = _normalize_markdown(mineru_result.markdown or "")
    blocks = _blocks_from_markdown(markdown, source_path, file_id, pages)
    warnings = _add_page_match_warning(warnings, blocks, pages)
    return _build_parsed_document(filename, source_path, markdown, blocks, "mineru_light", warnings, mineru_result)


def _document_from_text_layer(
    filename: str,
    source_path: str,
    file_id: int | None,
    pages: list[PdfTextPage],
    warnings: list[str],
) -> ParsedDocument:
    """使用本地 text layer 生成 Markdown 和结构块。"""

    markdown = _pages_to_markdown(pages)
    blocks = _blocks_from_pages(pages, source_path, file_id)
    parse_status = "success" if blocks else "failed"
    parsed = _build_parsed_document(filename, source_path, markdown, blocks, "text_layer", warnings, None)
    parsed.parse_status = parse_status
    return parsed


def _build_parsed_document(
    filename: str,
    source_path: str,
    markdown: str,
    blocks: list[DocumentBlock],
    content_source: str,
    warnings: list[str],
    mineru_result: MinerULightResult | None,
) -> ParsedDocument:
    """构造普通 PDF 解析结果。"""

    return ParsedDocument(
        filename=filename,
        file_type="pdf",
        file_path=source_path,
        contract_content=markdown or None,
        blocks=blocks,
        parser_name="pymupdf-text-layer+mineru-light",
        parse_status="success" if blocks else "failed",
        warnings=warnings,
        metadata=_build_document_metadata(blocks, content_source, mineru_result),
    )


def _build_document_metadata(
    blocks: list[DocumentBlock],
    content_source: str,
    mineru_result: MinerULightResult | None,
) -> dict[str, object]:
    """生成 PDF 文档级元数据。"""

    metadata: dict[str, object] = {
        "content_format": "markdown",
        "content_source": content_source,
        "block_count": len(blocks),
        "page_number_source": "text_layer",
    }
    if mineru_result:
        metadata["mineru_state"] = mineru_result.state
        metadata["mineru_result_url"] = mineru_result.result_url
        metadata["mineru_task_id"] = mineru_result.task_id
    return metadata


def _blocks_from_pages(
    pages: list[PdfTextPage],
    source_path: str,
    file_id: int | None,
) -> list[DocumentBlock]:
    """把 text layer 页面转换为解析块。"""

    blocks: list[DocumentBlock] = []
    cursor = 0
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        block = _make_block(file_id, source_path, len(blocks) + 1, text, "text", page.page_number, cursor)
        blocks.append(block)
        cursor = (block.source_location.end_offset or cursor) + 2
    return blocks


def _blocks_from_markdown(
    markdown: str,
    source_path: str,
    file_id: int | None,
    pages: list[PdfTextPage],
) -> list[DocumentBlock]:
    """把 MinerU Markdown 转换为解析块，并尝试回填页码。"""

    blocks: list[DocumentBlock] = []
    cursor = 0
    for text, element_type in _split_markdown_blocks(markdown):
        page_number = _infer_page_number(text, pages)
        block = _make_block(file_id, source_path, len(blocks) + 1, text, element_type, page_number, cursor)
        blocks.append(block)
        cursor = (block.source_location.end_offset or cursor) + 2
    return blocks


def _make_block(
    file_id: int | None,
    source_path: str,
    block_index: int,
    text: str,
    element_type: str,
    page_number: int | None,
    start_offset: int,
) -> DocumentBlock:
    """创建 PDF 解析块。"""

    end_offset = start_offset + len(text)
    location = SourceLocation(
        file_path=source_path,
        page_number=page_number,
        block_index=block_index,
        layout_index=block_index,
        start_offset=start_offset,
        end_offset=end_offset,
        element_type=element_type,
    )
    return DocumentBlock(
        block_id=_build_block_id(file_id, source_path, page_number, block_index),
        text=text,
        normalized_text=_markdown_to_plain_text(text),
        source_location=location,
        page_number=page_number,
        block_index=block_index,
        char_count=len(text),
        metadata={"element_type": element_type, "content_format": "markdown", "page_number_source": "text_layer"},
    )


def _build_block_id(file_id: int | None, source_path: str, page_number: int | None, block_index: int) -> str:
    """生成 PDF 解析块唯一标识。"""

    file_part = f"file-{file_id}" if file_id is not None else Path(source_path).stem
    page_part = page_number if page_number is not None else "unknown"
    return f"{file_part}-page-{page_part}-block-{block_index}"


def _split_markdown_blocks(markdown: str) -> list[tuple[str, str]]:
    """按 Markdown 标题、表格和空行拆出解析块。"""

    blocks: list[tuple[str, str]] = []
    current: list[str] = []
    current_type = "paragraph"
    for line in markdown.splitlines():
        line_type = _line_element_type(line)
        if _should_flush_block(line, line_type, current_type, current):
            blocks.append(("\n".join(current).strip(), current_type))
            current = []
        current_type = line_type if not current else current_type
        if line.strip():
            current.append(line.rstrip())
    if current:
        blocks.append(("\n".join(current).strip(), current_type))
    return [(text, element_type) for text, element_type in blocks if text]


def _line_element_type(line: str) -> str:
    """识别 Markdown 行的元素类型。"""

    stripped = line.strip()
    if stripped.startswith("#"):
        return "heading"
    if stripped.startswith("|") and stripped.endswith("|"):
        return "table"
    if stripped.startswith(("- ", "* ", "+ ")):
        return "list_item"
    return "paragraph"


def _should_flush_block(line: str, line_type: str, current_type: str, current: list[str]) -> bool:
    """判断是否需要结束当前 Markdown 块。"""

    if not current:
        return False
    if not line.strip():
        return True
    return line_type != current_type


def _pages_to_markdown(pages: list[PdfTextPage]) -> str:
    """把 text layer 页面转换为带页标的 Markdown。"""

    parts = [f"<!-- page_number: {page.page_number} -->\n\n{page.text.strip()}" for page in pages if page.text.strip()]
    return "\n\n".join(parts)


def _normalize_markdown(markdown: str) -> str:
    """清理 MinerU Markdown 外层空白。"""

    return markdown.replace("\r\n", "\n").strip()


def _infer_page_number(text: str, pages: list[PdfTextPage]) -> int | None:
    """用本地 text layer 对 Markdown 块做轻量页码回填。"""

    needle = _normalize_for_matching(text)
    if not needle:
        return None
    for page in pages:
        if needle[:24] in _normalize_for_matching(page.text):
            return page.page_number
    return _best_overlap_page(needle, pages)


def _best_overlap_page(needle: str, pages: list[PdfTextPage]) -> int | None:
    """使用字符集合重叠度兜底推断页码。"""

    best_page = None
    best_score = 0
    needle_chars = set(needle[:80])
    for page in pages:
        score = len(needle_chars & set(_normalize_for_matching(page.text)))
        if score > best_score:
            best_page = page.page_number
            best_score = score
    return best_page if best_score >= 8 else None


def _normalize_for_matching(text: str) -> str:
    """把文本转换为适合页码匹配的紧凑字符串。"""

    plain = _markdown_to_plain_text(text)
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", plain)


def _markdown_to_plain_text(text: str) -> str:
    """清理 Markdown 标记，得到轻量纯文本。"""

    return re.sub(r"[#|`*_>\-\[\]():]+", " ", text).strip()


def _add_page_match_warning(
    warnings: list[str],
    blocks: list[DocumentBlock],
    pages: list[PdfTextPage],
) -> list[str]:
    """为未能回填页码的 MinerU 块添加告警。"""

    if pages and any(block.page_number is None for block in blocks):
        return [*warnings, "pdf_page_number_partially_unmatched"]
    return warnings


def _main_test_pdf_parser() -> None:
    """执行普通 PDF 解析器的本文件自检。"""

    try:
        parsed = parse_text_pdf_file("/tmp/missing.pdf")
    except Exception as error:
        raise AssertionError("缺失 PDF 应返回失败结构，不应抛出异常") from error
    assert parsed.parse_status == "failed"
    assert "pdf_file_missing" in parsed.warnings


if __name__ == "__main__":
    _main_test_pdf_parser()
