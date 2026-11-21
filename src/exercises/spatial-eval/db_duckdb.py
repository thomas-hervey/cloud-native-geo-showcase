"""DuckDB-backed storage for spatial eval comparisons.

Unified comparisons table — one row per (place, source_a, source_b, run_id, variant_id).
cognitive_level is a GENERATED COLUMN derived from question_type (L1–L5).

Usage:
    from db_duckdb import EvalDB
    db = EvalDB()             # uses config.DUCKDB_PATH
    db = EvalDB(":memory:")   # in-memory (tests only)
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

import duckdb

import config
from models import ComparisonRecord, GroundTruthRecord


_CREATE_COMPARISONS = """
CREATE TABLE IF NOT EXISTS comparisons (
    run_id          TEXT NOT NULL,
    place           TEXT NOT NULL,
    source_a        TEXT NOT NULL,
    source_b        TEXT NOT NULL DEFAULT '',
    variant_id      TEXT NOT NULL DEFAULT 'baseline_v2',
    question_type   TEXT NOT NULL DEFAULT 'bbox_identification',
    cognitive_level TEXT GENERATED ALWAYS AS (
        CASE question_type
            WHEN 'bbox_identification'    THEN 'L1'
            WHEN 'polygon_identification' THEN 'L1'
            WHEN 'topology_relation'      THEN 'L2'
            WHEN 'symbolic_rule'          THEN 'L3'
            WHEN 'causal_prediction'      THEN 'L4'
            WHEN 'planning'               THEN 'L5'
            ELSE 'L1'
        END
    ),
    iou             REAL,
    overlap_a       REAL,
    overlap_b       REAL,
    hausdorff_m     REAL,
    centroid_err_m  REAL,
    composite_score REAL,
    de9im_string    TEXT,
    de9im_label     TEXT,
    geom_a          TEXT,
    geom_b          TEXT,
    neighbor_list_a TEXT,
    neighbor_list_b TEXT,
    neighbor_iou    REAL,
    model_id        TEXT,
    prompt_text     TEXT,
    raw_response    TEXT,
    confidence      TEXT,
    notes           TEXT,
    valid           BOOLEAN DEFAULT true,
    created_at      TIMESTAMP DEFAULT current_timestamp,
    UNIQUE (place, source_a, source_b, run_id, variant_id)
)
"""

_CREATE_GROUND_TRUTHS = """
CREATE TABLE IF NOT EXISTS ground_truths (
    place       TEXT NOT NULL,
    source      TEXT NOT NULL,
    geom_wkt    TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT current_timestamp,
    UNIQUE (place, source)
)
"""

# Column names in INSERT order (excludes server-computed cognitive_level, created_at)
_INSERT_COLUMNS = (
    "run_id", "place", "source_a", "source_b", "variant_id", "question_type",
    "iou", "overlap_a", "overlap_b", "hausdorff_m", "centroid_err_m",
    "composite_score", "de9im_string", "de9im_label", "geom_a", "geom_b",
    "neighbor_list_a", "neighbor_list_b", "neighbor_iou",
    "model_id", "prompt_text", "raw_response", "confidence", "notes", "valid",
)


class EvalDB:
    """Thread-safe DuckDB connection for spatial eval data."""

    def __init__(self, path: Path | str | None = None) -> None:
        if path is None:
            path = config.DUCKDB_PATH
        if isinstance(path, Path):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(path)
        self._conn = duckdb.connect(self._path)
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(_CREATE_COMPARISONS)
            self._conn.execute(_CREATE_GROUND_TRUTHS)
            # Databases created before `valid` was in the DDL need the column added.
            # Check first: DuckDB 1.5's ADD COLUMN IF NOT EXISTS on an existing
            # column resets every value to the default, flipping invalid rows to valid.
            has_valid = self._conn.execute(
                "SELECT COUNT(*) FROM duckdb_columns() "
                "WHERE table_name = 'comparisons' AND column_name = 'valid'"
            ).fetchone()[0]
            if not has_valid:
                self._conn.execute(
                    "ALTER TABLE comparisons ADD COLUMN valid BOOLEAN DEFAULT true"
                )
            try:
                self._conn.execute("INSTALL spatial;")
                self._conn.execute("LOAD spatial;")
            except Exception:
                pass  # spatial may already be installed or offline

    # ── Schema helpers ────────────────────────────────────────────────────────

    def table_names(self) -> list[str]:
        with self._lock:
            rel = self._conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            )
            return [r[0] for r in rel.fetchall()]

    # ── comparisons ──────────────────────────────────────────────────────────

    def insert_comparison(self, record: ComparisonRecord) -> None:
        data = record.model_dump(exclude={"cognitive_level", "created_at"})
        cols = ", ".join(_INSERT_COLUMNS)
        placeholders = ", ".join("?" for _ in _INSERT_COLUMNS)
        values = tuple(data[col] for col in _INSERT_COLUMNS)
        with self._lock:
            try:
                self._conn.execute(
                    f"INSERT INTO comparisons ({cols}) VALUES ({placeholders})",
                    values,
                )
            except duckdb.ConstraintException:
                logger.warning(
                    "Skipping duplicate comparison: place=%s source_a=%s source_b=%s run_id=%s variant_id=%s",
                    record.place, record.source_a, record.source_b,
                    record.run_id, record.variant_id,
                )

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
            where.append("cognitive_level = ?")
            params.append(cognitive_level)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            rel = self._conn.execute(
                f"SELECT * FROM comparisons {clause} ORDER BY place, source_a, variant_id, run_id",
                params,
            )
            cols = [d[0] for d in rel.description]
            rows = rel.fetchall()
        return [ComparisonRecord(**dict(zip(cols, r))) for r in rows]

    def get_experiment_coverage(self) -> dict[str, int]:
        """Return {cognitive_level: count} for LLM rows only."""
        with self._lock:
            rel = self._conn.execute(
                """
                SELECT cognitive_level, COUNT(*) AS n
                FROM comparisons
                WHERE source_a LIKE 'llm:%'
                GROUP BY cognitive_level
                ORDER BY cognitive_level
                """
            )
            rows = rel.fetchall()
        return {r[0]: r[1] for r in rows}

    # ── ground_truths ────────────────────────────────────────────────────────

    def insert_ground_truth(self, record: GroundTruthRecord) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO ground_truths (place, source, geom_wkt)
                VALUES (?, ?, ?)
                ON CONFLICT (place, source) DO UPDATE SET
                    geom_wkt = excluded.geom_wkt,
                    created_at = now()
                """,
                (record.place, record.source, record.geom_wkt),
            )

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
            rel = self._conn.execute(
                f"SELECT * FROM ground_truths {clause} ORDER BY place, source",
                params,
            )
            cols = [d[0] for d in rel.description]
            rows = rel.fetchall()
        return [GroundTruthRecord(**dict(zip(cols, r))) for r in rows]

    def get_gt_neighbors(self, source: str) -> dict[str, list[str]]:
        """Derive neighbor lists using ST_Touches on ground truth polygons."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT a.place AS place,
                       list(b.place ORDER BY b.place) AS neighbors
                FROM ground_truths a
                JOIN ground_truths b
                  ON a.source = b.source
                 AND a.place <> b.place
                 AND ST_Touches(
                         ST_GeomFromText(a.geom_wkt),
                         ST_GeomFromText(b.geom_wkt)
                     )
                WHERE a.source = ?
                GROUP BY a.place
                """,
                [source],
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def close(self) -> None:
        self._conn.close()


# ── maintenance ──────────────────────────────────────────────────────────────

# Columns declared NOT NULL DEFAULT in _CREATE_COMPARISONS; legacy rows may hold NULLs.
_NOT_NULL_DEFAULTS = {"source_b": "''", "variant_id": "'baseline_v2'",
                      "question_type": "'bbox_identification'"}
_UNIQUE_KEY = ("place", "source_a", "source_b", "run_id", "variant_id")


def compact_database(path: Path) -> tuple[int, int]:
    """Rebuild a DuckDB file from the canonical schema, reclaiming space.

    Rebuilding through ``_CREATE_COMPARISONS`` (not ``CREATE TABLE AS``) keeps
    the UNIQUE key, the ``created_at`` default and the generated
    ``cognitive_level`` column, and carries ``ground_truths`` over too. While
    copying it also repairs rows written to a degraded schema: duplicates on
    the UNIQUE key are dropped (earliest kept) and NULL ``created_at`` is set
    to now.

    The rebuilt copy is verified row-for-row before it replaces ``path``; the
    previous file is kept as ``<name>.bak``. On any failure the original file
    is untouched.

    Returns:
        (rows before, rows after) for the comparisons table.
    """
    tmp_path = path.with_name(path.stem + ".compact" + path.suffix)
    tmp_path.unlink(missing_ok=True)

    def col_expr(col: str) -> str:
        default = _NOT_NULL_DEFAULTS.get(col)
        return f"COALESCE({col}, {default})" if default else col

    con = duckdb.connect(str(tmp_path))
    try:
        con.execute(f"ATTACH '{path}' AS src (READ_ONLY)")
        src_cols = {r[0] for r in con.execute(
            "SELECT column_name FROM duckdb_columns() "
            "WHERE database_name = 'src' AND table_name = 'comparisons'"
        ).fetchall()}
        cols = [c for c in _INSERT_COLUMNS if c in src_cols]
        select_cols = ", ".join(f"{col_expr(c)} AS {c}" for c in cols)
        partition = ", ".join(_UNIQUE_KEY)
        con.execute(_CREATE_COMPARISONS)
        con.execute(_CREATE_GROUND_TRUTHS)
        before = con.execute("SELECT COUNT(*) FROM src.comparisons").fetchone()[0]
        # Materialize the COALESCEd rows before deduplicating: in DuckDB 1.5.1,
        # QUALIFY/row_number over a wide subquery mis-binds columns positionally.
        con.execute(f"""
            CREATE TEMP TABLE staged AS
            SELECT {select_cols}, COALESCE(created_at, now()) AS created_at
            FROM src.comparisons
        """)
        con.execute(f"""
            INSERT INTO comparisons BY NAME
            SELECT {", ".join(cols)}, created_at FROM staged
            QUALIFY row_number() OVER (PARTITION BY {partition}
                                       ORDER BY created_at) = 1
        """)
        _verify_compacted(con, cols)
        con.execute("DROP TABLE staged")
        con.execute("""
            INSERT INTO ground_truths BY NAME
            SELECT place, source, geom_wkt, COALESCE(created_at, now()) AS created_at
            FROM src.ground_truths
        """)
        after = con.execute("SELECT COUNT(*) FROM comparisons").fetchone()[0]
        con.execute("DETACH src")
        con.execute("CHECKPOINT")
    except Exception:
        con.close()
        tmp_path.unlink(missing_ok=True)
        raise
    con.close()
    # Keep the previous file until the caller deletes it; never discard data here.
    path.replace(path.with_name(path.name + ".bak"))
    tmp_path.replace(path)
    return before, after


def _verify_compacted(con: duckdb.DuckDBPyConnection, cols: list[str]) -> None:
    """Abort compaction unless the rebuilt table holds exactly the staged distinct rows."""
    key = ", ".join(cols)
    missing = con.execute(
        f"SELECT COUNT(*) FROM (SELECT DISTINCT {key} FROM staged EXCEPT SELECT {key} FROM comparisons)"
    ).fetchone()[0]
    extra = con.execute(
        f"SELECT COUNT(*) FROM (SELECT {key} FROM comparisons EXCEPT SELECT {key} FROM staged)"
    ).fetchone()[0]
    if missing or extra:
        raise RuntimeError(
            f"Compaction verification failed ({missing} rows missing, {extra} unexpected); "
            "original database left untouched."
        )
