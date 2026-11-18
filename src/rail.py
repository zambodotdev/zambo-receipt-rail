"""The payment rail: operation-key store with a three-state resume lookup.

State machine for one operation key:
  - record + result  -> REPLAY: return the stored result, never re-execute.
  - no record        -> PROCEED: "not checked"; the caller decides knowingly.
  - record, no result -> UNKNOWN: reconcile against the chain by key before
                         any re-send. Never default either way.

The store is a local SQLite file; in production the same states are the
Zambo server's saved-job semantics.
"""
import json
import sqlite3
import time


class Rail:
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS operations ("
            " op_key TEXT PRIMARY KEY, params TEXT NOT NULL,"
            " result TEXT, receipt_id TEXT, created_at REAL NOT NULL)"
        )
        self.db.commit()

    def begin(self, op_key: str, params: dict) -> str:
        """Register the operation key BEFORE the first attempt."""
        row = self.db.execute(
            "SELECT result FROM operations WHERE op_key = ?", (op_key,)
        ).fetchone()
        if row is None:
            self.db.execute(
                "INSERT INTO operations (op_key, params, created_at) VALUES (?, ?, ?)",
                (op_key, json.dumps(params, sort_keys=True), time.time()),
            )
            self.db.commit()
            return "proceed"
        return "replay" if row[0] is not None else "unknown"

    def complete(self, op_key: str, result: dict, receipt_id: str) -> None:
        self.db.execute(
            "UPDATE operations SET result = ?, receipt_id = ? WHERE op_key = ?",
            (json.dumps(result, sort_keys=True), receipt_id, op_key),
        )
        self.db.commit()

    def lookup(self, op_key: str):
        row = self.db.execute(
            "SELECT params, result, receipt_id FROM operations WHERE op_key = ?",
            (op_key,),
        ).fetchone()
        if row is None:
            return None
        return {
            "params": json.loads(row[0]),
            "result": json.loads(row[1]) if row[1] is not None else None,
            "receipt_id": row[2],
        }
