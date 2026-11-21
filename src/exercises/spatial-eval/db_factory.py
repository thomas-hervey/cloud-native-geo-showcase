"""Factory for creating eval DB backend instances.

Always use get_db() in scripts rather than importing backends directly.
The --db flag in each script controls which backend is used.
"""
from __future__ import annotations

from typing import Literal

from db_protocol import EvalDBProtocol


def get_db(backend: Literal["sqlite", "duckdb"], **kwargs) -> EvalDBProtocol:
    """Return a DB backend instance for the given backend name.

    Args:
        backend: "duckdb" for the current backend, "sqlite" for legacy.
        **kwargs: Passed to the backend constructor (e.g. path override for tests).

    Returns:
        An EvalDBProtocol-conforming database instance.

    Raises:
        ValueError: If backend is not "sqlite" or "duckdb".
    """
    if backend == "duckdb":
        from db_duckdb import EvalDB
        return EvalDB(**kwargs)
    if backend == "sqlite":
        from db import ResultsDB
        return ResultsDB(**kwargs)
    raise ValueError(
        f"Unknown DB backend: {backend!r}. Choose 'sqlite' or 'duckdb'."
    )
