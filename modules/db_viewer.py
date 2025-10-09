# modules/db_viewer.py
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os

# === 定义数据库路径 ===
BASE_DIR = os.path.dirname(__file__)
DB_PATHS = {
    "System DB": os.path.join(BASE_DIR, "..", "database", "system.db"),
    "User DB": os.path.join(BASE_DIR, "..", "database", "user.db"),
}

def get_current_db_path():
    """获取当前选择的数据库路径"""
    return DB_PATHS.get(current_db.get(), list(DB_PATHS.values())[0])

def execute_query():
    """执行 SQL 查询或操作"""
    query = sql_box.get("1.0", tk.END).strip()
    if not query:
        return

    db_path = get_current_db_path()

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            if query.lower().startswith("select"):
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                update_table(columns, rows)
            else:
                conn.commit()
                messagebox.showinfo("成功", f"SQL 执行成功 ✅\n数据库: {os.path.basename(db_path)}")
    except sqlite3.Error as e:
        messagebox.showerror("SQL 错误", f"{e}\n数据库: {os.path.basename(db_path)}")

def update_table(columns, rows):
    """更新表格显示"""
    for item in tree.get_children():
        tree.delete(item)
    tree["columns"] = columns
    tree["show"] = "headings"
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor="w")
    for row in rows:
        tree.insert("", tk.END, values=row)

def refresh_table_list():
    """快速列出数据库中的所有表"""
    db_path = get_current_db_path()
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
        update_table(["Table Name"], tables)
    except sqlite3.Error as e:
        messagebox.showerror("错误", f"无法加载表列表: {e}")

# === GUI 主体 ===
root = tk.Tk()
root.title("🧭 SQLite 数据浏览器")
root.geometry("950x650")

# ⚙️ 现在才创建 StringVar
current_db = tk.StringVar(value=list(DB_PATHS.keys())[0])

# 顶部区域：DB 选择 + 刷新表按钮
top_frame = tk.Frame(root)
top_frame.pack(fill=tk.X, padx=10, pady=5)

tk.Label(top_frame, text="选择数据库：", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(0, 5))
db_selector = ttk.Combobox(top_frame, textvariable=current_db, values=list(DB_PATHS.keys()), width=20, state="readonly")
db_selector.pack(side=tk.LEFT)
db_selector.current(0)

refresh_btn = tk.Button(top_frame, text="📋 查看所有表", command=refresh_table_list, bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
refresh_btn.pack(side=tk.LEFT, padx=10)

# SQL 输入区
sql_box = scrolledtext.ScrolledText(root, height=6, font=("Consolas", 11))
sql_box.pack(fill=tk.X, padx=10, pady=5)
sql_box.insert(tk.END, "SELECT name FROM sqlite_master WHERE type='table';")

# 执行按钮
btn = tk.Button(root, text="执行 SQL", command=execute_query, bg="#4CAF50", fg="white", font=("Arial", 11, "bold"))
btn.pack(pady=5)

# 数据显示区
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

tree = ttk.Treeview(frame)
tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
scrollbar.pack(side=tk.RIGHT, fill="y")
tree.configure(yscrollcommand=scrollbar.set)

root.mainloop()
