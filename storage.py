import sqlite3
from datetime import datetime
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT,
                company TEXT,
                url TEXT,
                seen_at TEXT NOT NULL
            )
        """)
        conn.commit()


def is_seen(job_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return row is not None


def mark_seen(job_id: str, source: str, title: str, company: str, url: str):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO seen_jobs (id, source, title, company, url, seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_id, source, title, company, url, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
        by_source = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM seen_jobs GROUP BY source"
        ).fetchall()
        return {"total": total, "by_source": {r["source"]: r["cnt"] for r in by_source}}
