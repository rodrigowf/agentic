import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

_DB_LOCK = threading.Lock()
_CONNECTION_ARGS = dict(check_same_thread=False, isolation_level=None)

DEFAULT_DB_PATH = os.getenv(
    "VOICE_CONVERSATION_DB_PATH",
    os.path.join(os.path.dirname(__file__), "voice_conversations.db"),
)


def _utc_now() -> str:
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()


class ConversationStore:
    """Simple SQLite-backed store for voice conversations and events."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self._init_db()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, **_CONNECTION_ARGS)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with _DB_LOCK:
            with self._connection() as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        voice_model TEXT,
                        metadata TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        source TEXT,
                        type TEXT,
                        payload TEXT NOT NULL,
                        FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_conversation_events_conversation
                    ON conversation_events(conversation_id, id)
                    """
                )

    # ------------------------------------------------------------------
    # Conversation helpers
    # ------------------------------------------------------------------

    def create_conversation(
        self,
        name: Optional[str] = None,
        voice_model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        conversation_id = str(uuid.uuid4())
        now = _utc_now()
        record = {
            "id": conversation_id,
            "name": name or "Untitled conversation",
            "created_at": now,
            "updated_at": now,
            "voice_model": voice_model,
            "metadata": metadata or {},
        }
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, name, created_at, updated_at, voice_model, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["name"],
                    record["created_at"],
                    record["updated_at"],
                    record["voice_model"],
                    json.dumps(record["metadata"]),
                ),
            )
        return record

    def list_conversations(self) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, created_at, updated_at, voice_model, metadata
                FROM conversations
                ORDER BY datetime(updated_at) DESC
                """
            ).fetchall()
        return [self._row_to_conversation(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT id, name, created_at, updated_at, voice_model, metadata
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()
        return self._row_to_conversation(row) if row else None

    def rename_conversation(self, conversation_id: str, name: str) -> Optional[Dict[str, Any]]:
        now = _utc_now()
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE conversations
                SET name = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, now, conversation_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_conversation(conversation_id)

    def update_metadata(self, conversation_id: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        now = _utc_now()
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE conversations
                SET metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(metadata), now, conversation_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def append_event(
        self,
        conversation_id: str,
        payload: Dict[str, Any],
        *,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = timestamp or _utc_now()
        payload_json = json.dumps(payload)
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversation_events (conversation_id, timestamp, source, type, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, ts, source, event_type, payload_json),
            )
            event_id = cursor.lastrowid
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (ts, conversation_id),
            )
        return {
            "id": event_id,
            "conversation_id": conversation_id,
            "timestamp": ts,
            "source": source,
            "type": event_type,
            "payload": payload,
        }

    def list_events(
        self,
        conversation_id: str,
        *,
        after_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query = ["SELECT id, conversation_id, timestamp, source, type, payload FROM conversation_events WHERE conversation_id = ?"]
        params: List[Any] = [conversation_id]
        if after_id is not None:
            query.append("AND id > ?")
            params.append(after_id)
        query.append("ORDER BY id ASC")
        if limit is not None:
            query.append("LIMIT ?")
            params.append(limit)
        sql = " ".join(query)
        with self._connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [self._row_to_event(row) for row in rows]

    # ------------------------------------------------------------------
    # Row converters
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_conversation(row: sqlite3.Row) -> Dict[str, Any]:
        metadata = {}
        voice_model = None
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except json.JSONDecodeError:
                metadata = {"raw": row["metadata"]}
        if row["voice_model"]:
            voice_model = row["voice_model"]
        return {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "voice_model": voice_model,
            "metadata": metadata,
        }

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Dict[str, Any]:
        payload = {}
        if row["payload"]:
            try:
                payload = json.loads(row["payload"])
            except json.JSONDecodeError:
                payload = {"raw": row["payload"]}
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "timestamp": row["timestamp"],
            "source": row["source"],
            "type": row["type"],
            "payload": payload,
        }


store = ConversationStore()
