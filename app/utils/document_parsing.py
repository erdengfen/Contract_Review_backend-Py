import json
import mimetypes
import sys
import urllib
import uuid
import requests
from docx.oxml import CT_P, CT_Tbl
import docx
from docx import Document
from lxml import etree
from pathlib import Path
from tqdm.auto import tqdm
import subprocess
import os
import pdf2docx



underline_styles = {
    "true": "text-decoration:underline;",
    None: "",  # 没有下划线
    'single': "text-decoration:underline;",
    'double': "text-decoration:underline double;",
    'wavy': "text-decoration:underline wavy;",
    'dotted': "text-decoration:underline dotted;",
    'thick': "text-decoration:underline thick;",
    'dash': "text-decoration:underline dashed;",
    'dotDash': "text-decoration:underline dot-dash;",
    'dotDotDash': "text-decoration:underline dot-dot-dash;",
    'wave': "text-decoration:underline wavy;"  # 兼容其他波浪线表示
}


def upload(file, file_options):
    """
    上传到后端服务
    :param file: 本地文件路径
    :param file_options: 文件上传配置
    :return: 上传后的 URL
    """
    # print(config_manager.config)
    # if config_manager.config.get("WZ_SERVER", {}).get("PYTHONENV", "") == "production":
    #     url = config_manager.config.get("WZ_SERVER", {}).get("OfficialStationUpload", "")
    # else:
    #     url = config_manager.config.get("WZ_SERVER", {}).get("TestStationUpload", "")
    return  file
    file_options_lower = {k.lower(): v for k, v in file_options.items()}
    authorization = file_options_lower.get("authorization")  # 获取 authorization
    headers = {
        "Authorization": f"{authorization}"
    }

    try:

        file_name = os.path.basename(file)
        object_name = file_options.get("objectName", file_name)


        file_mime = mimetypes.guess_type(file)[0] or "application/octet-stream"

        with open(file, 'rb') as f:
            files = {
                "file": (file_name, f, file_mime),  # 明确指定 Content-Type
                "objectName": (None, object_name)  # 确保 objectName 也在 form-data 里
            }

            response = requests.post(url, headers=headers, files=files)

        if response.status_code == 200:

            response_data = response.json()
            new_url = response_data.get("data")
            print("Upload successful:", new_url)
            return new_url
        else:
            print("Upload failed:", response.status_code, response.text)
            return None
    except FileNotFoundError:
        print(f"File not found: {file}")
        return None
    except requests.exceptions.RequestException as e:
        print("Upload failed:", e)
        return None
    except Exception as e:
        print("An unexpected error occurred:", e)
        return None


def resolve_paths(input_path, output_path):
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve() if output_path else None
    output = {}
    if input_path.is_dir():
        output["batch"] = True
        output["input"] = str(input_path)
        if output_path:
            assert output_path.is_dir()
        else:
            output_path = str(input_path)
    else:
        output["batch"] = False
        assert str(input_path).endswith((".doc", ".DOC"))
        output["input"] = str(input_path)
        if output_path and output_path.is_dir():
            output_path = str(output_path / f"{str(input_path.stem)}.docx")
        elif output_path:
            assert str(output_path).endswith(".docx")
        else:
            output_path = str(input_path.parent / f"{str(input_path.stem)}.docx")
    output["output"] = output_path
    return output


def macos(paths, keep_active):
    script = (Path(__file__).parent / "convert.jxa").resolve()
    cmd = [
        "/usr/bin/osascript",
        "-l",
        "JavaScript",
        str(script),
        str(paths["input"]),
        str(paths["output"]),
        str(keep_active).lower(),
    ]

    def run(cmd):
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE)
        while True:
            line = process.stderr.readline().rstrip()
            if not line:
                break
            yield line.decode("utf-8")

    total = len(list(Path(paths["input"]).glob("*.doc*"))) if paths["batch"] else 1
    pbar = tqdm(total=total)
    for line in run(cmd):
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg["result"] == "success":
            pbar.update(1)
        elif msg["result"] == "error":
            print(msg)
            sys.exit(1)


def windows(paths, keep_active):
    import win32com.client

    word = win32com.client.Dispatch("Word.Application")
    wdFormatDocumentDefault = 16

    if paths["batch"]:
        for doc_filepath in tqdm(sorted(Path(paths["input"]).glob("[!~]*.doc*"))):
            docx_filepath = Path(paths["output"]) / f"{str(doc_filepath.stem)}.docx"
            doc = word.Documents.Open(str(doc_filepath))
            doc.SaveAs(str(docx_filepath), FileFormat=wdFormatDocumentDefault)
            doc.Close(0)
    else:
        pbar = tqdm(total=1)
        doc_filepath = Path(paths["input"]).resolve()
        docx_filepath = Path(paths["output"]).resolve()
        doc = word.Documents.Open(str(doc_filepath))
        doc.SaveAs(str(docx_filepath), FileFormat=wdFormatDocumentDefault)
        doc.Close(0)
        pbar.update(1)

    if not keep_active:
        word.Quit()


def linux(paths, keep_active):
    input_path = paths["input"]
    output_path = paths["output"]
    output_dir = os.path.dirname(output_path)
    # print(input_path, output_dir)
    os.system("libreoffice --headless --invisible --convert-to docx %s --outdir %s" % (input_path, output_dir))


def docx2html(doc_path, file_options):
    """解析 docx，保留标题、样式、表格、图片、超链接、列表等元素，转换为 HTML"""
    doc = Document(doc_path)
    link_target_list = []

    print(doc._element.xml)

    def get_style(run):

        """获取字体样式：粗体、颜色、字号、下划线、删除线、文本高亮"""
        style = ""
        # 字体
        font_family = None
        r_fonts_element = run._r.find(".//w:rFonts",
                                      namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})
        if r_fonts_element is not None:
            font_family = r_fonts_element.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii") or \
                          r_fonts_element.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi") or \
                          r_fonts_element.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia")

        if font_family:
            style += f"font-family:{font_family};"
        # 粗体
        if run.bold:
            style += "font-weight:bold;"
        # 斜体
        if run.italic:
            style += "font-style:italic;"

        # 字号
        if run.font.size:
            style += f"font-size:{run.font.size.pt}px;"
        else:
            sz_element = run._r.find(".//w:sz", namespaces={
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})
            if sz_element is not None:
                font_size_half_points = int(sz_element.get("val", 0))
                font_size_pts = font_size_half_points / 2
                style += f"font-size:{font_size_pts}px;"

        # 字体颜色
        if run.font.color and run.font.color.rgb:
            rgb = run.font.color.rgb
            style += f"color:#{rgb};"

        underline_value = None
        if run.underline:
            underline_str = str(run.underline).lower()
            underline_value = underline_str.split('(')[0].strip()

        underline_style = underline_styles.get(underline_value, "")
        style += underline_style
        # 删除线
        if 'strike' in run._r.xml:
            style += "text-decoration:line-through;"

        # 高亮颜色
        if run.font.highlight_color:
            highlight_colors = {
                'YELLOW': '#FFFF00',
                'GREEN': '#00FF00',
                'TURQUOISE': '#40E0D0',
                'PINK': '#FFC0CB',
                'BLUE': '#0000FF',
                'RED': '#FF0000',
                'BROWN': '#A52A2A'
            }
            highlight_color = highlight_colors.get(run.font.highlight_color.name, '#FFFF00')
            style += f"background-color:{highlight_color};"

        return f' style="{style}"' if style else ""

    def get_paragraph_style(paragraph, is_list_item=False):
        """获取段落对齐、缩进、间距"""
        style = ""
        print(paragraph._element.xml)

        if paragraph.alignment == 1:
            style += "text-align:center;"
        elif paragraph.alignment == 2:
            style += "text-align:right;"
        elif paragraph.alignment == 3:
            style += "text-align:justify;"


        if paragraph.paragraph_format.first_line_indent:
            style += f"text-indent:{paragraph.paragraph_format.first_line_indent.pt}px;"
        if paragraph.paragraph_format.left_indent:
            style += f"margin-left:{paragraph.paragraph_format.left_indent.pt}px;"
        if paragraph.paragraph_format.right_indent:
            style += f"margin-right:{paragraph.paragraph_format.right_indent.pt}px;"


        if is_list_item:

            if paragraph.paragraph_format.left_indent:
                style += f"padding-left:{paragraph.paragraph_format.left_indent.pt}px;"


        if paragraph.paragraph_format.space_before:
            style += f"margin-top:{paragraph.paragraph_format.space_before.pt}px;"
        if paragraph.paragraph_format.space_after:
            style += f"margin-bottom:{paragraph.paragraph_format.space_after.pt}px;"

        if paragraph.paragraph_format.line_spacing:
            line_spacing = paragraph.paragraph_format.line_spacing
            if isinstance(line_spacing, float):
                style += f"line-height:{line_spacing}em;"
            else:
                style += f"line-height:{line_spacing.pt}px;"

        return f' style="{style}"' if style else ""

    def extract_images(paragraph, file_options):
        """提取段落中的图片并上传至OSS，返回上传后的图片URL"""
        img_html = ""
        temp_dir = os.path.join(os.getcwd(), "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        for run in paragraph.runs:
            for drawing in run._element.findall(
                    ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing"):
                blip = drawing.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
                if blip is not None:
                    rId = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                    if rId in paragraph.part.rels:
                        image_part = paragraph.part.rels[rId].target_part
                        image_data = image_part.blob
                        image_ext = image_part.content_type.split("/")[-1]
                        file_name = f"image_{uuid.uuid4().hex}.{image_ext}"


                        temp_img_path = os.path.join(temp_dir, file_name)
                        with open(temp_img_path, "wb") as img_file:
                            img_file.write(image_data)

                        image_url = upload(temp_img_path, file_options)
                        if image_url:
                            img_html += f'<img src="{image_url}" alt="Image" style="max-width:100%;" />'
                        else:
                            img_html += f'<img src="{None}" alt="Image" style="max-width:100%;" />'

                        os.remove(temp_img_path)

        return img_html

    def detect_list(paragraph):
        """检测是否是列表项（有序或无序）"""
        p_xml = paragraph._element.xml
        if 'w:numPr' in p_xml:
            if "w:numFmt w:val=\"bullet\"" in p_xml:
                return "ul"
            return "ol"
        return None

    def process_table(table):
        """
        解析 Word 文档中的表格，并转换为 HTML 表格格式，同时保留边框和合并单元格信息。
        """

        num_rows = len(table.rows)
        num_cols = len(table.columns)


        # print("Table XML Structure:")
        # print(table._element.xml)


        namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        element = table._element
        element_str = etree.tostring(element, encoding='unicode')
        tree = etree.fromstring(element_str)

        border_styles = {key: '' for key in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']}
        border_colors = {key: '' for key in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']}
        borders = tree.xpath('.//w:tblBorders', namespaces=namespaces)

        if borders:
            for border in borders[0]:
                border_tag = border.tag.split('}')[1]
                border_type = border.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'none')
                border_size = border.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz', '0')
                border_color = border.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color', '')

                border_size_px = round(int(border_size) * 0.125 * 1.33)
                css_border_type = {'dashSmallGap': 'dashed', 'dashDot': 'dotted', 'single': 'solid'}.get(border_type,
                                                                                                         'solid')

                border_styles[border_tag] = f"{border_size_px}px {css_border_type}"
                border_colors[border_tag] = f"#{border_color}" if border_color else ''


        shading = tree.xpath('.//w:shading', namespaces=namespaces)
        cell_shading = shading[0].get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill',
                                      '') if shading else ''


        html_table = "<table border='1' style='border-collapse:collapse;'>"
        merged_cells = set()


        data = [[{'text': '', 'gridSpan': False, 'gridSpan_num': 0, 'vMerge': False} for _ in range(num_cols)] for _ in
                range(num_rows)]

        for row_index, row in enumerate(table.rows):
            col_index = 0
            while col_index < len(row.cells):
                cell = row.cells[col_index]


                if (row_index, col_index) in merged_cells:
                    col_index += 1
                    continue

                cell_text = cell.text or ""


                grid_span = cell._element.xpath('.//w:gridSpan')
                gridSpan_num = int(grid_span[0].val) if grid_span else 1
                gridSpan = gridSpan_num > 1


                v_merge = cell._element.xpath('.//w:vMerge')
                vMerge = bool(v_merge)


                data[row_index][col_index] = {
                    'text': cell_text,
                    'gridSpan': gridSpan,
                    'gridSpan_num': gridSpan_num,
                    'vMerge': vMerge
                }
                col_index += 1

        for row_index in range(num_rows):
            html_table += "<tr>"
            for col_index in range(num_cols):
                if (row_index, col_index) in merged_cells:
                    continue

                cell = data[row_index][col_index]
                # cell_text = cell['text']

                cell_text = (cell['text'] or "").replace("\n", "<br>")

                colspan = cell['gridSpan_num'] if cell['gridSpan'] else 1
                rowspan = 1

                # 计算跨行数
                if cell['vMerge']:
                    for r in range(row_index + 1, num_rows):
                        if data[r][col_index]['vMerge']:
                            rowspan += 1
                            merged_cells.add((r, col_index))
                        else:
                            break

                # 记录所有被合并的列单元格
                for i in range(1, colspan):
                    merged_cells.add((row_index, col_index + i))

                # 生成 HTML 代码
                html_table += f"<td style='border-top:{border_styles['top']};border-left:{border_styles['left']};" \
                              f"border-bottom:{border_styles['bottom']};border-right:{border_styles['right']};" \
                              f"border-color:{border_colors['top']};background-color:{cell_shading};'"

                if colspan > 1:
                    html_table += f" colspan='{colspan}'"
                if rowspan > 1:
                    html_table += f" rowspan='{rowspan}'"

                html_table += f">{cell_text}</td>"

            html_table += "</tr>"

        html_table += "</table>"
        return html_table

    def find_run_by_text(runs, text):
        """根据文本查找对应的 Run 对象"""
        for run in runs:
            if run.text and text in run.text:
                return run
        return None

    def extract_paragraph_content(paragraph, file_options):
        """提取段落内容，生成 HTML"""
        para_html = ""
        for child in paragraph._element.xpath(".//*"):
            if child.tag.endswith("}t"):  # 普通文本
                text = child.text.strip() if child.text else ""
                if text:
                    if text.startswith("http"):
                        para_html += f'<a href="{text}" target="_blank">{text}</a>'
                    else:
                        run = find_run_by_text(paragraph.runs, text)
                        if run:
                            para_html += f"<span{get_style(run)}>{text}</span>"
            elif child.tag.endswith("}hyperlink"):  # 超链接
                rId = child.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                if rId:
                    rel = paragraph.part.rels.get(rId)
                    if rel:
                        link_target = rel.target_ref
                        link_target = urllib.parse.unquote(link_target)
                        print("link_target:", link_target)
                        link_text_elements = child.xpath(".//w:t")
                        link_text = "".join([t.text for t in link_text_elements if t is not None and t.text])
                        # 判断超链接目标是否为本地文件链接（file:// 开头）
                        if link_target.startswith('file:///'):  # 本地文件链接

                            file_path = link_target[len('file:///'):]

                            if os.path.exists(file_path):
                                # 调用上传函数上传文件
                                file_upload_url = upload(file_path, file_options)
                                if file_upload_url:
                                    link_target_list.append({
                                        "file_path": file_path,
                                        "file_upload_url": file_upload_url
                                    })
                                    para_html += f'<a href="{file_upload_url}" target="_blank">{link_text}</a>'  # 使用上传后的 URL
                                else:
                                    para_html += f'<a href="{link_target}" target="_blank">{link_text}</a>'  # 上传失败时仍使用原始链接
                            else:
                                para_html += f'<a href="{link_target}" target="_blank">{link_text}</a>'  # 文件不存在时显示原始链接
                        elif link_target.startswith('http'):
                            # 找到包含该超链接的 Run 对象以获取样式
                            run = find_run_by_text(paragraph.runs, link_text)
                            if run:
                                style_attr = get_style(run)
                            else:
                                style_attr = ""
                            para_html += f'<a href="{link_target}" target="_blank"{style_attr}>{link_text}</a>'
                        else:
                            if len(link_target_list) > 0:
                                for link_target_item in link_target_list:
                                    if os.path.basename(link_target_item["file_path"]) == link_target:
                                        para_html += f'<a href="{link_target_item["file_upload_url"]}" target="_blank">{link_text}</a>'
                                        break
                                    else:
                                        para_html += f'<a href="{link_target}" target="_blank">{link_text}</a>'

            elif child.tag.endswith("}drawing"):
                img_html = extract_images(paragraph, file_options)
                if img_html:
                    para_html += img_html
            elif child.tag.endswith("}br"):
                para_html += "<br />"
        return para_html

    def process_paragraph(para, file_options):
        """处理段落内容，生成 HTML"""
        para_html = extract_paragraph_content(para, file_options)

        # 如果是列表项，则用 <li> 包裹
        current_list_type = detect_list(para)
        if current_list_type:
            return f"<li>{para_html}</li>"

        # 如果是标题，则用 <hX> 标签包裹
        if para.style and para.style.name.startswith("Heading"):
            level = para.style.name.split()[-1]
            return f"<h{level}{get_paragraph_style(para)}>{para.text}</h{level}>"

        # 默认用 <p> 标签包裹
        return f"<p{get_paragraph_style(para)}>{para_html}</p>"

    def convert_doc_to_html(doc, file_options):
        """将 DOCX 文档转换为 HTML"""
        html_content = ""
        list_stack = []  # 使用栈管理列表层级和类型

        for block in doc.element.body:
            if isinstance(block, CT_P):  # 段落
                para = docx.text.paragraph.Paragraph(block, doc)
                current_list_type = detect_list(para)
                # 如果当前段落是列表项
                if current_list_type:
                    # 如果列表类型发生变化，关闭之前的列表
                    if list_stack and list_stack[-1] != current_list_type:
                        while list_stack and list_stack[-1] != current_list_type:
                            html_content += f"</{list_stack.pop()}>"

                    # 如果栈为空或类型匹配，直接添加 <li>
                    if not list_stack or list_stack[-1] == current_list_type:
                        if not list_stack:
                            html_content += f"<{current_list_type}>"
                            list_stack.append(current_list_type)
                    else:
                        # 如果嵌套列表，打开新的列表标签
                        html_content += f"<{current_list_type}>"
                        list_stack.append(current_list_type)

                    # 添加列表项内容
                    para_html = process_paragraph(para, file_options)
                    html_content += para_html

                else:
                    # 如果不是列表项，关闭所有列表
                    while list_stack:
                        html_content += f"</{list_stack.pop()}>"


                    para_html = process_paragraph(para, file_options)
                    html_content += para_html

            elif isinstance(block, CT_Tbl):
                table = docx.table.Table(block, doc)
                html_content += process_table(table)


        while list_stack:
            html_content += f"</{list_stack.pop()}>"

        return html_content


    return convert_doc_to_html(doc=doc, file_options=file_options)


def docx2md(doc_path, file_options):
    """将 .docx 文档转换为 Markdown，保留结构和基本样式"""
    doc = Document(doc_path)
    link_target_list = []

    def get_md_inline_style(run):
        """将 Word Run 样式转为 Markdown 内联格式（或 HTML）"""
        text = run.text or ""
        if not text.strip():
            return ""

        # 删除线
        if 'strike' in run._r.xml:
            text = f"~~{text}~~"

        # 粗体
        if run.bold:
            text = f"**{text}**"

        # 斜体
        if run.italic:
            text = f"*{text}*"

        # 下划线：Markdown 不支持，用 <u>
        if run.underline:
            text = f"<u>{text}</u>"

        # 高亮：用 <mark>（非标准 Markdown，但常见）
        try:
            if run.font.highlight_color:
                text = f"<mark>{text}</mark>"
        except Exception as e:
            text=  text
        # 颜色/字体等：忽略（或可扩展为 <span style="...">）
        return text

    def detect_list(paragraph):
        p_xml = paragraph._element.xml
        if 'w:numPr' in p_xml:
            if "w:numFmt w:val=\"bullet\"" in p_xml:
                return "ul"
            return "ol"
        return None

    def extract_images_md(paragraph, file_options):
        """提取图片并返回 Markdown 图片语法"""
        md_images = []
        temp_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(temp_dir, exist_ok=True)

        for run in paragraph.runs:
            for drawing in run._element.findall(
                    ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing"):
                blip = drawing.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
                if blip is not None:
                    rId = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                    if rId in paragraph.part.rels:
                        image_part = paragraph.part.rels[rId].target_part
                        image_data = image_part.blob
                        image_ext = image_part.content_type.split("/")[-1]
                        file_name = f"image_{uuid.uuid4().hex}.{image_ext}"
                        temp_img_path = os.path.join(temp_dir, file_name)
                        with open(temp_img_path, "wb") as f:
                            f.write(image_data)

                        image_url = upload(temp_img_path, file_options)
                        os.remove(temp_img_path)
                        if image_url:
                            md_images.append(f"![Image]({image_url})")
                        else:
                            md_images.append("![Image](None)")
        return " ".join(md_images)

    def process_table_md(table):
        """将表格转为 Markdown 表格（不支持合并单元格）"""
        rows = []
        for i, row in enumerate(table.rows):
            cells = [cell.text.strip().replace("\n", "<br>") for cell in row.cells]
            rows.append(cells)

        if not rows:
            return ""

        # 简单表格：只处理第一行作为 header（如果存在）
        try:
            header = rows[0]
            body = rows[1:]
            col_count = len(header)
            separator = ["---"] * col_count
            table_lines = ["| " + " | ".join(header) + " |"]
            table_lines.append("| " + " | ".join(separator) + " |")
            for r in body:
                # 补齐列数
                r = (r + [""] * col_count)[:col_count]
                table_lines.append("| " + " | ".join(r) + " |")
            return "\n".join(table_lines)
        except Exception:
            # 降级：转为纯文本
            return "\n".join(["\t".join(row) for row in rows])

    def extract_paragraph_text_md(paragraph, file_options):
        """提取段落文本，转为 Markdown 兼容内容"""
        content_parts = []

        # 先处理图片（因为图片在 runs 中）
        img_md = extract_images_md(paragraph, file_options)
        if img_md:
            content_parts.append(img_md)

        # 处理文本和超链接
        for child in paragraph._element.xpath(".//*"):
            if child.tag.endswith("}t"):  # 普通文本
                text = child.text or ""
                if text.strip():
                    run = next((r for r in paragraph.runs if r.text and text in r.text), None)
                    if run:
                        styled_text = get_md_inline_style(run)
                        content_parts.append(styled_text)
                    else:
                        content_parts.append(text)

            elif child.tag.endswith("}hyperlink"):
                rId = child.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                if rId and rId in paragraph.part.rels:
                    rel = paragraph.part.rels[rId]
                    link_target = urllib.parse.unquote(rel.target_ref)
                    link_text_elements = child.xpath(".//w:t")
                    link_text = "".join([t.text for t in link_text_elements if t is not None and t.text])
                    link_text = link_text.strip()

                    # 处理本地文件
                    if link_target.startswith('file:///'):
                        file_path = link_target[len('file:///'):]
                        if os.path.exists(file_path):
                            uploaded_url = upload(file_path, file_options)
                            if uploaded_url:
                                link_target_list.append({"file_path": file_path, "file_upload_url": uploaded_url})
                                content_parts.append(f"[{link_text}]({uploaded_url})")
                            else:
                                content_parts.append(f"[{link_text}]({link_target})")
                        else:
                            content_parts.append(f"[{link_text}]({link_target})")
                    elif link_target.startswith('http'):
                        content_parts.append(f"[{link_text}]({link_target})")
                    else:
                        # 相对路径：尝试匹配已上传文件
                        matched = False
                        for item in link_target_list:
                            if os.path.basename(item["file_path"]) == link_target:
                                content_parts.append(f"[{link_text}]({item['file_upload_url']})")
                                matched = True
                                break
                        if not matched:
                            content_parts.append(f"[{link_text}]({link_target})")

            elif child.tag.endswith("}br"):
                content_parts.append("<br>")

        return "".join(content_parts).strip()

    def process_paragraph_md(para, file_options):
        text = extract_paragraph_text_md(para, file_options)
        if not text:
            return ""

        if para.style and para.style.name.startswith("Heading"):
            level = para.style.name.split()[-1]
            if level.isdigit():
                level = int(level)
                level = max(1, min(6, level))
                return f"{'#' * level} {text}\n"


        current_list_type = detect_list(para)
        if current_list_type:
            return text


        return f"{text}\n\n"


    md_lines = []
    list_stack = []

    for block in doc.element.body:
        if isinstance(block, CT_P):
            para = docx.text.paragraph.Paragraph(block, doc)
            current_list_type = detect_list(para)

            if current_list_type:
                # 确保列表正确嵌套
                while len(list_stack) > 0 and list_stack[-1] != current_list_type:
                    list_stack.pop()

                if not list_stack or list_stack[-1] != current_list_type:
                    list_stack.append(current_list_type)

                content = process_paragraph_md(para, file_options)
                indent = "  " * (len(list_stack) - 1)
                prefix = "- " if current_list_type == "ul" else f"{len([x for x in list_stack if x == 'ol'])}. "
                md_lines.append(f"{indent}{prefix}{content}")
            else:
                # 非列表：关闭所有列表
                list_stack.clear()
                md_lines.append(process_paragraph_md(para, file_options))

        elif isinstance(block, CT_Tbl):
            table_md = process_table_md(docx.table.Table(block, doc))
            md_lines.append(table_md + "\n\n")

    return "".join(md_lines).strip()


def doc2docx(input_path, output_path=None, keep_active=False):
    paths = resolve_paths(input_path, output_path)
    if sys.platform == "darwin":
        return macos(paths, keep_active)
    elif sys.platform == "win32":
        return windows(paths, keep_active)
    elif sys.platform == "linux" or sys.platform == "linux2":
        return linux(paths, keep_active)
    else:
        raise NotImplementedError(
            (
                "doc2docx is not implemented for linux as it requires Microsoft Word to"
                " be installed"
            ),
        )


def mk_pdf2docx(pdf_path, docx_path):
    """将 PDF 转换为 DOCX"""
    converter = pdf2docx.Converter(pdf_path)
    converter.convert(docx_path, multi_processing=True)
    converter.close()
    return docx_path


