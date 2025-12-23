"""
@Project ：contract_review
@File    ：contract_comparison_test.py
@IDE     ：PyCharm
@Author  ：CyanYuMu
@Date    ：2025/11/24 13:24
"""
import os
from pathlib import Path
from docx import Document
from app.services.document_comparison import diff_docs

BASE_DIR = Path(__file__).resolve().parent.parent
FILE_PATH_STD = BASE_DIR / "data/std.docx"
FILE_PATH_CMP = BASE_DIR / "data/cmp.docx"


def _make_doc(path, paragraphs):
    """生成 docx 文档，写入若干段落。"""
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(path)


def test_insert(tmp_path):
    """
    情况：新文档比旧文档多出段落（insert）。
    验证：
    - diff 中存在 operation == "insert"
    - comparison_text 正确
    """
    std_path = tmp_path / "std.docx"
    cmp_path = tmp_path / "cmp.docx"

    _make_doc(std_path, ["A", "B"])
    _make_doc(cmp_path, ["A", "B", "C"])

    result = diff_docs(str(std_path), str(cmp_path))
    diffs = result["diffs"]

    assert any(
        d["operation"] == "insert" and d["comparison_text"] == "C"
        for d in diffs
    )


def test_delete(tmp_path):
    """
    情况：标准文档比新文档多（delete）。
    验证：
    - diff 中存在 operation == "delete"
    - standard_text 正确
    """
    std_path = tmp_path / "std.docx"
    cmp_path = tmp_path / "cmp.docx"

    _make_doc(std_path, ["A", "B", "C"])
    _make_doc(cmp_path, ["A", "C"])

    result = diff_docs(str(std_path), str(cmp_path))
    diffs = result["diffs"]

    assert any(
        d["operation"] == "delete" and d["standard_text"] == "B"
        for d in diffs
    )


def test_replace(tmp_path):
    """
    情况：段落被替换（replace）。
    验证：
    - operation == "replace"
    - standard_text / comparison_text 正确
    - char_diff 存在并包含至少一条字符 diff
    """
    std_path = tmp_path / "std.docx"
    cmp_path = tmp_path / "cmp.docx"

    _make_doc(std_path, ["合同有效期为三年"])
    _make_doc(cmp_path, ["合同有效期为五年"])

    result = diff_docs(str(std_path), str(cmp_path))
    diffs = result["diffs"]

    replace_items = [d for d in diffs if d["operation"] == "replace"]
    assert replace_items, "未检测到 replace 操作"

    item = replace_items[0]
    assert item["standard_text"] == "合同有效期为三年"
    assert item["comparison_text"] == "合同有效期为五年"
    assert item["char_diff"], "replace 必须包含字符级 diff"


def test_no_change(tmp_path):
    """
    情况：两个文档完全一致
    验证：
    - diffs 列表为空
    - summary 字段正确
    """
    std_path = tmp_path / "std.docx"
    cmp_path = tmp_path / "cmp.docx"

    _make_doc(std_path, ["A", "B"])
    _make_doc(cmp_path, ["A", "B"])

    result = diff_docs(str(std_path), str(cmp_path))
    assert result["diffs"] == []
    assert result["summary"]["difference_count"] == 0


def test_large_file_performance(benchmark):
    """
    性能测试：需要你在 tests/data/ 放入真实大文件。
    benchmark 会自动重复执行多次，统计平均耗时。

    注意：
    - 不在 benchmark 中写 print（会被重复执行几十次）
    - 只做纯性能测量
    """
    assert FILE_PATH_STD.exists(), f"缺少大文件: {FILE_PATH_STD}"
    assert FILE_PATH_CMP.exists(), f"缺少大文件: {FILE_PATH_CMP}"

    benchmark(lambda: diff_docs(str(FILE_PATH_STD), str(FILE_PATH_CMP)))


def test_inspect_large_file_once():
    """
    单独打印一次大文件 diff，用于人工检查输出是否正确。
    不参与性能统计。
    """
    if not FILE_PATH_STD.exists() or not FILE_PATH_CMP.exists():
        return  # 没有大文件时自动跳过

    result = diff_docs(str(FILE_PATH_STD), str(FILE_PATH_CMP))

    print("\n===== 大文件比对结果（仅首次运行打印） =====")
    print("summary:", result["summary"])
    print("diff count:", len(result["diffs"]))
    print("前 5 条 diff：")
    for item in result["diffs"][:5]:
        print(item)

def test_diff_documents(base_dir = BASE_DIR):
    """
    测试比对两个文件
    """
    std_path = base_dir / "data/graph_std.docx"
    cmp_path = base_dir / "data/graph_cmp.docx"
    result = diff_docs(str(std_path), str(cmp_path))
    print(result)


