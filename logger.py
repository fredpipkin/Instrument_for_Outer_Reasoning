# logger.py
# Persists command events and state snapshots to SQLite.
# Standard library only. Write-only from the instrument's perspective.

import sqlite3
import time
import json
from typing import Optional

from config import DB_FILENAME


class SessionLogger:

    def __init__(self) -> None:
        self._conn: sqlite3.Connection = sqlite3.connect(DB_FILENAME, check_same_thread=False)
        self._sid:  Optional[int]      = None
        self._init_schema()

    def _init_schema(self) -> None:
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                start_ts      REAL,
                end_ts        REAL,
                command_count INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER,
                ts          REAL,
                event_type  TEXT,
                command     TEXT,
                argument    TEXT,
                state_json  TEXT,
                alerts_json TEXT,
                rapid_flag  INTEGER
            )
        """)
        self._conn.commit()

    def begin(self) -> None:
        c = self._conn.cursor()
        c.execute("INSERT INTO sessions (start_ts) VALUES (?)", (time.time(),))
        self._conn.commit()
        self._sid = c.lastrowid

    def log_command(self, command: str, argument: str, snap: dict) -> None:
        if self._sid is None:
            return
        state_vars = {k: snap[k] for k in ("LAT", "ATTN", "MEM", "DRIFT", "EXT")}
        c = self._conn.cursor()
        c.execute(
            """INSERT INTO events
               (session_id, ts, event_type, command, argument,
                state_json, alerts_json, rapid_flag)
               VALUES (?, ?, 'COMMAND', ?, ?, ?, ?, ?)""",
            (
                self._sid, time.time(), command,
                argument[:400] if argument else "",
                json.dumps(state_vars),
                json.dumps(snap.get("alerts", [])),
                int(snap.get("rapid_flag", False)),
            ),
        )
        self._conn.commit()

    def end(self, command_count: int) -> None:
        if self._sid is None:
            return
        c = self._conn.cursor()
        c.execute(
            "UPDATE sessions SET end_ts=?, command_count=? WHERE id=?",
            (time.time(), command_count, self._sid),
        )
        self._conn.commit()
        self._conn.close()
