"""
用户管理模块
提供用户注册、登录、用户信息管理功能
使用 SQLite 存储，与现有 memory.db 共用数据目录
"""

import os
import sys
import sqlite3
import time
import hashlib
import secrets
import uuid
import threading
from typing import Optional, Dict
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _hash_password(password: str, salt: str = None) -> tuple:
    """使用 PBKDF2-SHA256 哈希密码，返回 (hash, salt)"""
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return pw_hash.hex(), salt


def _verify_password(password: str, stored_hash: str) -> bool:
    """验证密码，stored_hash 格式: pbkdf2$salt$hash"""
    try:
        _, salt, hash_hex = stored_hash.split("$")
        pw_hash, _ = _hash_password(password, salt)
        return secrets.compare_digest(pw_hash, hash_hex)
    except (ValueError, AttributeError):
        return False


def _make_password_hash(password: str) -> str:
    """生成存储用的密码哈希字符串: pbkdf2$salt$hash"""
    hash_hex, salt = _hash_password(password)
    return f"pbkdf2${salt}${hash_hex}"

try:
    from backend.core.logging_config import get_logger
    logger = get_logger("user")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _ensure_private_permissions(path: str, is_dir: bool = False) -> None:
    """尽量收紧本地文件/目录权限（仅在类Unix系统生效）"""
    try:
        if os.name == "posix":
            os.chmod(path, 0o700 if is_dir else 0o600)
    except Exception:
        pass


@dataclass
class User:
    """用户数据模型"""
    id: str
    username: str
    password_hash: str
    user_type: str = "c_end"        # c_end / b_end
    nickname: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    house_area: Optional[float] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    is_active: bool = True


class UserStore:
    """用户存储（SQLite）"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
            data_dir = os.getenv("DATA_DIR", default_dir)
            os.makedirs(data_dir, exist_ok=True)
            _ensure_private_permissions(data_dir, is_dir=True)
            db_path = os.path.join(data_dir, "users.db")
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()
        _ensure_private_permissions(self.db_path)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    user_type TEXT DEFAULT 'c_end',
                    nickname TEXT,
                    phone TEXT,
                    city TEXT,
                    house_area REAL,
                    budget_min REAL,
                    budget_max REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            conn.commit()
            conn.close()
            logger.info("用户数据库初始化完成", extra={"db_path": self.db_path})

    def create_user(self, username: str, password: str, user_type: str = "c_end",
                    nickname: str = None, phone: str = None, city: str = None) -> Optional[User]:
        """创建用户"""
        now = time.time()
        user_id = f"u_{uuid.uuid4().hex[:16]}"
        password_hash = _make_password_hash(password)

        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT INTO users (id, username, password_hash, user_type, nickname, phone, city, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, username, password_hash, user_type, nickname, phone, city, now, now)
                )
                conn.commit()
                logger.info("用户创建成功", extra={"user_id": user_id, "username": username})
                return User(
                    id=user_id, username=username, password_hash=password_hash,
                    user_type=user_type, nickname=nickname, phone=phone, city=city,
                    created_at=now, updated_at=now,
                )
            except sqlite3.IntegrityError:
                logger.warning("用户名已存在", extra={"username": username})
                return None
            finally:
                conn.close()

    def verify_user(self, username: str, password: str) -> Optional[User]:
        """验证用户登录"""
        with self._lock:
            conn = self._get_conn()
            row = conn.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)).fetchone()
            conn.close()

        if row is None:
            return None

        if not _verify_password(password, row["password_hash"]):
            return None

        return self._row_to_user(row)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        with self._lock:
            conn = self._get_conn()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            conn.close()

        if row is None:
            return None
        return self._row_to_user(row)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        with self._lock:
            conn = self._get_conn()
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            conn.close()

        if row is None:
            return None
        return self._row_to_user(row)

    def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户信息"""
        allowed_fields = {"nickname", "phone", "city", "house_area", "budget_min", "budget_max", "user_type"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        if not updates:
            return False

        updates["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]

        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if user is None:
            return False
        if not _verify_password(old_password, user.password_hash):
            return False

        new_hash = _make_password_hash(new_password)
        with self._lock:
            conn = self._get_conn()
            conn.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                         (new_hash, time.time(), user_id))
            conn.commit()
            conn.close()
        return True

    def _row_to_user(self, row) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            user_type=row["user_type"] or "c_end",
            nickname=row["nickname"],
            phone=row["phone"],
            city=row["city"],
            house_area=row["house_area"],
            budget_min=row["budget_min"],
            budget_max=row["budget_max"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_active=bool(row["is_active"]),
        )


# 全局单例
_user_store: Optional[UserStore] = None

def get_user_store() -> UserStore:
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store
