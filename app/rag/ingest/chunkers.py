"""
RAG 入库切分工具。
"""
from __future__ import annotations

import re
from typing import Iterable


ARTICLE_HEADER_PATTERN = re.compile(
    r"(第[一二三四五六七八九十百千万零〇两0-9]+条[^\n]*)"
)


class LegalTextChunker:
    """
    外部法律文本切分器。

    优先按“第X条”结构切分；若没有条级结构，则回退为按段落合并切分。
    """

    def split(self, text: str) -> list[dict[str, str]]:
        text = (text or "").strip()
        if not text:
            return []

        article_chunks = self._split_by_article(text)
        if article_chunks:
            return article_chunks
        return self._split_by_paragraph(text)

    def _split_by_article(self, text: str) -> list[dict[str, str]]:
        matches = list(ARTICLE_HEADER_PATTERN.finditer(text))
        if not matches:
            return []

        chunks: list[dict[str, str]] = []
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            chunk_text = text[start:end].strip()
            header = match.group(1).strip()
            body = chunk_text[len(header):].strip()
            chunks.append(
                {
                    "article_no": self._extract_article_no(header),
                    "title": header,
                    "content": body or chunk_text,
                }
            )
        return chunks

    def _split_by_paragraph(self, text: str) -> list[dict[str, str]]:
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
        if not paragraphs:
            return []
        return [
            {
                "article_no": f"段落{i}",
                "title": f"段落{i}",
                "content": paragraph,
            }
            for i, paragraph in enumerate(paragraphs, start=1)
        ]

    @staticmethod
    def _extract_article_no(header: str) -> str:
        match = re.match(r"(第[一二三四五六七八九十百千万零〇两0-9]+条)", header)
        return match.group(1) if match else header


class InternalRuleChunker:
    """
    内部规则切分器。

    默认按空行拆段，保持规则语义的自然段边界。
    """

    def split(self, text: str) -> list[str]:
        text = (text or "").strip()
        if not text:
            return []
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
        return paragraphs or [text]


def batched(items: Iterable, batch_size: int) -> list[list]:
    """
    将列表按批次切分。
    """
    batch_size = max(batch_size, 1)
    batch: list = []
    batches: list[list] = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            batches.append(batch)
            batch = []
    if batch:
        batches.append(batch)
    return batches


def _main_test_chunkers():
    legal_chunker = LegalTextChunker()
    chunks = legal_chunker.split(
        "第一条 总则\n合同应当遵循平等原则。\n\n第二条 履行\n当事人应全面履行义务。"
    )
    assert len(chunks) == 2
    assert chunks[0]["article_no"] == "第一条"

    rule_chunker = InternalRuleChunker()
    rule_chunks = rule_chunker.split("付款条款必须明确。\n\n违约责任必须量化。")
    assert len(rule_chunks) == 2

    assert batched([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    print("RAG chunkers self test passed")


if __name__ == "__main__":
    _main_test_chunkers()
