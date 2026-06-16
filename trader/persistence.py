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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_key TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                params TEXT,
                init_cash REAL,
                lot_size REAL,
                source TEXT,
                interval_seconds INTEGER,
                status TEXT,
                start_time TEXT,
                end_time TEXT,
                total_returns REAL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                trade_time TEXT,
                action TEXT,
                price REAL,
                shares REAL,
                cost REAL,
                realized_pl REAL,
                cash_after REAL,
                shares_after REAL,
                total_value REAL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (session_id) REFERENCES paper_sessions(id)
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

    # ── Paper Sessions ─────────────────────────────────────

    def save_paper_session(
        self,
        strategy_key: str,
        stock_code: str,
        params: dict | None = None,
        init_cash: float = 100000.0,
        lot_size: float = 100.0,
        source: str = 'auto',
        interval_seconds: int = 300,
        status: str = 'running',
    ) -> int:
        with self._lock:
            conn = self._get_conn()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.execute(
                """
                INSERT INTO paper_sessions
                    (strategy_key, stock_code, params, init_cash, lot_size,
                     source, interval_seconds, status, start_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_key,
                    stock_code,
                    json.dumps(params, ensure_ascii=False) if params else None,
                    init_cash,
                    lot_size,
                    source,
                    interval_seconds,
                    status,
                    now,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_paper_session(
        self,
        session_id: int,
        status: str | None = None,
        total_returns: float | None = None,
    ) -> None:
        with self._lock:
            conn = self._get_conn()
            fields = []
            values = []
            if status is not None:
                fields.append("status = ?")
                values.append(status)
                if status in ('stopped', 'idle'):
                    fields.append("end_time = ?")
                    values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            if total_returns is not None:
                fields.append("total_returns = ?")
                values.append(total_returns)
            if fields:
                values.append(session_id)
                conn.execute(
                    f"UPDATE paper_sessions SET {', '.join(fields)} WHERE id = ?",
                    values,
                )
                conn.commit()

    def get_paper_session(self, session_id: int) -> dict | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM paper_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("params"):
            d["params"] = json.loads(d["params"])
        return d

    def list_paper_sessions(self, limit: int = 20, offset: int = 0) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM paper_sessions ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        items = []
        for r in rows:
            d = dict(r)
            if d.get("params"):
                d["params"] = json.loads(d["params"])
            items.append(d)
        return items

    # ── Paper Trades ───────────────────────────────────────

    def save_paper_trade(
        self,
        session_id: int,
        trade_time: str,
        action: str,
        price: float,
        shares: float,
        cost: float,
        realized_pl: float = 0.0,
        cash_after: float = 0.0,
        shares_after: float = 0.0,
        total_value: float = 0.0,
    ) -> int:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(
                """
                INSERT INTO paper_trades
                    (session_id, trade_time, action, price, shares, cost,
                     realized_pl, cash_after, shares_after, total_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, trade_time, action, price, shares, cost,
                    realized_pl, cash_after, shares_after, total_value,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_paper_trades(self, session_id: int, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM paper_trades
               WHERE session_id = ? ORDER BY id DESC LIMIT ?""",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


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


# ── Module-level 快捷函数 — Paper Sessions ─────────────────


def save_paper_session(
    strategy_key: str,
    stock_code: str,
    params: dict | None = None,
    init_cash: float = 100000.0,
    lot_size: float = 100.0,
    source: str = 'auto',
    interval_seconds: int = 300,
    status: str = 'running',
) -> int:
    """Create a new paper trading session, returns session id."""
    return get_db().save_paper_session(
        strategy_key, stock_code, params, init_cash, lot_size,
        source, interval_seconds, status,
    )


def update_paper_session(
    session_id: int,
    status: str | None = None,
    total_returns: float | None = None,
) -> None:
    """Update paper session status / returns."""
    return get_db().update_paper_session(session_id, status, total_returns)


def get_paper_session(session_id: int) -> dict | None:
    """Get paper session by id."""
    return get_db().get_paper_session(session_id)


def list_paper_sessions(limit: int = 20, offset: int = 0) -> list[dict]:
    """List paper sessions, newest first."""
    return get_db().list_paper_sessions(limit, offset)


def save_paper_trade(
    session_id: int,
    trade_time: str,
    action: str,
    price: float,
    shares: float,
    cost: float,
    realized_pl: float = 0.0,
    cash_after: float = 0.0,
    shares_after: float = 0.0,
    total_value: float = 0.0,
) -> int:
    """Record a paper trade."""
    return get_db().save_paper_trade(
        session_id, trade_time, action, price, shares, cost,
        realized_pl, cash_after, shares_after, total_value,
    )


def get_paper_trades(session_id: int, limit: int = 50) -> list[dict]:
    """Get trades for a paper session, newest first."""
    return get_db().get_paper_trades(session_id, limit)
