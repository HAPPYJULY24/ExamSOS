# pages/Export PDF.py
# 用于让用户手动导出的模块（支持简单 Markdown）

import streamlit as st
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from datetime import datetime

st.set_page_config(page_title="PDF 导出", layout="wide")
st.title("📑 PDF 导出工具")

st.write("请将你想导出的内容粘贴到下面输入框：")

# 输入框
user_text = st.text_area(
    "粘贴内容：",
    height=400,
    placeholder="在这里粘贴 GPT 生成的笔记，确认后再导出为 PDF..."
)

# 文件名输入框
custom_filename = st.text_input("导出文件名（不需要输入 .pdf）：", "")


def clean_text(text: str) -> str:
    """
    清理不需要导出的标记，例如 FILE: Document_1
    """
    # 去掉 FILE: Document_x 开头的行
    text = re.sub(r"^FILE: Document_\d+\s*\n?", "", text, flags=re.MULTILINE)
    return text


def save_to_pdf(text, filename="exported_notes.pdf"):
    """使用 reportlab 将文本导出为 PDF，支持简单 Markdown 格式"""

    # 在导出前清理
    text = clean_text(text)

    # 输出目录
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, filename)

    # 创建 PDF
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    # 样式
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CustomTitle",
        fontSize=16,
        leading=20,
        spaceAfter=15,
        textColor=colors.HexColor("#2C3E50"),
        alignment=1,  # 居中
    ))
    styles.add(ParagraphStyle(
        name="CustomBody",
        fontSize=11,
        leading=16,
        spaceAfter=8,
    ))

    story = []

    # 添加标题
    story.append(Paragraph("ExamSOS", styles["CustomTitle"]))
    story.append(Spacer(1, 12))

    # 添加时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f"Time export {timestamp}", styles["CustomBody"]))
    story.append(Spacer(1, 20))

    # 逐行写入正文（解析 Markdown）
    bullet_items = []
    for line in text.split("\n"):
        line = line.strip()

        # 空行
        if not line:
            if bullet_items:
                story.append(ListFlowable(bullet_items, bulletType='bullet'))
                bullet_items = []
            story.append(Spacer(1, 12))
            continue

        # 处理 Markdown 粗体
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)

        # 处理标题
        if line.startswith("## "):
            if bullet_items:
                story.append(ListFlowable(bullet_items, bulletType='bullet'))
                bullet_items = []
            story.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("# "):
            if bullet_items:
                story.append(ListFlowable(bullet_items, bulletType='bullet'))
                bullet_items = []
            story.append(Paragraph(line[2:], styles["Heading1"]))

        # 处理列表
        elif line.startswith("- "):
            bullet_items.append(ListItem(Paragraph(line[2:], styles["CustomBody"])))
        else:
            if bullet_items:
                story.append(ListFlowable(bullet_items, bulletType='bullet'))
                bullet_items = []
            story.append(Paragraph(line, styles["CustomBody"]))

    # 收尾（如果最后还有列表）
    if bullet_items:
        story.append(ListFlowable(bullet_items, bulletType='bullet'))

    doc.build(story)
    return pdf_path


# 生成 PDF
if st.button("📑 生成 PDF"):
    if user_text.strip():
        # 确定文件名
        if custom_filename.strip():
            filename = f"{custom_filename.strip()}.pdf"
        else:
            # 自动用正文第一行作为文件名
            first_line = user_text.split("\n")[0].strip()
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", first_line)  # 去掉非法字符
            filename = f"{safe_title or 'exported_notes'}.pdf"

        pdf_path = save_to_pdf(user_text, filename=filename)
        st.success(f"✅ PDF 已生成！文件名：{filename}")

        # 下载按钮
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="⬇️ 下载 PDF",
                data=f,
                file_name=filename,
                mime="application/pdf"
            )
    else:
        st.warning("⚠️ 请输入内容再生成 PDF")
