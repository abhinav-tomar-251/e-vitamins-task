# TASK DATABASE
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

class TaskDatabase:
    """SQLite-backed task database."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "tasks.db")
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL,
                due_date TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def create(self, title: str, description: str, priority: str, due_date: str, status: str) -> dict:
        created_at = datetime.now().isoformat()
        cursor = self.conn.execute(
            "INSERT INTO tasks (title, description, priority, due_date, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, priority, due_date, status, created_at),
        )
        self.conn.commit()
        task_id = str(cursor.lastrowid)
        return {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "due_date": due_date,
            "status": status,
            "created_at": created_at,
        }

    def update(self, task_id: str, **kwargs) -> Optional[dict]:
        task = self._get_task(task_id)
        if task is None:
            return None

        allowed_fields = {"title", "description", "priority", "due_date", "status"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        if not updates:
            return dict(task)

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        params = list(updates.values()) + [task_id]
        self.conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", params)
        self.conn.commit()
        return self._get_task(task_id)

    def delete(self, task_id: str) -> bool:
        cursor = self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_all(self) -> List[dict]:
        cursor = self.conn.execute("SELECT * FROM tasks ORDER BY id")
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def _get_task(self, task_id: str) -> Optional[dict]:
        cursor = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return self._row_to_task(row) if row else None

    def _row_to_task(self, row: sqlite3.Row) -> dict:
        task = dict(row)
        task["id"] = str(task["id"])
        return task

    def close(self) -> None:
        self.conn.close()
