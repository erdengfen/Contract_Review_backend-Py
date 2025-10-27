"""
@Project ：Contract_Review_backend-Py 
@File    ：document_annotation.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/27 10:28 
"""
from spire.doc import *

from spire.pdf import *
import  json
import time, re, os, uuid
from spire.doc import Document, Paragraph, Table, TableCell, ShapeObject, ShapeType, Comment, CommentMark, \
    CommentMarkType
from spire.doc.common import Color
class DocumentPdf:
    @staticmethod
    def add_comments_and_highlight(input_path, rules, author):
        doc = PdfDocument()
        doc.LoadFromFile(input_path)
        results, count = [], 0

        for page_index in range(doc.Pages.Count):
            page = doc.Pages.get_Item(page_index)
            finder = PdfTextFinder(page)
            finder.Options.Parameter = TextFindParameter.WholeWord

            for rule in rules:
                keyword = rule["keyword"]
                comment_text = rule["comment"]
                color = rule.get("color", (255, 255, 0))
                fragments = finder.Find(keyword)
                if fragments:
                    for fragment in fragments:
                        for i in range(len(fragment.Bounds)):
                            rect = fragment.Bounds[i]
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

        output_path = f"./output/{os.path.splitext(os.path.basename(input_path))[0]}_标注_{uuid.uuid4().hex[:8]}.pdf"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.SaveToFile(output_path)
        doc.Dispose()

        # 保存日志
        log_path = f"./output/{os.path.splitext(os.path.basename(input_path))[0]}_标注日志_{uuid.uuid4().hex[:8]}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

        return output_path, log_path, count

    @staticmethod
    def update_comments_by_log(input_path, log_path, updated_comment_text=None):
        doc = PdfDocument()
        doc.LoadFromFile(input_path)

        with open(log_path, "r", encoding="utf-8") as f:
            logs = json.load(f)

        updated = 0

        for page_index in range(doc.Pages.Count):
            page = doc.Pages.get_Item(page_index)
            to_remove = []
            to_add = []

            # 先收集需要更新的批注
            for annotation_index in range(page.AnnotationsWidget.Count):
                annotation = page.AnnotationsWidget.get_Item(annotation_index)
                if isinstance(annotation, PdfTextMarkupAnnotation):
                    for log_item in logs:
                        if log_item["page"] == page_index + 1 and annotation.Text == log_item["comment"]:
                            to_remove.append(annotation)
                            # 重新创建批注
                            new_annotation = PdfTextMarkupAnnotation(
                                annotation.Author,
                                updated_comment_text or log_item["comment"],
                                annotation.Bounds[0]
                            )
                            new_annotation.TextMarkupType = annotation.TextMarkupType
                            new_annotation.TextMarkupColor = annotation.TextMarkupColor
                            to_add.append(new_annotation)
                            updated += 1

            # 删除旧批注
            for ann in to_remove:
                page.AnnotationsWidget.Remove(ann)

            # 添加更新后的批注
            for ann in to_add:
                page.AnnotationsWidget.Add(ann)

        output_path = f"./output/{os.path.splitext(os.path.basename(input_path))[0]}_批注已更新_{uuid.uuid4().hex[:8]}.pdf"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.SaveToFile(output_path)
        doc.Dispose()

        print(f"PDF 已更新 {updated} 条批注内容")
        return output_path

    @staticmethod
    def replace_text_by_keyword(input_path, rules, replacement_template="{old_text}（已修订）"):
        doc = PdfDocument()
        doc.LoadFromFile(input_path)
        replace_count = 0

        for page_index in range(doc.Pages.Count):
            page = doc.Pages.get_Item(page_index)
            finder = PdfTextFinder(page)

            for rule in rules:
                keyword = rule["keyword"]
                fragments = finder.Find(keyword)
                if fragments:
                    for fragment in fragments:
                        # PDF 不可直接修改文本，采用覆盖注释形式标记修改
                        rect = fragment.Bounds[0]
                        overlay_annotation = PdfTextMarkupAnnotation(
                            "系统",
                            replacement_template.format(old_text=keyword),
                            rect
                        )
                        overlay_annotation.TextMarkupType = PdfTextMarkupAnnotationType.Highlight
                        overlay_annotation.TextMarkupColor = PdfRGBColor(255, 255, 0)  # 黄色高亮
                        page.AnnotationsWidget.Add(overlay_annotation)
                        replace_count += 1

        output_path = f"./output/{os.path.splitext(os.path.basename(input_path))[0]}_文本已替换_{uuid.uuid4().hex[:8]}.pdf"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.SaveToFile(output_path)
        doc.Dispose()

        print(f"PDF 已替换 {replace_count} 处文本（以高亮标注替代）")
        return output_path

    @staticmethod
    def test():
        AUTHOR = "pan"
        COMMENT_RULES = [
            {"keyword": "网站建设", "comment": "此处需明确网站建设的技术要求"},
            {"keyword": "验收", "comment": "需补充验收标准和责任方"},
            {"keyword": "合同金额", "comment": "确认金额计算是否包含税费"},
        ]
        FILE_PATH = "校园主页升级改版服务合同.pdf"

        print("Step 1: 添加批注 + 高亮")
        output_path, log_path, count = DocumentPdf.add_comments_and_highlight(FILE_PATH, COMMENT_RULES, AUTHOR)
        print(f"添加批注完成，共 {count} 条")
        print(f"输出 PDF：{output_path}")
        print(f"批注日志：{log_path}\n")

        print("Step 2: 更新批注文本")
        updated_comment_text = "请根据新版本规范修订此处内容"
        updated_pdf_path = DocumentPdf.update_comments_by_log(output_path, log_path, updated_comment_text)
        print(f"更新后的 PDF：{updated_pdf_path}\n")

        print("Step 3: 替换关键词文本")
        replaced_pdf_path = DocumentPdf.replace_text_by_keyword(updated_pdf_path, COMMENT_RULES,
                                                                replacement_template="{old_text}（请修订）")
        print(f"替换关键词后的 PDF：{replaced_pdf_path}\n")

        print("PDF 测试流程完成")
        return replaced_pdf_path, log_path


class DocumentDoc:

    # ========== 功能一：添加批注与高亮 ==========
    @staticmethod
    def add_comments_and_highlight(input_path, rules):
        """
        为文档中所有文本（包括段落、表格、文本框等）添加高亮和批注
        :param input_path: 输入文件路径
        :param rules: [{"keyword": "...", "comment": "...", "author": "..."}]
        :return: (输出文件路径, 批注结果列表)
        """
        doc = Document()
        doc.LoadFromFile(input_path)

        results = []
        comment_counter = 0

        def traverse_elements(collection, section_index=None, paragraph_index=None):
            nonlocal comment_counter

            for idx in range(len(collection)):
                obj = collection[idx]

                if isinstance(obj, Paragraph):
                    traverse_elements(obj.ChildObjects, section_index, paragraph_index)

                elif isinstance(obj, Table):
                    for r in range(obj.Rows.Count):
                        row = obj.Rows.get_Item(r)
                        for c in range(row.Cells.Count):
                            cell = row.Cells.get_Item(c)
                            traverse_elements(cell.ChildObjects, section_index, paragraph_index)

                elif isinstance(obj, ShapeObject):
                    if obj.ShapeType == ShapeType.TextBox:
                        traverse_elements(obj.ChildObjects, section_index, paragraph_index)

                elif isinstance(obj, TextRange):
                    text = obj.Text.strip()
                    if not text:
                        continue
                    for rule in rules:
                        keyword = rule["keyword"]
                        comment_text = rule["comment"]

                        if keyword in text:
                            comment_counter += 1
                            obj.CharacterFormat.HighlightColor = Color.FromArgb(255, 255, 255, 0)

                            comment = Comment(doc)
                            comment.Body.AddParagraph().Text = comment_text
                            comment.Format.Author = rule["author"]

                            comment_start = CommentMark(doc, CommentMarkType.CommentStart)
                            comment_end = CommentMark(doc, CommentMarkType.CommentEnd)
                            comment_start.CommentId = comment.Format.CommentId
                            comment_end.CommentId = comment.Format.CommentId

                            parent_para = obj.OwnerParagraph
                            insert_index = parent_para.ChildObjects.IndexOf(obj)
                            parent_para.ChildObjects.Insert(insert_index, comment_start)
                            parent_para.ChildObjects.Insert(insert_index + 2, comment_end)
                            parent_para.ChildObjects.Insert(insert_index + 3, comment)

                            results.append({
                                "comment_id": comment.Format.CommentId,
                                "keyword": keyword,
                                "comment": comment_text,
                                "author": rule["author"],
                                "section_index": section_index,
                                "paragraph_index": paragraph_index,
                                "text_snippet": text[:100]
                            })
        for i in range(doc.Sections.Count):
            section = doc.Sections.get_Item(i)
            for j in range(section.Paragraphs.Count):
                paragraph = section.Paragraphs.get_Item(j)
                traverse_elements(paragraph.ChildObjects, section_index=i, paragraph_index=j)

            for t in range(section.Tables.Count):
                table = section.Tables.get_Item(t)
                traverse_elements([table], section_index=i)

        if comment_counter == 0:
            print("未找到任何匹配关键词。")

        base_name = os.path.basename(input_path)
        file_name, ext = os.path.splitext(base_name)
        output_path = f"./output/{file_name}_批注高亮_{uuid.uuid4().hex[:8]}{ext}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.SaveToFile(output_path)
        doc.Close()

        return output_path, results

    @staticmethod
    def add_comments_and_highlight_textRange(input_path, rules):
        """
        段落/表格单元级匹配 + 批注（修正版）
        支持表格中长文本匹配（包括跨段落/单元格关键词）
        防止对同一文本与同一规则重复批注
        """
        def normalize_text(text):
            return re.sub(r"[\s\u200b\u00a0\r\n]+", "", text or "").strip()
        doc = Document()
        doc.LoadFromFile(input_path)

        results = []
        comment_counter = 0
        start_time = time.time()
        annotated_container_ids = set()
        matched_pairs = set()

        def highlight_container(container):
            """对 Paragraph 或 TableCell 全部高亮 (黄色)"""
            if isinstance(container, Paragraph):
                for i in range(container.ChildObjects.Count):
                    sub = container.ChildObjects.get_Item(i)
                    if sub.__class__.__name__ == "TextRange":
                        sub.CharacterFormat.HighlightColor =  Color.FromArgb(255, 255, 255, 0)
            elif isinstance(container, TableCell):
                for i in range(container.Paragraphs.Count):
                    highlight_container(container.Paragraphs.get_Item(i))

        def add_comment(container, comment_text, author):
            """在 Paragraph 或 TableCell 级添加批注"""
            comment = Comment(doc)
            comment.Body.AddParagraph().Text = comment_text
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
                # 插入到单元格首段与末段
                first_para = container.Paragraphs.get_Item(0)
                last_para = container.Paragraphs.get_Item(container.Paragraphs.Count - 1)
                first_para.ChildObjects.Insert(0, start)
                last_para.ChildObjects.Add(end)
                last_para.ChildObjects.Add(comment)
            return comment.Format.CommentId

        def extract_full_text(obj):
            """
            提取对象纯文本，忽略 Comment/CommentMark，支持 Paragraph/TableCell/Table/ShapeObject
            返回未规范化原始文本（后面统一 normalize）
            """
            text = ""
            # Paragraph: 聚合其 TextRange
            if isinstance(obj, Paragraph):
                for i in range(obj.ChildObjects.Count):
                    sub = obj.ChildObjects.get_Item(i)
                    cls_name = sub.__class__.__name__
                    if cls_name == "TextRange":
                        text += sub.Text
            # TableCell: 聚合其段落
            elif isinstance(obj, TableCell):
                for i in range(obj.Paragraphs.Count):
                    text += extract_full_text(obj.Paragraphs.get_Item(i))
            # Table: 聚合所有 cell 文本（注意：我们不会在 Table 层做匹配）
            elif isinstance(obj, Table):
                for r in range(obj.Rows.Count):
                    row = obj.Rows.get_Item(r)
                    for c in range(row.Cells.Count):
                        text += extract_full_text(row.Cells.get_Item(c))

            elif isinstance(obj, ShapeObject) and obj.ShapeType == ShapeType.TextBox:
                for i in range(obj.ChildObjects.Count):
                    text += extract_full_text(obj.ChildObjects.get_Item(i))

            elif hasattr(obj, 'Text') and isinstance(obj.Text, str):
                text += obj.Text
            return text

        def traverse_elements(obj, section_index=None, depth=0):
            """
            遍历入口现在接收单一对象（Paragraph/Table/TableCell/ShapeObject 等）
            - 对 Table 不做直接匹配，只递归进入 cells
            - 对 TableCell / Paragraph / TextBox 的段落 做匹配
            """
            nonlocal comment_counter
            if depth > 12:
                return

            # ---- 计算文本并规范化 ----
            raw_text = extract_full_text(obj)
            text_content = normalize_text(raw_text)
            # 若文本非空，则尝试匹配（但限定匹配对象类型：Paragraph 或 TableCell 或 TextBox-contained paragraph）
            is_container_matchable = isinstance(obj, (Paragraph, TableCell)) or (
                        isinstance(obj, ShapeObject) and obj.ShapeType == ShapeType.TextBox)
            if text_content and is_container_matchable:
                print(text_content)
                # 遍历规则，按规则去重：同一规则对相同规范化文本只匹配一次
                for rule in rules:
                    rule_key = normalize_text(rule["keyword"])
                    if not rule_key:
                        continue
                    pair_key = (rule_key, text_content)
                    if pair_key in matched_pairs:
                        continue  # 已命中过，不再重复匹配

                    if rule_key in text_content:
                        cid_holder = id(obj)
                        if cid_holder in annotated_container_ids:
                            matched_pairs.add(pair_key)
                            break

                        # 添加高亮与批注
                        highlight_container(obj)
                        comment_id = add_comment(obj, rule["comment"], rule["author"])
                        comment_counter += 1
                        annotated_container_ids.add(cid_holder)
                        matched_pairs.add(pair_key)

                        results.append({
                            "comment_id": comment_id,
                            "keyword": rule["keyword"],
                            "comment": rule["comment"],
                            "author": rule["author"],
                            "text_snippet": text_content[:200],
                            "section_index": section_index
                        })
                        break  # 一段文本命中一条规则后跳出

            # ---- 递归到子结构 ----
            # Table -> cells
            if isinstance(obj, Table):
                for r in range(obj.Rows.Count):
                    row = obj.Rows.get_Item(r)
                    for c in range(row.Cells.Count):
                        cell = row.Cells.get_Item(c)
                        traverse_elements(cell, section_index, depth + 1)

            # TableCell -> its paragraphs (但如果 TableCell 已被批注过则可以选择跳过其内部重复检测)
            elif isinstance(obj, TableCell):
                if id(obj) in annotated_container_ids:
                    return
                for p in range(obj.Paragraphs.Count):
                    para = obj.Paragraphs.get_Item(p)
                    traverse_elements(para, section_index, depth + 1)

            # Paragraph -> 可能包含 TextBox / 子对象
            elif isinstance(obj, Paragraph):
                # 如果此段已被批注则不再向下递归（避免重复）
                if id(obj) in annotated_container_ids:
                    return
                for i in range(obj.ChildObjects.Count):
                    sub = obj.ChildObjects.get_Item(i)
                    cls_name = sub.__class__.__name__
                    # 递归处理嵌套 ShapeObject/TextBox 或子 Paragraph
                    if cls_name in ("ShapeObject", "Paragraph"):
                        traverse_elements(sub, section_index, depth + 1)

            # ShapeObject(TextBox) -> 遍历其子对象（通常为段落）
            elif isinstance(obj, ShapeObject) and obj.ShapeType == ShapeType.TextBox:
                for i in range(obj.ChildObjects.Count):
                    traverse_elements(obj.ChildObjects.get_Item(i), section_index, depth + 1)

        # ---- 主循环：逐节遍历（先段落再表格，但我们在 traverse 元素内部避免重复） ----
        for i in range(doc.Sections.Count):
            sec = doc.Sections.get_Item(i)
            # 先遍历节中的段落（这些段落可能是表格外的普通段落）
            for p_idx in range(sec.Paragraphs.Count):
                para = sec.Paragraphs.get_Item(p_idx)
                traverse_elements(para, section_index=i)
            # 再遍历节中的表格（表格内部将在 traverse 中被处理到单元格）
            for t_idx in range(sec.Tables.Count):
                table = sec.Tables.get_Item(t_idx)
                traverse_elements(table, section_index=i)

        # 保存与返回
        print(f"✅ 匹配完成，共添加批注 {comment_counter} 条，用时 {time.time() - start_time:.2f}s")

        base_name = os.path.basename(input_path)
        name, ext = os.path.splitext(base_name)
        output_path = f"./output/{name}_批注修正_{uuid.uuid4().hex[:6]}{ext}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.SaveToFile(output_path)
        doc.Close()

        return output_path, results


    # ========== 功能二：更新批注内容 ==========\
    @staticmethod
    def update_comments_by_log(input_path, results, updated_comment_text=None):
        """
        更新批注内容
        :param input_path: 输入文件路径
        :param results: 规则列表，每个规则包含 "comment_id"、"keyword"、"comment"
        :param updated_comment_text: 更新后的批注内容（可选）
        :return: 处理结果列表，每个元素包含 "comment_id"、"keyword"、"comment"
        """
        doc = Document()
        doc.LoadFromFile(input_path)
        updated = 0
        for i in range(doc.Comments.Count):
            comment = doc.Comments.get_Item(i)

            for item in results:
                if comment.Format.CommentId == item["comment_id"]:
                    for p in range(comment.Body.Paragraphs.Count):
                        para = comment.Body.Paragraphs.get_Item(p)
                        if updated_comment_text:
                            para.Text = updated_comment_text
                        else:
                            para.Text = item["comment"]
                    updated += 1

        base_name = os.path.basename(input_path)
        file_name, ext = os.path.splitext(base_name)
        output_path = f"./output/{file_name}_批注已更新_{uuid.uuid4().hex[:8]}{ext}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.SaveToFile(output_path)
        doc.Close()

        print(f"已更新 {updated} 条批注内容。")
        print(f"输出文档：{output_path}")
        return output_path

    @staticmethod
    def replace_text_by_keyword(input_path, results, replacement_template="{old_text}（已修订）"):
        """
        根据批注日志替换文档中对应的关键词文本
        :param input_path: 原文档路径
        :param log_path: 批注日志路径
        :param replacement_template: 替换模板，可包含 {old_text} 占位符
        """
        doc = Document()
        doc.LoadFromFile(input_path)



        replace_count = 0

        for i in range(doc.Sections.Count):
            section = doc.Sections.get_Item(i)
            for j in range(section.Paragraphs.Count):
                paragraph = section.Paragraphs.get_Item(j)

                for item in results:
                    keyword = item["keyword"]
                    new_text = replacement_template.format(old_text=keyword)

                    # 遍历子对象查找 TextRange 并替换内容
                    for k in range(paragraph.ChildObjects.Count):
                        obj = paragraph.ChildObjects.get_Item(k)
                        if isinstance(obj, TextRange) and keyword in obj.Text:
                            obj.Text = obj.Text.replace(keyword, new_text)
                            replace_count += 1

        # 保存输出文档
        base_name = os.path.basename(input_path)
        file_name, ext = os.path.splitext(base_name)
        output_path = f"./output/{file_name}_文本已替换_{uuid.uuid4().hex[:8]}{ext}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.SaveToFile(output_path)
        doc.Close()

        print(f"已替换 {replace_count} 处文本。")
        print(f"输出文档：{output_path}")
        return output_path

    @staticmethod
    def test():
        # ========== 全局配置 ==========
        FILE_PATH = r"../../data/校园主页升级改版服务合同.docx"

        # 批量关键词与对应批注
        COMMENT_RULES = [
            {
                "keyword": "按合同总价的千分之二向甲方支付违约金。",
                "comment": "违约金",
                "author": "pan"
            },
            {
                "keyword": "服务要求和标准：乙方提供的服务必须完全符合国家有关标准和规范，不得违反法律法规，确保安全、服务到位，服从甲方安排管理。",
                "comment": "需补充验收标准和责任方",
                "author": "pan"
            },
            {
                "keyword": "设计元素要与学校自身特色强相关，避免与学校无关的设计元素出现，以强化我校门户网站的品牌识别度。",
                "comment": "设计元素要与学校自身特色强相关",
                "author": "pan"
            },
            {
                "keyword": "提供不少于5次现场培训，包括对内容管理、模版设计制作、栏目修改、管理与维护技术方法等全方位培训，并提供培训手册、操作手册等资料。",
                "comment": "现场培训",
                "author": "pan"
            }
        ]
        output_doc, results = DocumentDoc.add_comments_and_highlight_textRange(FILE_PATH, COMMENT_RULES)
        print(results)
        # # Step 1：添加批注 + 高亮 + 生成日志
        # output_doc, results = DocumentDoc.add_comments_and_highlight(FILE_PATH, COMMENT_RULES)
        # print(results)
        # # Step 2：更新批注文本（例如，审阅后修改批注内容）
        # updated_doc = DocumentDoc.update_comments_by_log(output_doc, results, updated_comment_text="请根据新版本规范修订此处内容")
        #
        # # Step 3：替换正文中关键词文本（例如，插入“（已修订）”后缀）
        # replaced_doc = DocumentDoc.replace_text_by_keyword(updated_doc, results, replacement_template="{old_text}（请修订）")


# 调用测试
if __name__ == "__main__":
    DocumentDoc.test()


