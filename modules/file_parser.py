# modules/file_parser.py
# 文件格式的转换，文件内容的提取
# 输入处理器（上传 → 提取文字）

import os
import io
import tempfile
from pptx import Presentation
from docx import Document
import fitz  # PyMuPDF
from PIL import Image, ImageStat
import numpy as np
import streamlit as st
import easyocr

# 初始化 OCR 引擎（中英文）
OCR_READER = easyocr.Reader(['en', 'ch_sim'], gpu=False)  # gpu=True 如果服务器支持 GPU


def ocr_image(pil_img):
    """OCR 识别图片 -> 文字（使用 easyocr）"""
    try:
        img_np = np.array(pil_img.convert('RGB'))
        result = OCR_READER.readtext(img_np, detail=0)
        return "\n".join(result).strip()
    except Exception as e:
        return f"❌ OCR 识别失败: {e}"


def is_text_image(pil_img, threshold=0.05):
    """
    简单判断图片是否可能包含文字
    threshold: 亮度方差阈值，默认 0.05
    """
    gray = pil_img.convert("L")
    stat = ImageStat.Stat(gray)
    variance = stat.var[0] / 255**2  # 方差归一化
    return variance > threshold


def extract_text_from_pptx_file(file_bytes, filename="unknown.pptx"):
    """
    直接用 python-pptx 提取文字，同时对嵌入图片做 OCR（优化版）
    filename: 可选，方便在日志或调试中使用
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        pptx_path = os.path.join(tmpdir, filename)
        with open(pptx_path, "wb") as f:
            f.write(file_bytes)

        prs = Presentation(pptx_path)
        text = []

        for i, slide in enumerate(prs.slides, start=1):
            slide_text = []

            # 1️⃣ 提取可编辑文字
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        para_text = para.text.strip()
                        if para_text:
                            slide_text.append(para_text)

            # 2️⃣ 对 slide 内图片做 OCR（优化：只对可能含文字的图片）
            for shape in slide.shapes:
                if shape.shape_type == 13:  # Picture 类型
                    try:
                        image = shape.image
                        pil_img = Image.open(io.BytesIO(image.blob))
                        if is_text_image(pil_img):
                            ocr_text = ocr_image(pil_img)
                            if ocr_text:
                                slide_text.append(ocr_text)
                    except Exception as e:
                        slide_text.append(f"❌ Slide 图片 OCR 失败: {e}")

            if slide_text:
                text.append(f"【Slide {i} - {filename}】\n" + "\n".join(set(slide_text)))

        return "\n\n".join(text)



def extract_text_from_file(uploaded_file, filename=None):
    """
    根据文件类型提取纯文本（支持 PPTX/DOCX/PDF/TXT，全部带 OCR）
    uploaded_file: 文件对象或 io.BytesIO
    filename: 可选，用于指定文件名（方便缓存/日志）
    """
    if filename is None:
        # 尝试从文件对象获取 name 属性
        filename = getattr(uploaded_file, "name", "unknown").lower()
    else:
        filename = filename.lower()

    # 如果是 BytesIO，需要 reset
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    file_bytes = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file
    file_stream = io.BytesIO(file_bytes)

    # -------- PPTX --------
    if filename.endswith(".pptx"):
        return extract_text_from_pptx_file(file_bytes, filename=filename)

    # -------- DOCX --------
    elif filename.endswith(".docx"):
        doc = Document(file_stream)
        text = []

        for p in doc.paragraphs:
            if p.text.strip():
                text.append(p.text)

        # 图片 OCR
        for rel in doc.part.rels.values():
            if hasattr(rel, "target_ref") and "image" in rel.target_ref:
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

                ocr_text = ""
                if not page_text or len(page_text) < 30:  # 页文字过少才 OCR
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = ocr_image(img)

                combined_parts = set()
                if page_text:
                    combined_parts.add(page_text)
                if ocr_text:
                    combined_parts.add(ocr_text)

                combined_text = "\n".join(combined_parts)
                text.append(f"【第 {page_num} 页 - {filename}】\n{combined_text}")

        return "\n\n".join(text)

    # -------- TXT --------
    elif filename.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")

    else:
        return f"❌ 不支持的文件格式: {filename}"



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
