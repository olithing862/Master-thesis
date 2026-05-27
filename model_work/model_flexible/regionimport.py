import pandas as pd
import numpy as np
import folium
import matplotlib.pyplot as plt
import io
import base64
from pathlib import Path

# ── Colour palette ────────────────────────────────────────────────────────────
REGION_COLORS = {
    "Middle East & India":  "#b5432a",
    "West Australia":       "#b8860b",
    "East Australia":       "#d4a017",
    "S Latin America":      "#2e86ab",
    "N Latin America":      "#5ba4cf",
    "West Africa":          "#4a7c59",
    "East Africa":          "#6aaa64",
    "Red Sea":              "#c97b38",
    "Mediterranean":        "#8b5e83",
    "China & Hong Kong":    "#e05c5c",
    "South-east Asia":      "#5c9e8a",
    "NA West Coast":        "#3d6166",
    "NA East Coast":        "#2c4a52",
    "Gulf of Mexico":       "#7a9e7e",
    "Nordics":              "#4a6fa5",
    "Western Europe":       "#6b9e78",
    "Japan & South Korea":  "#c4a35a",
    "Other":                "#aaaaaa",
}

# Short display names for the donut centre
SHORT_NAMES = {
    "Middle East & India":  "Mid East\n& India",
    "Japan & South Korea":  "Japan &\nS Korea",
    "China & Hong Kong":    "China &\nHK",
    "South-east Asia":      "SE Asia",
    "NA East Coast":        "NA East",
    "NA West Coast":        "NA West",
    "Gulf of Mexico":       "Gulf of\nMexico",
    "S Latin America":      "S Lat.\nAm.",
    "N Latin America":      "N Lat.\nAm.",
    "Western Europe":       "W Europe",
    "East Australia":       "E Aus.",
    "West Australia":       "W Aus.",
    "East Africa":          "E Africa",
    "West Africa":          "W Africa",
    "Mediterranean":        "Medit.",
    "Nordics":              "Nordics",
    "Red Sea":              "Red Sea",
}

# Demand region centroids
REGION_CENTROIDS = {
    "Western Europe":       (51.0,   8.0),
    "Nordics":              (63.0,  15.0),
    "Mediterranean":        (37.0,  18.0),
    "Middle East & India":  (23.0,  58.0),
    "Red Sea":              (18.0,  42.0),
    "Japan & South Korea":  (35.5, 128.0),
    "China & Hong Kong":    (32.0, 114.0),
    "South-east Asia":      ( 5.0, 110.0),
    "West Australia":       (-26.0, 116.0),
    "East Australia":       (-33.0, 151.0),
    "East Africa":          (-10.0,  37.0),
    "West Africa":          (  8.0,  -5.0),
    "NA East Coast":        ( 38.0, -77.0),
    "NA West Coast":        ( 42.0,-122.0),
    "Gulf of Mexico":       ( 24.0, -90.0),
    "N Latin America":      ( 10.0, -68.0),
    "S Latin America":      (-25.0, -55.0),
}


def make_donut_png(region_shares: dict, total_mt: float,
                   demand_region: str, size_px: int = 200) -> str:
    """
    Render a donut chart with the demand region name and total Mt
    in the centre hole. Returns base64-encoded PNG.
    """
    labels = list(region_shares.keys())
    sizes  = list(region_shares.values())
    colors = [REGION_COLORS.get(r, "#aaaaaa") for r in labels]

    fig, ax = plt.subplots(figsize=(2, 2), dpi=size_px // 2)

    ax.pie(
        sizes,
        colors=colors,
        startangle=90,
        wedgeprops={
            "linewidth": 0.8,
            "edgecolor": "white",
            "width": 0.45,   # donut hole — 0=full hole, 1=full pie
        },
    )
    ax.set_aspect("equal")

    # Centre text: short region name + Mt total
    short = SHORT_NAMES.get(demand_region, demand_region)
    ax.text(0,  0.12, short,
            ha="center", va="center",
            fontsize=6, fontweight="bold",
            color="#222222", linespacing=1.25)
    ax.text(0, -0.22, f"{total_mt:.0f} Mt",
            ha="center", va="center",
            fontsize=8, color="#555555")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True,
                bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def plot_region_flow_map(
    nodes_csv,
    flows_csv,
    prod_csv,
    output_html,
    zoom_start=2,
    tiles="CartoDB positron",
    min_flow_mt=0.5,
    min_icon_px=50,
    max_icon_px=160,
):
    # ── Load ──────────────────────────────────────────────────────────────────
    nodes_df = pd.read_csv(nodes_csv)
    flows_df = pd.read_csv(flows_csv)
    prod_df  = pd.read_csv(prod_csv)

    # Green ammonia only
    flows_df = flows_df[~flows_df["commodity"].astype(str).str.startswith("pf")]
    prod_df  = prod_df[~prod_df["node_id"].astype(str).str.startswith("pf")]

    # Node info lookup
    node_info = {
        str(r["node_id"]): {
            "region":   str(r.get("region", "Other")),
            "type":     str(r.get("type", "")),
            "lat":      float(r["lat"]),
            "lon":      float(r["lon"]),
        }
        for _, r in nodes_df.iterrows()
    }

    # Production node -> region
    prod_region = {
        str(r["node_id"]): node_info.get(str(r["node_id"]), {}).get("region", "Other")
        for _, r in prod_df.iterrows()
    }

    # ── Aggregate flows to (demand region, prod region) ───────────────────────
    records = []
    for _, row in flows_df[flows_df["flow"] > 1e-6].iterrows():
        to_id   = str(row["to_id"])
        from_id = str(row["from_id"])
        flow    = float(row["flow"])

        to_info = node_info.get(to_id, {})
        if to_info.get("type") != "offtake":
            continue

        demand_reg = to_info.get("region", "Other")

        # Try direct lookup, then fall back to commodity field
        p_reg = prod_region.get(from_id)
        if p_reg is None:
            commodity = str(row.get("commodity", ""))
            p_node = commodity.split("_")[0] if "_" in commodity else commodity
            p_reg = prod_region.get(p_node, "Other")

        records.append({
            "demand_region": demand_reg,
            "prod_region":   p_reg,
            "flow":          flow,
        })

    flow_df = pd.DataFrame(records)
    if flow_df.empty:
        print("No offtake flows found — check node types and commodity column.")
        return

    region_totals = flow_df.groupby("demand_region")["flow"].sum()
    region_mix    = flow_df.groupby(
        ["demand_region", "prod_region"])["flow"].sum().unstack(fill_value=0)

    max_total = region_totals.max() or 1

    # ── Build map ─────────────────────────────────────────────────────────────
    m = folium.Map(
        location=[20, 20],
        zoom_start=zoom_start,
        tiles=tiles,
        zoom_snap=0.25,
        zoom_delta=0.5,
    )

    for demand_reg, total_mt in region_totals.items():
        if total_mt < min_flow_mt:
            continue
        if demand_reg not in REGION_CENTROIDS:
            print(f"No centroid defined for: {demand_reg}")
            continue

        lat, lon = REGION_CENTROIDS[demand_reg]

        # Build share dict
        if demand_reg in region_mix.index:
            row_shares = region_mix.loc[demand_reg]
            shares = {k: v for k, v in row_shares.items() if v > 0}
        else:
            shares = {"Other": total_mt}

        # Icon size proportional to total_mt
        icon_px = int(
            min_icon_px + (max_icon_px - min_icon_px) * (total_mt / max_total)
        )

        png_b64 = make_donut_png(
            shares, total_mt,
            demand_region=demand_reg,
            size_px=icon_px * 2,
        )

        icon = folium.DivIcon(
            html=(
                f'<img src="data:image/png;base64,{png_b64}" '
                f'width="{icon_px}" height="{icon_px}" '
                f'style="margin-left:-{icon_px//2}px; '
                f'margin-top:-{icon_px//2}px; '
                f'filter: drop-shadow(0 1px 3px rgba(0,0,0,0.25));">'
            ),
            icon_size=(icon_px, icon_px),
            icon_anchor=(icon_px // 2, icon_px // 2),
        )

        tip = (
            f"<b>{demand_reg}</b><br>"
            f"Total green received: {total_mt:.1f} Mt<br>"
            + "<br>".join(
                f"{k}: {v:.1f} Mt ({100*v/total_mt:.0f}%)"
                for k, v in sorted(shares.items(),
                                   key=lambda x: x[1], reverse=True)
            )
        )
        folium.Marker(
            location=[lat, lon],
            icon=icon,
            tooltip=folium.Tooltip(tip, sticky=True),
        ).add_to(m)

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_html = (
        '<div style="position:fixed; bottom:20px; left:20px; z-index:1000; '
        'background:white; padding:10px 14px; border-radius:8px; '
        'border:1px solid #ccc; font-size:11px; line-height:1.9; '
        'max-height:420px; overflow-y:auto;">'
        '<b style="font-size:12px;">Production region</b><br>'
    )
    for region, color in REGION_COLORS.items():
        if region == "Other":
            continue
        legend_html += (
            f'<span style="display:inline-block;width:11px;height:11px;'
            f'border-radius:50%;background:{color};'
            f'margin-right:6px;vertical-align:middle;"></span>'
            f'{region}<br>'
        )
    legend_html += (
        '<br><i style="color:#888;font-size:10px;">'
        'Donut size proportional to<br>green NH&#x2083; received</i>'
        '</div>'
    )
    m.get_root().html.add_child(folium.Element(legend_html))

    m.save(output_html)
    print(f"Saved: {output_html}")
    return m


# ── Usage ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    results_base = Path("Results_final/fixed_steel")
    nodes_csv    = "model_work/DataFiles_flexible/nodes.csv"

    for scen_name in ["T3-S7", "T3-S9"]:
        results_dir = results_base / scen_name
        print(f"\n=== {scen_name} ===")
        plot_region_flow_map(
            nodes_csv   = nodes_csv,
            flows_csv   = results_dir / "results_flows.csv",
            prod_csv    = results_dir / "results_production.csv",
            output_html = results_dir / "region_flow_map.html",
        )