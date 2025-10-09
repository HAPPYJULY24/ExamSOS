# modules/db_schema.py

SYSTEM_TABLES = {
    # === 管理员信息表 ===
    "admin": """
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',            -- role: admin / operator / viewer
            is_active INTEGER DEFAULT 1,          -- 1 active, 0 disabled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
    """,

    # === 系统日志记录 ===
    "logs": """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_module TEXT,                   -- e.g., extractor, file_parser, api_gateway
            level TEXT,                           -- e.g., INFO / WARNING / ERROR / CRITICAL / CHANGE
            status TEXT CHECK(status IN ('work','down','change','warning')) NOT NULL,
            request_id TEXT,                      -- 用于 trace 单次请求
            by_user TEXT,                         -- 可存 user id 或 'system'
            by_admin TEXT,                        -- admin username who made change (if any)
            things TEXT,                          -- 简短描述（change 时说明动作）
            remark TEXT,                          -- 详细说明或堆栈信息
            reason TEXT,                          -- down/warning 时的原因
            meta TEXT                             -- JSON 字符串：可扩展字段（tokens, duration, model 等）
        );
    """,

    # === Token 使用记录 ===
    "token_usage": """
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,                      -- 如果无用户则为 NULL 或 'guest'
            model_name TEXT,                      -- e.g., gpt-4o-mini
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            cost_estimate REAL,                   -- 预估成本
            request_id TEXT,                      -- 关联到 logs.request_id
            remark TEXT
        );
    """,

    # === Token 使用汇总表（按天统计）===
    "usage_records": """
        CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            model TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            cost REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            day_key TEXT,  -- e.g. "2025-10-08"
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """,

    # === 管理操作审计日志 ===
    "audit_trail": """
        CREATE TABLE IF NOT EXISTS audit_trail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            admin_username TEXT,         -- who
            action TEXT,                 -- e.g., "disable_user", "update_quota"
            target_type TEXT,            -- e.g., "user", "config", "api_key"
            target_id TEXT,              -- e.g., user id or config key
            before TEXT,                 -- JSON string: before state
            after TEXT,                  -- JSON string: after state
            remark TEXT
        );
    """,

    # === 后台任务队列 ===
    "jobs": """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            task_name TEXT,              -- e.g., "parse_file", "generate_notes", "export_pdf"
            status TEXT,                 -- pending / running / success / failed
            user_id INTEGER,
            request_id TEXT,
            progress INTEGER DEFAULT 0,  -- 0-100
            result_path TEXT,            -- 存储结果地址（S3 或本地）
            error_message TEXT,
            meta TEXT                    -- JSON 字符串，存额外信息
        );
    """,

    # === 模块健康状态表 ===
    "module_status": """
        CREATE TABLE IF NOT EXISTS module_status (
            module_name TEXT PRIMARY KEY,             -- 模块名，如 'auth', 'logger'
            status TEXT DEFAULT 'unknown',            -- active / warning / error / down
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_count INTEGER DEFAULT 0,
            message TEXT                              -- 最近状态或错误描述
        );
    """
}


USER_TABLES = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,              -- bcrypt/argon2 哈希（OAuth 用户可为空）
            google_id TEXT,                  -- Google OAuth ID（可扩展 GitHub、Microsoft 等）
            github_id TEXT,
            role TEXT DEFAULT 'user',        -- user / admin / banned 等
            default_note_style TEXT,         -- 用户偏好的笔记样式
            default_lang TEXT,               -- 用户默认语言
            quota_plan TEXT DEFAULT 'free',  -- free / pro / team 等
            preferences TEXT,                -- JSON: 主题、UI设置、等
            is_active INTEGER DEFAULT 1,     -- 0=禁用, 1=启用
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,

    "user_sessions": """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            access_token TEXT,              -- JWT Access Token
            refresh_token TEXT,             -- JWT Refresh Token
            expires_at TIMESTAMP,           -- Token 过期时间
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """,

    "user_notes": """
        CREATE TABLE IF NOT EXISTS user_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            note_title TEXT,
            note_content TEXT,
            metadata TEXT,                   -- ✅ 新增：存储附加信息（JSON）
            feedback TEXT,                   -- ✅ 新增：用户或系统反馈
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """
}
