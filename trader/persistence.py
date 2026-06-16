"""
持久化层 — SQLite 参数预设与回测结果存储。

提供 PersistenceDB 类及线程安全的模块级函数。
"""
import os
import json
import sqlite3
import threading
from datetime import datetime

# DB 文件放在项目 data/ 目录下
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'hermes.db')


class PersistenceDB:
    """SQLite 持久化管理器。"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or DB_PATH
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    # ── 连接管理 ──────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self) -> None:
        """创建表结构（幂等）。"""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                strategy_key TEXT NOT NULL,
                params TEXT,
                source TEXT,
                lot_size REAL,
                init_cash REAL,
                stock_code TEXT,
                start_date TEXT,
                end_date TEXT,
                trade_price TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_key TEXT,
                stock_code TEXT,
                stock_name TEXT,
                start_date TEXT,
                end_date TEXT,
                params TEXT,
                metrics TEXT,
                trades_count INTEGER DEFAULT 0,
                total_returns REAL DEFAULT 0.0,
                sharp_ratio REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                preset_name TEXT
            )
        """)
        conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ── Presets ───────────────────────────────────────────

    def save_preset(
        self,
        name: str,
        strategy_key: str,
        params: dict | None = None,
        source: str | None = None,
        lot_size: float | None = None,
        init_cash: float | None = None,
        stock_code: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        trade_price: str | None = None,
    ) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """
                INSERT OR REPLACE INTO presets
                    (name, strategy_key, params, source, lot_size, init_cash,
                     stock_code, start_date, end_date, trade_price, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
                """,
                (
                    name,
                    strategy_key,
                    json.dumps(params, ensure_ascii=False) if params else None,
                    source,
                    lot_size,
                    init_cash,
                    stock_code,
                    start_date,
                    end_date,
                    trade_price,
                ),
            )
            conn.commit()

    def load_preset(self, name: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM presets WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("params"):
            d["params"] = json.loads(d["params"])
        return d

    def list_presets(self, strategy_key: str | None = None) -> list[dict]:
        conn = self._get_conn()
        if strategy_key:
            rows = conn.execute(
                "SELECT name, strategy_key, created_at FROM presets WHERE strategy_key = ? ORDER BY created_at DESC",
                (strategy_key,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT name, strategy_key, created_at FROM presets ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_preset(self, name: str) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM presets WHERE name = ?", (name,))
            conn.commit()

    def presets_for_strategy(self, strategy_key: str) -> list[dict]:
        """按策略 key 返回预设列表。"""
        return self.list_presets(strategy_key=strategy_key)

    # ── Results ───────────────────────────────────────────

    def save_result(
        self,
        strategy_key: str,
        stock_code: str,
        stock_name: str,
        start_date: str,
        end_date: str,
        params: dict | None = None,
        metrics: dict | None = None,
        trades_count: int = 0,
        total_returns: float = 0.0,
        sharp_ratio: float = 0.0,
        max_drawdown: float = 0.0,
        preset_name: str | None = None,
    ) -> int:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(
                """
                INSERT INTO results
                    (strategy_key, stock_code, stock_name, start_date, end_date,
                     params, metrics, trades_count, total_returns, sharp_ratio,
                     max_drawdown, preset_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_key,
                    stock_code,
                    stock_name,
                    start_date,
                    end_date,
                    json.dumps(params, ensure_ascii=False) if params else None,
                    json.dumps(metrics, ensure_ascii=False) if metrics else None,
                    trades_count,
                    total_returns,
                    sharp_ratio,
                    max_drawdown,
                    preset_name,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_result(self, result_id: int) -> dict | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM results WHERE id = ?", (result_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("params"):
            d["params"] = json.loads(d["params"])
        if d.get("metrics"):
            d["metrics"] = json.loads(d["metrics"])
        return d

    def list_results(self, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        conn = self._get_conn()
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM results ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
        count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        items = []
        for r in rows:
            d = dict(r)
            if d.get("params"):
                d["params"] = json.loads(d["params"])
            if d.get("metrics"):
                d["metrics"] = json.loads(d["metrics"])
            items.append(d)
        return items, count


# ── 单例 & 模块级函数 ────────────────────────────────────

_db: PersistenceDB | None = None
_db_lock = threading.Lock()


def get_db() -> PersistenceDB:
    global _db
    if _db is None:
        with _db_lock:
            if _db is None:
                _db = PersistenceDB()
    return _db


def init_db() -> bool:
    """初始化持久化层（幂等），在 main.py 或 stocks/__init__.py 启动时调用。"""
    get_db()
    return True


def close_db() -> None:
    global _db
    if _db is not None:
        _db.close()
        _db = None


# ── Module-level 快捷函数 ────────────────────────────────

def save_preset(
    name: str,
    strategy_key: str,
    params: dict | None = None,
    source: str | None = None,
    lot_size: float | None = None,
    init_cash: float | None = None,
    stock_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    trade_price: str | None = None,
) -> None:
    return get_db().save_preset(
        name, strategy_key, params, source, lot_size, init_cash,
        stock_code, start_date, end_date, trade_price,
    )


def load_preset_by_name(name: str) -> dict | None:
    return get_db().load_preset(name)


def list_presets(strategy_key: str | None = None) -> list[dict]:
    return get_db().list_presets(strategy_key)


def delete_preset(name: str) -> None:
    return get_db().delete_preset(name)


def save_result(
    strategy_key: str,
    stock_code: str,
    stock_name: str,
    start_date: str,
    end_date: str,
    params: dict | None = None,
    metrics: dict | None = None,
    trades_count: int = 0,
    total_returns: float = 0.0,
    sharp_ratio: float = 0.0,
    max_drawdown: float = 0.0,
    preset_name: str | None = None,
) -> int:
    return get_db().save_result(
        strategy_key, stock_code, stock_name, start_date, end_date,
        params, metrics, trades_count, total_returns, sharp_ratio,
        max_drawdown, preset_name,
    )


def get_result(result_id: int) -> dict | None:
    return get_db().get_result(result_id)


def list_results(page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    return get_db().list_results(page, page_size)
