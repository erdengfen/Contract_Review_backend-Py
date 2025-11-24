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

# 项目的 data/ 目录下存放用于性能测试的大文件
# BASE_DIR = 当前 test_diff.py 所在的目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 相对路径指向 data/ 中的大文件（需要你自己放入）
FILE_PATH_STD = BASE_DIR / "data/std.docx"
FILE_PATH_CMP = BASE_DIR / "data/cmp.docx"


def _make_doc(path, paragraphs):
    """
    帮助函数：由pytest创建一个临时 docx 文件。
    paragraphs (list[str]) : 要写入的段落内容。
    """
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(path)


def test_insert(tmp_path):
    """
    测试文档内容“插入”场景。
    标准文档： ["A", "B"]
    待比对文档： ["A", "B", "C"]

    预期：diff_docs 能识别新增的段落 "C"，并返回 type="inserted" 的 diff。
    """
    std_path = tmp_path / "std.docx"
    cmp_path = tmp_path / "cmp.docx"

    _make_doc(std_path, ["A", "B"])
    _make_doc(cmp_path, ["A", "B", "C"])  # 插入 C

    res = diff_docs(str(std_path), str(cmp_path))

    # 打印返回结果，方便调试
    print("=== test_insert diff result ===")
    for item in res:
        print(item)

    # 校验返回结果中是否存在插入段落 C
    assert any(item["type"] == "inserted" and item["cmp_text"] == "C" for item in res)


def test_delete(tmp_path):
    """
    测试文档内容“删除”场景。
    标准文档： ["A", "B", "C"]
    待比对文档： ["A", "C"]   -> 删除了 B

    预期：diff_docs 应识别被删除的段落 "B"，并返回 type="deleted"。
    """
    std_path = tmp_path / "std.docx"
    cmp_path = tmp_path / "cmp.docx"

    _make_doc(std_path, ["A", "B", "C"])
    _make_doc(cmp_path, ["A", "C"])  # 删除 B

    res = diff_docs(str(std_path), str(cmp_path))

    print("=== test_delete diff result ===")
    for item in res:
        print(item)

    # 校验结果包含被删除的 B
    assert any(item["type"] == "deleted" and item["std_text"] == "B" for item in res)


def test_modify(tmp_path):
    """
    测试文档内容“修改”场景。
    标准文档： ["合同有效期为三年"]
    待比对文档： ["合同有效期为五年"]

    预期：
      - diff_docs 能识别为 type="modified"
      - 并提供字符级 diff（detail 字段中有 replace 操作）
    """
    std_path = tmp_path / "std.docx"
    cmp_path = tmp_path / "cmp.docx"

    _make_doc(std_path, ["合同有效期为三年"])
    _make_doc(cmp_path, ["合同有效期为五年"])  # 修改 三 -> 五

    res = diff_docs(str(std_path), str(cmp_path))

    print("=== test_modify diff result ===")
    for item in res:
        print(item)
        if item["type"] == "modified":
            print("  --> 字符级 diff:")
            for detail in item["detail"]:
                print("     ", detail)

    # 找到类型为 modified 的 diff（段落修改）
    modified = next(item for item in res if item["type"] == "modified")

    assert modified["std_text"] == "合同有效期为三年"
    assert modified["cmp_text"] == "合同有效期为五年"

    # 字符级 diff 中必须包含 replace 变化（三 -> 五）
    assert any(d["type"] == "replace" for d in modified["detail"])


def test_no_change(tmp_path):
    """
    测试内容完全不变的情况。
    两个文档均为 ["A", "B", "C"]

    预期：diff_docs 返回空列表 []
    """
    std_path = tmp_path / "std.docx"
    cmp_path = tmp_path / "cmp.docx"

    _make_doc(std_path, ["A", "B", "C"])
    _make_doc(cmp_path, ["A", "B", "C"])

    res = diff_docs(str(std_path), str(cmp_path))

    print("=== test_no_change diff result ===")
    for item in res:
        print(item)

    assert res == []


def test_large_file_performance(benchmark):
    """
    使用 pytest-benchmark 测试性能。

    前置要求：
      你需要在项目的 data/ 目录放入大文件：
        data/std.docx
        data/cmp.docx

    pytest自动多次运行 diff_docs
      - 测量平均耗时
      - 给出基准性能报告
    """
    assert FILE_PATH_STD.exists(), "请将大文件 std.docx 放到 data/ 下"
    assert FILE_PATH_CMP.exists(), "请将大文件 cmp.docx 放到 data/ 下"

    #调用一次diff_docx看修改结果
    diff_result = diff_docs(str(FILE_PATH_STD), str(FILE_PATH_CMP))

    print("=== 大文件 diff 结果 ===")
    for item in diff_result:
        print(item)
        if item.get("type") == "modified" and "detail" in item:
            print("  --> 字符级 diff:")
            for d in item["detail"]:
                print("     ", d)

    # benchmark 会自动重复执行 lambda 内的函数并统计耗时
    benchmark(lambda: diff_docs(str(FILE_PATH_STD), str(FILE_PATH_CMP)))




