# modules/extractor.py
# AI 提取重点 (支持语言检测 & 三大模式 + 学科类型识别 + 更严格的分治处理)

from openai import OpenAI
from modules import file_handler
from config import DEFAULT_MODEL
from langdetect import detect
import re


# ------------------ 辅助函数 ------------------

def detect_language(text: str) -> str:
    """检测主要语言（返回 'en' 或 'zh'）"""
    try:
        lang = detect(text)
        return "zh" if lang and lang.startswith("zh") else "en"
    except:
        return "en"  # 默认英文


def detect_subject(text: str) -> str:
    """基于内容判断学科类型（简单关键词匹配）"""
    keywords = {
        "code": ["def ", "class ", "import ", "{", "}", "function", "程序", "代码", "编程"],
        "math": ["公式", "定理", "证明", "方程", "函数", "微积分", "matrix", "theorem"],
        "physics": ["力学", "电磁", "量子", "热力学", "波动", "Newton", "Einstein"],
        "chemistry": ["化学式", "分子", "反应", "酸碱", "化合物", "reaction"],
        "engineering": ["电路", "结构", "控制系统", "机械", "材料力学"],
        "theory": ["概念", "定义", "章节", "理论", "原理", "模型"]
    }
    text_lower = (text or "").lower()
    for subject, kws in keywords.items():
        for kw in kws:
            if kw.lower() in text_lower:
                return subject
    return "general"


def _looks_like_parse_error(text: str) -> bool:
    """检查解析结果是否很可能是错误/占位信息（避免把错误当正文发给模型）"""
    if not text:
        return True
    bad_signals = [
        "unsupported", "not supported", "cannot", "unable", "error", "failed",
        "无法", "不支持", "无法读取", "无法打开", "打不开", "unsupported file", "file format"
    ]
    low = text.lower()
    # 如果文本中包含这些明显的错误提示且长度很短（比如 < 200 字），认为是解析失败
    if len(text.strip()) < 300:
        for s in bad_signals:
            if s in low:
                return True
    # 另外如果文本只包含很少真实单词（如只有 'File format not supported'），判定为错误
    words = re.findall(r"[A-Za-z\u4e00-\u9fff0-9]+", text)
    if len(words) < 10:
        # 但允许短但有意义的文本，故设置阈值
        return True
    return False


def _chunk_text(text: str, max_chars: int = 3500):
    """把长文尝试在换行处切分，避免在段落中间切断"""
    chunks = []
    if not text:
        return []
    start = 0
    L = len(text)
    while start < L:
        end = min(start + max_chars, L)
        if end < L:
            nl = text.rfind("\n", start, end)
            if nl > start + 40:  # 保证至少保留一定长度
                end = nl
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks


# ------------------ 主函数 ------------------

def extract_summary(
    texts,
    api_key,
    mode="detailed",
    bilingual=False,
    target_lang="zh",
    generate_mock=False,
    custom_instruction=None
):
    """
    简化且更安全的 extract_summary：
    - 直接接收解析好的文本列表 (list[str])，不再解析文件
    - 对每段文本分块处理 -> 先抽取式笔记 -> 再合并生成最终 notes
    - 保证不生成与原文无关的条目
    """
    client = OpenAI(api_key=api_key)

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

    # ---------- 2) 分块 + chunk 抽取 ----------
    file_level_outputs = []
    for idx, text in enumerate(texts, start=1):
        fname = f"Document_{idx}"
        chunks = _chunk_text(text, max_chars=3000)
        chunk_summaries = []

        for c_idx, chunk in enumerate(chunks, start=1):
            chunk_prompt = f"""
You are an extractor whose job is to find **explicit** headings/terms and important sentences inside the given text chunk.
**Rules (must follow strictly)**:
1) Only extract items that explicitly appear in the text. Do NOT invent new headings or new technical terms.
2) If the text contains clear headings (like 'Chapter', 'Topic', 'Buffer Overflow'), use those exact headings.
3) For each extracted heading/term, include one short explanation (1-3 sentences) **directly paraphrased from the text**, and an example if present.
4) If no clear headings, select up to 5 important sentences and output as bullet points.
5) Output format (Markdown bullets only):
   - **<heading or phrase from text>**: <1-3 sentence paraphrase> (example: <example or N/A>)
6) Do NOT output preface, conclusion, or commentary.
7) Output language: {main_lang}.

Here is the chunk (START):
{chunk}
(END)
"""
            resp = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a careful extractor that only extracts content that appears in the input text."},
                    {"role": "user", "content": chunk_prompt}
                ],
                max_tokens=800,
                temperature=0.0
            )
            chunk_result = resp.choices[0].message.content.strip()
            if chunk_result:
                chunk_summaries.append(chunk_result)

        file_merged = "\n\n".join(chunk_summaries).strip()
        file_level_outputs.append({"name": fname, "content": file_merged})

    # ---------- 3) 合并所有文本并生成最终 notes ----------
    files_block = ""
    for fo in file_level_outputs:
        files_block += f"## FILE: {fo['name']}\n{fo['content']}\n\n"

    if mode == "detailed":
        mode_instruction = (
            "MODE: DETAILED\n"
            "For each FILE and each heading/term, produce:\n"
            " - Explanation: 3-6 short sentences, plain language.\n"
            " - Life/example: one-line real-life analogy if present, else N/A.\n"
            " - Exam example: if generate_mock=True, provide one short exam-style Q+A, else N/A.\n"
        )
    elif mode == "exam":
        mode_instruction = (
            "MODE: EXAM (concise notes)\n"
            "For each FILE and each heading/term, produce:\n"
            " - Short explanation: 1-2 short sentences (exam-ready).\n"
            " - Exam answer template: one-line phrasing.\n"
            " - Example: if generate_mock=True, provide 1 short practice Q+A, else N/A.\n"
        )
    else:  # custom
        custom_text = custom_instruction.strip() if custom_instruction else "No additional custom instruction."
        mode_instruction = (
            "MODE: CUSTOM\n"
            f"User custom instruction: {custom_text}\n"
            "Follow user instruction but still avoid inventing new headings or facts.\n"
        )

    final_prompt = f"""
You are a careful course-note synthesizer. Input: structured extracts from multiple files (headings and paraphrases).
**Strict rules (MUST follow)**:
1) Use only headings/terms that appear in the input. Do NOT invent new ones.
2) Output must be Markdown. For each file: "## FILE: <filename>".
3) Under each file, for each heading/term output:
   - Explanation: {('(3-6 sentences)' if mode == 'detailed' else '(1-2 sentences)')}
   - Life example: <content>  (if exam mode, N/A)
   - Exam example: <content>  (if generate_mock=False, N/A; else provide 1 short Q+A)
4) No preface, conclusion, or unrelated items. No parser error text allowed.
5) If heading repeats across files, keep detail first time, later write "(重复，参见上文)".

{mode_instruction}
Output language: {main_lang} {("(and " + target_lang_name + " translation after each field)" if bilingual else "")}

Now synthesize notes (BEGIN):
Subject detected: {subject}

{files_block}
(END)
"""

    resp2 = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "You are a disciplined note synthesizer. Follow instructions strictly."},
            {"role": "user", "content": final_prompt}
        ],
        max_tokens=3000,
        temperature=0.0
    )

    final_text = resp2.choices[0].message.content or ""
    final_text = re.sub(r"(?im)^\s*(file format|unsupported|无法读取).*$", "", final_text).strip()

    if len(final_text) < 30:
        raise RuntimeError("生成的笔记过短，可能模型未提取到有效内容。")

    return final_text
