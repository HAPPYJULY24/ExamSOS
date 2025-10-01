# modules/file_parser.py
# 文件格式的转换，文件内容的提取
#输入处理器（上传 → 提取文字）

import os
import tempfile
import subprocess
from pptx import Presentation
from docx import Document
import fitz  # PyMuPDF
import io
import streamlit as st
from PIL import Image
import numpy as np

# ⚡ 使用 easyocr 替换 pytesseract
import easyocr

# 初始化 OCR 引擎（中英文）
OCR_READER = easyocr.Reader(['en', 'ch_sim'], gpu=False)  # gpu=True 如果服务器支持 GPU

# ⚡ LibreOffice 路径
LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"


def convert_ppt_to_pptx(input_path, output_dir):
    """用 LibreOffice 把 .ppt 转换成 .pptx，返回新文件路径"""
    try:
        result = subprocess.run(
            [LIBREOFFICE_PATH, "--headless", "--convert-to", "pptx", "--outdir", output_dir, input_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print("LibreOffice 输出：", result.stdout)
        print("LibreOffice 错误：", result.stderr)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"❌ LibreOffice 转换失败: {e.stderr}")

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, base_name + ".pptx")
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"❌ LibreOffice 没有生成 {output_path}")

    return output_path


def ocr_image(pil_img):
    """OCR 识别图片 -> 文字（使用 easyocr）"""
    try:
        img_np = np.array(pil_img.convert('RGB'))
        result = OCR_READER.readtext(img_np, detail=0)
        return "\n".join(result).strip()
    except Exception as e:
        return f"❌ OCR 识别失败: {e}"


def extract_text_from_file(uploaded_file):
    """根据文件类型提取纯文本（支持 PPT/PPTX/DOCX/PDF/TXT，全部带 OCR）"""
    filename = uploaded_file.name.lower()

    # 一次性读入内存
    file_bytes = uploaded_file.read()
    file_stream = io.BytesIO(file_bytes)

    # -------- PPT / PPTX --------
    if filename.endswith((".ppt", ".pptx")):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, os.path.basename(filename))
            with open(file_path, "wb") as f:
                f.write(file_bytes)

            if filename.endswith(".ppt"):
                try:
                    pptx_path = convert_ppt_to_pptx(file_path, tmpdir)
                except Exception as e:
                    return f"❌ PPT 转换失败: {e}"
            else:
                pptx_path = file_path

            prs = Presentation(pptx_path)
            text = []

            for i, slide in enumerate(prs.slides, start=1):
                slide_text = []
                # 1️⃣ 直接提取文字
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text.append(shape.text)

                # 2️⃣ 整个 slide 转图片做 OCR
                img_path = os.path.join(tmpdir, f"slide_{i}.png")
                try:
                    # 用 libreoffice 转换 slide -> png
                    subprocess.run(
                        [LIBREOFFICE_PATH, "--headless", "--convert-to", "png", "--outdir", tmpdir, pptx_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    if os.path.exists(img_path):
                        pil_img = Image.open(img_path)
                        ocr_text = ocr_image(pil_img)
                        if ocr_text:
                            slide_text.append(ocr_text)
                except Exception as e:
                    slide_text.append(f"❌ Slide OCR 失败: {e}")

                if slide_text:
                    text.append(f"【Slide {i}】\n" + "\n".join(set(slide_text)))

            return "\n\n".join(text)

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
