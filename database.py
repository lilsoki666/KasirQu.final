import sqlite3
from pathlib import Path


class DatabaseHelper:

    def __init__(self, database_path):

        self.database_path = str(
            database_path
        )

        Path(
            self.database_path
        ).parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            timeout=10
        )

        self.connection.row_factory = (
            sqlite3.Row
        )

    def execute(
        self,
        query,
        parameters=()
    ):

        cursor = self.connection.execute(
            query,
            parameters
        )

        self.connection.commit()

        return cursor

    def fetchone(
        self,
        query,
        parameters=()
    ):

        return self.connection.execute(
            query,
            parameters
        ).fetchone()

    def fetchall(
        self,
        query,
        parameters=()
    ):

        return self.connection.execute(
            query,
            parameters
        ).fetchall()

    def close(self):

        try:

            self.connection.close()

        except Exception:

            pass
