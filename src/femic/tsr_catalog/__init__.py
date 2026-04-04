"""BC TSR document indexing helpers."""

from __future__ import annotations

from .cache import (
    TsrCacheError,
    TsrCacheFailure,
    TsrDownloadedPdf,
    TsrFetchResult,
    TsrInventoryDocument,
    fetch_tsr_pdfs,
    load_tsr_document_inventory,
)
from .crawl import (
    DEFAULT_TSR_LANDING_URL,
    DEFAULT_TSR_PUBLISH_ROOT_URL,
    DEFAULT_TSR_TSA_ROOT_URL,
    TsaRegistryRecord,
    TsrCatalogError,
    TsrCycleRecord,
    TsrDocumentRecord,
    TsrIndexResult,
    TsrLandingResource,
    TsrWrittenIndex,
    index_tsr_tsa_surfaces,
    write_tsr_index,
)

__all__ = [
    "DEFAULT_TSR_LANDING_URL",
    "DEFAULT_TSR_PUBLISH_ROOT_URL",
    "DEFAULT_TSR_TSA_ROOT_URL",
    "TsaRegistryRecord",
    "TsrCacheError",
    "TsrCacheFailure",
    "TsrCatalogError",
    "TsrCycleRecord",
    "TsrDownloadedPdf",
    "TsrDocumentRecord",
    "TsrFetchResult",
    "TsrInventoryDocument",
    "TsrIndexResult",
    "TsrLandingResource",
    "TsrWrittenIndex",
    "fetch_tsr_pdfs",
    "index_tsr_tsa_surfaces",
    "load_tsr_document_inventory",
    "write_tsr_index",
]
