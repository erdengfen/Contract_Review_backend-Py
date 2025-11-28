"""
@Project ：contract_review
@File    ：document_comparison.py
@IDE     ：PyCharm
@Author  ：CyanYuMu
@Date    ：2025/11/20 18:53
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from difflib import SequenceMatcher


def read_docx_paragraphs(path: str) -> List[str]:
    """读取 docx 段落并移除空行。"""
    doc = Document(path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def _build_char_diff(std_text: str, cmp_text: str) -> List[Dict[str, Any]]:
    """构造段落内部的字符级 diff 信息。"""
    matcher = SequenceMatcher(
        None, list(std_text), list(cmp_text), autojunk=False
    )
    chunks: List[Dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        chunk: Dict[str, Any] = {
            "operation": tag,
            "std_text": std_text[i1:i2],
            "cmp_text": cmp_text[j1:j2],
            "std_range": [i1, i2],
            "cmp_range": [j1, j2],
        }
        chunks.append(chunk)
    return chunks


def _append_diff_entry(
    results: List[Dict[str, Any]],
    *,
    std_index: Optional[int],
    cmp_index: Optional[int],
    operation: str,
    std_text: str,
    cmp_text: str,
    char_diff: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """整理 diff 数据结构，避免重复样板代码。"""
    if not std_text and not cmp_text:
        return
    entry: Dict[str, Any] = {
        "std_index": std_index,
        "cmp_index": cmp_index,
        "operation": operation,
        "standard_text": std_text,
        "comparison_text": cmp_text,
    }
    if char_diff:
        entry["char_diff"] = char_diff
    results.append(entry)


def diff_docs(std_docx: str, cmp_docx: str) -> Dict[str, Any]:
    """
    按段落比对两个 docx 文档，产出差异 JSON。

    返回结构:
    {
        "summary": {...},
        "diffs": [...]
    }
    """
    if not Path(std_docx).exists():
        raise FileNotFoundError(f"标准文档不存在: {std_docx}")
    if not Path(cmp_docx).exists():
        raise FileNotFoundError(f"比对文档不存在: {cmp_docx}")

    std_lines = read_docx_paragraphs(std_docx)
    cmp_lines = read_docx_paragraphs(cmp_docx)

    matcher = SequenceMatcher(None, std_lines, cmp_lines, autojunk=False)
    diff_result: List[Dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        if tag == "delete":
            for offset, line in enumerate(std_lines[i1:i2]):
                _append_diff_entry(
                    diff_result,
                    std_index=i1 + offset,
                    cmp_index=None,
                    operation="delete",
                    std_text=line,
                    cmp_text="",
                )
        elif tag == "insert":
            for offset, line in enumerate(cmp_lines[j1:j2]):
                _append_diff_entry(
                    diff_result,
                    std_index=None,
                    cmp_index=j1 + offset,
                    operation="insert",
                    std_text="",
                    cmp_text=line,
                )
        elif tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                std_idx = i1 + k if i1 + k < len(std_lines) else None
                cmp_idx = j1 + k if j1 + k < len(cmp_lines) else None
                std_text = std_lines[std_idx] if std_idx is not None and std_idx < i2 else ""
                cmp_text = cmp_lines[cmp_idx] if cmp_idx is not None and cmp_idx < j2 else ""
                char_diff = _build_char_diff(std_text, cmp_text)
                _append_diff_entry(
                    diff_result,
                    std_index=std_idx,
                    cmp_index=cmp_idx,
                    operation="replace",
                    std_text=std_text,
                    cmp_text=cmp_text,
                    char_diff=char_diff if char_diff else None,
                )

    summary = {
        "standard_paragraphs": len(std_lines),
        "comparison_paragraphs": len(cmp_lines),
        "difference_count": len(diff_result),
    }
    return {"summary": summary, "diffs": diff_result}