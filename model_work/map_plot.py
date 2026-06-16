"""
Static world map colored by region — thesis-figure quality.

Uses geopandas + matplotlib. Groups countries into user-defined regions
via an ISO-A3 → region mapping, then does a dissolve+plot.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Tuple

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes


# --------------------------------------------------------------------------
# Region definition: ISO-A3 -> region name
# --------------------------------------------------------------------------
# Any country not listed here will be drawn in the "Other" neutral color.
# --------------------------------------------------------------------------
REGION_MAPPING: Dict[str, str] = {
    # Western Europe
    "GBR": "Western Europe", "IRL": "Western Europe",
    "BEL": "Western Europe", "NLD": "Western Europe", "LUX": "Western Europe",
    "DEU": "Western Europe", "CHE": "Western Europe", "AUT": "Western Europe",
    "POL": "Western Europe", "CZE": "Western Europe", "SVK": "Western Europe",
    "HUN": "Western Europe", "SVN": "Western Europe", "HRV": "Western Europe",
    "ROU": "Western Europe", "BGR": "Western Europe", "EST": "Western Europe",
    "LVA": "Western Europe", "LTU": "Western Europe", "UKR": "Western Europe",
    "BLR": "Western Europe", "MDA": "Western Europe", "BIH": "Western Europe",
    "SRB": "Western Europe", "MNE": "Western Europe", "MKD": "Western Europe",
    "ALB": "Western Europe", "KOS": "Western Europe", "XKX": "Western Europe",
    "AND": "Western Europe", "MCO": "Western Europe", "LIE": "Western Europe",
    "SMR": "Western Europe", "VAT": "Western Europe",

    # Nordics
    "NOR": "Nordics", "SWE": "Nordics", "FIN": "Nordics",
    "DNK": "Nordics", "ISL": "Nordics",

    # Mediterranean
    "PRT": "Mediterranean", "ESP": "Mediterranean", "ITA": "Mediterranean",
    "GRC": "Mediterranean", "CYP": "Mediterranean", "MLT": "Mediterranean",
    "TUR": "Mediterranean", "MAR": "Mediterranean", "DZA": "Mediterranean",
    "TUN": "Mediterranean", "LBY": "Mediterranean", "SYR": "Mediterranean",
    "LBN": "Mediterranean", "ISR": "Mediterranean", "PSE": "Mediterranean",

    # Middle East & India (incl. Central Asia & Caucasus)
    "IRQ": "Middle East & India", "IRN": "Middle East & India",
    "KWT": "Middle East & India", "BHR": "Middle East & India",
    "QAT": "Middle East & India", "ARE": "Middle East & India",
    "OMN": "Middle East & India", "JOR": "Middle East & India",
    "IND": "Middle East & India", "PAK": "Middle East & India",
    "AFG": "Middle East & India", "LKA": "Middle East & India",
    "BGD": "Middle East & India", "NPL": "Middle East & India",
    "BTN": "Middle East & India",
    "KAZ": "Middle East & India", "UZB": "Middle East & India",
    "TKM": "Middle East & India", "KGZ": "Middle East & India",
    "TJK": "Middle East & India",
    "AZE": "Middle East & India", "ARM": "Middle East & India",
    "GEO": "Middle East & India",

    # Red Sea (littoral states)
    "EGY": "Red Sea", "SAU": "Red Sea", "YEM": "Red Sea",

    # Japan & South Korea
    "JPN": "Japan & South Korea", "KOR": "Japan & South Korea",
    "PRK": "Japan & South Korea",

    # China & Hong Kong
    "CHN": "China & Hong Kong", "HKG": "China & Hong Kong",
    "TWN": "China & Hong Kong", "MNG": "China & Hong Kong",

    # South-east Asia
    "THA": "South-east Asia", "VNM": "South-east Asia", "LAO": "South-east Asia",
    "KHM": "South-east Asia", "MMR": "South-east Asia", "MYS": "South-east Asia",
    "SGP": "South-east Asia", "IDN": "South-east Asia", "PHL": "South-east Asia",
    "BRN": "South-east Asia", "TLS": "South-east Asia",

    # Australia — split W/E at ~129°E via geometry cut below.
    # NZ & PNG grouped with East Australia.
    "NZL": "East Australia",
    "PNG": "East Australia",

    # East Africa
    "ETH": "East Africa", "SOM": "East Africa", "KEN": "East Africa",
    "UGA": "East Africa", "RWA": "East Africa", "BDI": "East Africa",
    "TZA": "East Africa", "MOZ": "East Africa", "MWI": "East Africa",
    "ZMB": "East Africa", "ZWE": "East Africa", "MDG": "East Africa",
    "SSD": "East Africa","ZAF": "East Africa", "BWA": "East Africa", 
    "LSO": "East Africa","SWZ": "East Africa", "SDN": "East Africa",
    "DJI": "East Africa","ERI": "East Africa",
    # West Africa (incl. central + southern)
    "MRT": "West Africa", "SEN": "West Africa", "GMB": "West Africa",
    "GNB": "West Africa", "GIN": "West Africa", "SLE": "West Africa",
    "LBR": "West Africa", "CIV": "West Africa", "GHA": "West Africa",
    "TGO": "West Africa", "BEN": "West Africa", "NGA": "West Africa",
    "NER": "West Africa", "MLI": "West Africa", "BFA": "West Africa",
    "TCD": "West Africa", "CMR": "West Africa", "CAF": "West Africa",
    "GAB": "West Africa", "COG": "West Africa", "COD": "West Africa",
    "AGO": "West Africa", "NAM": "West Africa", 
    "GNQ": "West Africa", "STP": "West Africa",

    # NA East Coast / NA West Coast / Gulf of Mexico handled by geometry
    # splits of USA, CAN, MEX (see GEOMETRY_SPLITS below).

    # Panama
    "PAN": "Panama",

    # N Latin America
    "GTM": "N Latin America", "BLZ": "N Latin America", "HND": "N Latin America",
    "SLV": "N Latin America", "NIC": "N Latin America", "CRI": "N Latin America",
    "CUB": "N Latin America", "JAM": "N Latin America", "HTI": "N Latin America",
    "DOM": "N Latin America", "PRI": "N Latin America", "BHS": "N Latin America",
    "TTO": "N Latin America", "COL": "N Latin America", "VEN": "N Latin America",
    "GUY": "N Latin America", "SUR": "N Latin America", "ECU": "N Latin America",

    # S Latin America
    "BRA": "S Latin America", "PER": "S Latin America", "BOL": "S Latin America",
    "PRY": "S Latin America", "URY": "S Latin America", "ARG": "S Latin America",
    "CHL": "S Latin America",

    # Russia — out of model scope, left as "Other".
}


# --------------------------------------------------------------------------
# Geometry splits for countries spanning multiple regions
# ISO-A3 -> [(region_name, bbox)] where bbox = (minx, miny, maxx, maxy) WGS84
# --------------------------------------------------------------------------
GEOMETRY_SPLITS: Dict[str, list] = {
    "AUS": [
        ("West Australia", (112.0, -45.0, 129.0, -9.0)),
        ("East Australia", (129.0, -45.0, 155.0, -9.0)),
    ],
    "USA": [
        # Alaska -> NA West Coast
        ("NA West Coast", (-180.0, 50.0, -129.0, 72.0)),
        # West coast states
        ("NA West Coast", (-125.0, 31.0, -114.0, 50.0)),
        # Gulf states (TX, LA, MS, AL, FL panhandle)
        ("Gulf of Mexico", (-107.0, 25.0, -80.5, 31.0)),
        # Rest of lower 48 -> East Coast
        ("NA East Coast", (-114.0, 31.0, -66.0, 50.0)),
        # Florida peninsula east coast
        ("NA East Coast", (-82.0, 24.5, -79.0, 31.0)),
    ],
    "CAN": [
        # BC + Yukon -> West Coast
        ("NA West Coast", (-141.0, 48.0, -114.0, 72.0)),
        # Rest of Canada -> East Coast
        ("NA East Coast", (-114.0, 41.0, -50.0, 84.0)),
    ],
    "MEX": [
        # Pacific coast
        ("NA West Coast", (-118.0, 14.0, -103.0, 33.0)),
        # Gulf + Caribbean coast
        ("Gulf of Mexico", (-103.0, 14.0, -86.0, 33.0)),
    ],
    "FRA": [
    ("Western Europe",   (-5.5, 41.0, 10.0, 52.0)),   # metropolitan France
    ("N Latin America",  (-55.0,  2.0, -51.0, 6.0)),  # French Guiana
    # (ignoring other DOMs — Réunion, Martinique etc., too small to matter at 110m)
    ],
}


# --------------------------------------------------------------------------
# Default palette — 18 regions + "Other"
# --------------------------------------------------------------------------
DEFAULT_REGION_ORDER = [
    "Western Europe", "Nordics", "Mediterranean", "Middle East & India",
    "Red Sea", "Japan & South Korea", "China & Hong Kong", "South-east Asia",
    "West Australia", "East Australia", "East Africa", "West Africa",
    "NA East Coast", "NA West Coast", "Gulf of Mexico", "Panama",
    "N Latin America", "S Latin America",
    "Other",
]

DEFAULT_PALETTE: Dict[str, str] = {
    "Western Europe":       "#1f77b4",
    "Nordics":              "#4a90d9",
    "Mediterranean":        "#aec7e8",
    "Middle East & India":  "#ff7f0e",
    "Red Sea":              "#ffbb78",
    "Japan & South Korea":  "#d62728",
    "China & Hong Kong":    "#e377c2",
    "South-east Asia":      "#ff9896",
    "West Australia":       "#8c564b",
    "East Australia":       "#c49c94",
    "East Africa":          "#2ca02c",
    "West Africa":          "#98df8a",
    "NA East Coast":        "#9467bd",
    "NA West Coast":        "#c5b0d5",
    "Gulf of Mexico":       "#bcbd22",
    "Panama":               "#17becf",
    "N Latin America":      "#7f7f7f",
    "S Latin America":      "#393b79",
    "Other":                "#e8e8e8",
}


def _box(minx, miny, maxx, maxy):
    """Shapely box helper (local import to avoid hard dep at module load)."""
    from shapely.geometry import box
    return box(minx, miny, maxx, maxy)


def build_regions_gdf(
    countries_gdf: gpd.GeoDataFrame,
    region_mapping: Mapping[str, str] = REGION_MAPPING,
    geometry_splits: Mapping[str, list] = GEOMETRY_SPLITS,
) -> gpd.GeoDataFrame:
    """
    Return a GeoDataFrame with columns [region, geometry], dissolved by region.

    Resolves each country's ISO-3 code row-by-row, preferring ISO_A3_EH over
    ADM0_A3 over ISO_A3. Skips "-99" placeholders that Natural Earth uses for
    disputed territories (Norway, France, Kosovo in plain ISO_A3).
    """
    iso_candidates = [c for c in ("ISO_A3_EH", "ADM0_A3", "ISO_A3", "iso_a3")
                      if c in countries_gdf.columns]
    if not iso_candidates:
        raise KeyError(
            f"Could not find an ISO-3 column in the GeoDataFrame. "
            f"Available: {list(countries_gdf.columns)}"
        )
    # Fallback for features with no valid ISO-3 code (e.g. Somaliland, N. Cyprus).
    # Keyed by Natural Earth's NAME field.
    NAME_OVERRIDES: Dict[str, str] = {
        "Somaliland":       "East Africa",
        "N. Cyprus":        "Mediterranean",
        "W. Sahara":        "Mediterranean",   # disputed; grouping with Morocco
        "Siachen Glacier":  "Middle East & India",
        "Mauritania":       "West Africa",    # some features have non-ASCII names
    }
    def _best_iso(row) -> Optional[str]:
        for col in iso_candidates:
            val = row[col]
            if val and val != "-99":
                return val
        return None

    rows = []
    for _, row in countries_gdf.iterrows():
        iso = _best_iso(row)
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        if iso in geometry_splits:
            for region_name, bbox in geometry_splits[iso]:
                clipped = geom.intersection(_box(*bbox))
                if not clipped.is_empty:
                    rows.append({"region": region_name, "geometry": clipped})
        elif iso in region_mapping:
            rows.append({"region": region_mapping[iso], "geometry": geom})
        else:
            # Fallback: try NAME_OVERRIDES before giving up to "Other".
            name = row.get("NAME") or row.get("name")
            region = NAME_OVERRIDES.get(name, "Other")
            rows.append({"region": region, "geometry": geom})

    out = gpd.GeoDataFrame(rows, crs=countries_gdf.crs)
    out = out.dissolve(by="region", as_index=False)
    return out


def plot_regions_map_static(
    countries_path: str | Path,
    region_mapping: Mapping[str, str] = REGION_MAPPING,
    geometry_splits: Mapping[str, list] = GEOMETRY_SPLITS,
    palette: Optional[Mapping[str, str]] = None,
    region_order: Optional[Iterable[str]] = None,
    other_color: str = "#e8e8e8",
    border_color: str = "white",
    border_width: float = 0.3,
    ocean_color: str = "#f4f6f8",
    projection_proj: Optional[str] = "+proj=robin",
    drop_antarctica: bool = True,
    title: Optional[str] = None,
    figsize: Tuple[float, float] = (14, 7),
    legend: bool = True,
    legend_loc: str = "lower left",
    legend_ncol: int = 2,
    save_path: Optional[str | Path] = None,
    dpi: int = 300,
) -> Tuple[Figure, Axes]:
    """
    Render the static regional world map.

    Parameters
    ----------
    countries_path : str | Path
        Path to a country polygon file (Natural Earth 110m admin_0_countries
        shapefile or GeoJSON is the standard choice).
    region_mapping : dict
        ISO-A3 -> region name.
    geometry_splits : dict
        ISO-A3 -> [(region_name, bbox), ...] for countries spanning multiple
        regions (USA, CAN, AUS, MEX by default).
    palette : dict, optional
        region -> color. Defaults to DEFAULT_PALETTE.
    region_order : iterable, optional
        Legend ordering. Defaults to DEFAULT_REGION_ORDER.
    projection_proj : str, optional
        PROJ string for output CRS. Default "+proj=robin" (Robinson).
        Set to None to keep lat/lon.
    drop_antarctica : bool
        Clip latitudes below -60.
    """
    palette = dict(palette) if palette else dict(DEFAULT_PALETTE)
    region_order = list(region_order) if region_order else list(DEFAULT_REGION_ORDER)

    countries = gpd.read_file(countries_path)
    if countries.crs is None:
        countries = countries.set_crs("EPSG:4326")
    else:
        countries = countries.to_crs("EPSG:4326")

    if drop_antarctica:
        countries = countries.clip(_box(-180, -60, 180, 90))

    regions_gdf = build_regions_gdf(countries, region_mapping, geometry_splits)

    if projection_proj:
        regions_gdf = regions_gdf.to_crs(projection_proj)

    # ---------- Plot ----------
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor(ocean_color)

    # Draw "Other" first so colored regions sit on top.
    other = regions_gdf[regions_gdf["region"] == "Other"]
    rest = regions_gdf[regions_gdf["region"] != "Other"]

    if not other.empty:
        other.plot(ax=ax, color=palette.get("Other", other_color),
                   edgecolor=border_color, linewidth=border_width)

    for region, sub in rest.groupby("region"):
        color = palette.get(region, other_color)
        sub.plot(ax=ax, color=color, edgecolor=border_color,
                 linewidth=border_width)

    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=13, pad=10)

    # ---------- Legend ----------
    # if legend:
    #     # Include ALL regions present (Other included) so legend is complete.
    #     present = set(regions_gdf["region"].unique())
    #     handles = [
    #         mpatches.Patch(facecolor=palette.get(r, other_color),
    #                        edgecolor=border_color, linewidth=0.5, label=r)
    #         for r in region_order if r in present
    #     ]
    #     # Append any regions that are present but missing from region_order.
    #     for r in sorted(present - set(region_order)):
    #         handles.append(
    #             mpatches.Patch(facecolor=palette.get(r, other_color),
    #                            edgecolor=border_color, linewidth=0.5, label=r)
    #         )
    #     ax.legend(
    #         handles=handles,
    #         loc=legend_loc,
    #         ncol=legend_ncol,
    #         frameon=True,
    #         fontsize=9,
    #         title="Region",
    #         title_fontsize=10,
    #     )

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
        print(f"Saved: {save_path}")
    return fig, ax


# -------------------- Example --------------------
if __name__ == "__main__":
    plot_regions_map_static(
        countries_path="/Users/oliviathingvad/Master-thesis/ne_110m_admin_0_countries.geojson",
        title="Region map",
        save_path="/Users/oliviathingvad/Master-thesis/model_work/regions_map.pdf",
    )
    plt.show()