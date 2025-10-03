# modules/file_parser.py
# 文件格式的转换，文件内容的提取
# 输入处理器（上传 → 提取文字）

import os
import tempfile
from pptx import Presentation
from docx import Document
import fitz  # PyMuPDF
import io
import streamlit as st
from PIL import Image
import numpy as np
import easyocr

# 初始化 OCR 引擎（中英文）
OCR_READER = easyocr.Reader(['en', 'ch_sim'], gpu=False)  # 如果服务器支持 GPU，可改成 True


def ocr_image(pil_img):
    """OCR 识别图片 -> 文字（使用 easyocr）"""
    try:
        img_np = np.array(pil_img.convert('RGB'))
        result = OCR_READER.readtext(img_np, detail=0)
        return "\n".join(result).strip()
    except Exception as e:
        return f"❌ OCR 识别失败: {e}"


def extract_text_from_file(uploaded_file):
    """根据文件类型提取纯文本（支持 PPTX/DOCX/PDF/TXT，全部带 OCR）"""
    filename = uploaded_file.name.lower()

    # 一次性读入内存
    file_bytes = uploaded_file.read()
    file_stream = io.BytesIO(file_bytes)

    # -------- PPTX --------
    if filename.endswith(".pptx"):
        prs = Presentation(file_stream)
        text = []

        for i, slide in enumerate(prs.slides, start=1):
            slide_text = []
            # 1️⃣ 直接提取文字
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text)

            # ⚠️ 这里只保留文字提取，不再强制做图片 OCR（性能更好）
            if slide_text:
                text.append(f"【Slide {i}】\n" + "\n".join(set(slide_text)))

        return "\n\n".join(text)

    elif filename.endswith(".ppt"):
        return "❌ 不支持 .ppt 格式，请先在本地另存为 .pptx 再上传。"

    # -------- DOCX --------
    elif filename.endswith(".docx"):
        doc = Document(file_stream)
        text = []

        # 1️⃣ 普通段落
        for p in doc.paragraphs:
            if p.text.strip():
                text.append(p.text)

        # 2️⃣ 图片 OCR
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                image_data = rel.target_part.blob
                pil_img = Image.open(io.BytesIO(image_data))
                ocr_text = ocr_image(pil_img)
                if ocr_text:
                    text.append(ocr_text)

        return "\n".join(text)

    # -------- PDF --------
    elif filename.endswith(".pdf"):
        text = []
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf_doc:
            for page_num, page in enumerate(pdf_doc, start=1):
                page_text = page.get_text("text").strip()

                # OCR 每一页（可选：如果只需要文本，可以关掉 OCR 提升速度）
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = ocr_image(img)

                combined_parts = set()
                if page_text:
                    combined_parts.add(page_text)
                if ocr_text:
                    combined_parts.add(ocr_text)

                combined_text = "\n".join(combined_parts)
                text.append(f"【第 {page_num} 页】\n{combined_text}")

        return "\n\n".join(text)

    # -------- TXT --------
    elif filename.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")

    else:
        return "❌ 不支持的文件格式"


def preview_files(uploaded_files):
    """只展示文件名，不显示内容"""
    for uf in uploaded_files:
        st.write(f"✅ {uf.name}")


def merge_files_text(uploaded_files):
    """把多个文件内容拼接成一个大字符串，带文件名分隔符"""
    all_texts = []
    for idx, uploaded_file in enumerate(uploaded_files, start=1):
        uploaded_file.seek(0)  # reset
        text = extract_text_from_file(uploaded_file)

        print(f"======= {uploaded_file.name} 内容预览 =======")
        print(text[:1000])

        labeled_text = f"\n======= 文件 {idx}: {uploaded_file.name} =======\n{text}\n"
        all_texts.append(labeled_text)

    return "\n".join(all_texts)
