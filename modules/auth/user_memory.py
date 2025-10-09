# modules/auth/user_memory.py

import json
from datetime import datetime
from modules.auth.routes_local import SessionLocal
from modules.auth.models import User, UserNote
import difflib


# ---------- 加载用户偏好 / 记忆 ----------
def load_user_memory(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.preferences:
            return {}
        prefs = json.loads(user.preferences)
        if not isinstance(prefs, dict):
            return {}
        return prefs
    except Exception as e:
        print(f"[LOAD MEMORY ERROR] {e}")
        return {}
    finally:
        db.close()


# ---------- 保存用户偏好 / 记忆 ----------
def save_user_memory(user_id: int, memory_dict: dict):
    db = SessionLocal()
    try:
        if not isinstance(memory_dict, dict):
            print("[save_user_memory] memory_dict 必须是 dict")
            return False

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # 合并已有偏好而非完全覆盖
        old_prefs = json.loads(user.preferences or "{}")
        merged = {**old_prefs, **memory_dict}

        user.preferences = json.dumps(merged, ensure_ascii=False)
        user.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"[save_user_memory] Error: {e}")
        return False
    finally:
        db.close()


# ---------- 记录用户反馈 ----------
def record_feedback(user_id: int, note_id: int, feedback_text: str):
    db = SessionLocal()
    try:
        note = (
            db.query(UserNote)
            .filter(UserNote.id == note_id, UserNote.user_id == user_id)
            .first()
        )
        if not note:
            return False
        note.feedback = feedback_text
        note.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"[record_feedback] Error: {e}")
        return False
    finally:
        db.close()


# ---------- 保存生成的新笔记 ----------
def save_user_note(user_id: int, title: str, content: str, metadata: dict = None):
    db = SessionLocal()
    try:
        new_note = UserNote(
            user_id=user_id,
            note_title=title,
            note_content=content,
            metadata=json.dumps(metadata or {}),
        )
        db.add(new_note)
        db.commit()
        db.refresh(new_note)
        return new_note.id
    except Exception as e:
        db.rollback()
        print(f"[save_user_note] Error: {e}")
        return None
    finally:
        db.close()


# ---------- 记录用户修改行为 ----------
def record_user_edit(user_id: int, original_text: str, new_text: str, request: str):
    """
    记录用户修改行为，用于个性化学习。
    """
    db = SessionLocal()
    try:
        diff = "\n".join(difflib.unified_diff(
            original_text.splitlines(),
            new_text.splitlines(),
            fromfile="original",
            tofile="edited",
            lineterm=""
        ))

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        memory = json.loads(user.preferences or "{}")

        edit_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "request": request,
            "diff": diff[:2000],  # ↑略微放宽上限
        }

        memory.setdefault("edit_history", []).append(edit_log)
        user.preferences = json.dumps(memory, ensure_ascii=False)
        user.updated_at = datetime.utcnow()

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"[record_user_edit] Error: {e}")
        return False
    finally:
        db.close()
