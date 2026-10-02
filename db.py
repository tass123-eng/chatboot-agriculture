"""PostgreSQL connection helpers for the Agri RAG application."""
import os
from contextlib import contextmanager
from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/agri_rag",
)


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    """Open a PostgreSQL connection and close it after use."""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()
