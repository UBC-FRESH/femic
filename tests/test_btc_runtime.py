"""Tests for femic.pipeline.btc_runtime BTC/Wine runtime configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import femic.pipeline.btc_runtime as btc_runtime
from femic.pipeline.btc_runtime import (
    DEFAULT_BATCHTIPSY_WINDOWS_EXE,
    DEFAULT_BTC_RUNTIME_CONFIG_RELPATH,
    FEMIC_BTC_HOST_MODE,
    FEMIC_BTC_USE_XVFB,
    FEMIC_BTC_WINEPREFIX,
    FEMIC_WINE_EXE_ENV,
    BTCRuntimeConfig,
    is_wsl,
    load_btc_runtime_config,
    resolve_btc_runtime_config,
    resolve_host_mode,
    to_windows_host_path,
)


def _write_instance_runtime_config(
    tmp_path: Path,
    fields: dict[str, str | bool | None],
) -> Path:
    """Write a BTC runtime YAML under tmp_path and return the instance root."""
    instance_root = tmp_path / "instance"
    cfg_path = instance_root / DEFAULT_BTC_RUNTIME_CONFIG_RELPATH
    cfg_path.parent.mkdir(parents=True)
    lines = ["tipsy_btc:"]
    for key, value in fields.items():
        if value is None:
            lines.append(f"  {key}: null")
        elif isinstance(value, bool):
            lines.append(f"  {key}: {str(value).lower()}")
        else:
            lines.append(f"  {key}: {value}")
    lines.append("")
    cfg_path.write_text("\n".join(lines), encoding="utf-8")
    return instance_root


def test_default_batchtipsy_windows_exe_path() -> None:
    assert DEFAULT_BATCHTIPSY_WINDOWS_EXE == Path(
        r"C:\Program Files\TIPSY 4.7\BTC\TIPSYbtc.exe"
    )


def test_btc_runtime_config_defaults() -> None:
    cfg = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
    )
    assert cfg.use_xvfb is False
    assert cfg.host_mode == "auto"
    assert cfg.xvfb_executable is None


def test_resolve_host_mode_windows_native(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(btc_runtime.os, "name", "nt")
    assert resolve_host_mode() == "windows"
    assert resolve_host_mode("auto") == "windows"
    assert resolve_host_mode("windows") == "windows"
    assert resolve_host_mode("wine") == "windows"


def test_resolve_host_mode_wsl_interop(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_which(name: str) -> str | None:
        if name in ("powershell.exe", "cmd.exe"):
            return f"/mnt/c/Windows/System32/{name}"
        return None

    monkeypatch.setattr(btc_runtime.shutil, "which", _fake_which)
    assert resolve_host_mode(env={"WSL_DISTRO_NAME": "Ubuntu"}) == "wsl-interop"
    assert (
        resolve_host_mode("auto", env={"WSL_DISTRO_NAME": "Ubuntu"})
        == "wsl-interop"
    )
    assert (
        resolve_host_mode("wsl-interop", env={"WSL_DISTRO_NAME": "Ubuntu"})
        == "wsl-interop"
    )


def test_resolve_host_mode_wsl_interop_via_os_environ(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    monkeypatch.setattr(
        btc_runtime.shutil,
        "which",
        lambda name: "/mnt/c/Windows/System32/cmd.exe"
        if name == "cmd.exe"
        else None,
    )
    assert resolve_host_mode() == "wsl-interop"


def test_resolve_host_mode_windows_on_posix_fails_loud() -> None:
    with pytest.raises(RuntimeError, match="not native Windows"):
        resolve_host_mode("windows")


def test_resolve_host_mode_wsl_interop_without_carrier_fails_loud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(btc_runtime.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="wsl-interop"):
        resolve_host_mode("wsl-interop", env={"WSL_DISTRO_NAME": "Ubuntu"})


def test_resolve_host_mode_explicit_wine_honored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(btc_runtime.shutil, "which", lambda _name: None)
    assert resolve_host_mode("wine") == "wine"
    assert resolve_host_mode("auto") == "wine"
    assert resolve_host_mode(None) == "wine"


def test_is_wsl_guards_missing_proc_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)

    def _missing_read(self: Path, *args: Any, **kwargs: Any) -> str:
        raise FileNotFoundError(f"{self} does not exist")

    monkeypatch.setattr(Path, "read_text", _missing_read)
    assert is_wsl() is False


def test_is_wsl_detects_microsoft_kernel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda self, *args, **kwargs: (
            "Linux version 5.15.90.1-microsoft-standard-WSL2"
        ),
    )
    assert is_wsl() is True


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        ("0", False),
        ("false", False),
        ("no", False),
    ],
)
def test_resolve_use_xvfb_parses_env_bool(raw_value: str, expected: bool) -> None:
    cfg = resolve_btc_runtime_config(env={FEMIC_BTC_USE_XVFB: raw_value})
    assert cfg.use_xvfb is expected


def test_resolve_use_xvfb_env_bool_rejects_junk() -> None:
    with pytest.raises(ValueError, match=FEMIC_BTC_USE_XVFB):
        resolve_btc_runtime_config(env={FEMIC_BTC_USE_XVFB: "maybe"})


def test_resolve_btc_runtime_config_arg_beats_env(tmp_path: Path) -> None:
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {
            "batch_tipsy_exe": "/tmp/yaml-exe.exe",
            "wine_prefix": "/tmp/yaml",
            "wine_executable": "/tmp/yaml-wine",
            "use_xvfb": True,
            "host_mode": "wine",
        },
    )
    cfg = resolve_btc_runtime_config(
        btc_exe="/tmp/arg.exe",
        wine_prefix="/tmp/arg",
        wine_executable="/tmp/arg-wine",
        use_xvfb=False,
        host_mode="wine",
        instance_root=instance_root,
        env={
            "FEMIC_BATCHTIPSY_EXE": "/tmp/env.exe",
            FEMIC_BTC_WINEPREFIX: "/tmp/env",
            "FEMIC_WINE_EXE": "/tmp/env-wine",
            FEMIC_BTC_USE_XVFB: "1",
            FEMIC_BTC_HOST_MODE: "windows",
        },
    )
    assert cfg.batch_tipsy_exe == Path("/tmp/arg.exe")
    assert cfg.wine_prefix == Path("/tmp/arg")
    assert cfg.wine_executable == "/tmp/arg-wine"
    assert cfg.use_xvfb is False
    assert cfg.host_mode == "wine"


def test_resolve_btc_runtime_config_env_beats_yaml(tmp_path: Path) -> None:
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {
            "batch_tipsy_exe": "/tmp/yaml-exe.exe",
            "wine_prefix": "/tmp/yaml",
            "wine_executable": "/tmp/yaml-wine",
            "use_xvfb": True,
            "host_mode": "wine",
        },
    )
    cfg = resolve_btc_runtime_config(
        instance_root=instance_root,
        env={
            "FEMIC_BATCHTIPSY_EXE": "/tmp/env.exe",
            FEMIC_BTC_WINEPREFIX: "/tmp/env",
            "FEMIC_WINE_EXE": "/tmp/env-wine",
            FEMIC_BTC_USE_XVFB: "0",
            FEMIC_BTC_HOST_MODE: "wine",
        },
    )
    assert cfg.batch_tipsy_exe == Path("/tmp/env.exe")
    assert cfg.wine_prefix == Path("/tmp/env")
    assert cfg.wine_executable == "/tmp/env-wine"
    assert cfg.use_xvfb is False
    assert cfg.host_mode == "wine"


def test_resolve_btc_runtime_config_yaml_beats_discovery(tmp_path: Path) -> None:
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {
            "batch_tipsy_exe": "/tmp/yaml-exe.exe",
            "wine_prefix": "/tmp/yaml",
            "wine_executable": "/tmp/yaml-wine",
            "use_xvfb": True,
            "host_mode": "wine",
        },
    )
    cfg = resolve_btc_runtime_config(instance_root=instance_root, env={})
    assert cfg.batch_tipsy_exe == Path("/tmp/yaml-exe.exe")
    assert cfg.wine_prefix == Path("/tmp/yaml")
    assert cfg.wine_executable == "/tmp/yaml-wine"
    assert cfg.use_xvfb is True
    assert cfg.host_mode == "wine"


def test_resolve_wine_prefix_discovery_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    (home / ".wine-tipsy64" / "drive_c").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {"wine_prefix": None},
    )
    cfg = resolve_btc_runtime_config(instance_root=instance_root, env={})
    assert cfg.wine_prefix == home / ".wine-tipsy64"


def test_resolve_wine_prefix_discovery_falls_to_second_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    (home / ".wine-tipsy64").mkdir(parents=True)
    (home / ".wine-tipsy47" / "drive_c").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {"wine_prefix": None},
    )
    cfg = resolve_btc_runtime_config(instance_root=instance_root, env={})
    assert cfg.wine_prefix == home / ".wine-tipsy47"


def test_resolve_batch_tipsy_exe_none_when_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {"batch_tipsy_exe": None},
    )
    cfg = resolve_btc_runtime_config(instance_root=instance_root, env={})
    assert cfg.batch_tipsy_exe is None


def test_to_windows_host_path_maps_mnt_drive() -> None:
    mapped = to_windows_host_path(
        "/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe"
    )
    assert mapped == r"C:\Program Files\TIPSY 4.7\BTC\TIPSYbtc.exe"


def test_to_windows_host_path_preserves_windows_style() -> None:
    windows_path = r"C:\Program Files\x\y.exe"
    assert to_windows_host_path(windows_path) == windows_path


def test_to_windows_host_path_rejects_unmappable_path() -> None:
    with pytest.raises(ValueError, match="/mnt/"):
        to_windows_host_path("/home/gep/foo")


def test_is_headless_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(btc_runtime.os, "name", "posix")
    assert btc_runtime.is_headless(env={}) is True
    assert btc_runtime.is_headless(env={"DISPLAY": ""}) is True
    assert btc_runtime.is_headless(env={"DISPLAY": ":99"}) is False


def test_is_headless_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(btc_runtime.os, "name", "nt")
    assert btc_runtime.is_headless(env={}) is False
    assert btc_runtime.is_headless(env={"DISPLAY": ":99"}) is False


def test_load_btc_runtime_config_missing_returns_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert load_btc_runtime_config() == {}
    assert load_btc_runtime_config(instance_root=tmp_path / "missing") == {}
    assert load_btc_runtime_config(path=tmp_path / "missing.yaml") == {}


def test_load_btc_runtime_config_parses_section(tmp_path: Path) -> None:
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {"wine_prefix": "/tmp/x", "use_xvfb": True},
    )
    loaded = load_btc_runtime_config(instance_root=instance_root)
    assert loaded == {"wine_prefix": "/tmp/x", "use_xvfb": True}


def test_load_btc_runtime_config_explicit_path(tmp_path: Path) -> None:
    cfg_path = tmp_path / "custom.yaml"
    cfg_path.write_text("tipsy_btc:\n  host_mode: windows\n", encoding="utf-8")
    loaded = load_btc_runtime_config(path=cfg_path)
    assert loaded == {"host_mode": "windows"}


def test_host_mode_label() -> None:
    assert btc_runtime.host_mode_label("windows") == "Windows native"
    assert btc_runtime.host_mode_label("wine") == "Wine"
    assert btc_runtime.host_mode_label("wsl-interop") == "WSL interop to Windows"
    assert btc_runtime.host_mode_label("auto") == "auto"


def test_env_has_wine_intent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(FEMIC_BTC_WINEPREFIX, raising=False)
    monkeypatch.delenv("WINEPREFIX", raising=False)
    monkeypatch.delenv(FEMIC_WINE_EXE_ENV, raising=False)
    assert btc_runtime.env_has_wine_intent({}) is False
    assert btc_runtime.env_has_wine_intent(None) is False
    assert (
        btc_runtime.env_has_wine_intent({FEMIC_BTC_WINEPREFIX: "/opt/wine"}) is True
    )
    assert btc_runtime.env_has_wine_intent({"WINEPREFIX": "/opt/wine"}) is True
    assert btc_runtime.env_has_wine_intent({FEMIC_WINE_EXE_ENV: "wine64"}) is True
    assert btc_runtime.env_has_wine_intent({FEMIC_BTC_WINEPREFIX: ""}) is False


def test_resolve_host_mode_wsl_with_wine_intent_prefers_wine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_which(name: str) -> str | None:
        if name in ("powershell.exe", "cmd.exe"):
            return f"/mnt/c/Windows/System32/{name}"
        return None

    monkeypatch.setattr(btc_runtime.shutil, "which", _fake_which)
    wsl_env = {"WSL_DISTRO_NAME": "Ubuntu"}
    assert resolve_host_mode(env=wsl_env, wine_intent=True) == "wine"
    assert resolve_host_mode("auto", env=wsl_env, wine_intent=True) == "wine"
    assert resolve_host_mode("wine", env=wsl_env, wine_intent=True) == "wine"
    # An explicit wsl-interop request still wins over wine intent.
    assert (
        resolve_host_mode("wsl-interop", env=wsl_env, wine_intent=True)
        == "wsl-interop"
    )
    # Without wine intent, auto still selects wsl-interop on WSL.
    assert resolve_host_mode(env=wsl_env, wine_intent=False) == "wsl-interop"


def test_resolve_btc_runtime_config_wsl_wine_prefix_param_prefers_wine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        btc_runtime.shutil,
        "which",
        lambda name: "/mnt/c/Windows/System32/cmd.exe"
        if name == "cmd.exe"
        else None,
    )
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {"wine_prefix": None},
    )
    cfg = resolve_btc_runtime_config(
        wine_prefix="/opt/prefix",
        instance_root=instance_root,
        env={"WSL_DISTRO_NAME": "Ubuntu"},
    )
    assert cfg.wine_prefix == Path("/opt/prefix")
    assert cfg.host_mode == "wine"


def test_resolve_btc_runtime_config_wsl_femic_wine_exe_prefers_wine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        btc_runtime.shutil,
        "which",
        lambda name: "/mnt/c/Windows/System32/cmd.exe"
        if name == "cmd.exe"
        else None,
    )
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {"wine_prefix": None},
    )
    cfg = resolve_btc_runtime_config(
        instance_root=instance_root,
        env={"WSL_DISTRO_NAME": "Ubuntu", FEMIC_WINE_EXE_ENV: "wine64"},
    )
    assert cfg.wine_executable == "wine64"
    assert cfg.host_mode == "wine"


def test_resolve_btc_runtime_config_wsl_yaml_wine_intent_prefers_wine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """m4: YAML-set wine_prefix + wine_executable (no arg/env) implies wine."""
    monkeypatch.setattr(
        btc_runtime.shutil,
        "which",
        lambda name: "/mnt/c/Windows/System32/cmd.exe"
        if name == "cmd.exe"
        else None,
    )
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {
            "wine_prefix": "/opt/yaml-prefix",
            "wine_executable": "wine64",
        },
    )
    cfg = resolve_btc_runtime_config(
        instance_root=instance_root,
        env={"WSL_DISTRO_NAME": "Ubuntu"},
    )
    assert cfg.wine_prefix == Path("/opt/yaml-prefix")
    assert cfg.wine_executable == "wine64"
    assert cfg.host_mode == "wine"


def test_resolve_btc_runtime_config_precedence_arg_env_yaml(tmp_path: Path) -> None:
    """m4: CLI arg > env var > YAML for a resolved field."""
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {
            "wine_prefix": "/tmp/yaml",
            "wine_executable": "/tmp/yaml-wine",
        },
    )
    cfg = resolve_btc_runtime_config(
        wine_prefix="/tmp/arg",
        instance_root=instance_root,
        env={
            FEMIC_BTC_WINEPREFIX: "/tmp/env",
            FEMIC_WINE_EXE_ENV: "/tmp/env-wine",
        },
    )
    assert cfg.wine_prefix == Path("/tmp/arg")
    assert cfg.wine_executable == "/tmp/env-wine"


def test_resolve_btc_runtime_config_wsl_no_wine_intent_selects_interop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        btc_runtime.shutil,
        "which",
        lambda name: "/mnt/c/Windows/System32/cmd.exe"
        if name == "cmd.exe"
        else None,
    )
    monkeypatch.setattr(
        Path, "home", staticmethod(lambda: tmp_path / "empty-home")
    )
    instance_root = _write_instance_runtime_config(
        tmp_path,
        {"wine_prefix": None},
    )
    cfg = resolve_btc_runtime_config(
        instance_root=instance_root,
        env={"WSL_DISTRO_NAME": "Ubuntu"},
    )
    assert cfg.wine_prefix is None
    assert cfg.host_mode == "wsl-interop"
