"""
@Project ：contract_review
@File    ：document_comparison.py
@IDE     ：PyCharm
@Author  ：CyanYuMu
@Date    ：2025/11/20 18:53
"""

from docx import Document
from difflib import SequenceMatcher

def read_docx_paragraphs(path):
    doc = Document(path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]

def diff_paragraphs(std_text,cmp_text):
    """
    进行文字上的diff
    :param std_text:
    :param cmp_text:
    :return:replace/delete/insert 片段组合,json字段
    """
    std_chars = list(std_text)
    cmp_chars = list(cmp_text)

    matcher = SequenceMatcher(None, std_chars, cmp_chars, autojunk=False)
    results = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue

        results.append({
            "type": tag,
            "std_text": "".join(std_chars[i1:i2]),
            "cmp_text": "".join(cmp_chars[j1:j2])
        })

    return results


def diff_docs(std_docx, cmp_docx):
    std_lines = read_docx_paragraphs(std_docx)
    cmp_lines = read_docx_paragraphs(cmp_docx)

    s = SequenceMatcher(None, std_lines, cmp_lines, autojunk=False)
    diff_result = []

    for tag, i1, i2, j1, j2 in s.get_opcodes():

        if tag == 'equal':
            continue

        elif tag == 'delete':
            for line in std_lines[i1:i2]:
                diff_result.append({
                    "type": "deleted",
                    "std_text": line
                })

        elif tag == 'insert':
            for line in cmp_lines[j1:j2]:
                diff_result.append({
                    "type": "inserted",
                    "cmp_text": line
                })

        elif tag == 'replace':
            # 逐段对比，然后做字级 diff
            max_len = max(i2 - i1, j2 - j1)

            for k in range(max_len):
                std_text = std_lines[i1 + k] if i1 + k < i2 else ""
                cmp_text = cmp_lines[j1 + k] if j1 + k < j2 else ""

                # 字级 diff
                char_diffs = diff_paragraph(std_text, cmp_text)

                diff_result.append({
                    "type": "modified",
                    "std_text": std_text,
                    "cmp_text": cmp_text,
                    "detail": char_diffs  # 细粒度修改
                })

    return diff_result