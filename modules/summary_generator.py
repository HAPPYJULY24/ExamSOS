# module/summary_generator.py

import streamlit as st
from modules import file_parser, extractor
from config import OPENAI_API_KEY
import pyperclip
import openai
from langdetect import detect

# ================= 原有导航栏函数 =================
def navigation_buttons(prev_label=None, next_label=None, prev_step=None, next_step=None):
    st.markdown(
        f"""
        <style>
        .fixed-buttons {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: white;
            padding: 10px 20px;
            border-radius: 10px;
            box-shadow: 0px 2px 10px rgba(0,0,0,0.2);
            z-index: 100;
        }}
        .fixed-buttons button {{
            padding: 8px 18px;
            margin: 0 8px;
            border-radius: 6px;
            border: none;
            background-color: #4CAF50;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }}
        .fixed-buttons button:disabled {{
            background-color: #ddd;
            color: #666;
            cursor: not-allowed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if prev_label and prev_step and st.button(f"⬅ {prev_label}", key=f"prev_{prev_step}"):
            st.session_state["step"] = prev_step
            st.rerun()
    with col_info:
        st.markdown(f"### 步骤 {st.session_state['step']}", unsafe_allow_html=True)
    with col_next:
        if next_label and next_step and st.button(f"{next_label} ➡", key=f"next_{next_step}"):
            st.session_state["step"] = next_step
            st.rerun()


# ================= 主程序入口 =================
def run():
    st.title("📘 ExamSOS - MVP 测试版")

    # ---------- 初始化 session_state ----------
    if "step" not in st.session_state:
        st.session_state["step"] = 1
    if "summary" not in st.session_state:
        st.session_state["summary"] = ""

    # ---------- 左上角返回首页 & 重新开始 ----------
    col_back, col_restart, _ = st.columns([1, 1, 8])
    with col_back:
        if st.button("⬅️ 返回首页", key="back_home"):
            st.session_state["page"] = "home"
            st.rerun()
    with col_restart:
        if st.button("🔄 重新开始", key="restart"):
            for key in ["uploaded_files", "summary", "step",
                        "bilingual", "target_lang", "style",
                        "pending_new_text", "pending_selected_text",
                        "pending_user_request", "show_pending"]:
                st.session_state.pop(key, None)
            st.session_state["step"] = 1
            st.rerun()

    st.markdown("---")

    # ---------- 步骤显示 ----------
    steps = ["📂 上传文件", "🌐 设置语言 & 风格", "📑 提取重点", "✏️ 修改与导出"]
    progress = int((st.session_state["step"] - 1) / (len(steps) - 1) * 100)
    st.progress(progress)
    st.markdown(f"### 当前进度：{steps[st.session_state['step']-1]}")

   
    # ---------- Step 1: 上传文件 ----------
    if st.session_state.get("step", 1) == 1:   # ✅ 防止 KeyError
        uploaded_files = st.file_uploader(
            "上传文件 (支持 PDF / DOCX / TXT / PPTX / PPT)",
            accept_multiple_files=True,
            type=["pdf", "docx", "txt", "pptx", "ppt"]
        )
        if uploaded_files:
            st.session_state["uploaded_files"] = uploaded_files
            st.session_state["parsed_texts"] = []   # 存放解析后的文本
            st.success("✅ 文件上传成功！")

            # 展示解析预览
            for uf in uploaded_files:
                st.subheader(f"📖 {uf.name} - 内容预览")

                preview_text = file_parser.extract_text_from_file(uf)

                # 存入 session_state
                st.session_state["parsed_texts"].append(preview_text)

                # ⚡ Debug：打印总字数
                st.caption(f"提取总字数: {len(preview_text)}")
                print(f"======= {uf.name} 提取完成，总字数 {len(preview_text)} =======")

                # ⚡ 控制台只打印前 1000 字，避免爆屏
                print(preview_text[:1000])

                # ⚡ 前端：展示前 2000 字（避免卡顿），并提示完整度
                st.text_area(
                    "内容 (预览，最多 2000 字)",
                    preview_text[:2000],
                    height=300,
                    key=f"preview_{uf.name}"
                )

                if len(preview_text) > 2000:
                    st.warning(
                        f"⚠️ 内容过长，已截断展示 (仅显示前 2000 字，完整字数 {len(preview_text)})"
                    )

        if uploaded_files:
            navigation_buttons(next_label="下一步", next_step=2)

   # ---------- Step 2: 设置语言 & 风格 & 学科 ----------
    elif st.session_state["step"] == 2:
        st.subheader("🎯 学习目标")
        study_goal = st.radio(
            "选择你希望生成的笔记用途：",
            ["详细模式（白话+例子，适合打基础）", 
            "考前笔记（简短+应试技巧）", 
            "客制化（自定义需求）"],
            index=0,
            key="goal_radio"
        )

        # 映射到 extractor.py 的 mode 参数
        goal_map = {
            "详细模式（白话+例子，适合打基础）": "detailed",
            "考前笔记（简短+应试技巧）": "exam",
            "客制化（自定义需求）": "custom",
        }
        st.session_state["style"] = goal_map[study_goal]

        # 如果是客制化，要求额外输入
        custom_instruction = None
        if st.session_state["style"] == "custom":
            custom_instruction = st.text_area(
                "请输入你想要的笔记生成方式（例如：结合思维导图形式、用表格总结、故事化解释等）",
                placeholder="在这里输入你的要求...",
                key="custom_style"
            )
        st.session_state["custom_instruction"] = custom_instruction

        st.subheader("📚 学科类别")
        subject = st.selectbox(
            "请选择资料所属学科：",
            ["未指定", "文科（历史/政治/文学）", "理科（数学/物理/化学）", "工程/计算机（代码/系统设计/电子）",
            "医学/生物", "商科/管理"]
        )
        st.session_state["subject"] = subject

        st.subheader("🌐 输出语言设置")
        mode = st.radio(
            "选择输出模式：",
            ["单语（保持原文语言）", "双语：英文 + 中文"],
            index=0,
            key="mode_radio"
        )
        bilingual = (mode == "双语：英文 + 中文")
        st.session_state["bilingual"] = bilingual
        st.session_state["target_lang"] = "zh" if bilingual else "en"

        st.subheader("📝 是否生成模拟考题")
        exam_q = st.checkbox("需要生成模拟考题（附参考答案）", value=False)
        st.session_state["need_exam_questions"] = exam_q

        navigation_buttons("上一步", "下一步", prev_step=1, next_step=3)
        
    # ---------- Step 3: 提取重点 ----------
    elif st.session_state.get("step") == 3:
        parsed_texts = st.session_state.get("parsed_texts", [])
        uploaded_files = st.session_state.get("uploaded_files", [])

        if parsed_texts and uploaded_files:
            st.subheader("📂 文件预览")
            file_parser.preview_files(uploaded_files)

            col_extract, col_back = st.columns([1, 1])
            with col_extract:
                if st.button("📑 提取重点", key="extract_step3"):
                    with st.spinner("AI 正在分析中..."):
                        # ✅ 传入字符串列表，不再传文件
                        summary = extractor.extract_summary(
                            texts=parsed_texts,
                            api_key=OPENAI_API_KEY,
                            bilingual=st.session_state.get("bilingual", False),
                            target_lang=st.session_state.get("target_lang", "zh"),
                            mode=st.session_state.get("style", "default"),
                            generate_mock=st.session_state.get("need_exam_questions", False),
                            custom_instruction=st.session_state.get("custom_instruction")
                        )
                    if summary.strip():
                        st.session_state["summary"] = summary
                        st.success("✅ 提取完成！")
                        st.session_state["step"] = 4
                        st.rerun()
            with col_back:
                if st.button("⬅️ 上一步", key="prev_step3"):
                    st.session_state["step"] = 2
                    st.rerun()
        else:
            st.warning("⚠️ 请先上传文件！")

    # ---------- Step 4: 修改与导出 ----------
    elif st.session_state["step"] == 4:
        st.subheader("📖 提取结果")

        summary_text = st.session_state.get("summary", "")

        if summary_text.strip():
            # ✅ 用 st.code 显示结果，自带复制按钮
            st.code(summary_text, language="text")
            st.caption("⬆️ 点击右上角的 📋 按钮即可复制内容")

            st.markdown("---")
            st.subheader("✏️ 局部修改")
            selected_text = st.text_area(
                "请输入你想修改的片段（从上面复制过来）",
                placeholder="粘贴需要调整的部分...",
                key="selected_text_area"
            )
            user_request = st.text_input(
                "请输入修改要求",
                placeholder="例如：翻译成英文 / 解释更详细 / 用表格总结",
                key="user_request_input"
            )

            if st.button("提交修改", key="submit_modification"):
                if not selected_text.strip() or not user_request.strip():
                    st.warning("⚠️ 请先粘贴片段并输入修改要求")
                else:
                    try:
                        lang = detect(selected_text)
                    except:
                        lang = "en"

                    if lang == "en":
                        lang_instruction = "Please make sure the output remains in English."
                    elif lang.startswith("zh"):
                        lang_instruction = "请确保输出保持为中文。"
                    else:
                        lang_instruction = "Keep the same language as the original text."

                    with st.spinner("AI 正在修改中..."):
                        client = openai.OpenAI(api_key=OPENAI_API_KEY)
                        prompt = f"""以下是文档中的一个片段，请根据用户的需求进行修改。
    注意：保持原文片段的语言风格不变。

    原文片段：
    {selected_text}

    用户的修改要求：
    {user_request}

    {lang_instruction}

    请输出修改后的结果：
    """
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        new_text = response.choices[0].message.content.strip()

                    st.session_state["pending_new_text"] = new_text
                    st.session_state["pending_selected_text"] = selected_text
                    st.session_state["pending_user_request"] = user_request
                    st.session_state["show_pending"] = True
                    st.rerun()

            if st.session_state.get("show_pending"):
                st.markdown("### 🔍 修改对比结果")
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("原文片段")
                    st.text_area("原文", st.session_state.get("pending_selected_text", ""), height=200, key="pending_original")
                with col2:
                    st.subheader("修改后")
                    st.text_area("修改后", st.session_state.get("pending_new_text", ""), height=200, key="pending_new")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 应用修改", key="apply_pending"):
                        pending_sel = st.session_state.get("pending_selected_text")
                        pending_new = st.session_state.get("pending_new_text")
                        if pending_sel and pending_sel in st.session_state["summary"]:
                            st.session_state["summary"] = st.session_state["summary"].replace(pending_sel, pending_new, 1)
                            st.session_state.pop("pending_new_text", None)
                            st.session_state.pop("pending_selected_text", None)
                            st.session_state.pop("pending_user_request", None)
                            st.session_state["show_pending"] = False
                            st.success("✅ 修改已应用！")
                            st.rerun()
                        else:
                            st.warning("⚠️ 未能在原文中找到待替换的片段，可能已被修改或不完全匹配。")
                with col2:
                    if st.button("❌ 取消修改", key="cancel_pending"):
                        st.session_state.pop("pending_new_text", None)
                        st.session_state.pop("pending_selected_text", None)
                        st.session_state.pop("pending_user_request", None)
                        st.session_state["show_pending"] = False
                        st.info("已取消修改。")
                        st.rerun()

        else:
            st.info("⚠️ 暂无内容，请先生成总结。")

        navigation_buttons("上一步", None, prev_step=3)

# --------- 主入口 ---------
if __name__ == "__main__":
    run()
