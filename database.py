import psycopg2
from psycopg2.extras import DictCursor
from psycopg2 import sql
from config import DATABASE_URL


def get_conn():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in the environment.")
    return psycopg2.connect(DATABASE_URL)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            cur.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
                ("menu_text", "👋 *Welcome!*\n\nJoin our channels below, then tap *✅ I've Joined — Verify*.")
            )
            cur.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
                ("menu_photo_file_id", "")
            )

            cur.execute("""
                CREATE TABLE IF NOT EXISTS buttons (
                    id       SERIAL PRIMARY KEY,
                    label    TEXT NOT NULL,
                    url      TEXT NOT NULL,
                    position INTEGER DEFAULT 0
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id               SERIAL PRIMARY KEY,
                    channel_id       TEXT NOT NULL UNIQUE,
                    channel_username TEXT NOT NULL,
                    invite_link      TEXT NOT NULL
                )
            """)

        conn.commit()


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key: str) -> str:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT value FROM settings WHERE key=%s", (key,))
            row = cur.fetchone()
            return row["value"] if row else ""


def set_setting(key: str, value: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) "
                "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value",
                (key, value)
            )
        conn.commit()


# ── Buttons ───────────────────────────────────────────────────────────────────

def get_buttons():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM buttons ORDER BY position, id")
            return [dict(row) for row in cur.fetchall()]


def add_button(label: str, url: str, position: int = 0):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO buttons (label, url, position) VALUES (%s, %s, %s)",
                (label, url, position)
            )
        conn.commit()


def delete_button(button_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM buttons WHERE id=%s", (button_id,))
        conn.commit()


def update_button(button_id: int, label: str, url: str, position: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE buttons SET label=%s, url=%s, position=%s WHERE id=%s",
                (label, url, position, button_id)
            )
        conn.commit()


# ── Channels ──────────────────────────────────────────────────────────────────

def get_channels():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM channels")
            return [dict(row) for row in cur.fetchall()]


def add_channel(channel_id: str, channel_username: str, invite_link: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO channels (channel_id, channel_username, invite_link) "
                "VALUES (%s, %s, %s) ON CONFLICT (channel_id) DO NOTHING",
                (channel_id, channel_username, invite_link)
            )
        conn.commit()


def delete_channel(ch_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM channels WHERE id=%s", (ch_id,))
        conn.commit()
