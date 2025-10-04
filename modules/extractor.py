# modules/extractor.py
# AI 提取重点 (支持语言检测 & 三大模式 + 学科类型识别 + 分块处理)

from openai import OpenAI
from config import DEFAULT_MODEL, OPENAI_API_KEY
from langdetect import detect
import re


# ================== 辅助函数 ==================

def detect_language(text: str) -> str:
    """检测主要语言（返回 'en' 或 'zh'）"""
    try:
        lang = detect(text)
        return "zh" if lang and lang.startswith("zh") else "en"
    except Exception:
        return "en"  # 默认英文


def detect_subject(text: str) -> str:
    """基于内容判断学科类型（简单关键词匹配）"""
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


def _looks_like_parse_error(text: str) -> bool:
    """检查文本是否可能是错误/占位信息"""
    if not text:
        return True
    bad_signals = [
        "unsupported", "not supported", "cannot", "unable", "error", "failed",
        "无法", "不支持", "无法读取", "无法打开", "打不开", "unsupported file", "file format",
    ]
    low = text.lower()
    if len(text.strip()) < 300:
        if any(s in low for s in bad_signals):
            return True
    words = re.findall(r"[A-Za-z\u4e00-\u9fff0-9]+", text)
    return len(words) < 10


def _chunk_text(text: str, max_chars: int = 3500):
    """把长文在换行处优先切分"""
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
):
    """
    提取重点笔记
    - 优先使用传入的 api_key，否则使用 config.OPENAI_API_KEY
    - mode: "detailed" / "exam" / "custom"
    - bilingual: 是否双语输出
    - target_lang: zh/en
    - generate_mock: 是否生成模拟题
    """
    key_to_use = api_key or OPENAI_API_KEY
    if not key_to_use:
        raise RuntimeError("❌ 没有可用的 OpenAI API Key，请检查 config.py 或传入参数。")

    client = OpenAI(api_key=key_to_use)

    # ---------- 1) 基本校验 ----------
    if not texts or not isinstance(texts, list):
        raise ValueError("extract_summary 需要传入解析后的文本列表 (list[str])")

    combined_text = "\n".join(texts)
    if not combined_text.strip():
        raise ValueError("没有可用的学习资料，请确认上传文件能被解析。")

    detected_lang = detect_language(combined_text)
    main_lang = "English" if detected_lang == "en" else "Chinese"
    target_lang_name = "Chinese" if target_lang == "zh" else "English"
    subject = detect_subject(combined_text)

    # ---------- 2) 分块抽取 ----------
    file_level_outputs = []
    for idx, text in enumerate(texts, start=1):
        fname = f"Document_{idx}"
        chunks = _chunk_text(text, max_chars=3000)
        chunk_summaries = []

        for c_idx, chunk in enumerate(chunks, start=1):
            chunk_prompt = f"""
You are an extractor whose job is to find **explicit** headings/terms and important sentences inside the given text chunk.

Rules:
1) Only extract items that explicitly appear in the text. Do NOT invent new headings or terms.
2) Use original headings if present.
3) Each item: heading + 1-3 sentence paraphrase + example if present.
4) If no headings, pick up to 5 important sentences as bullets.
5) Markdown bullets only.
6) Output language: {main_lang}.

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

        file_merged = "\n\n".join(chunk_summaries).strip()
        file_level_outputs.append({"name": fname, "content": file_merged})

    # ---------- 3) 合并所有文本 ----------
    files_block = "".join([f"## FILE: {fo['name']}\n{fo['content']}\n\n" for fo in file_level_outputs])

    # ---------- 4) 模式选择 ----------
    if mode == "detailed":
        mode_instruction = (
            "MODE: DETAILED\n"
            "For each FILE and each heading/term, produce:\n"
            " - Explanation: 3-6 short sentences\n"
            " - Life/example: one-line analogy if present, else N/A\n"
            " - Exam example: if generate_mock=True, short exam-style Q+A, else N/A\n"
        )
    elif mode == "exam":
        mode_instruction = (
            "MODE: EXAM\n"
            "For each FILE and each heading/term, produce:\n"
            " - Short explanation: 1-2 sentences\n"
            " - Exam answer template: one-line phrasing\n"
            " - Example: if generate_mock=True, short practice Q+A, else N/A\n"
        )
    else:
        custom_text = custom_instruction.strip() if custom_instruction else "No custom instruction."
        mode_instruction = f"MODE: CUSTOM\nUser instruction: {custom_text}\n"

    # ---------- 5) 总结生成 ----------
    final_prompt = f"""
You are a careful course-note synthesizer.

Rules:
1) Use only headings/terms from input. Do NOT invent.
2) Markdown only. Each file starts with "## FILE: <filename>".
3) For each heading/term:
   - Explanation: {'3-6 sentences' if mode == 'detailed' else '1-2 sentences'}
   - Life example
   - Exam example (if generate_mock=True)
4) No preface, conclusion, or unrelated items.

{mode_instruction}
Output language: {main_lang}{' and ' + target_lang_name + ' translation' if bilingual else ''}.

Input extracts:
Subject detected: {subject}

{files_block}
"""

    resp2 = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "You are a disciplined note synthesizer. Follow instructions strictly."},
            {"role": "user", "content": final_prompt},
        ],
        max_tokens=3000,
        temperature=0.0,
    )

    final_text = resp2.choices[0].message.content or ""
    final_text = re.sub(r"(?im)^\s*(file format|unsupported|无法读取).*$", "", final_text).strip()

    if len(final_text) < 30:
        raise RuntimeError("生成的笔记过短，可能模型未提取到有效内容。")

    return final_text
