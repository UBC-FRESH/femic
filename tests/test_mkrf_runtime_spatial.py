from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Polygon

from femic.workflows.mkrf import _project_mkrf_runtime_fragments


def test_project_mkrf_runtime_fragments_filters_x_and_projects_fields() -> None:
    source_gdf = gpd.GeoDataFrame(
        {
            "FOREST_COVER_ID": [9001, 9002],
            "Operability": ["Operable", "Low Operability"],
            "Shape_Length": [10.0, 20.0],
            "Shape_Area": [100.0, 200.0],
            "CONTCLAS": ["C", "X"],
            "AGE_2020": [80, 15],
            "AU_EX": ["1", "2"],
            "AU_FU": ["1", "2"],
            "RES_KEY": [101, 102],
            "CT_eligib": ["N", "Y"],
        },
        geometry=[
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(2, 0), (3, 0), (3, 1), (2, 1)]),
        ],
        crs="EPSG:3005",
    )

    out = _project_mkrf_runtime_fragments(source_gdf=source_gdf)

    assert len(out) == 1
    assert out.columns.tolist() == [
        "FOREST_COV",
        "Operabilit",
        "Shape_Leng",
        "Shape_Area",
        "CONTCLAS",
        "AGE_2020",
        "AU_EX",
        "AU_FU",
        "RES_KEY",
        "CT_eligib",
        "geometry",
    ]
    row = out.iloc[0]
    assert row["FOREST_COV"] == 9001
    assert row["Operabilit"] == "Operable"
    assert row["Shape_Leng"] == 10.0
    assert row["RES_KEY"] == 101
    assert row["CONTCLAS"] == "C"
