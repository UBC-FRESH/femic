"""Windows FAN$IER batch-runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any


DEFAULT_FANSIER_EXE_PATH = Path(r"C:\Program Files\TIPSY 4.7\Fansier\Fansier.exe")
DEFAULT_FANSIER_LOG_DIR = Path("tipsy_io/logs")
DEFAULT_FANSIER_BATCH_OUTPUT_DIR = Path("tipsy_io/logs/fansier_batch")
DEFAULT_FANSIER_REPORT_TYPE = "txt"
DEFAULT_FANSIER_DISCOUNT_NAME = "FEMIC Raw 0%"
DEFAULT_FANSIER_DEFAULT_DISCOUNT_NAME = "Fansier Defaults   (Discount Rate = 2%)"
DEFAULT_FANSIER_PRODUCT_NAME = "Lumber & Mill Residues (All Grades) (1)"
DEFAULT_FANSIER_AGE_NAME = "Max MAI (12.5)"
_SELECTION_SETTLE_SECONDS = 0.8
_CALC_LABEL_RE = re.compile(
    r"(?P<regimes>[\d,]+)\s+Regimes\s+X\s+(?P<settings>[\d,]+)\s+Assumptions\s+X\s+"
    r"(?P<products>[\d,]+)\s+Products\s+X\s+(?P<ages>[\d,]+)\s+Ages\s+=\s+"
    r"(?P<calculations>[\d,]+)\s+calculations"
)


class FansierRuntimeError(RuntimeError):
    """Raised when unattended FAN$IER automation fails."""


@dataclass(frozen=True)
class FansierCalculationCounts:
    """Parsed counts from FAN$IER batch-form status text."""

    regimes: int
    settings: int
    products: int
    ages: int
    calculations: int


@dataclass(frozen=True)
class FansierBatchRunResult:
    """Outputs from one unattended FAN$IER batch run."""

    run_id: str
    fansier_exe_path: Path
    rgm_path: Path
    output_dir: Path
    report_type: str
    long_report: bool
    product_cols: bool
    activity_cols: bool
    discount_name: str
    product_count: int
    age_count: int
    calculations: int
    first_output_path: Path
    output_files: tuple[Path, ...]
    manifest_path: Path
    status_label: str


def parse_fansier_calculation_counts(text: str) -> FansierCalculationCounts | None:
    """Parse the FAN$IER batch-form calculations label."""

    match = _CALC_LABEL_RE.search(text.strip())
    if not match:
        return None

    def _as_int(name: str) -> int:
        return int(match.group(name).replace(",", ""))

    return FansierCalculationCounts(
        regimes=_as_int("regimes"),
        settings=_as_int("settings"),
        products=_as_int("products"),
        ages=_as_int("ages"),
        calculations=_as_int("calculations"),
    )


def _build_fansier_batch_manifest_payload(
    *,
    result: FansierBatchRunResult,
) -> dict[str, Any]:
    return {
        "run_id": result.run_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "mode": "fansier_batch",
        "inputs": {
            "fansier_exe_path": str(result.fansier_exe_path),
            "rgm_path": str(result.rgm_path),
            "report_type": result.report_type,
            "long_report": result.long_report,
            "product_cols": result.product_cols,
            "activity_cols": result.activity_cols,
            "discount_name": result.discount_name,
        },
        "outputs": {
            "output_dir": str(result.output_dir),
            "first_output_path": str(result.first_output_path),
            "output_file_count": len(result.output_files),
            "output_files": [str(path) for path in result.output_files],
            "product_count": result.product_count,
            "age_count": result.age_count,
            "calculations": result.calculations,
            "status_label": result.status_label,
        },
    }


def _ensure_windows_host() -> None:
    if not sys.platform.startswith("win"):
        raise FansierRuntimeError(
            "FAN$IER unattended automation currently requires a Windows host."
        )


def _load_pywinauto() -> tuple[Any, Any]:
    try:
        from pywinauto import Application, Desktop  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised by import failure
        raise FansierRuntimeError(
            "pywinauto/comtypes are required for FAN$IER automation on Windows."
        ) from exc
    return Application, Desktop


def _wait_for_window(app: Any, title_re: str, timeout: float = 20.0) -> Any:
    end = time.time() + timeout
    while time.time() < end:
        try:
            win = app.window(title_re=title_re)
            if win.exists(timeout=0.5):
                return win
        except Exception:
            pass
        time.sleep(0.2)
    raise FansierRuntimeError(f"Timed out waiting for window {title_re!r}")


def _set_registry_defaults(
    *,
    run_id: str,
    out_dir: Path,
    report_type: str,
    short_report: bool,
    long_report: bool,
    product_cols: bool,
    activity_cols: bool,
) -> None:
    ps = rf"""
$key = 'HKCU:\Software\Ministry of Forests\FANSIER'
New-Item -Path $key -Force | Out-Null
Set-ItemProperty -Path $key -Name 'RunIdentifier' -Value '{run_id}'
Set-ItemProperty -Path $key -Name 'BatchPath' -Value '{str(out_dir)}\'
Set-ItemProperty -Path $key -Name 'ReportType' -Value '{report_type}'
Set-ItemProperty -Path $key -Name 'LongReport' -Value '{str(long_report)}'
Set-ItemProperty -Path $key -Name 'ShortReport' -Value '{str(short_report)}'
Set-ItemProperty -Path $key -Name 'ShortReportProductCols' -Value '{str(product_cols)}'
Set-ItemProperty -Path $key -Name 'ShortReportActivityCols' -Value '{str(activity_cols)}'
Set-ItemProperty -Path $key -Name 'ThousandSeparator' -Value 'False'
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def _start_fresh_fansier(*, fansier_exe_path: Path) -> Any:
    Application, _ = _load_pywinauto()
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Process Fansier -ErrorAction SilentlyContinue | Stop-Process -Force; exit 0",
        ],
        check=True,
    )
    time.sleep(1.0)
    subprocess.Popen([str(fansier_exe_path)])
    app = Application(backend="uia").connect(path=str(fansier_exe_path), timeout=20)
    _wait_for_window(app, r"FANSIER.*", timeout=20.0)
    return app


def _open_batch_from_main(app: Any) -> Any:
    for window in app.windows():
        try:
            if window.window_text().startswith("Batch"):
                return app.window(handle=window.handle)
        except Exception:
            pass
    main = _wait_for_window(app, r"FANSIER.*", timeout=20.0)
    main.set_focus()
    time.sleep(0.2)
    toolbar = main.child_window(
        auto_id="tooMain", control_type="ToolBar"
    ).wrapper_object()
    batch_btn = [
        child for child in toolbar.children() if child.window_text() == "Batch Process"
    ][0]
    end = time.time() + 15.0
    while time.time() < end:
        try:
            batch_btn.click_input()
        except Exception:
            try:
                batch_btn.click()
            except Exception:
                pass
        time.sleep(0.5)
        for window in app.windows():
            try:
                if window.window_text().startswith("Batch"):
                    return app.window(handle=window.handle)
            except Exception:
                pass
    raise FansierRuntimeError("Timed out waiting for Batch window after toolbar click")


def _load_discount_assumptions_from_file(app: Any, *, discount_dis_path: Path) -> None:
    _, Desktop = _load_pywinauto()
    if not discount_dis_path.exists():
        raise FansierRuntimeError(
            f"Discount assumptions file not found: {discount_dis_path}"
        )
    main = _wait_for_window(app, r"FANSIER.*", timeout=20.0)
    main.set_focus()
    discount_menu = None
    for item in main.descendants(control_type="MenuItem"):
        if item.window_text() == "Discount Assumptions":
            discount_menu = item
            break
    if discount_menu is None:
        raise FansierRuntimeError("Could not find FAN$IER Discount Assumptions menu")
    discount_menu.click_input()
    time.sleep(0.5)
    for item in main.descendants(control_type="MenuItem"):
        if item.window_text() == "Load Discount Assumptions...":
            item.click_input()
            break
    else:
        raise FansierRuntimeError("Could not find Load Discount Assumptions menu item")
    dlg = Desktop(backend="win32").window(
        title="Load Discount Assumptions", class_name="#32770"
    )
    dlg.wait("exists enabled visible ready", timeout=10)
    dlg.child_window(class_name="Edit", control_id=1148).wrapper_object().set_edit_text(
        str(discount_dis_path)
    )
    dlg.child_window(
        title="&Open", class_name="Button", control_id=1
    ).wrapper_object().click()
    time.sleep(1.0)


def _load_regime_via_dialog(batch: Any, *, rgm_path: Path) -> None:
    _, Desktop = _load_pywinauto()
    add = batch.child_window(auto_id="cmdAddRgm").wrapper_object()
    dlg = None
    end = time.time() + 15.0
    while time.time() < end:
        batch.set_focus()
        add.click_input()
        time.sleep(0.8)
        try:
            candidate = Desktop(backend="win32").window(
                title="Open", class_name="#32770"
            )
            candidate.wait("exists enabled visible ready", timeout=1.0)
            dlg = candidate
            break
        except Exception:
            pass
    if dlg is None:
        raise FansierRuntimeError("Timed out waiting for regime-file Open dialog")
    dlg.child_window(class_name="Edit", control_id=1148).wrapper_object().set_edit_text(
        str(rgm_path)
    )
    time.sleep(0.2)
    dlg.child_window(
        title="&Open", class_name="Button", control_id=1
    ).wrapper_object().click()
    regime_name = rgm_path.name
    end = time.time() + 20.0
    while time.time() < end:
        try:
            regime_list = batch.child_window(auto_id="lstRegime").wrapper_object()
            names = [
                item.window_text()
                for item in regime_list.descendants(control_type="ListItem")
            ]
            if regime_name in names:
                return
        except Exception:
            pass
        time.sleep(0.3)
    raise FansierRuntimeError(
        f"Timed out waiting for {regime_name!r} in batch regime list"
    )


def _toggle_item_state(item: Any, desired: bool) -> None:
    current = bool(item.get_toggle_state())
    if current == desired:
        return
    for _ in range(3):
        try:
            item.toggle()
        except Exception:
            try:
                item.click()
            except Exception:
                item.invoke()
        time.sleep(0.2)
        current = bool(item.get_toggle_state())
        if current == desired:
            return
    raise FansierRuntimeError(f"Could not set {item.window_text()!r} to {desired}")


def _toggle_exact_item(list_auto_id: str, item_name: str, win: Any) -> str:
    _wait_for_toggle_item(list_auto_id, item_name, win)
    for _ in range(5):
        for item in _toggle_items(list_auto_id, win):
            desired = item.window_text() == item_name
            _toggle_item_state(item, desired)
        _wait_for_batch_sync(win, timeout=10.0)
        for item in _toggle_items(list_auto_id, win):
            if item.window_text() == item_name and bool(item.get_toggle_state()):
                return item_name
    raise FansierRuntimeError(f"Could not set {item_name!r} in {list_auto_id}")


def _toggle_items(list_auto_id: str, win: Any) -> list[Any]:
    listview = win.child_window(auto_id=list_auto_id).wrapper_object()
    return list(listview.descendants(control_type="CheckBox"))


def _wait_for_toggle_item(
    list_auto_id: str, item_name: str, win: Any, timeout: float = 15.0
) -> None:
    end = time.time() + timeout
    while time.time() < end:
        for item in _toggle_items(list_auto_id, win):
            if item.window_text() == item_name:
                return
        time.sleep(0.2)
    raise FansierRuntimeError(f"Timed out waiting for {item_name!r} in {list_auto_id}")


def _checked_toggle_count(list_auto_id: str, win: Any) -> int:
    return sum(
        bool(item.get_toggle_state()) for item in _toggle_items(list_auto_id, win)
    )


def _current_batch_counts(win: Any) -> tuple[int, int, int]:
    return (
        _checked_toggle_count("lstSettings", win),
        _checked_toggle_count("chkProduct", win),
        _checked_toggle_count("chkAge", win),
    )


def _wait_for_batch_sync(win: Any, timeout: float = 10.0) -> None:
    end = time.time() + timeout
    last_signature = None
    stable_since = None
    last_label = ""
    while time.time() < end:
        actual = _current_batch_counts(win)
        parsed = parse_fansier_calculation_counts(
            win.child_window(auto_id="lblRuns").wrapper_object().window_text()
        )
        last_label = win.child_window(auto_id="lblRuns").wrapper_object().window_text()
        signature = (
            actual,
            None if parsed is None else (parsed.settings, parsed.products, parsed.ages),
            win.child_window(auto_id="cmdBatch").wrapper_object().is_enabled(),
        )
        now = time.time()
        if signature != last_signature:
            last_signature = signature
            stable_since = now
        counts_match = (
            parsed is not None
            and (
                parsed.settings,
                parsed.products,
                parsed.ages,
            )
            == actual
        )
        if (
            counts_match
            and stable_since is not None
            and (now - stable_since) >= _SELECTION_SETTLE_SECONDS
        ):
            return
        time.sleep(0.2)
    raise FansierRuntimeError(
        f"Batch form did not synchronize; actual={_current_batch_counts(win)!r}; "
        f"parsed={parse_fansier_calculation_counts(last_label)!r}; lblRuns={last_label!r}"
    )


def _invoke_list_context_action(list_auto_id: str, action_text: str, win: Any) -> None:
    listbox = win.child_window(auto_id=list_auto_id).wrapper_object()
    listbox.right_click_input(coords=(20, 20))
    end = time.time() + 10.0
    while time.time() < end:
        for item in win.descendants(control_type="MenuItem"):
            try:
                if item.window_text() == action_text:
                    item.click_input()
                    time.sleep(0.5)
                    return
            except Exception:
                pass
        time.sleep(0.2)
    raise FansierRuntimeError(
        f"Timed out trying to invoke {action_text!r} on {list_auto_id!r}"
    )


def _choose_all_toggles(list_auto_id: str, win: Any) -> list[str]:
    for _ in range(3):
        _invoke_list_context_action(list_auto_id, "Check All", win)
        _wait_for_batch_sync(win, timeout=12.0)
        items = _toggle_items(list_auto_id, win)
        if items and all(bool(item.get_toggle_state()) for item in items):
            return [item.window_text() for item in items]
    raise FansierRuntimeError(f"Could not set all toggles in {list_auto_id}")


def _select_regime(win: Any, regime_name: str) -> None:
    regime_list = win.child_window(auto_id="lstRegime").wrapper_object()
    end = time.time() + 15.0
    while time.time() < end:
        for item in regime_list.descendants(control_type="ListItem"):
            if item.window_text() == regime_name:
                for _ in range(5):
                    item.click_input()
                    time.sleep(0.4)
                    try:
                        if item.iface_selection_item.CurrentIsSelected:
                            return
                    except Exception:
                        return
        time.sleep(0.2)
    raise FansierRuntimeError(
        f"Target regime {regime_name!r} is not loaded in batch mode"
    )


def _ensure_checkbox_state(auto_id: str, desired: bool, win: Any) -> None:
    ctrl = win.child_window(auto_id=auto_id).wrapper_object()
    for _ in range(5):
        _toggle_item_state(ctrl, desired)
        time.sleep(0.2)
        if bool(ctrl.get_toggle_state()) == desired:
            return
    raise FansierRuntimeError(f"Could not set checkbox {auto_id!r} to {desired}")


def _ensure_discount_profile(win: Any, profile_name: str) -> None:
    available = [item.window_text() for item in _toggle_items("lstSettings", win)]
    if profile_name in available:
        return

    win.set_focus()
    win.child_window(auto_id="cmdSetAdd").wrapper_object().click_input()
    dlg = win.child_window(
        title="Discount Assumptions", auto_id="frmDiscountAssumptions"
    )
    dlg.wait("exists enabled visible ready", timeout=10)
    for auto_id, value in [
        ("txtDiscountRate", "0.0"),
        ("txtReinvestment", "0.0"),
        ("txtSunkDeflationRate", "0.0"),
        ("txtRealPriceInc", "0.0"),
        ("txtRealCostInc", "0.0"),
        ("txtRealIncDuration", "0"),
    ]:
        edit = dlg.child_window(auto_id=auto_id).wrapper_object()
        edit.set_edit_text(value)
        time.sleep(0.1)
    for auto_id in ("chkSunkCosts", "chkFinancial", "chkFTG"):
        try:
            _ensure_checkbox_state(auto_id, False, dlg)
        except Exception:
            pass
    chk = dlg.child_window(auto_id="chkAutoName").wrapper_object()
    if not bool(chk.get_toggle_state()):
        chk.click_input()
        time.sleep(0.2)
    dlg.child_window(auto_id="txtName").wrapper_object().set_edit_text(profile_name)
    time.sleep(0.2)
    ok = dlg.child_window(auto_id="cmdOK").wrapper_object()
    try:
        ok.invoke()
    except Exception:
        ok.click()
    _wait_for_toggle_item("lstSettings", profile_name, win, timeout=10.0)


def _wait_for_batch_ready(
    win: Any,
    *,
    settings_count: int,
    product_count: int,
    age_count: int,
    timeout: float = 15.0,
) -> FansierCalculationCounts:
    end = time.time() + timeout
    last_runs = ""
    while time.time() < end:
        last_runs = win.child_window(auto_id="lblRuns").wrapper_object().window_text()
        parsed = parse_fansier_calculation_counts(last_runs)
        actual_settings, actual_products, actual_ages = _current_batch_counts(win)
        if (
            parsed is not None
            and actual_settings == settings_count
            and actual_products == product_count
            and actual_ages == age_count
            and (parsed.settings, parsed.products, parsed.ages)
            == (settings_count, product_count, age_count)
            and win.child_window(auto_id="cmdBatch").wrapper_object().is_enabled()
        ):
            return parsed
        time.sleep(0.2)
    raise FansierRuntimeError(
        f"Batch selection never stabilized; last lblRuns={last_runs!r}"
    )


def run_fansier_batch(
    *,
    rgm_path: Path,
    out_dir: Path = DEFAULT_FANSIER_BATCH_OUTPUT_DIR,
    log_dir: Path = DEFAULT_FANSIER_LOG_DIR,
    run_id: str,
    fansier_exe_path: Path = DEFAULT_FANSIER_EXE_PATH,
    discount_name: str = DEFAULT_FANSIER_DISCOUNT_NAME,
    discount_dis_path: Path | None = None,
    report_type: str = DEFAULT_FANSIER_REPORT_TYPE,
    long_report: bool = False,
    product_cols: bool = True,
    activity_cols: bool = False,
    select_all_products: bool = False,
    select_all_ages: bool = False,
    product_name: str = DEFAULT_FANSIER_PRODUCT_NAME,
    age_name: str = DEFAULT_FANSIER_AGE_NAME,
) -> FansierBatchRunResult:
    """Run unattended FAN$IER batch extraction on Windows."""

    _ensure_windows_host()
    if report_type not in {"txt", "csv", "pdf"}:
        raise FansierRuntimeError(
            f"Unsupported report type {report_type!r}; expected txt/csv/pdf."
        )

    resolved_rgm_path = rgm_path.expanduser().resolve()
    if not resolved_rgm_path.exists():
        raise FileNotFoundError(f"FAN$IER regime file not found: {resolved_rgm_path}")
    resolved_fansier_exe = fansier_exe_path.expanduser().resolve()
    if not resolved_fansier_exe.exists():
        raise FileNotFoundError(f"Fansier.exe not found: {resolved_fansier_exe}")

    resolved_out_dir = out_dir.expanduser().resolve()
    resolved_log_dir = log_dir.expanduser().resolve()
    resolved_out_dir.mkdir(parents=True, exist_ok=True)
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    target = resolved_out_dir / f"{run_id}.{report_type}"
    before_files = {path.name for path in resolved_out_dir.iterdir()}
    for path in (
        resolved_out_dir / "Report.csv",
        resolved_out_dir / "Report.txt",
        resolved_out_dir / "Report.pdf",
        target,
    ):
        if path.exists():
            path.unlink()

    short_report = not long_report
    _set_registry_defaults(
        run_id=run_id,
        out_dir=resolved_out_dir,
        report_type=report_type,
        short_report=short_report,
        long_report=long_report,
        product_cols=product_cols,
        activity_cols=activity_cols,
    )
    app = _start_fresh_fansier(fansier_exe_path=resolved_fansier_exe)
    if discount_dis_path is not None:
        resolved_discount_dis = discount_dis_path.expanduser().resolve()
        _load_discount_assumptions_from_file(
            app,
            discount_dis_path=resolved_discount_dis,
        )
    batch = _open_batch_from_main(app)
    _load_regime_via_dialog(batch, rgm_path=resolved_rgm_path)
    _select_regime(batch, resolved_rgm_path.name)
    if discount_dis_path is None:
        _ensure_discount_profile(batch, discount_name)
    chosen_discount = _toggle_exact_item("lstSettings", discount_name, batch)
    try:
        _ensure_checkbox_state("chkProdFirst", False, batch)
    except Exception:
        pass
    if select_all_products:
        chosen_products = _choose_all_toggles("chkProduct", batch)
    else:
        chosen_products = [_toggle_exact_item("chkProduct", product_name, batch)]
    if select_all_ages:
        chosen_ages = _choose_all_toggles("chkAge", batch)
    else:
        chosen_ages = [_toggle_exact_item("chkAge", age_name, batch)]
    chosen_discount = _toggle_exact_item("lstSettings", chosen_discount, batch)
    _ensure_checkbox_state("chkFormatComma", False, batch)
    counts = _wait_for_batch_ready(
        batch,
        settings_count=1,
        product_count=len(chosen_products),
        age_count=len(chosen_ages),
    )

    start = batch.child_window(auto_id="cmdBatch").wrapper_object()
    if not start.is_enabled():
        raise FansierRuntimeError("Start Batch did not become enabled")
    start.set_focus()
    try:
        start.click_input()
    except Exception:
        try:
            start.click()
        except Exception:
            start.invoke()

    end = time.time() + 120.0
    result_path: Path | None = None
    output_files: tuple[Path, ...] = ()
    status_label = ""
    while time.time() < end:
        status_label = (
            batch.child_window(auto_id="lblStatus").wrapper_object().window_text()
        )
        after_files = {path.name for path in resolved_out_dir.iterdir()}
        new_files = sorted(after_files - before_files)
        if status_label == "Done" and (target.exists() or new_files):
            output_files = tuple(sorted(resolved_out_dir.glob(f"*.{report_type}")))
            result_path = (
                target if target.exists() else (resolved_out_dir / new_files[0])
            )
            break
        time.sleep(0.5)
    if result_path is None:
        raise FansierRuntimeError(
            f"Timed out waiting for FAN$IER output in {resolved_out_dir}"
        )

    result = FansierBatchRunResult(
        run_id=run_id,
        fansier_exe_path=resolved_fansier_exe,
        rgm_path=resolved_rgm_path,
        output_dir=resolved_out_dir,
        report_type=report_type,
        long_report=long_report,
        product_cols=product_cols,
        activity_cols=activity_cols,
        discount_name=chosen_discount,
        product_count=len(chosen_products),
        age_count=len(chosen_ages),
        calculations=counts.calculations,
        first_output_path=result_path,
        output_files=output_files,
        manifest_path=(resolved_log_dir / f"fansier_batch_manifest-{run_id}.json"),
        status_label=status_label,
    )
    result.manifest_path.write_text(
        json.dumps(_build_fansier_batch_manifest_payload(result=result), indent=2),
        encoding="utf-8",
    )
    try:
        batch.close()
    except Exception:
        pass
    return result
