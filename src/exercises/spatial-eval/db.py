"""SQLite storage for spatial eval comparisons — legacy backend.

Implements EvalDBProtocol. Use via db_factory.get_db("sqlite").
The DuckDB backend (db_duckdb.py) is the current default.

Internal column mapping (SQLite → ComparisonRecord field names):
    overlap_pct_a   → overlap_a
    overlap_pct_b   → overlap_b
    de9im           → de9im_string
    centroid_error_m → centroid_err_m
    composite       → composite_score
    polygon_wkt_a   → geom_a
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from models import ComparisonRecord, GroundTruthRecord

DEFAULT_DB = Path(__file__).parent / "data" / "results.db"

# Maps ComparisonRecord field names → SQLite column names
_FIELD_TO_COL: dict[str, str] = {
    "overlap_a": "overlap_pct_a",
    "overlap_b": "overlap_pct_b",
    "de9im_string": "de9im",
    "centroid_err_m": "centroid_error_m",
    "composite_score": "composite",
    "geom_a": "polygon_wkt_a",
}

# Maps SQLite column names → ComparisonRecord field names (reverse)
_COL_TO_FIELD: dict[str, str] = {v: k for k, v in _FIELD_TO_COL.items()}

# cognitive_level is GENERATED in DuckDB; derived here in Python
_QUESTION_TYPE_TO_LEVEL: dict[str, str] = {
    "bbox_identification": "L1",
    "polygon_identification": "L1",
    "topology_relation": "L2",
    "symbolic_rule": "L3",
    "causal_prediction": "L4",
    "planning": "L5",
}

_CREATE_COMPARISONS = """
CREATE TABLE IF NOT EXISTS comparisons (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT,
    place            TEXT    NOT NULL,
    source_a         TEXT    NOT NULL,
    source_b         TEXT    NOT NULL DEFAULT '',
    run              INTEGER NOT NULL DEFAULT 1,
    variant_id       TEXT    NOT NULL DEFAULT 'baseline_v2',
    question_type    TEXT    NOT NULL DEFAULT 'bbox_identification',
    tier             INTEGER,
    centroid_lat_a   REAL,
    centroid_lon_a   REAL,
    bbox_north_a     REAL,
    bbox_south_a     REAL,
    bbox_east_a      REAL,
    bbox_west_a      REAL,
    iou              REAL,
    overlap_pct_a    REAL,
    overlap_pct_b    REAL,
    de9im            TEXT,
    de9im_label      TEXT,
    hausdorff_m      REAL,
    centroid_error_m REAL,
    composite        REAL,
    polygon_wkt_a    TEXT,
    polygon_wkt_b    TEXT,
    geom_b           TEXT,
    neighbor_list_a  TEXT,
    neighbor_list_b  TEXT,
    neighbor_iou     REAL,
    model_id         TEXT,
    raw_response     TEXT,
    prompt_text      TEXT,
    confidence       TEXT,
    notes            TEXT,
    valid            INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT    DEFAULT (datetime('now')),
    UNIQUE(place, source_a, source_b, run_id, variant_id)
)
"""

_CREATE_GROUND_TRUTHS = """
CREATE TABLE IF NOT EXISTS ground_truths (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    place      TEXT NOT NULL,
    source     TEXT NOT NULL,
    geom_wkt   TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(place, source)
)
"""


class ResultsDB:
    """Thread-safe SQLite connection for spatial eval data (legacy backend)."""

    def __init__(self, path: Path = DEFAULT_DB, read_only: bool = False) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if read_only:
            db_uri = f"file:{path.absolute()}?mode=ro"
            self._conn = sqlite3.connect(db_uri, uri=True, check_same_thread=False, timeout=30)
        else:
            self._conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)

        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()

        if not read_only:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute(_CREATE_COMPARISONS)
            self._conn.execute(_CREATE_GROUND_TRUTHS)
            self._migrate()
            self._conn.commit()

    def _migrate(self) -> None:
        """Idempotent schema migrations for databases created before schema updates."""
        migrations = [
            "ALTER TABLE comparisons ADD COLUMN run_id TEXT;",
            "ALTER TABLE comparisons ADD COLUMN question_type TEXT NOT NULL DEFAULT 'bbox_identification';",
            "ALTER TABLE comparisons ADD COLUMN model_id TEXT;",
            "ALTER TABLE comparisons ADD COLUMN confidence TEXT;",
            "ALTER TABLE comparisons ADD COLUMN notes TEXT;",
            "ALTER TABLE comparisons ADD COLUMN neighbor_list_a TEXT;",
            "ALTER TABLE comparisons ADD COLUMN neighbor_list_b TEXT;",
            "ALTER TABLE comparisons ADD COLUMN neighbor_iou REAL;",
            "ALTER TABLE comparisons ADD COLUMN geom_b TEXT;",
        ]
        for sql in migrations:
            try:
                self._conn.execute(sql)
            except sqlite3.OperationalError:
                pass  # Column already exists

    # ── comparisons ──────────────────────────────────────────────────────────

    def insert_comparison(self, record: ComparisonRecord) -> None:
        # Map ComparisonRecord field names to SQLite column names
        data = record.model_dump(exclude={"cognitive_level", "created_at"})
        sqlite_data = {_FIELD_TO_COL.get(k, k): v for k, v in data.items()}
        sqlite_data["run"] = 1  # retired field; set to 1 for all new writes
        cols = ", ".join(sqlite_data.keys())
        placeholders = ", ".join("?" for _ in sqlite_data)
        values = tuple(
            int(v) if isinstance(v, bool) else v
            for v in sqlite_data.values()
        )
        with self._lock:
            self._conn.execute(
                f"INSERT OR REPLACE INTO comparisons ({cols}) VALUES ({placeholders})",
                values,
            )
            self._conn.commit()

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
    ) -> list[ComparisonRecord]:
        where, params = [], []
        if place:
            where.append("place = ?")
            params.append(place)
        if source_a:
            where.append("source_a = ?")
            params.append(source_a)
        if source_b:
            where.append("source_b = ?")
            params.append(source_b)
        if run_id:
            where.append("run_id = ?")
            params.append(run_id)
        if variant_id:
            where.append("variant_id = ?")
            params.append(variant_id)
        if variant_ids:
            placeholders = ",".join("?" for _ in variant_ids)
            where.append(f"variant_id IN ({placeholders})")
            params.extend(variant_ids)
        if question_type:
            where.append("question_type = ?")
            params.append(question_type)
        if cognitive_level:
            # Derive the question_types that map to this level and filter by them
            matching_types = [
                qt for qt, lvl in _QUESTION_TYPE_TO_LEVEL.items()
                if lvl == cognitive_level
            ]
            if matching_types:
                phs = ",".join("?" for _ in matching_types)
                where.append(f"question_type IN ({phs})")
                params.extend(matching_types)
            else:
                return []  # unknown level — no results

        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM comparisons {clause} "
                f"ORDER BY place, source_a, source_b, variant_id",
                params,
            ).fetchall()

        result = []
        for row in rows:
            d = dict(row)
            # Remap SQLite column names to ComparisonRecord field names
            remapped = {_COL_TO_FIELD.get(k, k): v for k, v in d.items()}
            # Derive cognitive_level from question_type
            remapped["cognitive_level"] = _QUESTION_TYPE_TO_LEVEL.get(
                remapped.get("question_type", ""), "L1"
            )
            # valid is stored as INTEGER in SQLite
            remapped["valid"] = bool(remapped.get("valid", 1))
            # Drop SQLite-only fields not in ComparisonRecord
            record_fields = set(ComparisonRecord.model_fields)
            remapped = {k: v for k, v in remapped.items() if k in record_fields}
            result.append(ComparisonRecord(**remapped))
        return result

    def get_experiment_coverage(self) -> dict[str, int]:
        """Return {cognitive_level: count} for LLM rows only."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT question_type, COUNT(*) AS n
                FROM comparisons
                WHERE source_a LIKE 'llm:%'
                GROUP BY question_type
                """
            ).fetchall()
        coverage: dict[str, int] = {}
        for question_type, count in rows:
            level = _QUESTION_TYPE_TO_LEVEL.get(question_type, "L1")
            coverage[level] = coverage.get(level, 0) + count
        return coverage

    # ── ground_truths ────────────────────────────────────────────────────────

    def insert_ground_truth(self, record: GroundTruthRecord) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO ground_truths (place, source, geom_wkt)
                VALUES (?, ?, ?)
                ON CONFLICT (place, source) DO UPDATE SET
                    geom_wkt = excluded.geom_wkt,
                    created_at = datetime('now')
                """,
                (record.place, record.source, record.geom_wkt),
            )
            self._conn.commit()

    def fetch_ground_truths(
        self,
        place: str | None = None,
        source: str | None = None,
    ) -> list[GroundTruthRecord]:
        where, params = [], []
        if place:
            where.append("place = ?")
            params.append(place)
        if source:
            where.append("source = ?")
            params.append(source)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            rows = self._conn.execute(
                f"SELECT place, source, geom_wkt, created_at "
                f"FROM ground_truths {clause} ORDER BY place, source",
                params,
            ).fetchall()
        return [GroundTruthRecord(**dict(row)) for row in rows]

    def get_gt_neighbors(self, source: str) -> dict[str, list[str]]:
        """SQLite has no spatial extension — returns empty dict."""
        return {}

    def close(self) -> None:
        self._conn.close()
