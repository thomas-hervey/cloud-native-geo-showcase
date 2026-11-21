import pandas as pd
from unittest.mock import patch
from ui.map_view import build_llm_layers


def test_build_llm_layers_filters_by_selected_runs():
    """Verify that build_llm_layers outputs layers only for run_ids in selected_runs."""
    run_ids = ["run-aaa", "run-bbb", "run-ccc"]
    data = {
        "source_a": ["test_model"] * 3,
        "source_b": ["gt_model"] * 3,
        "run_id": run_ids,
        "place": ["Test Place"] * 3,
        "iou": [0.5, 0.6, 0.7],
        "de9im_label": ["Match"] * 3,
        "variant_id": ["baseline_v2"] * 3,
        "bbox_west_a": [0, 0, 0],
        "bbox_south_a": [0, 0, 0],
        "bbox_east_a": [1, 1, 1],
        "bbox_north_a": [1, 1, 1],
    }
    valid_df = pd.DataFrame(data)
    known_models = ["test_model"]

    # 1. Filter for run-aaa and run-ccc only
    layers_ac = build_llm_layers(
        mdl="test_model",
        selected_place="Test Place",
        reference_gt="gt_model",
        valid_df=valid_df,
        known_models=known_models,
        selected_runs=["run-aaa", "run-ccc"],
        selected_variants=["baseline_v2"],
    )
    # run label is the last segment after "-": "run-aaa" → "aaa"
    run_ids_found = set()
    for lyr in layers_ac:
        if "aaa" in lyr["name"]:
            run_ids_found.add("run-aaa")
        elif "ccc" in lyr["name"]:
            run_ids_found.add("run-ccc")
        assert "bbb" not in lyr["name"]

    assert run_ids_found == {"run-aaa", "run-ccc"}

    # 2. Filter for run-bbb only
    layers_b = build_llm_layers(
        mdl="test_model",
        selected_place="Test Place",
        reference_gt="gt_model",
        valid_df=valid_df,
        known_models=known_models,
        selected_runs=["run-bbb"],
        selected_variants=["baseline_v2"],
    )
    run_ids_found_b = set()
    for lyr in layers_b:
        if "bbb" in lyr["name"]:
            run_ids_found_b.add("run-bbb")
        assert "aaa" not in lyr["name"]
        assert "ccc" not in lyr["name"]

    assert run_ids_found_b == {"run-bbb"}

    # 3. Empty selected_runs means show all
    layers_all = build_llm_layers(
        mdl="test_model",
        selected_place="Test Place",
        reference_gt="gt_model",
        valid_df=valid_df,
        known_models=known_models,
        selected_runs=[],
        selected_variants=["baseline_v2"],
    )
    all_ids = {lyr["name"].split(" ")[1].strip("(") for lyr in layers_all}
    assert len(layers_all) == 3  # all three runs
