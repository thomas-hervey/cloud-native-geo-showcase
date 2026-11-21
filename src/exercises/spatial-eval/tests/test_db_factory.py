"""Tests for db_factory.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from db_factory import get_db


def test_get_db_duckdb_returns_evaldb(tmp_path: Path) -> None:
    from db_duckdb import EvalDB
    db = get_db("duckdb", path=tmp_path / "test.duckdb")
    assert isinstance(db, EvalDB)
    db.close()


def test_get_db_sqlite_returns_resultsdb(tmp_path: Path) -> None:
    from db import ResultsDB
    db = get_db("sqlite", path=tmp_path / "test.db")
    assert isinstance(db, ResultsDB)
    db.close()


def test_get_db_invalid_backend_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown DB backend"):
        get_db("postgres")  # type: ignore[arg-type]
