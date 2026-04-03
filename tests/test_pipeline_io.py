from pathlib import Path

from femic.pipeline.io import (
    build_legacy_data_artifact_paths,
    resolve_legacy_siteprod_artifacts,
    resolve_legacy_thlb_raster_path,
    resolve_windows_annex_pointer_payload_path,
    LegacyExternalDataPaths,
)


def _external_paths(root: Path) -> LegacyExternalDataPaths:
    return LegacyExternalDataPaths(
        external_data_root=root,
        vri_vclr1p_path=root / "bc" / "vri" / "2019" / "VEG_COMP_LYR_R1_POLY.gdb",
        vdyp_input_pandl_path=(
            root
            / "bc"
            / "vri"
            / "2019"
            / "VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb"
        ),
        tsa_boundaries_path=root / "bc" / "tsa" / "FADM_TSA.gdb",
        site_prod_bc_gdb_path=root / "bc" / "siteprod" / "Site_Prod_BC.gdb",
        siteprod_tif_path=root / "bc" / "siteprod" / "siteprod.tif",
        siteprod_bandmap_path=root / "bc" / "siteprod" / "siteprod.bandmap.json",
    )


def test_resolve_legacy_thlb_raster_path_prefers_instance_path(tmp_path: Path) -> None:
    instance_data_root = tmp_path / "instance_data"
    instance_data_root.mkdir(parents=True)
    instance_thlb = instance_data_root / "misc.thlb.tif"
    instance_thlb.write_bytes(b"instance")

    external_root = tmp_path / "external_data"
    external_root.mkdir(parents=True)
    (external_root / "misc.thlb.tif").write_bytes(b"external")

    legacy_paths = build_legacy_data_artifact_paths(output_root=instance_data_root)
    resolved = resolve_legacy_thlb_raster_path(
        legacy_data_paths=legacy_paths,
        external_data_paths=_external_paths(external_root),
    )
    assert resolved == instance_thlb


def test_resolve_legacy_thlb_raster_path_falls_back_to_external(tmp_path: Path) -> None:
    instance_data_root = tmp_path / "instance_data"
    instance_data_root.mkdir(parents=True)
    external_root = tmp_path / "external_data"
    external_root.mkdir(parents=True)
    external_thlb = external_root / "misc.thlb.tif"
    external_thlb.write_bytes(b"external")

    legacy_paths = build_legacy_data_artifact_paths(output_root=instance_data_root)
    resolved = resolve_legacy_thlb_raster_path(
        legacy_data_paths=legacy_paths,
        external_data_paths=_external_paths(external_root),
    )
    assert resolved == external_thlb


def test_resolve_legacy_thlb_raster_path_returns_instance_when_both_missing(
    tmp_path: Path,
) -> None:
    instance_data_root = tmp_path / "instance_data"
    instance_data_root.mkdir(parents=True)
    external_root = tmp_path / "external_data"
    external_root.mkdir(parents=True)

    legacy_paths = build_legacy_data_artifact_paths(output_root=instance_data_root)
    resolved = resolve_legacy_thlb_raster_path(
        legacy_data_paths=legacy_paths,
        external_data_paths=_external_paths(external_root),
    )
    assert resolved == instance_data_root / "misc.thlb.tif"


def test_resolve_windows_annex_pointer_payload_path_maps_submodule_pointer(
    tmp_path: Path,
) -> None:
    worktree_root = tmp_path / "dataset"
    pointer_path = worktree_root / "data" / "bc" / "siteprod" / "siteprod.tif"
    pointer_path.parent.mkdir(parents=True)
    gitdir = tmp_path / "gitdir"
    payload = (
        gitdir
        / "annex"
        / "objects"
        / "fa1"
        / "741"
        / "MD5E-s10--deadbeef.tif"
        / "MD5E-s10--deadbeef.tif"
    )
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"payload")
    (worktree_root / ".git").write_text("gitdir: ../gitdir\n", encoding="utf-8")
    pointer_path.write_text(
        "../../../.git/annex/objects/Gp/pM/MD5E-s10--deadbeef.tif/MD5E-s10--deadbeef.tif",
        encoding="utf-8",
    )

    resolved = resolve_windows_annex_pointer_payload_path(pointer_path, os_name="nt")

    assert resolved == payload.resolve()


def test_resolve_windows_annex_pointer_payload_path_leaves_linux_paths_unchanged(
    tmp_path: Path,
) -> None:
    path = tmp_path / "misc.thlb.tif"
    path.write_text(
        "../.git/annex/objects/FM/vw/payload.tif/payload.tif",
        encoding="utf-8",
    )

    resolved = resolve_windows_annex_pointer_payload_path(path, os_name="posix")

    assert resolved == path


def test_resolve_legacy_siteprod_artifacts_prefers_instance_local_pair(
    tmp_path: Path,
) -> None:
    instance_data_root = tmp_path / "instance_data"
    instance_data_root.mkdir(parents=True)
    (instance_data_root / "siteprod.tif").write_bytes(b"instance")
    (instance_data_root / "siteprod.bandmap.json").write_text("{}", encoding="utf-8")

    external_root = tmp_path / "external_data"
    (external_root / "bc" / "siteprod").mkdir(parents=True)
    (external_root / "bc" / "siteprod" / "siteprod.tif").write_bytes(b"external")
    (external_root / "bc" / "siteprod" / "siteprod.bandmap.json").write_text(
        "{}", encoding="utf-8"
    )

    legacy_paths = build_legacy_data_artifact_paths(output_root=instance_data_root)
    resolved = resolve_legacy_siteprod_artifacts(
        legacy_data_paths=legacy_paths,
        external_data_paths=_external_paths(external_root),
    )
    assert resolved.use_prestacked is True
    assert resolved.siteprod_tif_path == instance_data_root / "siteprod.tif"
    assert (
        resolved.siteprod_bandmap_path == instance_data_root / "siteprod.bandmap.json"
    )


def test_resolve_legacy_siteprod_artifacts_falls_back_to_external_pair(
    tmp_path: Path,
) -> None:
    instance_data_root = tmp_path / "instance_data"
    instance_data_root.mkdir(parents=True)
    external_root = tmp_path / "external_data"
    (external_root / "bc" / "siteprod").mkdir(parents=True)
    external_tif = external_root / "bc" / "siteprod" / "siteprod.tif"
    external_bandmap = external_root / "bc" / "siteprod" / "siteprod.bandmap.json"
    external_tif.write_bytes(b"external")
    external_bandmap.write_text("{}", encoding="utf-8")

    legacy_paths = build_legacy_data_artifact_paths(output_root=instance_data_root)
    resolved = resolve_legacy_siteprod_artifacts(
        legacy_data_paths=legacy_paths,
        external_data_paths=_external_paths(external_root),
    )
    assert resolved.use_prestacked is True
    assert resolved.siteprod_tif_path == external_tif
    assert resolved.siteprod_bandmap_path == external_bandmap


def test_resolve_legacy_siteprod_artifacts_returns_legacy_paths_when_pair_missing(
    tmp_path: Path,
) -> None:
    instance_data_root = tmp_path / "instance_data"
    instance_data_root.mkdir(parents=True)
    external_root = tmp_path / "external_data"
    external_root.mkdir(parents=True)

    legacy_paths = build_legacy_data_artifact_paths(output_root=instance_data_root)
    resolved = resolve_legacy_siteprod_artifacts(
        legacy_data_paths=legacy_paths,
        external_data_paths=_external_paths(external_root),
    )
    assert resolved.use_prestacked is False
    assert resolved.siteprod_tif_path == instance_data_root / "siteprod.tif"
    assert (
        resolved.siteprod_bandmap_path == instance_data_root / "siteprod.bandmap.json"
    )
