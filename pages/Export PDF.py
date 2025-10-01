# pages/Export PDF.py
#用于让用户手动导出的模块

import streamlit as st
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
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


def save_to_pdf(text, filename="exported_notes.pdf"):
    """使用 reportlab 将文本导出为 PDF（简易 ChatGPT 风格）"""
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
    story.append(Paragraph("📑 ExamSOS 导出笔记", styles["CustomTitle"]))
    story.append(Spacer(1, 12))

    # 添加时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f"生成时间：{timestamp}", styles["CustomBody"]))
    story.append(Spacer(1, 20))

    # 逐行写入正文
    for line in text.split("\n"):
        if not line.strip():
            story.append(Spacer(1, 12))  # 空行
        elif line.strip().startswith("##"):
            story.append(Paragraph(line.strip("## "), styles["Heading2"]))
        elif line.strip().startswith("#"):
            story.append(Paragraph(line.strip("# "), styles["Heading1"]))
        elif line.strip().startswith("-"):
            story.append(Paragraph("• " + line.strip("- "), styles["CustomBody"]))
        else:
            story.append(Paragraph(line, styles["CustomBody"]))

    doc.build(story)

    return pdf_path


# 生成 PDF
if st.button("📑 生成 PDF"):
    if user_text.strip():
        pdf_path = save_to_pdf(user_text, filename="exported_notes.pdf")
        st.success("✅ PDF 已生成！")

        # 下载按钮
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="⬇️ 下载 PDF",
                data=f,
                file_name="exported_notes.pdf",
                mime="application/pdf"
            )
    else:
        st.warning("⚠️ 请输入内容再生成 PDF")
