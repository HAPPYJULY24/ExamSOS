# test_file_upload.py
import streamlit as st
from modules import file_parser  # ✅ 直接调用 file_parser.py

st.title("📂 文件解析 & GPT 提交 Demo")

uploaded_files = st.file_uploader(
    "上传文件 (支持 PDF / DOCX / TXT / PPTX / PPT)", 
    type=["pdf", "docx", "txt", "pptx", "ppt"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"共上传 {len(uploaded_files)} 个文件 ✅")

    for uploaded_file in uploaded_files:
        uploaded_file.seek(0)  # ⚡ 确保每次都能读到完整内容
        st.markdown(f"### 📖 文件: {uploaded_file.name}")
        extracted_text = file_parser.extract_text_from_file(uploaded_file)  # ✅ 调用模块里的函数

        # 控制台打印前 1000 字
        print(f"======= {uploaded_file.name} 内容预览 =======")
        print(extracted_text[:1000])

        # 前端展示
        st.text_area("文件内容预览", extracted_text, height=300, key=uploaded_file.name)

    # 模拟提交给 GPT
    if st.button("🚀 模拟提交到 GPT"):
        final_text = file_parser.merge_files_text(uploaded_files)  # ✅ 调用模块里的函数
        
        # 打印到控制台
        print("======= 模拟提交 GPT 的完整内容 =======")
        print(final_text[:2000])  # 只打印前 2000 字，防止爆掉控制台

        # 前端展示
        st.subheader("📝 提交给 GPT 的合并内容")
        st.text_area("GPT 输入内容", final_text, height=500)
        st.info("✅ 文件文本已准备好，可以发送到 GPT 进行处理")
