from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import subprocess

import numpy as np

from femic.pipeline.siteprod import (
    DEFAULT_SITEPROD_SPECIES_LOOKUP,
    assign_siteprod_from_raster,
    build_siteprod_layer_tif_path,
    enumerate_siteprod_layer_tif_paths,
    export_and_stack_siteprod_layers,
    list_siteprod_layers,
    load_siteprod_bandmap,
    mean_siteprod_for_row,
    parse_arc_raster_rescue_layer_mappings,
    resolve_arc_raster_rescue_executable_path,
    siteprod_species_lookup,
)


def test_parse_arc_raster_rescue_layer_mappings() -> None:
    stdout = "layer name\n0 site_prod_sw\n1 site_prod_pl\n"
    layer_species, species_layer = parse_arc_raster_rescue_layer_mappings(
        stdout_text=stdout
    )
    assert layer_species == {0: "SW", 1: "PL"}
    assert species_layer == {"SW": 0, "PL": 1}


def test_siteprod_species_lookup_prefers_full_code_then_initial() -> None:
    assert siteprod_species_lookup("FDI") == "FD"
    assert siteprod_species_lookup("FAKE") == "FD"
    assert DEFAULT_SITEPROD_SPECIES_LOOKUP["FDI"] == "FD"


def test_build_and_enumerate_siteprod_temp_paths(tmp_path: Path) -> None:
    prefix = tmp_path / "site_prod_bc_"
    p1 = build_siteprod_layer_tif_path(
        siteprod_tmpexport_tif_path_prefix=prefix,
        species="SW",
    )
    p2 = build_siteprod_layer_tif_path(
        siteprod_tmpexport_tif_path_prefix=prefix,
        species="PL",
    )
    p1.write_text("x", encoding="utf-8")
    p2.write_text("x", encoding="utf-8")

    found = enumerate_siteprod_layer_tif_paths(
        siteprod_tmpexport_tif_path_prefix=prefix
    )
    assert found == sorted([p1, p2])


def test_list_siteprod_layers_uses_runner_output(tmp_path: Path) -> None:
    exe_path = tmp_path / "arc_raster_rescue.exe"
    exe_path.write_text("", encoding="utf-8")

    def _run(cmd: list[object], capture_output: bool) -> SimpleNamespace:
        assert capture_output is True
        assert len(cmd) == 2
        assert str(cmd[1]).endswith(".gdb/")
        return SimpleNamespace(stdout=b"layer name\n0 site_prod_sw\n")

    layer_species, species_layer = list_siteprod_layers(
        arc_raster_rescue_exe_path=exe_path,
        siteprod_gdb_path=Path("Site_Prod_BC.gdb"),
        run_fn=_run,
    )
    assert layer_species == {0: "SW"}
    assert species_layer == {"SW": 0}


def test_resolve_arc_raster_rescue_prefers_env_override(tmp_path: Path) -> None:
    override = tmp_path / "override.exe"
    override.write_text("", encoding="utf-8")
    configured = tmp_path / "missing.exe"
    resolved = resolve_arc_raster_rescue_executable_path(
        configured_path=configured,
        env_override=str(override),
    )
    assert resolved == override.resolve()


def test_resolve_arc_raster_rescue_supports_source_root_fallback(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir(parents=True, exist_ok=True)
    configured = Path("ArcRasterRescue/build/arc_raster_rescue.exe")
    fallback = source_root / configured
    fallback.parent.mkdir(parents=True, exist_ok=True)
    fallback.write_text("", encoding="utf-8")
    resolved = resolve_arc_raster_rescue_executable_path(
        configured_path=configured,
        source_root_env=str(source_root),
    )
    assert resolved == fallback.resolve()


def test_export_and_stack_siteprod_layers(tmp_path: Path) -> None:
    class _FakeSrc:
        def __init__(self, path: Path) -> None:
            self.path = path
            self.meta = {"driver": "GTiff", "dtype": "uint8", "height": 1, "width": 1}

        def __enter__(self) -> "_FakeSrc":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def read(self, _band: int) -> np.ndarray:
            return np.array([[1]], dtype=np.uint8)

    class _FakeDst:
        def __init__(self, path: Path) -> None:
            self.path = path
            self.path.write_text("stack", encoding="utf-8")
            self.written_bands: list[int] = []

        def __enter__(self) -> "_FakeDst":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def write_band(self, band: int, _arr: np.ndarray) -> None:
            self.written_bands.append(band)

    class _FakeRio:
        def __init__(self) -> None:
            self.crs = SimpleNamespace(CRS=lambda payload: payload)
            self.last_dst: _FakeDst | None = None

        def open(self, path: Path, mode: str = "r", **_kwargs: object) -> object:
            if mode == "w":
                self.last_dst = _FakeDst(Path(path))
                return self.last_dst
            return _FakeSrc(Path(path))

    commands: list[list[object]] = []
    exe_path = tmp_path / "arc_raster_rescue.exe"
    exe_path.write_text("", encoding="utf-8")

    def _run(cmd: list[object], capture_output: bool = False) -> SimpleNamespace:
        commands.append(cmd)
        out_path = Path(cmd[3])  # type: ignore[index]
        out_path.write_text("layer", encoding="utf-8")
        return SimpleNamespace(stdout=b"")

    prefix = tmp_path / "site_prod_bc_"
    out_tif = tmp_path / "siteprod.tif"
    fake_rio = _FakeRio()

    export_and_stack_siteprod_layers(
        arc_raster_rescue_exe_path=exe_path,
        site_prod_bc_gdb_path=Path("Site_Prod_BC.gdb"),
        site_prod_bc_layerspecies={1: "SW", 2: "PL"},
        siteprod_layerspecies={0: "SW", 1: "PL"},
        siteprod_tmpexport_tif_path_prefix=prefix,
        siteprod_tif_path=out_tif,
        run_fn=_run,
        rio_module=fake_rio,
        message_fn=lambda *_args: None,
    )

    assert len(commands) == 2
    assert out_tif.is_file()
    assert fake_rio.last_dst is not None
    assert fake_rio.last_dst.written_bands == [1, 2]
    assert (
        enumerate_siteprod_layer_tif_paths(siteprod_tmpexport_tif_path_prefix=prefix)
        == []
    )


def test_export_and_stack_siteprod_layers_times_out_with_diagnostics(
    tmp_path: Path,
) -> None:
    exe_path = tmp_path / "arc_raster_rescue.exe"
    exe_path.write_text("", encoding="utf-8")
    prefix = tmp_path / "site_prod_bc_"
    out_tif = tmp_path / "siteprod.tif"

    def _run(_cmd: list[object], **_kwargs: object) -> SimpleNamespace:
        raise subprocess.TimeoutExpired(cmd="arc_raster_rescue", timeout=1)

    class _FakeRio:
        def __init__(self) -> None:
            self.crs = SimpleNamespace(CRS=lambda payload: payload)

        def open(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("stacking should not be reached on timeout")

    try:
        export_and_stack_siteprod_layers(
            arc_raster_rescue_exe_path=exe_path,
            site_prod_bc_gdb_path=Path("Site_Prod_BC.gdb"),
            site_prod_bc_layerspecies={1: "SW"},
            siteprod_layerspecies={0: "SW"},
            siteprod_tmpexport_tif_path_prefix=prefix,
            siteprod_tif_path=out_tif,
            run_fn=_run,
            rio_module=_FakeRio(),
            message_fn=lambda *_args: None,
        )
    except RuntimeError as exc:
        message = str(exc)
        assert "timed out" in message
        assert "species SW" in message
        assert "layer=1" in message
    else:
        raise AssertionError("expected RuntimeError for timeout path")


def test_export_and_stack_siteprod_layers_nonzero_returncode_raises(
    tmp_path: Path,
) -> None:
    exe_path = tmp_path / "arc_raster_rescue.exe"
    exe_path.write_text("", encoding="utf-8")
    prefix = tmp_path / "site_prod_bc_"
    out_tif = tmp_path / "siteprod.tif"

    def _run(_cmd: list[object], **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=2, stderr="boom")

    class _FakeRio:
        def __init__(self) -> None:
            self.crs = SimpleNamespace(CRS=lambda payload: payload)

        def open(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("stacking should not be reached on failure")

    try:
        export_and_stack_siteprod_layers(
            arc_raster_rescue_exe_path=exe_path,
            site_prod_bc_gdb_path=Path("Site_Prod_BC.gdb"),
            site_prod_bc_layerspecies={1: "SW"},
            siteprod_layerspecies={0: "SW"},
            siteprod_tmpexport_tif_path_prefix=prefix,
            siteprod_tif_path=out_tif,
            run_fn=_run,
            rio_module=_FakeRio(),
            message_fn=lambda *_args: None,
        )
    except RuntimeError as exc:
        message = str(exc)
        assert "failed for species SW" in message
        assert "returncode=2" in message
        assert "boom" in message
    else:
        raise AssertionError("expected RuntimeError for non-zero returncode path")


def test_mean_siteprod_for_row_and_assign_siteprod_from_raster() -> None:
    class _Row:
        def __init__(self, species: str) -> None:
            self.SPECIES_CD_1 = species
            self.geometry = object()

    values = np.array([[[0.0, 2.0]], [[0.0, 4.0]]], dtype=float)

    def _mask(
        _src: object, _geoms: list[object], crop: bool
    ) -> tuple[np.ndarray, None]:
        assert crop is True
        return values, None

    row = _Row("FDI")
    mean_value = mean_siteprod_for_row(
        row=row,
        raster_src=object(),
        mask_fn=_mask,
        np_module=np,
        siteprod_specieslayer={"FD": 1},
    )
    assert mean_value == 4.0

    class _FakeSrc:
        def __enter__(self) -> "_FakeSrc":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    class _FakeRio:
        def open(self, _path: Path) -> _FakeSrc:
            return _FakeSrc()

    class _Table:
        def __init__(self) -> None:
            self.written: dict[str, object] = {}

        def copy(self) -> "_Table":
            return self

        def __setitem__(self, key: str, value: object) -> None:
            self.written[key] = value

    table = _Table()

    def _row_apply(_table: _Table, fn: object, axis: int) -> list[float]:
        assert axis == 1
        assert callable(fn)
        return [fn(_Row("FDI"))]  # type: ignore[misc]

    out = assign_siteprod_from_raster(
        f_table=table,
        siteprod_tif_path=Path("siteprod.tif"),
        siteprod_specieslayer={"FD": 1},
        rio_module=_FakeRio(),
        mask_fn=_mask,
        np_module=np,
        row_apply_fn=_row_apply,
    )
    assert out is table
    assert table.written["siteprod"] == [4.0]



def test_load_siteprod_bandmap_prefers_bands_1_based(tmp_path: Path) -> None:
    path = tmp_path / "siteprod.bandmap.json"
    path.write_text(
        '{"bands_1_based": {"FD": 8, "HW": 10}, "ordered_species": ["FD", "HW"]}',
        encoding="utf-8",
    )
    layer_species, species_layer = load_siteprod_bandmap(bandmap_path=path)
    assert species_layer == {"FD": 7, "HW": 9}
    assert layer_species == {7: "FD", 9: "HW"}


def test_load_siteprod_bandmap_falls_back_to_ordered_species(tmp_path: Path) -> None:
    path = tmp_path / "siteprod.bandmap.json"
    path.write_text('{"ordered_species": ["AT", "BL", "CW"]}', encoding="utf-8")
    layer_species, species_layer = load_siteprod_bandmap(bandmap_path=path)
    assert layer_species == {0: "AT", 1: "BL", 2: "CW"}
    assert species_layer == {"AT": 0, "BL": 1, "CW": 2}
