# module/summary_generator.py

import streamlit as st
from modules import file_parser, extractor
from config import OPENAI_API_KEY
import openai
from langdetect import detect
from modules.logger import log_event
from modules.auth.user_memory import record_user_edit

# === 模块健康状态上报 ===
from modules.utils.system_status import update_module_status

try:
    update_module_status("summary_generator", "active", "模块加载成功")
except Exception as e:
    update_module_status("summary_generator", "error", str(e))

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


# ---------- 主程序入口（修正版 run） ----------
def run():
    st.title("📘 ExamSOS - MVP 测试版")

    # ---------- 初始化 session_state ----------
    if "step" not in st.session_state:
        st.session_state["step"] = 1
    if "summary" not in st.session_state:
        st.session_state["summary"] = ""

    # 保证 uploaded_files 在函数内始终有定义（从 session 读取）
    uploaded_files = st.session_state.get("uploaded_files", None)

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
                        "pending_user_request", "show_pending", "parsed_texts"]:
                st.session_state.pop(key, None)
            st.session_state["step"] = 1
            st.rerun()

    st.markdown("---")

    # ---------- 步骤显示 ----------
    steps = ["📂 上传文件", "🌐 设置语言 & 风格", "📑 提取重点", "✏️ 修改与导出"]
    current_step = st.session_state.get("step", 1)
    current_step = max(1, min(current_step, len(steps)))
    progress = int((current_step - 1) / (len(steps) - 1) * 100)
    st.progress(progress)
    st.markdown(f"### 当前进度：{steps[current_step - 1]}")

    # ================= 性能优化部分（并行 + 缓存函数） =================
    from concurrent.futures import ThreadPoolExecutor

    @st.cache_data(show_spinner=False)
    def cached_extract(file_bytes, file_name):
        """缓存解析结果：以 (bytes, filename) 为 key"""
        import io
        from modules import file_parser
        return file_parser.extract_text_from_file(io.BytesIO(file_bytes), file_name)

    def extract_texts_parallel(files):
        """并行解析多个 Streamlit UploadedFile 列表（返回 list[str]）"""
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for f in files:
                # f is streamlit.uploaded_file.UploadedFile
                futures.append(
                    executor.submit(
                        cached_extract,
                        f.getvalue(),  # bytes
                        f.name
                    )
                )
            for fut in futures:
                results.append(fut.result())
        return results
    # =================================================

    # ---------- Step 1: 上传文件 ----------
    if current_step == 1:
        # 使用不同变量接收上传组件，避免未执行分支时污染 uploaded_files 局部变量
        new_uploads = st.file_uploader(
            "上传文件 (支持 PDF / DOCX / TXT / PPTX )",
            accept_multiple_files=True,
            type=["pdf", "docx", "txt", "pptx"]
        )

        # 用户上传了新文件：写入 session 并触发解析（清理旧解析）
        if new_uploads:
            try:
                log_event("summary_generator", "INFO", "work", "用户上传文件", meta={"count": len(new_uploads)})
                st.session_state["uploaded_files"] = new_uploads
                uploaded_files = new_uploads  
                st.session_state.pop("parsed_texts", None)

                with st.spinner("⏳ 正在解析文件..."):
                    st.session_state["parsed_texts"] = extract_texts_parallel(new_uploads)
                st.success("✅ 文件解析完成！")

                log_event("summary_generator", "INFO", "work", "文件解析成功", meta={"files": [f.name for f in new_uploads]})
            except Exception as e:
                log_event("summary_generator", "ERROR", "down", "文件解析失败", remark=str(e), reason="文件解析异常")
                st.error(f"❌ 文件解析出错：{e}")

        # 如果 session 中已有 parsed_texts（来自之前上传），也显示预览
        if uploaded_files and st.session_state.get("parsed_texts"):
            for uf, preview_text in zip(uploaded_files, st.session_state["parsed_texts"]):
                st.subheader(f"📖 {uf.name} - 内容预览")
                st.caption(f"提取总字数: {len(preview_text)}")
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

        navigation_buttons(next_label="下一步", next_step=2)

      # ---------- Step 2: 设置语言 & 风格 & 学科 ----------
    elif st.session_state["step"] == 2:
        # ========== 新增：尝试加载用户历史偏好 ==========
        user = st.session_state.get("user")
        if user and "id" in user:
            from modules.auth.user_memory import load_user_memory
            prefs = load_user_memory(user["id"])
            if prefs:
                st.session_state.update(prefs)
                log_event("summary_generator", "INFO", "load", "用户偏好已加载", meta=prefs)

        # ========== 表单主体 ==========
        st.subheader("🎯 学习目标")
        study_goal = st.radio(
            "选择你希望生成的笔记用途：",
            [
                "详细模式（白话+例子，适合打基础）",
                "考前笔记（简短+应试技巧）",
                "客制化（自定义需求）"
            ],
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
            [
                "未指定",
                "文科（历史/政治/文学）",
                "理科（数学/物理/化学）",
                "工程/计算机（代码/系统设计/电子）",
                "医学/生物",
                "商科/管理"
            ]
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

        # ======== 自定义导航按钮逻辑 ========
        col_prev, col_next = st.columns(2)

        with col_prev:
            if st.button("⬅️ 上一步", key="prev_step2"):
                st.session_state["step"] = 1
                st.rerun()

        with col_next:
            if st.button("➡️ 下一步", key="next_step3"):
                # ======== 保存用户偏好到数据库 ========
                if user and "id" in user:
                    from modules.auth.user_memory import save_user_memory

                    prefs = {
                        "study_goal": study_goal,
                        "style": st.session_state["style"],
                        "custom_instruction": custom_instruction,
                        "subject": subject,
                        "bilingual": bilingual,
                        "target_lang": st.session_state["target_lang"],
                        "need_exam_questions": exam_q
                    }

                    success = save_user_memory(user["id"], prefs)
                    if success:
                        log_event("summary_generator", "INFO", "save", "用户偏好已保存", meta=prefs)
                    else:
                        log_event("summary_generator", "ERROR", "save", "偏好保存失败", meta=prefs)
                else:
                    log_event("summary_generator", "WARNING", "skip", "未登录用户跳过偏好保存")

                # ======== 进入下一步 ========
                st.session_state["step"] = 3
                st.rerun()

        
    # ---------- Step 3: 提取重点 ----------
    elif current_step == 3:
        # 从 session 读取（始终优先使用 session 中的持久值）
        uploaded_files = st.session_state.get("uploaded_files", [])
        parsed_texts = st.session_state.get("parsed_texts", [])

        if parsed_texts and uploaded_files:
            st.subheader("📂 文件预览")
            file_parser.preview_files(uploaded_files)

            col_extract, col_back = st.columns([1, 1])
            with col_extract:
                if st.button("📑 提取重点", key="extract_step3"):
                    log_event("summary_generator", "INFO", "work", "AI提取开始")
                    try:
                        with st.spinner("AI 正在分析中..."):
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
                                log_event("summary_generator", "INFO", "work", "AI提取完成")
                                st.rerun()
                    except Exception as e:
                        log_event("summary_generator", "ERROR", "down", "AI提取失败", remark=str(e), reason="模型调用失败")
                        st.error(f"❌ AI 提取失败：{e}")
            with col_back:
                if st.button("⬅️ 上一步", key="prev_step3"):
                    st.session_state["step"] = 2
                    st.rerun()
        else:
            st.warning("⚠️ 请先上传文件并完成解析！")

# ---------- Step 4: 修改与导出 ----------
    elif st.session_state["step"] == 4:
        st.subheader("📖 提取结果")

        summary_text = st.session_state.get("summary", "")

        if summary_text.strip():
            # ✅ 显示生成的总结内容
            st.code(summary_text, language="text")
            st.caption("⬆️ 点击右上角的 📋 按钮即可复制内容")

            st.markdown("---")
            st.subheader("✏️ 局部修改")

            # ======== 用户输入修改请求 ========
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

            # ======== 提交修改请求 ========
            if st.button("提交修改", key="submit_modification"):
                if not selected_text.strip() or not user_request.strip():
                    st.warning("⚠️ 请先粘贴片段并输入修改要求")
                else:
                    try:
                        lang = detect(selected_text)
                    except:
                        lang = "en"

                    lang_instruction = {
                        "en": "Please make sure the output remains in English.",
                        "zh": "请确保输出保持为中文。"
                    }.get(lang[:2], "Keep the same language as the original text.")

                    with st.spinner("AI 正在修改中..."):
                        try:
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

                            # ======== 保存修改结果到 session ========
                            st.session_state["pending_original"] = selected_text
                            st.session_state["pending_new"] = new_text
                            st.session_state["pending_request"] = user_request
                            st.session_state["show_pending"] = True

                            log_event(
                                "summary_generator", "INFO", "change",
                                "AI 修改完成",
                                meta={"request": user_request, "lang": lang}
                            )
                            st.rerun()

                        except Exception as e:
                            log_event(
                                "summary_generator", "ERROR", "down",
                                "AI 修改失败",
                                remark=str(e),
                                reason="模型调用异常"
                            )
                            st.error(f"❌ AI 修改失败：{e}")

            # ======== 显示修改对比结果 ========
            if st.session_state.get("show_pending"):
                st.markdown("### 🔍 修改对比结果")
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("原文片段")
                    st.text_area(
                        "原文",
                        st.session_state.get("pending_original", ""),
                        height=200,
                        key="pending_original_text"
                    )

                with col2:
                    st.subheader("修改后")
                    st.text_area(
                        "修改后",
                        st.session_state.get("pending_new", ""),
                        height=200,
                        key="pending_new_text"
                    )

                # ======== 确认或取消修改 ========
                col_apply, col_cancel = st.columns(2)

                with col_apply:
                    if st.button("✅ 应用修改", key="apply_pending"):
                        original = st.session_state.get("pending_original")
                        new = st.session_state.get("pending_new")
                        request = st.session_state.get("pending_request")

                        if original and original in st.session_state["summary"]:
                            st.session_state["summary"] = st.session_state["summary"].replace(original, new, 1)

                            # ✅✅✅ 新增：记录用户修改行为（保存修改习惯）
                            user_id = st.session_state.get("user", {}).get("id")
                            if user_id:
                                record_user_edit(user_id, original, new, request)

                            log_event(
                                "summary_generator", "INFO", "change",
                                "用户应用修改",
                                meta={"request": request}
                            )

                            # 清理状态
                            for k in ["pending_original", "pending_new", "pending_request", "show_pending"]:
                                st.session_state.pop(k, None)
                            st.success("✅ 修改已应用！")
                            st.rerun()
                        else:
                            st.warning("⚠️ 未能在原文中找到待替换的片段，可能已被修改或不完全匹配。")

                with col_cancel:
                    if st.button("❌ 取消修改", key="cancel_pending"):
                        for k in ["pending_original", "pending_new", "pending_request", "show_pending"]:
                            st.session_state.pop(k, None)
                        log_event("summary_generator", "INFO", "work", "用户取消修改")
                        st.info("已取消修改。")
                        st.rerun()

        else:
            st.info("⚠️ 暂无内容，请先生成总结。")

        # ======== 底部导航按钮 ========
        navigation_buttons("上一步", None, prev_step=3)

# --------- 主入口 ---------
if __name__ == "__main__":
    run()
