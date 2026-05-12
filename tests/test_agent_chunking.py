"""Agent 文档切片层测试。

本测试验证 Step 6 初版规则切片、定位元数据和人工审查落盘产物。
"""
import json
from pathlib import Path

import pytest

from src.agent.chunking import chunk_parsed_document
from src.agent.contracts import DocumentBlock, ParsedDocument, SourceLocation

TEST_DATA_DIR = Path(__file__).resolve().parent / "data"
PARSED_OUTPUT_DIR = TEST_DATA_DIR / "parsed_outputs"
REAL_PARSED_CANDIDATES = [
    PARSED_OUTPUT_DIR / "real_contract.parsed.json",
    PARSED_OUTPUT_DIR / "real_contract.pdf.parsed.json",
]


def _build_block(
    block_id: str,
    text: str,
    *,
    page_number: int,
    layout_index: int,
    start_offset: int,
    element_type: str = "paragraph",
) -> DocumentBlock:
    """构造带来源定位的解析块。"""

    location = SourceLocation(
        file_path="/tmp/contract.docx",
        page_number=page_number,
        block_index=layout_index,
        layout_index=layout_index,
        start_offset=start_offset,
        end_offset=start_offset + len(text),
        element_type=element_type,
    )
    return DocumentBlock(
        block_id=block_id,
        text=text,
        normalized_text=text,
        source_location=location,
        page_number=page_number,
        block_index=layout_index,
        char_count=len(text),
        metadata={"element_type": element_type},
    )


def _build_sample_parsed_document() -> ParsedDocument:
    """构造可稳定验证的解析文档。"""

    blocks = [
        _build_block("b1", "# 第一条 总则", page_number=1, layout_index=1, start_offset=0, element_type="heading"),
        _build_block("b2", "甲方应按合同约定付款。", page_number=1, layout_index=2, start_offset=20),
        _build_block("b3", "| 节点 | 金额 |\n| --- | --- |\n| 验收后 | 100万元 |", page_number=2, layout_index=3, start_offset=50, element_type="table"),
        _build_block("b4", "乙方逾期交付的，应承担违约责任。", page_number=2, layout_index=4, start_offset=120),
    ]
    return ParsedDocument(filename="sample_contract.docx", file_type="docx", file_path="/tmp/contract.docx", blocks=blocks)


def _dump_chunks_for_review(chunks: list[DocumentBlock], name: str) -> tuple[Path, Path]:
    """把 chunk Markdown 和结构化 JSON 临时落盘，便于人工审查。"""

    PARSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = PARSED_OUTPUT_DIR / f"{name}.chunks.md"
    json_path = PARSED_OUTPUT_DIR / f"{name}.chunks.json"
    md_path.write_text(_chunks_to_markdown(chunks), encoding="utf-8")
    json_path.write_text(
        json.dumps([chunk.model_dump(mode="json") for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return md_path, json_path


def _chunks_to_markdown(chunks: list[DocumentBlock]) -> str:
    """生成便于人工审查的 chunk Markdown。"""

    parts = []
    for chunk in chunks:
        pages = chunk.metadata["edit_locator"]["page_numbers"]
        layouts = chunk.metadata["edit_locator"]["layout_indices"]
        parts.append(f"<!-- chunk_id: {chunk.block_id}; pages: {pages}; layouts: {layouts} -->\n\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def test_chunker_respects_hard_limit_and_structure_boundary() -> None:
    """切片结果不能超过硬上限，并应优先在结构块边界回退。"""

    parsed = _build_sample_parsed_document()
    chunks = chunk_parsed_document(parsed, max_chars=50)

    assert len(chunks) >= 2
    assert all(len(chunk.text) <= 50 for chunk in chunks)
    assert chunks[0].metadata["source_block_ids"] == ["b1", "b2"]
    assert chunks[1].metadata["source_block_ids"] == ["b3"]


def test_oversized_block_splits_at_semantic_punctuation() -> None:
    """单个超长块应优先回退到句末符号切分。"""

    text = "甲方应付款。" + ("付款条件明确" * 8) + "。乙方应交付。" + ("交付条件明确" * 8) + "。"
    parsed = ParsedDocument(
        filename="long.docx",
        file_type="docx",
        blocks=[_build_block("long-b1", text, page_number=1, layout_index=1, start_offset=0)],
    )
    chunks = chunk_parsed_document(parsed, max_chars=70)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 70 for chunk in chunks)
    assert chunks[0].text.endswith("。")
    assert chunks[0].metadata["source_locations"][0]["start_offset"] == 0


def test_chunk_metadata_keeps_location_and_edit_locator() -> None:
    """chunk metadata 必须保留页码、版面序号、源块和修改定位参数。"""

    parsed = _build_sample_parsed_document()
    chunks = chunk_parsed_document(parsed, max_chars=4000)
    chunk = chunks[0]

    assert chunk.metadata["page_numbers"] == [1, 2]
    assert chunk.metadata["layout_indices"] == [1, 2, 3, 4]
    assert chunk.metadata["edit_locator"]["source_block_ids"] == ["b1", "b2", "b3", "b4"]
    assert chunk.metadata["edit_locator"]["start_offset"] == 0
    assert chunk.metadata["edit_locator"]["end_offset"] > 120
    assert chunk.source_location.element_type == "chunk"


def test_chunking_outputs_visible_files_for_review() -> None:
    """切片测试应输出可见 Markdown 和 JSON，供人工审查。"""

    parsed = _build_sample_parsed_document()
    chunks = chunk_parsed_document(parsed, max_chars=70)
    md_path, json_path = _dump_chunks_for_review(chunks, "chunking_sample")

    assert md_path.exists()
    assert json_path.exists()
    assert "chunk_id" in md_path.read_text(encoding="utf-8")


def test_real_parsed_document_can_be_chunked_and_dumped_for_review() -> None:
    """如果存在真实解析产物，则切片并输出到 tests/data/parsed_outputs。"""

    parsed_path = next((path for path in REAL_PARSED_CANDIDATES if path.exists()), None)
    if parsed_path is None:
        pytest.skip("请先生成真实解析产物，再执行真实切片审查")

    parsed = ParsedDocument.model_validate_json(parsed_path.read_text(encoding="utf-8"))
    chunks = chunk_parsed_document(parsed)
    md_path, json_path = _dump_chunks_for_review(chunks, parsed_path.stem)

    assert chunks
    assert all(len(chunk.text) <= 4000 for chunk in chunks)
    assert md_path.exists()
    assert json_path.exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
