from femic.cli.main import app
from femic.pipeline.io import build_vri_checkpoint_paths, normalize_tsa_list


def test_cli_app_importable() -> None:
    assert app is not None


def test_pipeline_transform_smoke_helpers() -> None:
    tsas = normalize_tsa_list([8, "16"])
    checkpoints = build_vri_checkpoint_paths(output_root="data", count=3)

    assert tsas == ["08", "16"]
    assert checkpoints[1].name == "vri_vclr1p_checkpoint1.feather"
    assert checkpoints[3].name == "vri_vclr1p_checkpoint3.feather"
