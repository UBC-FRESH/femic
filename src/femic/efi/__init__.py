"""EFI model application and backtesting.

The contracts package defines the model card and the coefficients document.
This package applies the linear form, checks applicability, and reports a
backtest. It is the execution layer, not a new statistical method.
"""

from femic.efi.application import (
    EFI_COEFFICIENTS_SCHEMA_VERSION,
    EFIApplicationError,
    LinearEFIModel,
    apply_linear_model,
    backtest_linear_model,
    load_linear_efi_model,
)

__all__ = [
    "EFI_COEFFICIENTS_SCHEMA_VERSION",
    "EFIApplicationError",
    "LinearEFIModel",
    "apply_linear_model",
    "backtest_linear_model",
    "load_linear_efi_model",
]
