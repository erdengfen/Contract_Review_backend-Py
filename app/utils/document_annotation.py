"""
重构后的文档批注/高亮处理模块
包含：
 - PdfProcessor: 基于 spire.pdf 的 PDF 批注/高亮/替换工具
 - DocProcessor: 基于 spire.doc 的 Word(DOC/DOCX) 批注/高亮/替换工具

改进点：
 - 将重复逻辑抽象成内部辅助函数（保存/生成路径/加载/释放/日志）
 - 使用 dataclass 描述规则，增加类型提示
 - 增加异常处理与资源释放（上下文管理风格）
 - 统一输出路径生成逻辑
 - 避免重复对同一容器/文本重复批注
 - 记录并返回更结构化的结果（便于后续处理）
 - 减少对全局状态的依赖，函数参数明确

注意：此代码依赖 spire.doc / spire.pdf 的 Python 封装（与原代码一致）。
"""
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Dict, Any
import os
import json
import uuid
import time
import re
# 引入第三方库（与原代码保持一致）
from spire.pdf import PdfDocument, PdfTextFinder, TextFindParameter, PdfTextMarkupAnnotation, PdfTextMarkupAnnotationType, PdfRGBColor
from spire.doc import Document, Paragraph, Table, TableCell, ShapeObject, ShapeType, Comment, CommentMark, CommentMarkType, TextRange
from spire.doc.common import Color
@dataclass
class Rule:
    keyword: str
    comment: str
    author: Optional[str] = None
    color: Optional[Tuple[int, int, int]] = None


def _ensure_output_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _unique_path(input_path: str, suffix: str, ext: str) -> str:
    base = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join("./output", f"{base}_{suffix}_{uuid.uuid4().hex[:8]}{ext}")


class PdfProcessor:
    """处理 PDF：添加批注/高亮、按日志更新批注、用覆盖注释方式替换文本
    保持原接口兼容性：返回 (output_path, log_path, count) 或单一路径。
    """

    @staticmethod
    def add_comments_and_highlight(input_path: str, rules: List[Rule], author: str) -> Tuple[str, str, int]:
        doc = PdfDocument()
        try:
            doc.LoadFromFile(input_path)
            results = []
            count = 0

            for page_index in range(doc.Pages.Count):
                page = doc.Pages.get_Item(page_index)
                finder = PdfTextFinder(page)
                finder.Options.Parameter = TextFindParameter.WholeWord

                for rule in rules:
                    keyword = rule.keyword
                    comment_text = rule.comment
                    color = rule.color or (255, 255, 0)

                    fragments = finder.Find(keyword)
                    if not fragments:
                        continue

                    for fragment in fragments:
                        for rect in fragment.Bounds:
                            annotation = PdfTextMarkupAnnotation(author, comment_text, rect)
                            annotation.TextMarkupType = PdfTextMarkupAnnotationType.Highlight
                            annotation.TextMarkupColor = PdfRGBColor(color[0], color[1], color[2])
                            page.AnnotationsWidget.Add(annotation)

                            results.append({
                                "keyword": keyword,
                                "comment": comment_text,
                                "page": page_index + 1,
                                "x": rect.Left,
                                "y": rect.Top,
                                "type": "pdf"
                            })
                            count += 1

            output_path = _unique_path(input_path, "标注", ".pdf")
            _ensure_output_dir(output_path)
            doc.SaveToFile(output_path)

            # 写日志
            log_path = _unique_path(input_path, "标注日志", ".json")
            _ensure_output_dir(log_path)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)

            return output_path, log_path, count
        finally:
            try:
                doc.Dispose()
            except Exception:
                pass

    @staticmethod
    def update_comments_by_log(input_path: str, log_path: str, updated_comment_text: Optional[str] = None) -> str:
        doc = PdfDocument()
        try:
            doc.LoadFromFile(input_path)
            with open(log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)

            updated = 0
            # 构建快速查找集合：按 (page, comment_text)
            log_map = {(item["page"], item["comment"]): item for item in logs}

            for page_index in range(doc.Pages.Count):
                page = doc.Pages.get_Item(page_index)
                to_remove = []
                to_add = []

                for ai in range(page.AnnotationsWidget.Count):
                    annotation = page.AnnotationsWidget.get_Item(ai)
                    # 有的注释对象可能不是文本标注
                    if not isinstance(annotation, PdfTextMarkupAnnotation):
                        continue

                    key = (page_index + 1, annotation.Text)
                    if key in log_map:
                        # 记录删除并重新创建
                        to_remove.append(annotation)
                        new_text = updated_comment_text or annotation.Text
                        new_annotation = PdfTextMarkupAnnotation(annotation.Author, new_text, annotation.Bounds[0])
                        new_annotation.TextMarkupType = annotation.TextMarkupType
                        new_annotation.TextMarkupColor = annotation.TextMarkupColor
                        to_add.append(new_annotation)
                        updated += 1

                # 批量删除/添加
                for ann in to_remove:
                    try:
                        page.AnnotationsWidget.Remove(ann)
                    except Exception:
                        pass
                for ann in to_add:
                    page.AnnotationsWidget.Add(ann)

            output_path = _unique_path(input_path, "批注已更新", ".pdf")
            _ensure_output_dir(output_path)
            doc.SaveToFile(output_path)
            return output_path
        finally:
            try:
                doc.Dispose()
            except Exception:
                pass

    @staticmethod
    def replace_text_by_keyword(input_path: str, rules: List[Rule], replacement_template: str = "{old_text}（已修订）") -> str:
        doc = PdfDocument()
        try:
            doc.LoadFromFile(input_path)
            replace_count = 0

            for page_index in range(doc.Pages.Count):
                page = doc.Pages.get_Item(page_index)
                finder = PdfTextFinder(page)

                for rule in rules:
                    keyword = rule.keyword
                    fragments = finder.Find(keyword)
                    if not fragments:
                        continue

                    for fragment in fragments:
                        rect = fragment.Bounds[0]
                        overlay_annotation = PdfTextMarkupAnnotation(
                            "系统",
                            replacement_template.format(old_text=keyword),
                            rect
                        )
                        overlay_annotation.TextMarkupType = PdfTextMarkupAnnotationType.Highlight
                        overlay_annotation.TextMarkupColor = PdfRGBColor(255, 255, 0)
                        page.AnnotationsWidget.Add(overlay_annotation)
                        replace_count += 1

            output_path = _unique_path(input_path, "文本已替换", ".pdf")
            _ensure_output_dir(output_path)
            doc.SaveToFile(output_path)
            print(f"PDF 已替换 {replace_count} 处文本（以高亮标注替代）")
            return output_path
        finally:
            try:
                doc.Dispose()
            except Exception:
                pass


class DocProcessor:
    """处理 Word 文档（.doc/.docx）
    - 支持在段落/表格/文本框级别进行匹配并添加批注与高亮
    - 支持通过 comment_id 更新批注
    - 支持文本替换（真替换）
    """

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"[\s\u200b\u00a0\r\n]+", "", text).strip()

    @staticmethod
    def _extract_full_text(obj: Any) -> str:
        # 与原函数一致：递归抽取 Paragraph/TableCell/Table 的文本
        text = ""
        if isinstance(obj, Paragraph):
            for i in range(obj.ChildObjects.Count):
                sub = obj.ChildObjects.get_Item(i)
                if getattr(sub, '__class__', None) and sub.__class__.__name__ == 'TextRange':
                    text += sub.Text
        elif isinstance(obj, TableCell):
            for i in range(obj.Paragraphs.Count):
                text += DocProcessor._extract_full_text(obj.Paragraphs.get_Item(i))
        elif isinstance(obj, Table):
            for r in range(obj.Rows.Count):
                row = obj.Rows.get_Item(r)
                for c in range(row.Cells.Count):
                    text += DocProcessor._extract_full_text(row.Cells.get_Item(c))
        elif isinstance(obj, ShapeObject) and obj.ShapeType == ShapeType.TextBox:
            for i in range(obj.ChildObjects.Count):
                text += DocProcessor._extract_full_text(obj.ChildObjects.get_Item(i))
        elif hasattr(obj, 'Text') and isinstance(obj.Text, str):
            text += obj.Text
        return text

    @staticmethod
    def add_comments_and_highlight_textRange(input_path: str, rules: List[Rule]) -> Tuple[str, List[Dict[str, Any]]]:
        doc = Document()
        doc.LoadFromFile(input_path)

        results = []
        comment_counter = 0
        start_time = time.time()

        annotated_container_ids = set()
        matched_pairs = set()

        def highlight_container(container: Any):
            # 对段落或单元格的 TextRange 全部高亮
            if isinstance(container, Paragraph):
                for i in range(container.ChildObjects.Count):
                    sub = container.ChildObjects.get_Item(i)
                    if sub.__class__.__name__ == 'TextRange':
                        sub.CharacterFormat.HighlightColor = Color.FromArgb(255, 255, 255, 0)
            elif isinstance(container, TableCell):
                for i in range(container.Paragraphs.Count):
                    highlight_container(container.Paragraphs.get_Item(i))

        def add_comment(container: Any, comment_text: str, author: Optional[str]):
            comment = Comment(doc)
            comment.Body.AddParagraph().Text = comment_text
            if author:
                comment.Format.Author = author

            start = CommentMark(doc, CommentMarkType.CommentStart)
            end = CommentMark(doc, CommentMarkType.CommentEnd)
            start.CommentId = comment.Format.CommentId
            end.CommentId = comment.Format.CommentId

            if isinstance(container, Paragraph):
                container.ChildObjects.Insert(0, start)
                container.ChildObjects.Add(end)
                container.ChildObjects.Add(comment)
            elif isinstance(container, TableCell):
                first_para = container.Paragraphs.get_Item(0)
                last_para = container.Paragraphs.get_Item(container.Paragraphs.Count - 1)
                first_para.ChildObjects.Insert(0, start)
                last_para.ChildObjects.Add(end)
                last_para.ChildObjects.Add(comment)
            return comment.Format.CommentId

        def traverse_elements(obj: Any, section_index: int = None, depth: int = 0):
            nonlocal comment_counter
            if depth > 12:
                return

            raw_text = DocProcessor._extract_full_text(obj)
            text_content = DocProcessor._normalize_text(raw_text)
            is_matchable = isinstance(obj, (Paragraph, TableCell)) or (
                isinstance(obj, ShapeObject) and obj.ShapeType == ShapeType.TextBox
            )

            if text_content and is_matchable:
                for rule in rules:
                    rule_key = DocProcessor._normalize_text(rule.keyword)
                    if not rule_key:
                        continue
                    pair_key = (rule_key, text_content)
                    if pair_key in matched_pairs:
                        continue

                    if rule_key in text_content:
                        cid_holder = id(obj)
                        if cid_holder in annotated_container_ids:
                            matched_pairs.add(pair_key)
                            break

                        highlight_container(obj)
                        cid = add_comment(obj, rule.comment, rule.author)
                        comment_counter += 1
                        annotated_container_ids.add(cid_holder)
                        matched_pairs.add(pair_key)

                        results.append({
                            "comment_id": cid,
                            "keyword": rule.keyword,
                            "comment": rule.comment,
                            "author": rule.author,
                            "text_snippet": text_content[:200],
                            "section_index": section_index,
                        })
                        break

            # 递归：Table -> cells; TableCell -> paragraphs; Paragraph -> 子对象; TextBox -> 子对象
            if isinstance(obj, Table):
                for r in range(obj.Rows.Count):
                    row = obj.Rows.get_Item(r)
                    for c in range(row.Cells.Count):
                        traverse_elements(row.Cells.get_Item(c), section_index, depth + 1)
            elif isinstance(obj, TableCell):
                if id(obj) in annotated_container_ids:
                    return
                for p in range(obj.Paragraphs.Count):
                    traverse_elements(obj.Paragraphs.get_Item(p), section_index, depth + 1)
            elif isinstance(obj, Paragraph):
                if id(obj) in annotated_container_ids:
                    return
                for i in range(obj.ChildObjects.Count):
                    sub = obj.ChildObjects.get_Item(i)
                    cls_name = sub.__class__.__name__
                    if cls_name in ("ShapeObject", "Paragraph"):
                        traverse_elements(sub, section_index, depth + 1)
            elif isinstance(obj, ShapeObject) and obj.ShapeType == ShapeType.TextBox:
                for i in range(obj.ChildObjects.Count):
                    traverse_elements(obj.ChildObjects.get_Item(i), section_index, depth + 1)

        # 主循环
        for i in range(doc.Sections.Count):
            sec = doc.Sections.get_Item(i)
            for p_idx in range(sec.Paragraphs.Count):
                traverse_elements(sec.Paragraphs.get_Item(p_idx), section_index=i)
            for t_idx in range(sec.Tables.Count):
                traverse_elements(sec.Tables.get_Item(t_idx), section_index=i)

        output_path = _unique_path(input_path, "批注修正", os.path.splitext(input_path)[1])
        _ensure_output_dir(output_path)
        doc.SaveToFile(output_path)
        doc.Close()

        print(f"匹配完成，共添加批注 {comment_counter} 条，用时 {time.time() - start_time:.2f}s")
        return output_path, results

    @staticmethod
    def update_comments_by_log(input_path: str, results: List[Dict[str, Any]], updated_comment_text: Optional[str] = None) -> str:
        doc = Document()
        doc.LoadFromFile(input_path)
        updated = 0
        id_map = {item['comment_id']: item for item in results}

        for i in range(doc.Comments.Count):
            comment = doc.Comments.get_Item(i)
            if comment.Format.CommentId in id_map:
                new_text = updated_comment_text or id_map[comment.Format.CommentId]['comment']
                for p in range(comment.Body.Paragraphs.Count):
                    comment.Body.Paragraphs.get_Item(p).Text = new_text
                updated += 1

        output_path = _unique_path(input_path, "批注已更新", os.path.splitext(input_path)[1])
        _ensure_output_dir(output_path)
        doc.SaveToFile(output_path)
        doc.Close()
        print(f"已更新 {updated} 条批注内容。")
        return output_path

    @staticmethod
    def replace_text_by_keyword(input_path: str, results: List[Dict[str, Any]], replacement_template: str = "{old_text}（已修订）") -> str:
        doc = Document()
        doc.LoadFromFile(input_path)

        replace_count = 0
        for i in range(doc.Sections.Count):
            section = doc.Sections.get_Item(i)
            for j in range(section.Paragraphs.Count):
                paragraph = section.Paragraphs.get_Item(j)
                for item in results:
                    keyword = item['keyword']
                    new_text = replacement_template.format(old_text=keyword)
                    for k in range(paragraph.ChildObjects.Count):
                        obj = paragraph.ChildObjects.get_Item(k)
                        if obj.__class__.__name__ == 'TextRange' and keyword in obj.Text:
                            obj.Text = obj.Text.replace(keyword, new_text)
                            replace_count += 1

        output_path = _unique_path(input_path, "文本已替换", os.path.splitext(input_path)[1])
        _ensure_output_dir(output_path)
        doc.SaveToFile(output_path)
        doc.Close()

        print(f"已替换 {replace_count} 处文本。")
        return output_path


#简易使用示例（保留为注释）
if __name__ == '__main__':
    pdf_rules = [Rule('网站建设', '此处需明确网站建设的技术要求'), Rule('验收', '需补充验收标准和责任方')]
    PdfProcessor.add_comments_and_highlight('合同.pdf', pdf_rules, author='pan')

    doc_rules = [Rule('违约金', '违约金说明', author='pan')]
    DocProcessor.add_comments_and_highlight_textRange('合同.docx', doc_rules)
