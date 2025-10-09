# modules/extractor.py
# AI 提取重点 (支持语言检测 & 三大模式 + 学科类型识别 + 分块处理 + 日志记录 + Token 记录 + 模块健康检测)

from openai import OpenAI
from config import DEFAULT_MODEL, OPENAI_API_KEY
from modules.utils.system_status import update_module_status 
from langdetect import detect
import re, time, traceback
import streamlit as st

# === 引入模块 ===
from modules.logger import (
    log_event,
    log_token_usage,
    calculate_cost,
    #init_module_health,
)

# 如果你在 logger 中实现了 init_module_health 可以启用它
# try:
#     init_module_health("extractor")
# except Exception:
#     pass

def get_current_user_id():
    """安全地从 session_state 获取当前登录用户"""
    try:
        return st.session_state.get("user_id", "guest")
    except Exception:
        return "guest"


# ================== 辅助函数 ==================
def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return "zh" if lang and lang.startswith("zh") else "en"
    except Exception:
        return "en"


def detect_subject(text: str) -> str:
    keywords = {
        "code": ["def ", "class ", "import ", "{", "}", "function", "程序", "代码", "编程"],
        "math": ["公式", "定理", "证明", "方程", "函数", "微积分", "matrix", "theorem"],
        "physics": ["力学", "电磁", "量子", "热力学", "波动", "Newton", "Einstein"],
        "chemistry": ["化学式", "分子", "反应", "酸碱", "化合物", "reaction"],
        "engineering": ["电路", "结构", "控制系统", "机械", "材料力学"],
        "theory": ["概念", "定义", "章节", "理论", "原理", "模型"],
    }
    text_lower = (text or "").lower()
    for subject, kws in keywords.items():
        if any(kw.lower() in text_lower for kw in kws):
            return subject
    return "general"


def _chunk_text(text: str, max_chars: int = 3500):
    if not text:
        return []
    chunks, start, L = [], 0, len(text)
    while start < L:
        end = min(start + max_chars, L)
        if end < L:
            nl = text.rfind("\n", start, end)
            if nl > start + 40:
                end = nl
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks


# ================== 主函数 ==================
def extract_summary(
    texts,
    api_key=None,
    mode="detailed",
    bilingual=False,
    target_lang="zh",
    generate_mock=False,
    custom_instruction=None,
    user_id=None,
):
    start_time = time.time()
    request_id = f"req_{int(start_time)}"
    source_module = "extractor"

    # ====== 新增：token 计数器 ======
    prompt_tokens_total = 0
    completion_tokens_total = 0
    total_tokens_total = 0

    try:
        log_event(
            source_module=source_module,
            level="INFO",
            status="work",
            things="extract_start",
            remark=f"Mode={mode}, bilingual={bilingual}, custom={bool(custom_instruction)}",
            meta={"request_id": request_id},
        )

        # 模块进入工作状态
        update_module_status("extractor", "running")

        key_to_use = api_key or OPENAI_API_KEY
        if not key_to_use:
            raise RuntimeError("❌ 没有可用的 OpenAI API Key，请检查 config.py 或传入参数。")

        client = OpenAI(api_key=key_to_use)

        if not texts or not isinstance(texts, list):
            raise ValueError("extract_summary 需要传入解析后的文本列表 (list[str])")

        combined_text = "\n".join(texts)
        if not combined_text.strip():
            raise ValueError("没有可用的学习资料，请确认上传文件能被解析。")

        detected_lang = detect_language(combined_text)
        main_lang = "English" if detected_lang == "en" else "Chinese"
        target_lang_name = "Chinese" if target_lang == "zh" else "English"
        subject = detect_subject(combined_text)

        # ---------- 分块抽取 ----------
        file_level_outputs = []
        for idx, text in enumerate(texts, start=1):
            fname = f"Document_{idx}"
            chunks = _chunk_text(text, max_chars=3000)
            chunk_summaries = []

            for c_idx, chunk in enumerate(chunks, start=1):
                try:
                    chunk_prompt = f"""
You are an extractor whose job is to find explicit headings/terms and important sentences inside the given text chunk.

Rules:
1) Only extract items that explicitly appear in the text.
2) Use original headings if present.
3) Each item: heading + 1-3 sentence paraphrase + example if present.
4) Markdown bullets only.
5) Output language: {main_lang}.

Here is the chunk:
{chunk}
"""
                    resp = client.chat.completions.create(
                        model=DEFAULT_MODEL,
                        messages=[
                            {"role": "system", "content": "You are a careful extractor that only extracts content that appears in the input text."},
                            {"role": "user", "content": chunk_prompt},
                        ],
                        max_tokens=800,
                        temperature=0.0,
                    )

                    chunk_result = resp.choices[0].message.content.strip()
                    if chunk_result:
                        chunk_summaries.append(chunk_result)

                    # ✅ 记录 token 使用（已有）
                    if hasattr(resp, "usage") and resp.usage:
                        user_id = user_id or get_current_user_id()
                        p = getattr(resp.usage, "prompt_tokens", 0) or 0
                        c = getattr(resp.usage, "completion_tokens", 0) or 0
                        t = getattr(resp.usage, "total_tokens", 0) or (p + c)

                        # 写入 token_usage 表（你已有的函数）
                        log_token_usage(
                            user_id=user_id,
                            model=DEFAULT_MODEL,
                            prompt_tokens=p,
                            completion_tokens=c,
                            total_tokens=t
                        )

                        # ====== 累加计数器 ======
                        prompt_tokens_total += int(p)
                        completion_tokens_total += int(c)
                        total_tokens_total += int(t)

                except Exception as chunk_err:
                    log_event(
                        source_module=source_module,
                        level="WARNING",
                        status="warning",
                        things="chunk_failed",
                        remark=f"Chunk {idx}-{c_idx} failed: {chunk_err}",
                        meta={"request_id": request_id},
                    )

            file_merged = "\n\n".join(chunk_summaries).strip()
            file_level_outputs.append({"name": fname, "content": file_merged})

        # ---------- 合并所有文本 ----------
        files_block = "".join([f"## FILE: {fo['name']}\n{fo['content']}\n\n" for fo in file_level_outputs])

        # ---------- 模式指令 ----------
        if mode == "detailed":
            mode_instruction = (
                "MODE: DETAILED\n"
                "For each FILE and each heading/term, produce detailed explanations and examples.\n"
            )
        elif mode == "exam":
            mode_instruction = (
                "MODE: EXAM\n"
                "Provide short Q&A style notes.\n"
            )
        else:
            custom_text = custom_instruction.strip() if custom_instruction else "No custom instruction."
            mode_instruction = f"MODE: CUSTOM\nUser instruction: {custom_text}\n"

        # ---------- 生成最终总结 ----------
        final_prompt = f"""
You are a disciplined note synthesizer.
{mode_instruction}
Output language: {main_lang}{' and ' + target_lang_name + ' translation' if bilingual else ''}.
Input extracts:
Subject detected: {subject}

{files_block}
"""

        resp2 = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are a disciplined note synthesizer."},
                {"role": "user", "content": final_prompt},
            ],
            max_tokens=3000,
            temperature=0.0,
        )

        final_text = resp2.choices[0].message.content or ""
        final_text = re.sub(r"(?im)^\s*(file format|unsupported|无法读取).*$", "", final_text).strip()

        # ✅ 记录 token 使用 (总汇阶段)
        if hasattr(resp2, "usage") and resp2.usage:
            user_id = user_id or get_current_user_id()
            p2 = getattr(resp2.usage, "prompt_tokens", 0) or 0
            c2 = getattr(resp2.usage, "completion_tokens", 0) or 0
            t2 = getattr(resp2.usage, "total_tokens", 0) or (p2 + c2)

            log_token_usage(
                user_id=user_id,
                model=DEFAULT_MODEL,
                prompt_tokens=p2,
                completion_tokens=c2,
                total_tokens=t2
            )

            # ====== 累加计数器 ======
            prompt_tokens_total += int(p2)
            completion_tokens_total += int(c2)
            total_tokens_total += int(t2)

        if len(final_text) < 30:
            raise RuntimeError("生成的笔记过短，可能模型未提取到有效内容。")

        duration = round(time.time() - start_time, 2)

        # ====== 计算估算费用（尝试不同签名的 calculate_cost） ======
        estimated_cost = None
        try:
            # 最常见： calculate_cost(model, total_tokens)
            estimated_cost = calculate_cost(DEFAULT_MODEL, total_tokens_total)
        except TypeError:
            try:
                # 另一种可能： calculate_cost(model, prompt_tokens, completion_tokens)
                estimated_cost = calculate_cost(DEFAULT_MODEL, prompt_tokens_total, completion_tokens_total)
            except Exception:
                estimated_cost = None
        except Exception:
            estimated_cost = None

        log_event(
            source_module=source_module,
            level="INFO",
            status="work",
            things="extract_success",
            remark=f"Processed {len(texts)} docs in {duration}s, subject={subject}",
            meta={
                "duration": duration,
                "mode": mode,
                "bilingual": bilingual,
                "request_id": request_id,
                "prompt_tokens": prompt_tokens_total,
                "completion_tokens": completion_tokens_total,
                "total_tokens": total_tokens_total,
                "estimated_cost": estimated_cost,
            },
        )

        # ✅ 成功后更新状态为运行中
        update_module_status("extractor", "running")

        # === 保存笔记 ===
        if user_id:
            try:
                from modules.auth.routes_local import SessionLocal
                from modules.auth.models import UserNote
                from datetime import datetime
                import json

                db = SessionLocal()
                note = UserNote(
                    user_id=user_id,
                    note_title=f"Auto Extracted ({mode}) - {subject}",
                    note_content=final_text,
                    metadata=json.dumps({
                        "mode": mode,
                        "bilingual": bilingual,
                        "subject": subject,
                        "duration": duration,
                        "request_id": request_id,
                        "prompt_tokens": prompt_tokens_total,
                        "completion_tokens": completion_tokens_total,
                        "total_tokens": total_tokens_total,
                        "estimated_cost": estimated_cost,
                    }),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(note)
                db.commit()
                db.close()
            except Exception as save_err:
                log_event(
                    source_module=source_module,
                    level="ERROR",
                    status="warning",
                    things="note_save_failed",
                    remark=f"笔记保存失败: {save_err}",
                    meta={"request_id": request_id},
                )

        return final_text

    except Exception as e:
        # ❌ 出错时更新健康状态
        update_module_status("extractor", "down")
        log_event(
            source_module=source_module,
            level="ERROR",
            status="down",
            things="extract_failed",
            remark=str(e),
            reason="exception",
            meta={"trace": traceback.format_exc(), "request_id": request_id},
        )
        raise e
