import sqlite3
from typing import Optional

DB_PATH = "feeds.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id   TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                feed_url     TEXT NOT NULL,
                display_name TEXT,
                colour       TEXT NOT NULL DEFAULT '0x808080',
                last_seen    TEXT,
                active       INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.commit()


def add_feed(
    channel_id: str,
    channel_name: str,
    feed_url: str,
    display_name: Optional[str],
    colour: str,
    last_seen: Optional[str],
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO feeds (channel_id, channel_name, feed_url, display_name, colour, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (channel_id, channel_name, feed_url, display_name, colour, last_seen),
        )
        conn.commit()


def remove_feed(channel_id: str, feed_url: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM feeds WHERE channel_id = ? AND feed_url = ?",
            (channel_id, feed_url),
        )
        conn.commit()
        return cursor.rowcount


def update_display_name(channel_id: str, current_name: str, new_name: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE feeds SET display_name = ? WHERE channel_id = ? AND display_name = ?",
            (new_name, channel_id, current_name),
        )
        conn.commit()
        return cursor.rowcount


def get_all_feeds() -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM feeds ORDER BY channel_name, display_name"
        ).fetchall()


def get_feeds_by_channel(channel_id: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM feeds WHERE channel_id = ?", (channel_id,)
        ).fetchall()


def feed_exists(channel_id: str, feed_url: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM feeds WHERE channel_id = ? AND feed_url = ?",
            (channel_id, feed_url),
        ).fetchone()
        return row is not None


def set_active(channel_id: str, active: int) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE feeds SET active = ? WHERE channel_id = ?",
            (active, channel_id),
        )
        conn.commit()
        return cursor.rowcount


def update_last_seen(feed_id: int, url: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE feeds SET last_seen = ? WHERE id = ?",
            (url, feed_id),
        )
        conn.commit()


def set_feed_active_by_id(feed_id: int, active: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE feeds SET active = ? WHERE id = ?",
            (active, feed_id),
        )
        conn.commit()


def get_active_feeds() -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM feeds WHERE active = 1"
        ).fetchall()


def get_feed_counts() -> tuple[int, int]:
    with _connect() as conn:
        active = conn.execute(
            "SELECT COUNT(*) FROM feeds WHERE active = 1"
        ).fetchone()[0]
        paused = conn.execute(
            "SELECT COUNT(*) FROM feeds WHERE active = 0"
        ).fetchone()[0]
        return active, paused
