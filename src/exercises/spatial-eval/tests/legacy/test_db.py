# tests/test_db.py
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_db_insert_and_query_comparison():
    from db import ResultsDB
    from models import ComparisonRecord
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = ResultsDB(Path(f.name))
        db.insert_comparison(ComparisonRecord(
            run_id="run-1", place="The Richmond",
            source_a="claude-haiku-4-5", source_b="click_that_hood",
            iou=0.65, overlap_a=0.72, overlap_b=0.61,
            de9im_string="212101212", de9im_label="overlaps",
            hausdorff_m=320.0, centroid_err_m=120.0,
            composite_score=0.72, valid=True,
        ))
        rows = db.fetch_comparisons()
        assert len(rows) == 1
        assert rows[0].place == "The Richmond"
        assert rows[0].source_a == "claude-haiku-4-5"
        assert rows[0].source_b == "click_that_hood"
        assert rows[0].iou == 0.65
        assert rows[0].de9im_label == "overlaps"


def test_db_fetch_filter_by_source_b():
    from db import ResultsDB
    from models import ComparisonRecord
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = ResultsDB(Path(f.name))
        for source_b in ("click_that_hood", "osm"):
            db.insert_comparison(ComparisonRecord(
                run_id="run-1", place="Chinatown",
                source_a="gpt-4o-mini", source_b=source_b,
                iou=0.5, overlap_a=0.6, overlap_b=0.5,
                de9im_string="212101212", de9im_label="overlaps",
                hausdorff_m=200.0, centroid_err_m=80.0,
                composite_score=0.6, valid=True,
            ))
        rows = db.fetch_comparisons(source_b="osm")
        assert len(rows) == 1
        assert rows[0].source_b == "osm"
