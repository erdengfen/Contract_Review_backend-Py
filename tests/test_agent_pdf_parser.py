"""Agent 普通 PDF 解析层测试。

本测试验证 Step 5.2 普通 PDF 的本地 text layer、可选 MinerU Markdown 融合和 Step 4 路由接线。
"""
import json
from pathlib import Path

import fitz
import pytest

from src.agent.contracts import DocumentIntakeRequest
from src.agent.document_intake import sense_document
from src.agent.parsers import MinerULightResult, parse_document_from_sensing, parse_text_pdf_file

TEST_DATA_DIR = Path(__file__).resolve().parent / "data"
REAL_PDF_PATH = TEST_DATA_DIR / "real_contract.pdf"
PARSED_OUTPUT_DIR = TEST_DATA_DIR / "parsed_outputs"


class _FakeMinerUClient:
    """用于测试 MinerU Markdown 融合的假客户端。"""

    def __init__(self, markdown: str | None = None, should_fail: bool = False) -> None:
        self.markdown = markdown
        self.should_fail = should_fail

    def parse_file(self, file_path: str, *, language: str = "ch") -> MinerULightResult:
        """返回固定 Markdown 或模拟异常。"""

        if self.should_fail:
            raise RuntimeError("fake_mineru_failed")
        return MinerULightResult(state="done", markdown=self.markdown, result_url="https://example.test/result.md")


def _write_text_pdf(path: Path) -> None:
    """写入包含两页文字层的 PDF 样例。"""

    document = fitz.open()
    first_page = document.new_page()
    first_page.insert_text((72, 72), "PageOne Payment Clause\nPay after acceptance 100")
    second_page = document.new_page()
    second_page.insert_text((72, 72), "PageTwo Liability Clause\nLate payment liability")
    document.save(path)
    document.close()


def _build_request(path: Path, filename: str = "合同.pdf") -> DocumentIntakeRequest:
    """构造文档感知请求。"""

    return DocumentIntakeRequest(
        file_id=99,
        user_id=7,
        filename=filename,
        file_type="pdf",
        save_path=str(path),
    )


def _dump_parsed_document_for_review(parsed, source_path: Path) -> tuple[Path, Path]:
    """把真实 PDF 解析结果临时落盘，便于人工审查 Markdown 和结构化 JSON。"""

    PARSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = PARSED_OUTPUT_DIR / f"{source_path.stem}.pdf.parsed.md"
    json_path = PARSED_OUTPUT_DIR / f"{source_path.stem}.pdf.parsed.json"
    md_path.write_text(parsed.contract_content or "", encoding="utf-8")
    json_path.write_text(
        json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return md_path, json_path


def test_pdf_text_layer_parser_outputs_page_blocks(tmp_path: Path) -> None:
    """无 MinerU 客户端时，普通 PDF 应使用本地 text layer 输出页码块。"""

    path = tmp_path / "合同.pdf"
    _write_text_pdf(path)
    parsed = parse_text_pdf_file(str(path), filename="合同.pdf", file_id=99)

    assert parsed.parse_status == "success"
    assert parsed.metadata["content_source"] == "text_layer"
    assert parsed.blocks[0].page_number == 1
    assert parsed.blocks[1].page_number == 2
    assert "<!-- page_number: 1 -->" in parsed.contract_content


def test_step4_pdf_text_route_connects_to_parser(tmp_path: Path) -> None:
    """Step 4 的普通 PDF 路由应接到 Step 5.2 PDF 解析层。"""

    path = tmp_path / "合同.pdf"
    _write_text_pdf(path)
    sensing = sense_document(_build_request(path))
    parsed = parse_document_from_sensing(sensing)

    assert sensing.route == "pdf_text_extract"
    assert parsed.parse_status == "success"
    assert parsed.metadata["source_route"] == "pdf_text_extract"
    assert parsed.blocks[0].block_id == "file-99-page-1-block-1"


def test_mineru_markdown_is_used_when_client_returns_result(tmp_path: Path) -> None:
    """传入 MinerU 客户端时，应优先使用 Markdown，并保留表格块结构。"""

    path = tmp_path / "合同.pdf"
    _write_text_pdf(path)
    markdown = "# Payment Clause\n\nPageOne Payment Clause\n\n| Node | Amount |\n| --- | --- |\n| Acceptance | 100 |"
    parsed = parse_text_pdf_file(
        str(path),
        filename="合同.pdf",
        file_id=99,
        mineru_client=_FakeMinerUClient(markdown),
    )

    assert parsed.metadata["content_source"] == "mineru_light"
    assert parsed.contract_content.startswith("# Payment Clause")
    assert any(block.metadata["element_type"] == "table" for block in parsed.blocks)
    assert parsed.blocks[1].page_number == 1


def test_mineru_failure_falls_back_to_text_layer(tmp_path: Path) -> None:
    """MinerU 轻量解析失败时，应回退到本地 text layer。"""

    path = tmp_path / "合同.pdf"
    _write_text_pdf(path)
    parsed = parse_text_pdf_file(
        str(path),
        filename="合同.pdf",
        file_id=99,
        mineru_client=_FakeMinerUClient(should_fail=True),
    )

    assert parsed.parse_status == "success"
    assert parsed.metadata["content_source"] == "text_layer"
    assert "mineru_light_failed" in parsed.warnings


def test_real_pdf_file_can_be_parsed_and_dumped_for_review() -> None:
    """解析 tests/data 下的真实 PDF，并把审查产物写到 tests/data/parsed_outputs。"""

    if not REAL_PDF_PATH.exists():
        pytest.skip(f"请将真实 PDF 文件放到: {REAL_PDF_PATH}")

    sensing = sense_document(_build_request(REAL_PDF_PATH, REAL_PDF_PATH.name))
    parsed = parse_document_from_sensing(sensing)
    md_path, json_path = _dump_parsed_document_for_review(parsed, REAL_PDF_PATH)

    assert sensing.route == "pdf_text_extract"
    assert parsed.parse_status == "success"
    assert parsed.blocks
    assert md_path.exists()
    assert json_path.exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
