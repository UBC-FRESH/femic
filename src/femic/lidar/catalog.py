"""LidarBC source discovery, tile-index parsing, and AOI selection contracts.

The module treats the public LidarBC feature service as a discovery surface
only. It does not download tile bytes or reproject/resample source rasters.
Those boundaries belong to the later materialization and product phases.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

LIDARBC_SOURCE_ID = "lidarbc"
LIDARBC_TITLE = "LidarBC Open LiDAR Data Portal"
LIDARBC_PORTAL_URL = "https://lidar.gov.bc.ca/pages/download-discovery"
LIDARBC_CATALOGUE_URL = (
    "https://catalogue.data.gov.bc.ca/dataset/lidarbc-open-lidar-data-portal"
)
LIDARBC_INDEX_ITEM_URL = (
    "https://www.arcgis.com/home/item.html?id=5f6a1f31212a4cb2826743d2e52ef02a"
)
LIDARBC_FEATURE_SERVICE_URL = (
    "https://services6.arcgis.com/ubm4tcTYICKBpist/arcgis/rest/services/"
    "LiDAR_BC_S3_Public/FeatureServer"
)
LIDARBC_LICENCE_ID = "OGL-BC"
LIDARBC_LICENCE_URL = (
    "https://www2.gov.bc.ca/gov/content/data/open-data/open-government-licence-bc"
)
LIDARBC_NATIVE_CRS = "EPSG:3005"
LIDAR_SELECTION_SCHEMA_VERSION = "femic.lidar.selection.v1"

Bbox = tuple[float, float, float, float]


class LidarCatalogError(RuntimeError):
    """Raised when a LiDAR source contract or discovery request is invalid."""


@dataclass(frozen=True)
class LidarProductLayer:
    """One direct-download layer in a LiDAR source tile index."""

    product: str
    layer_id: int
    layer_name: str
    grid_scale: str | None

    def to_dict(self) -> dict[str, object]:
        """Return the layer as a JSON-serializable mapping."""

        return {
            "product": self.product,
            "layer_id": self.layer_id,
            "layer_name": self.layer_name,
            "grid_scale": self.grid_scale,
        }


LIDARBC_LAYERS: tuple[LidarProductLayer, ...] = (
    LidarProductLayer("dsm", 1, "LiDAR DSM Index 1:2,500", "1:2500"),
    LidarProductLayer("dsm", 2, "LiDAR DSM Index 1:10,000", "1:10000"),
    LidarProductLayer("dsm", 3, "LiDAR DSM Index 1:20,000", "1:20000"),
    LidarProductLayer("point_cloud", 4, "LiDAR Point Cloud Index", None),
    LidarProductLayer("dem", 5, "LiDAR DEM Index 1:2,500", "1:2500"),
    LidarProductLayer("dem", 6, "LiDAR DEM Index 1:20,000", "1:20000"),
)
LIDARBC_SUPPORTED_PRODUCTS: tuple[str, ...] = ("point_cloud", "dem", "dsm")
LIDARBC_DERIVED_PRODUCTS: tuple[str, ...] = ("chm",)


@dataclass(frozen=True)
class LidarSourceFamily:
    """An explicit public LiDAR source contract."""

    source_id: str
    title: str
    portal_url: str
    catalogue_url: str
    index_item_url: str
    feature_service_url: str
    licence_id: str
    licence_url: str
    native_crs: str
    supported_products: tuple[str, ...]
    derived_products: tuple[str, ...]
    metadata_caveat: str
    storage_boundary: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the source contract as a JSON-serializable mapping."""

        return {
            "source_id": self.source_id,
            "title": self.title,
            "portal_url": self.portal_url,
            "catalogue_url": self.catalogue_url,
            "index_item_url": self.index_item_url,
            "feature_service_url": self.feature_service_url,
            "licence_id": self.licence_id,
            "licence_url": self.licence_url,
            "native_crs": self.native_crs,
            "supported_products": list(self.supported_products),
            "derived_products": list(self.derived_products),
            "metadata_caveat": self.metadata_caveat,
            "storage_boundary": self.storage_boundary,
            "notes": list(self.notes),
        }


LIDARBC_SOURCE = LidarSourceFamily(
    source_id=LIDARBC_SOURCE_ID,
    title=LIDARBC_TITLE,
    portal_url=LIDARBC_PORTAL_URL,
    catalogue_url=LIDARBC_CATALOGUE_URL,
    index_item_url=LIDARBC_INDEX_ITEM_URL,
    feature_service_url=LIDARBC_FEATURE_SERVICE_URL,
    licence_id=LIDARBC_LICENCE_ID,
    licence_url=LIDARBC_LICENCE_URL,
    native_crs=LIDARBC_NATIVE_CRS,
    supported_products=LIDARBC_SUPPORTED_PRODUCTS,
    derived_products=LIDARBC_DERIVED_PRODUCTS,
    metadata_caveat=(
        "The BC Data Catalogue package wrapper records an Access Only licence "
        "because it fronts the ArcGIS portal application. The LidarBC portal, "
        "index item, and provincial open-data listing identify the data "
        "products as OGL-BC."
    ),
    storage_boundary=(
        "P79.1 discovery is metadata-only. Tile bytes require an explicit "
        "instance or external-data root in P79.2; no provincial mirror is "
        "created."
    ),
    notes=(
        (
            "CHM and canopy structure metrics are FEMIC-derived products, not "
            "separate LidarBC tile-index layers."
        ),
        (
            "Individual-tree products are consumed from LidarBC where a suitable "
            "public product exists; FEMIC does not invent a new segmentation "
            "algorithm in P79."
        ),
        (
            "Native CRS, vertical datum, spacing, point classes, and accuracy "
            "report links travel with each selected tile."
        ),
    ),
)


@dataclass(frozen=True)
class LidarTile:
    """One normalized tile-index record with provenance fields."""

    source_id: str
    product: str
    layer_id: int
    object_id: int
    filename: str
    maptile: str | None
    storage_path: str | None
    download_url: str | None
    accuracy_report_url: str | None
    info_file: str | None
    grid_scale: str | None
    acquisition_year: int | None
    projection: str | None
    spacing: str | None
    point_density_ppm2: int | None
    contract_id: str | None
    operator_name: str | None
    operator_number: str | None
    vertical_datum: str | None
    point_format: str | None
    point_classes: tuple[int, ...]
    bbox_epsg3005: Bbox
    area_m2: float | None

    @property
    def tile_id(self) -> str:
        """Return a stable tile identity within the source index."""

        return f"{self.source_id}:{self.layer_id}:{self.object_id}"

    def to_dict(self) -> dict[str, object]:
        """Return the tile as a JSON-serializable mapping."""

        return {
            "tile_id": self.tile_id,
            "source_id": self.source_id,
            "product": self.product,
            "layer_id": self.layer_id,
            "object_id": self.object_id,
            "filename": self.filename,
            "maptile": self.maptile,
            "storage_path": self.storage_path,
            "download_url": self.download_url,
            "accuracy_report_url": self.accuracy_report_url,
            "info_file": self.info_file,
            "grid_scale": self.grid_scale,
            "acquisition_year": self.acquisition_year,
            "projection": self.projection,
            "spacing": self.spacing,
            "point_density_ppm2": self.point_density_ppm2,
            "contract_id": self.contract_id,
            "operator_name": self.operator_name,
            "operator_number": self.operator_number,
            "vertical_datum": self.vertical_datum,
            "point_format": self.point_format,
            "point_classes": list(self.point_classes),
            "bbox_epsg3005": list(self.bbox_epsg3005),
            "area_m2": self.area_m2,
        }


@dataclass(frozen=True)
class LidarTileSelection:
    """An AOI-scoped, provenance-carrying LiDAR tile selection manifest."""

    source: LidarSourceFamily
    generated_utc: str
    aoi_bbox_epsg3005: Bbox
    products: tuple[str, ...]
    tiles: tuple[LidarTile, ...]
    request_urls: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = LIDAR_SELECTION_SCHEMA_VERSION

    @property
    def tile_count(self) -> int:
        """Return the number of selected tiles."""

        return len(self.tiles)

    @property
    def total_area_m2(self) -> float:
        """Return the summed indexed tile area in square metres."""

        return sum(tile.area_m2 or 0.0 for tile in self.tiles)

    def to_dict(self) -> dict[str, object]:
        """Return the selection manifest as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "generated_utc": self.generated_utc,
            "source": self.source.to_dict(),
            "aoi": {
                "bbox_epsg3005": list(self.aoi_bbox_epsg3005),
                "crs": self.source.native_crs,
            },
            "products": list(self.products),
            "summary": {
                "tile_count": self.tile_count,
                "total_area_m2": self.total_area_m2,
            },
            "tiles": [tile.to_dict() for tile in self.tiles],
            "request_urls": list(self.request_urls),
            "warnings": list(self.warnings),
        }


def normalize_bbox_epsg3005(value: Sequence[object]) -> Bbox:
    """Validate and normalize a BC Albers bounding box.

    Parameters
    ----------
    value
        Four finite numbers in ``minx,miny,maxx,maxy`` order, in EPSG:3005.

    Returns
    -------
    tuple of float
        The normalized bounding box.

    Raises
    ------
    LidarCatalogError
        If the value is not four finite numbers with ``minx < maxx`` and
        ``miny < maxy``.
    """

    if len(value) != 4:
        raise LidarCatalogError(
            "A LiDAR AOI bounding box must contain four numbers in "
            "`minx,miny,maxx,maxy` order."
        )
    try:
        coordinates = tuple(float(str(item)) for item in value)
    except (TypeError, ValueError) as exc:
        raise LidarCatalogError(
            "A LiDAR AOI bounding box must contain numeric values."
        ) from exc
    if not all(math.isfinite(item) for item in coordinates):
        raise LidarCatalogError("A LiDAR AOI bounding box must contain finite values.")
    minx, miny, maxx, maxy = coordinates
    if minx >= maxx or miny >= maxy:
        raise LidarCatalogError(
            "A LiDAR AOI bounding box requires `minx < maxx` and `miny < maxy`."
        )
    return (minx, miny, maxx, maxy)


def bbox_intersects(first: Sequence[object], second: Sequence[object]) -> bool:
    """Return whether two BC Albers boxes overlap with positive area.

    Edge-touching tiles are excluded. Both inputs are validated and normalized
    before the comparison.
    """

    a = normalize_bbox_epsg3005(first)
    b = normalize_bbox_epsg3005(second)
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def lidarbc_layers_for_product(product: str) -> tuple[LidarProductLayer, ...]:
    """Return the direct-download layers for one LidarBC product.

    Raises
    ------
    LidarCatalogError
        If the product is derived or unsupported as a direct tile layer.
    """

    if product in LIDARBC_DERIVED_PRODUCTS:
        raise LidarCatalogError(
            f"LidarBC product {product!r} is FEMIC-derived and has no direct "
            "tile-index layer."
        )
    layers = tuple(layer for layer in LIDARBC_LAYERS if layer.product == product)
    if not layers:
        supported = ", ".join(LIDARBC_SUPPORTED_PRODUCTS)
        raise LidarCatalogError(
            f"Unsupported LidarBC product {product!r}; supported direct products "
            f"are: {supported}."
        )
    return layers


def build_lidarbc_tile_query_url(
    layer_id: int,
    *,
    aoi_bbox_epsg3005: Sequence[object],
    page_size: int = 2000,
    result_offset: int = 0,
    feature_service_url: str = LIDARBC_FEATURE_SERVICE_URL,
) -> str:
    """Build one paginated LidarBC tile-index query URL.

    The query asks the feature service for an EPSG:3005 envelope intersection
    and returns geometry and attributes in EPSG:3005.
    """

    if page_size <= 0:
        raise LidarCatalogError("LiDAR query page size must be positive.")
    if result_offset < 0:
        raise LidarCatalogError("LiDAR query result offset cannot be negative.")
    bbox = normalize_bbox_epsg3005(aoi_bbox_epsg3005)
    params = [
        ("where", "1=1"),
        ("geometry", ",".join(f"{coordinate:.3f}" for coordinate in bbox)),
        ("geometryType", "esriGeometryEnvelope"),
        ("inSR", "3005"),
        ("spatialRel", "esriSpatialRelIntersects"),
        ("outFields", "*"),
        ("returnGeometry", "true"),
        ("outSR", "3005"),
        ("orderByFields", "OBJECTID ASC"),
        ("resultOffset", str(result_offset)),
        ("resultRecordCount", str(page_size)),
        ("f", "json"),
    ]
    return f"{feature_service_url.rstrip('/')}/{layer_id}/query?{urlencode(params)}"


def tile_from_arcgis_feature(
    feature: Mapping[str, object],
    *,
    product: str,
    layer_id: int,
) -> LidarTile:
    """Normalize one ArcGIS tile-index feature into a :class:`LidarTile`.

    Raises
    ------
    LidarCatalogError
        If required identity fields or usable geometry are missing, or if the
        product does not match the declared layer.
    """

    layer = next((item for item in LIDARBC_LAYERS if item.layer_id == layer_id), None)
    if layer is not None and layer.product != product:
        raise LidarCatalogError(
            f"Layer {layer_id} is {layer.product!r}, not {product!r}."
        )
    attributes = _as_mapping(feature.get("attributes"), context="tile attributes")
    geometry = _as_mapping(feature.get("geometry"), context="tile geometry")
    filename = _as_optional_str(attributes.get("filename"))
    object_id = _as_optional_int(attributes.get("OBJECTID"))
    if filename is None:
        raise LidarCatalogError("LidarBC tile feature is missing `filename`.")
    if object_id is None:
        raise LidarCatalogError("LidarBC tile feature is missing `OBJECTID`.")
    bbox = _bbox_from_arcgis_geometry(geometry)
    area_m2 = _as_optional_float(attributes.get("Shape__Area"))
    grid_scale = _as_optional_str(attributes.get("grid_scale"))
    if grid_scale is None and layer is not None:
        grid_scale = layer.grid_scale
    return LidarTile(
        source_id=LIDARBC_SOURCE_ID,
        product=product,
        layer_id=layer_id,
        object_id=object_id,
        filename=filename,
        maptile=_as_optional_str(attributes.get("maptile")),
        storage_path=_as_optional_str(attributes.get("path")),
        download_url=_as_optional_str(attributes.get("s3Url")),
        accuracy_report_url=_as_optional_str(attributes.get("s3RptUrl")),
        info_file=_as_optional_str(attributes.get("info_file")),
        grid_scale=grid_scale,
        acquisition_year=_first_optional_int(
            attributes.get("year"),
            attributes.get("YEAR_"),
        ),
        projection=_as_optional_str(attributes.get("projection")),
        spacing=_as_optional_str(attributes.get("spacing")),
        point_density_ppm2=_as_optional_int(attributes.get("density")),
        contract_id=_as_optional_str(attributes.get("contract")),
        operator_name=_as_optional_str(attributes.get("oper_name")),
        operator_number=_as_optional_str(attributes.get("op_number")),
        vertical_datum=_as_optional_str(attributes.get("vert_datum")),
        point_format=_as_optional_str(attributes.get("point_form")),
        point_classes=_parse_point_classes(attributes.get("classes")),
        bbox_epsg3005=bbox,
        area_m2=area_m2,
    )


def discover_lidarbc_tiles(
    aoi_bbox_epsg3005: Sequence[object],
    products: Sequence[str],
    *,
    page_size: int = 2000,
    max_pages_per_layer: int = 100,
    timeout_sec: float = 60.0,
    generated_utc: str | None = None,
) -> LidarTileSelection:
    """Discover LidarBC tiles intersecting an AOI.

    Derived products such as CHM are recorded as warnings because they have no
    direct LidarBC tile-index layer. Discovery only reads the public feature
    service; it never downloads tile payloads.

    Raises
    ------
    LidarCatalogError
        If a product is unsupported, the service returns an error, or
        pagination exceeds ``max_pages_per_layer``.
    """

    bbox = normalize_bbox_epsg3005(aoi_bbox_epsg3005)
    requested = _normalize_products(products)
    warnings: list[str] = []
    request_urls: list[str] = []
    tiles_by_id: dict[str, LidarTile] = {}
    for product in requested:
        if product in LIDARBC_DERIVED_PRODUCTS:
            warnings.append(
                f"Product {product!r} is FEMIC-derived; no direct LidarBC "
                "tile-index layer was queried."
            )
            continue
        for layer in lidarbc_layers_for_product(product):
            layer_tiles, layer_urls = _fetch_layer_tiles(
                layer,
                aoi_bbox_epsg3005=bbox,
                page_size=page_size,
                max_pages=max_pages_per_layer,
                timeout_sec=timeout_sec,
            )
            request_urls.extend(layer_urls)
            if not layer_tiles:
                warnings.append(
                    f"No LidarBC tiles intersect the AOI for product "
                    f"{product!r} at layer {layer.layer_id}."
                )
            for tile in layer_tiles:
                tiles_by_id[tile.tile_id] = tile
    tiles = tuple(
        sorted(
            tiles_by_id.values(),
            key=lambda tile: (tile.product, tile.layer_id, tile.object_id),
        )
    )
    return LidarTileSelection(
        source=LIDARBC_SOURCE,
        generated_utc=generated_utc or datetime.now(UTC).isoformat(),
        aoi_bbox_epsg3005=bbox,
        products=requested,
        tiles=tiles,
        request_urls=tuple(request_urls),
        warnings=tuple(warnings),
    )


def write_lidar_selection_manifest(
    selection: LidarTileSelection,
    path: Path,
) -> Path:
    """Write a selection manifest as reviewed, pretty-printed JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(selection.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def _normalize_products(products: Sequence[str]) -> tuple[str, ...]:
    if not products:
        raise LidarCatalogError("At least one LiDAR product must be requested.")
    normalized: list[str] = []
    for product in products:
        text = product.strip()
        if not text:
            raise LidarCatalogError("LiDAR product names cannot be empty.")
        if text not in normalized:
            normalized.append(text)
    return tuple(normalized)


def _fetch_layer_tiles(
    layer: LidarProductLayer,
    *,
    aoi_bbox_epsg3005: Bbox,
    page_size: int,
    max_pages: int,
    timeout_sec: float,
) -> tuple[tuple[LidarTile, ...], tuple[str, ...]]:
    if max_pages <= 0:
        raise LidarCatalogError("LiDAR query page limit must be positive.")
    tiles: list[LidarTile] = []
    request_urls: list[str] = []
    seen: set[str] = set()
    offset = 0
    for _ in range(max_pages):
        url = build_lidarbc_tile_query_url(
            layer.layer_id,
            aoi_bbox_epsg3005=aoi_bbox_epsg3005,
            page_size=page_size,
            result_offset=offset,
        )
        request_urls.append(url)
        payload = _load_json(url, timeout_sec=timeout_sec)
        features = _feature_mappings(payload)
        if not features:
            return (tuple(tiles), tuple(request_urls))
        for feature in features:
            tile = tile_from_arcgis_feature(
                feature,
                product=layer.product,
                layer_id=layer.layer_id,
            )
            if tile.tile_id in seen:
                continue
            if not bbox_intersects(tile.bbox_epsg3005, aoi_bbox_epsg3005):
                continue
            seen.add(tile.tile_id)
            tiles.append(tile)
        exceeded = bool(payload.get("exceededTransferLimit"))
        if len(features) < page_size and not exceeded:
            return (tuple(tiles), tuple(request_urls))
        offset += len(features)
    raise LidarCatalogError(
        f"LidarBC layer {layer.layer_id} exceeded {max_pages} pages; "
        "narrow the AOI or raise the page limit."
    )


def _load_json(url: str, *, timeout_sec: float) -> Mapping[str, object]:
    try:
        with urlopen(url, timeout=timeout_sec) as response:
            payload: object = json.load(response)
    except (OSError, json.JSONDecodeError) as exc:
        raise LidarCatalogError(f"Unable to read LidarBC response: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise LidarCatalogError("LidarBC returned a non-object JSON response.")
    result = {str(key): value for key, value in payload.items()}
    if "error" in result:
        raise LidarCatalogError(f"LidarBC returned an error payload: {result['error']}")
    return result


def _feature_mappings(
    payload: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    raw_features = payload.get("features")
    if raw_features is None:
        return ()
    if not isinstance(raw_features, list):
        raise LidarCatalogError("LidarBC response `features` must be a list.")
    features: list[Mapping[str, object]] = []
    for item in raw_features:
        if isinstance(item, Mapping):
            features.append({str(key): value for key, value in item.items()})
    return tuple(features)


def _as_mapping(value: object, *, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LidarCatalogError(f"LidarBC tile {context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    return text


def _as_optional_int(value: object) -> int | None:
    text = _as_optional_str(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _as_optional_float(value: object) -> float | None:
    text = _as_optional_str(value)
    if text is None:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _first_optional_int(*values: object) -> int | None:
    for value in values:
        parsed = _as_optional_int(value)
        if parsed is not None:
            return parsed
    return None


def _parse_point_classes(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    raw_values: list[object]
    if isinstance(value, (list, tuple)):
        raw_values = list(value)
    else:
        text = str(value).strip()
        if not text:
            return ()
        decoded: object
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, list):
            raw_values = list(decoded)
        else:
            raw_values = [piece for piece in text.split(",") if piece.strip()]
    classes: set[int] = set()
    for item in raw_values:
        try:
            classes.add(int(str(item).strip()))
        except ValueError:
            continue
    return tuple(sorted(classes))


def _bbox_from_arcgis_geometry(geometry: Mapping[str, object]) -> Bbox:
    raw_rings = geometry.get("rings")
    if isinstance(raw_rings, list):
        xs: list[float] = []
        ys: list[float] = []
        for ring in raw_rings:
            if not isinstance(ring, list):
                continue
            for point in ring:
                if not isinstance(point, (list, tuple)) or len(point) < 2:
                    continue
                try:
                    x = float(str(point[0]))
                    y = float(str(point[1]))
                except (TypeError, ValueError):
                    continue
                if math.isfinite(x) and math.isfinite(y):
                    xs.append(x)
                    ys.append(y)
        if xs and ys:
            return (min(xs), min(ys), max(xs), max(ys))
    xmin = _as_optional_float(geometry.get("xmin"))
    ymin = _as_optional_float(geometry.get("ymin"))
    xmax = _as_optional_float(geometry.get("xmax"))
    ymax = _as_optional_float(geometry.get("ymax"))
    if xmin is not None and ymin is not None and xmax is not None and ymax is not None:
        return normalize_bbox_epsg3005((xmin, ymin, xmax, ymax))
    raise LidarCatalogError("LidarBC tile geometry has no usable polygon rings.")
