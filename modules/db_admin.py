# modules/db_admin.py
import sqlite3
import os
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk

# ---------- 数据库路径 ----------
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "database")
DB_PATHS = {
    "系统数据库 (system.db)": os.path.join(BASE_DIR, "system.db"),
    "用户数据库 (user.db)": os.path.join(BASE_DIR, "user.db"),
}

# 检查数据库文件是否存在
for name, path in DB_PATHS.items():
    if not os.path.exists(path):
        print(f"⚠️ 数据库未找到：{path}")
        print(f"🔧 正在自动创建空数据库文件...")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "a").close()

# ---------- 执行 SQL ----------
def execute_sql():
    sql = sql_box.get("1.0", tk.END).strip()
    db_choice = db_selector.get()
    db_path = DB_PATHS.get(db_choice)

    if not sql:
        messagebox.showwarning("提示", "请输入 SQL 语句！")
        return
    if not db_path or not os.path.exists(db_path):
        messagebox.showerror("错误", "未选择有效的数据库！")
        return

    try:
        with sqlite3.connect(db_path) as conn:
            conn.executescript(sql)
            conn.commit()

        output_box.config(state="normal")
        output_box.delete("1.0", tk.END)
        output_box.insert(tk.END, f"✅ SQL 执行成功！\n\n数据库：{db_choice}\n路径：{db_path}\n\nSQL：\n{sql}\n")
        output_box.config(state="disabled")
    except sqlite3.Error as e:
        output_box.config(state="normal")
        output_box.delete("1.0", tk.END)
        output_box.insert(tk.END, f"❌ SQL 执行错误：\n{str(e)}")
        output_box.config(state="disabled")

# ---------- Tkinter 界面 ----------
root = tk.Tk()
root.title("🧱 SQLite 数据库管理器 (DB Admin)")
root.geometry("900x700")

# 顶部选择框
frame_top = tk.Frame(root)
frame_top.pack(fill=tk.X, padx=10, pady=10)

tk.Label(frame_top, text="选择数据库：", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(0, 5))
db_selector = ttk.Combobox(frame_top, values=list(DB_PATHS.keys()), state="readonly", font=("Arial", 11))
db_selector.pack(side=tk.LEFT, fill=tk.X, expand=True)
db_selector.current(0)  # 默认选中第一个

# SQL 输入框
tk.Label(root, text="请输入 SQL 语句：", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
sql_box = scrolledtext.ScrolledText(root, height=12, font=("Consolas", 11))
sql_box.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)
sql_box.insert(tk.END, "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);\n")

# 执行按钮
execute_btn = tk.Button(root, text="执行 SQL", command=execute_sql, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
execute_btn.pack(pady=10)

# 输出区
tk.Label(root, text="执行结果：", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
output_box = scrolledtext.ScrolledText(root, height=15, font=("Consolas", 11), state="disabled", bg="#f4f4f4")
output_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# 启动主循环
root.mainloop()
