"""Session and run store for the Lucas agent."""

import aiosqlite
import os
from datetime import datetime
from typing import Optional


class RunStore:
    """Store for recording Lucas runs to the dashboard database."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get("SQLITE_PATH", "/data/lucas.db")
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize database connection and ensure tables exist."""
        self._db = await aiosqlite.connect(self.db_path)
        # Ensure runs table exists (same schema as CronJob uses)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                namespace TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'autonomous',
                status TEXT NOT NULL DEFAULT 'running',
                pod_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                fix_count INTEGER DEFAULT 0,
                report TEXT,
                log TEXT
            )
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS fixes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                timestamp TEXT NOT NULL,
                namespace TEXT NOT NULL,
                pod_name TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT,
                fix_applied TEXT,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (run_id) REFERENCES runs(id)
            )
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                namespace TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            )
        """)
        await self._db.commit()

    async def close(self):
        """Close database connection."""
        if self._db:
            await self._db.close()

    async def create_run(self, namespace: str, mode: str = "autonomous") -> int:
        """Create a new run record and return its ID."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await self._db.execute(
            """INSERT INTO runs (started_at, namespace, mode, status)
               VALUES (?, ?, ?, 'running')""",
            (now, namespace, mode)
        )
        await self._db.commit()
        return cursor.lastrowid

    async def update_run(
        self,
        run_id: int,
        status: str = "ok",
        pod_count: int = 0,
        error_count: int = 0,
        fix_count: int = 0,
        report: str = None,
        log: str = None
    ):
        """Update a run record with results."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await self._db.execute(
            """UPDATE runs SET
               ended_at = ?,
               status = ?,
               pod_count = ?,
               error_count = ?,
               fix_count = ?,
               report = ?,
               log = ?
               WHERE id = ?""",
            (now, status, pod_count, error_count, fix_count, report, log, run_id)
        )
        await self._db.commit()

    async def record_fix(
        self,
        run_id: int,
        namespace: str,
        pod_name: str,
        error_type: str,
        error_message: str = None,
        fix_applied: str = None,
        status: str = "pending"
    ):
        """Record a fix attempt."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await self._db.execute(
            """INSERT INTO fixes (run_id, timestamp, namespace, pod_name, error_type, error_message, fix_applied, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, now, namespace, pod_name, error_type, error_message, fix_applied, status)
        )
        await self._db.commit()

    async def record_token_usage(
        self,
        run_id: int,
        namespace: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ):
        """Record token usage for a run."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        total_tokens = input_tokens + output_tokens
        await self._db.execute(
            """INSERT INTO token_usage (run_id, namespace, model, input_tokens, output_tokens, total_tokens, cost, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, namespace, model, input_tokens, output_tokens, total_tokens, cost, now)
        )
        await self._db.commit()


class SessionStore:
    """SQLite-based session store."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get("SQLITE_PATH", "/data/lucas.db")
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize database connection and create tables."""
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS slack_sessions (
                thread_ts TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                namespace TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await self._db.commit()

    async def close(self):
        """Close database connection."""
        if self._db:
            await self._db.close()

    async def save_session(
        self,
        thread_ts: str,
        session_id: str,
        channel: str,
        namespace: str = None
    ):
        """Save or update a session mapping."""
        now = datetime.utcnow().isoformat()
        await self._db.execute("""
            INSERT INTO slack_sessions (thread_ts, session_id, channel, namespace, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(thread_ts) DO UPDATE SET
                session_id = excluded.session_id,
                updated_at = excluded.updated_at
        """, (thread_ts, session_id, channel, namespace, now, now))
        await self._db.commit()

    async def get_session(self, thread_ts: str) -> Optional[str]:
        """Get session ID for a thread."""
        async with self._db.execute(
            "SELECT session_id FROM slack_sessions WHERE thread_ts = ?",
            (thread_ts,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_channel(self, thread_ts: str) -> Optional[str]:
        """Get channel for a thread."""
        async with self._db.execute(
            "SELECT channel FROM slack_sessions WHERE thread_ts = ?",
            (thread_ts,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def has_session(self, thread_ts: str) -> bool:
        """Check if a thread has an associated session."""
        return await self.get_session(thread_ts) is not None

    async def delete_session(self, thread_ts: str):
        """Delete a session mapping."""
        await self._db.execute(
            "DELETE FROM slack_sessions WHERE thread_ts = ?",
            (thread_ts,)
        )
        await self._db.commit()

    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """Remove sessions older than specified days. Returns count deleted."""
        cursor = await self._db.execute("""
            DELETE FROM slack_sessions
            WHERE datetime(updated_at) < datetime('now', ?)
        """, (f"-{days} days",))
        await self._db.commit()
        return cursor.rowcount

    async def get_session_count(self) -> int:
        """Get total number of sessions."""
        async with self._db.execute("SELECT COUNT(*) FROM slack_sessions") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
