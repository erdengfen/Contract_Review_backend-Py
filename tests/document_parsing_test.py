"""
@Project ：Contract_Review_backend-Py
@File    ：document_parsing_test.py
@IDE     ：PyCharm
@Author  ：潘尚国
@Date    ：2025/10/20 15:07
"""
from app.utils.document_parsing import mk_pdf2docx, doc2docx, docx2html,docx2md

if __name__ == '__main__':

    doc_path = r"F:\cy-project-python-psg\Contract_Review_backend-Py\output\校园主页升级改版服务合同.docx"
    html_content = None
    new_path = None
    if doc_path.endswith(".pdf"):
        new_path = doc_path.replace(".pdf", ".docx")
        mk_pdf2docx(doc_path, new_path)
    elif doc_path.endswith('.doc'):
        new_path = doc_path.replace('.doc', '.docx')
        doc2docx(doc_path, new_path)
    else:
        new_path = doc_path
    md_content = docx2md(new_path,
                             file_options={})
    # 输出 HTML
    with open("../output/output.md", "w", encoding="utf-8") as f:
        f.write(md_content)