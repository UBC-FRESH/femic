"""BTC / BatchTIPSY runtime configuration for the femic launcher.

Centralizes the Wine and BatchTIPSY runtime surface so the BTC launcher in
``femic.pipeline.tipsy`` never has to re-derive host mode, prefix, or Wine
executable settings. This module must never import ``femic.pipeline.tipsy``
(no circular imports); Wine discovery is imported lazily from
``femic.patchworks_runtime`` instead.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
from typing import Any, Mapping

import yaml

# Environment variable controlling the dedicated BTC Wine prefix.
FEMIC_BTC_WINEPREFIX = "FEMIC_BTC_WINEPREFIX"
# Environment variable toggling xvfb-run wrapping for headless Wine runs.
FEMIC_BTC_USE_XVFB = "FEMIC_BTC_USE_XVFB"
# Environment variable selecting the BTC host mode ("auto"|"windows"|"wine"|"wsl-interop").
FEMIC_BTC_HOST_MODE = "FEMIC_BTC_HOST_MODE"
# Environment variable overriding the Wine executable used for BTC runs.
FEMIC_WINE_EXE_ENV = "FEMIC_WINE_EXE"
# Single source of truth for the default Windows BatchTIPSY executable path.
DEFAULT_BATCHTIPSY_WINDOWS_EXE = Path(r"C:\Program Files\TIPSY 4.7\BTC\TIPSYbtc.exe")
# Config-file relative path looked up under the instance root or current directory.
DEFAULT_BTC_RUNTIME_CONFIG_RELPATH = "config/tipsy.btc.runtime.yaml"

_BTC_HOST_MODE_LABELS = {
    "auto": "auto",
    "windows": "Windows native",
    "wine": "Wine",
    "wsl-interop": "WSL interop to Windows",
}
_WINDOWS_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:\\")
_WSL_MNT_PATH_RE = re.compile(r"^/mnt/([A-Za-z])(?:/|$)(.*)$", re.DOTALL)
_WINE_PREFIX_CANDIDATE_NAMES = (".wine-tipsy64", ".wine-tipsy47")
_BTC_RUNTIME_CONFIG_SECTION = "tipsy_btc"
_BTC_RUNTIME_CONFIG_FIELDS = (
    "batch_tipsy_exe",
    "wine_prefix",
    "wine_executable",
    "use_xvfb",
    "host_mode",
)
# Carrier executables the WSL-interop wrapper actually constructs.
_INTEROP_CARRIER_BASENAMES = ("powershell.exe", "cmd.exe")


class BTCRuntimeConfigError(ValueError):
    """Invalid BTC runtime configuration."""


@dataclass(frozen=True)
class BTCRuntimeConfig:
    """Resolved BTC/Wine runtime settings for BatchTIPSY execution.

    Attributes:
        batch_tipsy_exe: BatchTIPSY executable path, or None when resolution is
            deferred to ``tipsy.resolve_btc_executable``.
        wine_executable: Wine executable path/name used to run Windows binaries.
        wine_prefix: Wine prefix directory hosting the Windows TIPSY install.
        use_xvfb: Whether to wrap the Wine subprocess in ``xvfb-run`` on
            headless hosts.
        host_mode: Host mode label; one of ``"auto"``, ``"windows"``,
            ``"wine"``, or ``"wsl-interop"``.
        xvfb_executable: Resolved ``xvfb-run`` executable, or None when it is
            not available on PATH.
    """

    batch_tipsy_exe: Path | None
    wine_executable: str | None
    wine_prefix: Path | None
    use_xvfb: bool = False
    host_mode: str = "auto"
    xvfb_executable: str | None = None


def is_wsl() -> bool:
    """Return true when running inside WSL (Windows Subsystem for Linux)."""

    return _env_is_wsl(os.environ)


def _env_is_wsl(env: Mapping[str, str]) -> bool:
    if str(env.get("WSL_DISTRO_NAME", "")).strip():
        return True
    try:
        proc_version = Path("/proc/version").read_text(
            encoding="utf-8", errors="ignore"
        )
    except OSError:
        return False
    return "microsoft" in proc_version.lower()


def resolve_host_mode(
    requested: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    wine_intent: bool = False,
) -> str:
    """Resolve the effective BTC host mode for this host.

    Args:
        requested: Explicitly requested mode; one of ``"auto"``, ``"windows"``,
            ``"wine"``, or ``"wsl-interop"``. ``None`` (or ``"auto"``) enables
            discovery.
        env: Environment mapping to consult (defaults to ``os.environ``).
        wine_intent: When true and ``requested`` is ``None``/``"auto"``,
            resolve to ``"wine"`` instead of auto-selecting ``wsl-interop``
            on WSL hosts. Explicit Wine configuration (a prefix or Wine
            executable from arguments, environment, or YAML) implies this
            intent; ``wsl-interop`` is only auto-selected when no Wine intent
            exists.

    Returns:
        The resolved host mode: ``"windows"``, ``"wine"``, or ``"wsl-interop"``.

    Raises:
        RuntimeError: when an explicitly requested mode cannot run on this host.
    """
    env = os.environ if env is None else env
    normalized = (requested or "").strip().lower() or "auto"
    if normalized == "windows":
        if os.name != "nt":
            raise RuntimeError(
                "BTC host mode 'windows' was requested, but this host is not "
                f"native Windows (os.name={os.name!r}). Use 'wine' or "
                "'wsl-interop' instead."
            )
        return "windows"
    if os.name == "nt":
        return "windows"
    if normalized == "wsl-interop" or (
        normalized == "auto" and not wine_intent and _env_is_wsl(env)
    ):
        if _interop_carrier_available():
            return "wsl-interop"
        if normalized == "wsl-interop":
            raise RuntimeError(
                "BTC host mode 'wsl-interop' was requested, but neither "
                "powershell.exe nor cmd.exe is reachable on PATH."
            )
    return "wine"


def env_has_wine_intent(env: Mapping[str, str] | None) -> bool:
    """Return true when the environment carries explicit Wine intent.

    Any of ``FEMIC_BTC_WINEPREFIX``, ``WINEPREFIX``, or ``FEMIC_WINE_EXE``
    signals that the caller wants Wine rather than WSL interop even when
    host mode is left as ``auto``.

    Args:
        env: Environment mapping to consult; ``None`` reads ``os.environ``.

    Returns:
        True when any Wine-intent environment variable is set to a
        non-empty value.
    """

    lookup = os.environ if env is None else env
    return any(
        str(lookup.get(name, "")).strip()
        for name in (FEMIC_BTC_WINEPREFIX, "WINEPREFIX", FEMIC_WINE_EXE_ENV)
    )


def _has_wine_intent(raw_wine_prefix: object, raw_wine_executable: object) -> bool:
    """Return true when explicit Wine configuration implies Wine intent.

    Any non-None Wine prefix or Wine executable value (from an argument,
    environment variable, or the YAML config) signals that an unresolved
    ``auto`` host mode should resolve to ``wine`` rather than auto-selecting
    ``wsl-interop`` on WSL hosts.

    Args:
        raw_wine_prefix: Raw Wine prefix value before path normalization.
        raw_wine_executable: Raw Wine executable value before normalization.

    Returns:
        True when either value is not None.
    """

    # Empty-string values (e.g. FEMIC_BTC_WINEPREFIX="") still count as
    # intent: the check is `is not None` pre-normalization, as in the
    # original inline expression.
    return raw_wine_prefix is not None or raw_wine_executable is not None


def _interop_carrier_available() -> bool:
    return (
        shutil.which("powershell.exe") is not None
        or shutil.which("cmd.exe") is not None
    )


def is_wsl_interop_carrier(value: str) -> bool:
    """Return true when a value names a Windows interop carrier executable.

    The check is a case-insensitive basename comparison against
    ``powershell.exe`` and ``cmd.exe`` — exactly the carriers the
    WSL-interop wrapper constructs. Absolute paths are accepted when their
    basename matches (e.g. ``/mnt/c/Windows/System32/powershell.exe``).

    Args:
        value: Candidate carrier executable path or bare command name.

    Returns:
        True when the basename (case-insensitive) is ``powershell.exe`` or
        ``cmd.exe``.
    """

    return Path(str(value)).name.lower() in _INTEROP_CARRIER_BASENAMES


def is_headless(env: Mapping[str, str] | None = None) -> bool:
    """Return true when no interactive display is available."""

    env = os.environ if env is None else env
    if os.name == "nt":
        return False
    return not str(env.get("DISPLAY", "")).strip()


def find_xvfb_run() -> str | None:
    """Return the xvfb-run executable path when available on PATH."""

    return shutil.which("xvfb-run")


def host_mode_label(mode: str) -> str:
    """Return a short human-readable label for a BTC host mode."""

    normalized = str(mode).strip().lower()
    return _BTC_HOST_MODE_LABELS.get(normalized, str(mode))


def to_windows_host_path(path: str | Path) -> str:
    """Map a POSIX path to a Windows drive path for WSL interop.

    Args:
        path: Absolute path, either already Windows-style (``C:\\...``) or
            under ``/mnt/<drive>/...``.

    Returns:
        The Windows-style path using backslash separators and an uppercase
        drive letter.

    Raises:
        ValueError: when the path is neither Windows-style nor under
            ``/mnt/<drive>``.
    """
    text = str(path)
    if _WINDOWS_DRIVE_PATH_RE.match(text):
        return text
    match = _WSL_MNT_PATH_RE.match(text)
    if match is None:
        raise ValueError(
            f"Path {text!r} is not usable for WSL interop: it must already be "
            "Windows-style (e.g. 'C:\\...') or live under /mnt/<drive>/..."
        )
    drive, remainder = match.groups()
    windows_remainder = remainder.replace("/", "\\")
    return f"{drive.upper()}:\\{windows_remainder}"


def load_btc_runtime_config(
    path: str | Path | None = None,
    instance_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load the BTC runtime YAML config, returning {} when it is absent.

    Args:
        path: Explicit config file path; when given, a missing file is treated
            as an absent config.
        instance_root: Directory to search for
            ``config/tipsy.btc.runtime.yaml`` before falling back to the
            current working directory.

    Returns:
        The ``tipsy_btc`` section as a dict, or {} when no config file exists.

    Raises:
        BTCRuntimeConfigError: when an existing config file cannot be parsed.
    """
    resolved_path = _resolve_btc_runtime_config_path(
        path=path,
        instance_root=instance_root,
    )
    if resolved_path is None:
        return {}
    try:
        payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise BTCRuntimeConfigError(
            f"Could not parse BTC runtime config {resolved_path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BTCRuntimeConfigError(
            "BTC runtime config must contain a top-level object: "
            f"{resolved_path}"
        )
    section = payload.get(_BTC_RUNTIME_CONFIG_SECTION, {})
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise BTCRuntimeConfigError(
            f"BTC runtime config section {_BTC_RUNTIME_CONFIG_SECTION!r} "
            f"must be an object: {resolved_path}"
        )
    return {
        key: value
        for key, value in section.items()
        if key in _BTC_RUNTIME_CONFIG_FIELDS
    }


def _resolve_btc_runtime_config_path(
    *,
    path: str | Path | None,
    instance_root: str | Path | None,
) -> Path | None:
    """Return the first existing BTC runtime config file, or None."""

    if path is not None:
        candidate = Path(path).expanduser()
        return candidate if candidate.is_file() else None
    if instance_root is not None:
        candidate = (
            Path(instance_root).expanduser() / DEFAULT_BTC_RUNTIME_CONFIG_RELPATH
        )
        if candidate.is_file():
            return candidate
    candidate = Path.cwd() / DEFAULT_BTC_RUNTIME_CONFIG_RELPATH
    return candidate if candidate.is_file() else None


def resolve_btc_runtime_config(
    *,
    btc_exe: str | Path | None = None,
    wine_prefix: str | Path | None = None,
    wine_executable: str | None = None,
    use_xvfb: bool | None = None,
    host_mode: str | None = None,
    instance_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> BTCRuntimeConfig:
    """Resolve BTC runtime settings for the current host.

    Precedence per field: explicit argument > environment variable > YAML
    config > discovery default.

    On WSL hosts an unresolved ``host_mode`` of ``"auto"`` auto-selects
    ``wsl-interop`` only when no Wine intent exists; supplying a Wine prefix
    or Wine executable (argument, ``FEMIC_BTC_WINEPREFIX``/``WINEPREFIX``/
    ``FEMIC_WINE_EXE``, or YAML) resolves ``auto`` to ``wine`` instead.

    Args:
        btc_exe: Explicit BatchTIPSY executable path.
        wine_prefix: Explicit Wine prefix directory.
        wine_executable: Explicit Wine executable path/name.
        use_xvfb: Explicit xvfb-run wrapping flag.
        host_mode: Explicit host mode (``auto``, ``windows``, ``wine``,
            ``wsl-interop``).
        instance_root: Directory whose ``config/`` may hold the runtime YAML.
        env: Environment mapping to consult (defaults to ``os.environ``).

    Returns:
        The resolved BTC runtime configuration.

    Raises:
        ValueError: when an environment boolean is not parseable, or when an
            explicitly requested host mode is impossible on this host.
    """
    env = os.environ if env is None else env
    yaml_config = load_btc_runtime_config(instance_root=instance_root)

    raw_batch_tipsy_exe = _first_set(
        btc_exe,
        env.get("FEMIC_BATCHTIPSY_EXE"),
        yaml_config.get("batch_tipsy_exe"),
    )
    raw_wine_prefix = _first_set(
        wine_prefix,
        env.get(FEMIC_BTC_WINEPREFIX),
        env.get("WINEPREFIX"),
        yaml_config.get("wine_prefix"),
    )
    raw_wine_executable = _first_set(
        wine_executable,
        env.get(FEMIC_WINE_EXE_ENV),
        yaml_config.get("wine_executable"),
    )
    raw_host_mode = _first_set(
        host_mode,
        env.get(FEMIC_BTC_HOST_MODE),
        yaml_config.get("host_mode"),
    )
    # Explicit Wine configuration (argument, environment, or YAML) implies
    # Wine intent: on WSL hosts an unresolved "auto" mode must pick Wine
    # rather than silently auto-selecting wsl-interop (M1).
    has_wine_intent = _has_wine_intent(raw_wine_prefix, raw_wine_executable)

    resolved_wine_prefix = _discover_wine_prefix()
    if raw_wine_prefix is not None:
        resolved_wine_prefix = _as_optional_path(raw_wine_prefix)
    resolved_wine_executable = _discover_wine_executable()
    if raw_wine_executable is not None:
        resolved_wine_executable = _as_optional_str(raw_wine_executable)

    return BTCRuntimeConfig(
        batch_tipsy_exe=_as_optional_path(raw_batch_tipsy_exe),
        wine_executable=resolved_wine_executable,
        wine_prefix=resolved_wine_prefix,
        use_xvfb=_resolve_use_xvfb(
            use_xvfb=use_xvfb,
            env=env,
            yaml_value=yaml_config.get("use_xvfb"),
        ),
        host_mode=resolve_host_mode(
            requested=None if raw_host_mode is None else str(raw_host_mode),
            env=env,
            wine_intent=has_wine_intent,
        ),
        xvfb_executable=find_xvfb_run(),
    )


def _first_set(*values: object) -> object:
    """Return the first non-None value, or None when every value is None."""

    for value in values:
        if value is not None:
            return value
    return None


def _as_optional_path(value: object) -> Path | None:
    """Normalize a path-like value, treating empty text as unset."""

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Path(text).expanduser()


def _as_optional_str(value: object) -> str | None:
    """Normalize a string value, treating empty text as unset."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_use_xvfb(
    *,
    use_xvfb: bool | None,
    env: Mapping[str, str],
    yaml_value: object,
) -> bool:
    """Resolve the xvfb flag using arg > env > YAML > False precedence."""

    if use_xvfb is not None:
        return bool(use_xvfb)
    raw_env = env.get(FEMIC_BTC_USE_XVFB)
    if raw_env is not None:
        return _parse_bool_env(raw_env)
    if yaml_value is not None:
        return bool(yaml_value)
    return False


def _parse_bool_env(value: str) -> bool:
    """Parse a FEMIC boolean environment value, failing loud on junk.

    Args:
        value: Raw environment value for ``FEMIC_BTC_USE_XVFB``.

    Returns:
        True for ``1``/``true``/``yes``; False for ``0``/``false``/``no``.

    Raises:
        ValueError: when the value is not a recognized boolean token.
    """

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(
        f"Invalid boolean for {FEMIC_BTC_USE_XVFB}: {value!r} "
        "(expected '1', 'true', 'yes', '0', 'false', or 'no')"
    )


def _discover_wine_prefix() -> Path | None:
    """Return the first existing FEMIC BTC Wine prefix candidate.

    Scans ``~/.wine-tipsy64`` then ``~/.wine-tipsy47`` for a usable
    ``drive_c`` directory.

    Returns:
        The first candidate prefix containing a ``drive_c`` directory, or
        None when no candidate exists.
    """

    for name in _WINE_PREFIX_CANDIDATE_NAMES:
        candidate = Path.home() / name
        if (candidate / "drive_c").is_dir():
            return candidate
    return None


def _discover_wine_executable() -> str | None:
    """Return the discovered Wine executable, or None when unavailable.

    Discovery is deliberately non-fatal: a missing Wine binary is reported at
    preflight/run time, not while resolving configuration.

    Returns:
        The resolved Wine executable path/name, or None when Wine cannot be
        discovered (or discovery itself fails).
    """

    try:
        from femic.patchworks_runtime import find_wine_executable
    except ImportError:
        return None
    try:
        return find_wine_executable()
    except Exception:
        return None
