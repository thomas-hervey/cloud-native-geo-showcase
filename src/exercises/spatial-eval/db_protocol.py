"""Structural protocol for eval database backends.

Both EvalDB (DuckDB) and ResultsDB (SQLite) implement this protocol.
Use isinstance(db, EvalDBProtocol) in tests to verify conformance without
requiring inheritance from a common base class.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from models import ComparisonRecord, GroundTruthRecord


@runtime_checkable
class EvalDBProtocol(Protocol):
    """Shared interface for DuckDB and SQLite eval database backends."""

    def insert_comparison(self, record: ComparisonRecord) -> None: ...

    def fetch_comparisons(
        self,
        place: str | None = None,
        source_a: str | None = None,
        source_b: str | None = None,
        run_id: str | None = None,
        variant_id: str | None = None,
        variant_ids: list[str] | None = None,
        question_type: str | None = None,
        cognitive_level: str | None = None,
    ) -> list[ComparisonRecord]: ...

    def insert_ground_truth(self, record: GroundTruthRecord) -> None: ...

    def fetch_ground_truths(
        self,
        place: str | None = None,
        source: str | None = None,
    ) -> list[GroundTruthRecord]: ...

    def get_experiment_coverage(self) -> dict[str, int]: ...

    def get_gt_neighbors(self, source: str) -> dict[str, list[str]]: ...

    def close(self) -> None: ...
