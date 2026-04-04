"""BC TSR site crawling and canonical TSA document indexing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from pathlib import Path, PurePosixPath
import json
import re
from typing import Callable
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_TSR_LANDING_URL = (
    "https://www2.gov.bc.ca/gov/content/industry/forestry/managing-our-forest-resources/"
    "timber-supply-review-and-allowable-annual-cut"
)
DEFAULT_TSR_PUBLISH_ROOT_URL = (
    "https://www.for.gov.bc.ca/ftp/HTS/external/!publish/Timber_Supply_Review/"
)
DEFAULT_TSR_TSA_ROOT_URL = urljoin(DEFAULT_TSR_PUBLISH_ROOT_URL, "TSA/")

_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (compatible; FEMIC/0.1; +https://github.com/UBC-FRESH/femic)"
)
_LANDING_LINK_RE = re.compile(r'https://[^"\']+')
_DIRECTORY_ENTRY_RE = re.compile(
    r"(?P<timestamp>\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)\s+"
    r"(?P<size>&lt;dir&gt;|[\d,]+)\s+<A HREF=\"(?P<href>[^\"]+)\">(?P<name>[^<]+)</A><br>",
    re.IGNORECASE,
)
_TSA_DIR_RE = re.compile(r"^(?P<name>.+)_(?P<code>\d+)$")
_CYCLE_YEAR_RE = re.compile(r"TSR_(?P<year>\d{4})", re.IGNORECASE)
_PDF_SUFFIX_RE = re.compile(r"\.pdf$", re.IGNORECASE)


class TsrCatalogError(RuntimeError):
    """Raised when TSR pages cannot be crawled or parsed."""


FetchText = Callable[[str], str]


@dataclass(frozen=True)
class TsrLandingResource:
    """One general TSR landing-page resource."""

    title: str
    url: str
    document_type: str

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "document_type": self.document_type,
        }


@dataclass(frozen=True)
class TsrCycleRecord:
    """One TSA TSR cycle directory."""

    cycle_label: str
    cycle_year: int | None
    url: str
    listed_modified_raw: str
    document_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "cycle_label": self.cycle_label,
            "cycle_year": self.cycle_year,
            "url": self.url,
            "listed_modified_raw": self.listed_modified_raw,
            "document_count": self.document_count,
        }


@dataclass(frozen=True)
class TsaRegistryRecord:
    """Canonical metadata for one TSA folder in the TSR corpus."""

    tsa_id: str
    tsa_code: str
    tsa_name: str
    tsa_directory_name: str
    url: str
    listed_modified_raw: str
    cycles: tuple[TsrCycleRecord, ...]

    @property
    def document_count(self) -> int:
        return sum(cycle.document_count for cycle in self.cycles)

    def to_dict(self) -> dict[str, object]:
        return {
            "tsa_id": self.tsa_id,
            "tsa_code": self.tsa_code,
            "tsa_name": self.tsa_name,
            "tsa_directory_name": self.tsa_directory_name,
            "url": self.url,
            "listed_modified_raw": self.listed_modified_raw,
            "cycle_count": len(self.cycles),
            "document_count": self.document_count,
            "cycles": [cycle.to_dict() for cycle in self.cycles],
        }


@dataclass(frozen=True)
class TsrDocumentRecord:
    """One discovered TSR document file under a TSA cycle."""

    tsa_id: str
    tsa_code: str
    tsa_name: str
    cycle_label: str
    cycle_year: int | None
    title: str
    document_type: str
    file_name: str
    file_extension: str
    relative_path: str
    url: str
    listed_modified_raw: str
    size_bytes: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "tsa_id": self.tsa_id,
            "tsa_code": self.tsa_code,
            "tsa_name": self.tsa_name,
            "cycle_label": self.cycle_label,
            "cycle_year": self.cycle_year,
            "title": self.title,
            "document_type": self.document_type,
            "file_name": self.file_name,
            "file_extension": self.file_extension,
            "relative_path": self.relative_path,
            "url": self.url,
            "listed_modified_raw": self.listed_modified_raw,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class TsrIndexResult:
    """Canonical TSR crawl result for TSA surfaces."""

    generated_utc: str
    landing_url: str
    publish_root_url: str
    tsa_root_url: str
    landing_resources: tuple[TsrLandingResource, ...]
    registry: tuple[TsaRegistryRecord, ...]
    documents: tuple[TsrDocumentRecord, ...]

    def registry_payload(self) -> dict[str, object]:
        return {
            "generated_utc": self.generated_utc,
            "landing_url": self.landing_url,
            "publish_root_url": self.publish_root_url,
            "tsa_root_url": self.tsa_root_url,
            "landing_resources": [item.to_dict() for item in self.landing_resources],
            "tsa_count": len(self.registry),
            "document_count": len(self.documents),
            "tsas": [record.to_dict() for record in self.registry],
        }

    def documents_payload(self) -> dict[str, object]:
        return {
            "generated_utc": self.generated_utc,
            "tsa_root_url": self.tsa_root_url,
            "document_count": len(self.documents),
            "documents": [record.to_dict() for record in self.documents],
        }


@dataclass(frozen=True)
class TsrWrittenIndex:
    """Paths written by the canonical TSR index exporter."""

    output_root: Path
    registry_path: Path
    documents_path: Path
    tsa_count: int
    document_count: int


@dataclass(frozen=True)
class _DirectoryEntry:
    name: str
    url: str
    listed_modified_raw: str
    is_directory: bool
    size_bytes: int | None


@dataclass(frozen=True)
class _TsaIdentity:
    tsa_id: str
    tsa_code: str
    tsa_name: str
    directory_name: str


def _default_fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": _BROWSER_USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_directory_entries(
    html_text: str, *, base_url: str
) -> tuple[_DirectoryEntry, ...]:
    entries: list[_DirectoryEntry] = []
    for match in _DIRECTORY_ENTRY_RE.finditer(html_text):
        raw_name = unescape(match.group("name")).strip()
        if raw_name == "[To Parent Directory]":
            continue
        raw_href = unescape(match.group("href")).strip()
        raw_size = unescape(match.group("size")).strip()
        url = urljoin(base_url, raw_href)
        is_directory = raw_size.casefold() == "<dir>"
        size_bytes = None if is_directory else int(raw_size.replace(",", ""))
        entries.append(
            _DirectoryEntry(
                name=raw_name,
                url=url,
                listed_modified_raw=match.group("timestamp").strip(),
                is_directory=is_directory,
                size_bytes=size_bytes,
            )
        )
    return tuple(entries)


def _infer_landing_resource_title(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    name = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE)
    return name.replace("_", " ").strip()


def _infer_landing_document_type(url: str) -> str:
    lowered = url.casefold()
    if "tsr_timber_supply_areas" in lowered:
        return "tsa_guide"
    if "tsr_tree_farm_licences" in lowered:
        return "tfl_guide"
    if "backgrounder" in lowered:
        return "backgrounder"
    if "document_descriptions" in lowered:
        return "document_descriptions"
    return "supporting_document"


def _extract_landing_resources(html_text: str) -> tuple[TsrLandingResource, ...]:
    resources: list[TsrLandingResource] = []
    seen: set[str] = set()
    for match in _LANDING_LINK_RE.finditer(html_text):
        url = unescape(match.group(0))
        normalized = url.rstrip(".,);")
        if normalized in seen:
            continue
        seen.add(normalized)
        lowered = normalized.casefold()
        if "timber_supply_review" in lowered or lowered.endswith(".pdf"):
            resources.append(
                TsrLandingResource(
                    title=_infer_landing_resource_title(normalized),
                    url=normalized,
                    document_type=_infer_landing_document_type(normalized),
                )
            )
    return tuple(resources)


def _parse_tsa_identity(directory_name: str) -> _TsaIdentity:
    match = _TSA_DIR_RE.match(directory_name)
    if not match:
        raise TsrCatalogError(
            f"Could not parse TSA identity from directory name: {directory_name}"
        )
    tsa_name = match.group("name").replace("_", " ").strip()
    tsa_code = match.group("code")
    tsa_id = f"tsa_{tsa_code}"
    return _TsaIdentity(
        tsa_id=tsa_id,
        tsa_code=tsa_code,
        tsa_name=tsa_name,
        directory_name=directory_name,
    )


def _cycle_year(cycle_label: str) -> int | None:
    match = _CYCLE_YEAR_RE.search(cycle_label)
    return int(match.group("year")) if match else None


def _infer_document_type(relative_path: PurePosixPath) -> str:
    lowered = relative_path.as_posix().casefold()
    name = relative_path.name.casefold()
    if "_dpkg_" in lowered or "data_package" in lowered or "data package" in lowered:
        return "data_package"
    if "_ra_" in lowered or "rationale" in lowered:
        return "rationale"
    if "_pdp_" in lowered or "discussion" in lowered:
        return "discussion_paper"
    if name == "readme.txt":
        return "readme"
    if name.endswith(".pdf"):
        return "supporting_document"
    return "document"


def _humanize_title(name: str) -> str:
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", name)
    return re.sub(r"[_\-]+", " ", stem).strip()


def _collect_cycle_documents(
    *,
    fetch_text: FetchText,
    tsa: _TsaIdentity,
    cycle_label: str,
    cycle_year: int | None,
    cycle_url: str,
    relative_prefix: PurePosixPath,
) -> tuple[TsrDocumentRecord, ...]:
    html_text = fetch_text(cycle_url)
    entries = _parse_directory_entries(html_text, base_url=cycle_url)
    documents: list[TsrDocumentRecord] = []
    for entry in entries:
        relative_path = relative_prefix / entry.name
        if entry.is_directory:
            documents.extend(
                _collect_cycle_documents(
                    fetch_text=fetch_text,
                    tsa=tsa,
                    cycle_label=cycle_label,
                    cycle_year=cycle_year,
                    cycle_url=entry.url,
                    relative_prefix=relative_path,
                )
            )
            continue
        file_extension = PurePosixPath(entry.name).suffix.lower().lstrip(".")
        documents.append(
            TsrDocumentRecord(
                tsa_id=tsa.tsa_id,
                tsa_code=tsa.tsa_code,
                tsa_name=tsa.tsa_name,
                cycle_label=cycle_label,
                cycle_year=cycle_year,
                title=_humanize_title(entry.name),
                document_type=_infer_document_type(relative_path),
                file_name=entry.name,
                file_extension=file_extension,
                relative_path=relative_path.as_posix(),
                url=entry.url,
                listed_modified_raw=entry.listed_modified_raw,
                size_bytes=entry.size_bytes,
            )
        )
    return tuple(documents)


def index_tsr_tsa_surfaces(
    *,
    landing_url: str = DEFAULT_TSR_LANDING_URL,
    publish_root_url: str = DEFAULT_TSR_PUBLISH_ROOT_URL,
    tsa_root_url: str = DEFAULT_TSR_TSA_ROOT_URL,
    fetch_text: FetchText | None = None,
) -> TsrIndexResult:
    """Crawl BC TSR TSA surfaces into canonical registry and document metadata."""

    fetcher = fetch_text or _default_fetch_text
    try:
        landing_html = fetcher(landing_url)
        tsa_root_html = fetcher(tsa_root_url)
    except Exception as exc:  # pragma: no cover - thin network wrapper
        raise TsrCatalogError(
            f"Failed to fetch TSR landing/index pages: {exc}"
        ) from exc

    landing_resources = _extract_landing_resources(landing_html)
    tsa_entries = tuple(
        entry
        for entry in _parse_directory_entries(tsa_root_html, base_url=tsa_root_url)
        if entry.is_directory
    )

    registry: list[TsaRegistryRecord] = []
    documents: list[TsrDocumentRecord] = []
    for tsa_entry in tsa_entries:
        tsa_identity = _parse_tsa_identity(tsa_entry.name)
        tsa_html = fetcher(tsa_entry.url)
        cycle_entries = tuple(
            entry
            for entry in _parse_directory_entries(tsa_html, base_url=tsa_entry.url)
            if entry.is_directory
        )
        cycles: list[TsrCycleRecord] = []
        for cycle_entry in cycle_entries:
            cycle_year = _cycle_year(cycle_entry.name)
            cycle_documents = _collect_cycle_documents(
                fetch_text=fetcher,
                tsa=tsa_identity,
                cycle_label=cycle_entry.name,
                cycle_year=cycle_year,
                cycle_url=cycle_entry.url,
                relative_prefix=PurePosixPath(cycle_entry.name),
            )
            documents.extend(cycle_documents)
            cycles.append(
                TsrCycleRecord(
                    cycle_label=cycle_entry.name,
                    cycle_year=cycle_year,
                    url=cycle_entry.url,
                    listed_modified_raw=cycle_entry.listed_modified_raw,
                    document_count=len(cycle_documents),
                )
            )
        registry.append(
            TsaRegistryRecord(
                tsa_id=tsa_identity.tsa_id,
                tsa_code=tsa_identity.tsa_code,
                tsa_name=tsa_identity.tsa_name,
                tsa_directory_name=tsa_identity.directory_name,
                url=tsa_entry.url,
                listed_modified_raw=tsa_entry.listed_modified_raw,
                cycles=tuple(sorted(cycles, key=lambda item: item.cycle_label)),
            )
        )

    return TsrIndexResult(
        generated_utc=datetime.now(UTC).isoformat(),
        landing_url=landing_url,
        publish_root_url=publish_root_url,
        tsa_root_url=tsa_root_url,
        landing_resources=landing_resources,
        registry=tuple(
            sorted(registry, key=lambda item: (int(item.tsa_code), item.tsa_name))
        ),
        documents=tuple(
            sorted(
                documents,
                key=lambda item: (
                    int(item.tsa_code),
                    item.cycle_year or 0,
                    item.relative_path,
                ),
            )
        ),
    )


def write_tsr_index(result: TsrIndexResult, output_root: Path) -> TsrWrittenIndex:
    """Write canonical TSR registry and document inventory JSON outputs."""

    output_root.mkdir(parents=True, exist_ok=True)
    registry_path = output_root / "tsa_registry.json"
    documents_path = output_root / "tsa_documents.json"
    registry_path.write_text(
        json.dumps(result.registry_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    documents_path.write_text(
        json.dumps(result.documents_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return TsrWrittenIndex(
        output_root=output_root,
        registry_path=registry_path,
        documents_path=documents_path,
        tsa_count=len(result.registry),
        document_count=len(result.documents),
    )
