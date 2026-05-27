import searoute as sr
import pandas as pd
import numpy as np
import folium
from pathlib import Path


# ── Colour palette ────────────────────────────────────────────────────────────
PROD_COLOR      = "#b8860b"   # dark-gold  – production nodes
TRANSIT_COLOR   = "#3d6166"   # teal       – active transit nodes
STEEL_COLOR     = "#6b9e78"  # steel-blue – steel demand
FERT_COLOR      = "#c97b38"  # burnt-orange – fertiliser demand
SHIP_COLOR      = "#4a6fa5"  # dark-green – shipping bunkering ports
FLOW_SHIP_COLOR = "#3a8db4ba"   # deep-magenta – maritime flow lines
FLOW_LAND_COLOR = "#4d4d4d"   # dark-grey  – onshore flow lines
# ─────────────────────────────────────────────────────────────────────────────


def duplicate_for_antimeridian(coords):
    """
    Return the original coords AND a longitude-shifted copy (+360 and -360).
    This ensures maritime routes crossing the antimeridian appear on both
    sides of the map when panning, without any splitting artefacts.
    Each copy is returned as a separate segment in a list.
    """
    if not coords:
        return [coords]
    shifted_east = [(lat, lon + 360) for lat, lon in coords]
    shifted_west = [(lat, lon - 360) for lat, lon in coords]
    return [coords, shifted_east, shifted_west]


def curved_line(lat1, lon1, lat2, lon2, curvature=0.15, n_points=30):
    """Bezier-curved onshore line between two coordinates."""
    mid_lat = (lat1 + lat2) / 2
    mid_lon = (lon1 + lon2) / 2
    dlat, dlon = lat2 - lat1, lon2 - lon1
    ctrl_lat = mid_lat - dlon * curvature
    ctrl_lon = mid_lon + dlat * curvature
    t = np.linspace(0, 1, n_points)
    curve_lat = (1 - t)**2 * lat1 + 2*(1-t)*t * ctrl_lat + t**2 * lat2
    curve_lon = (1 - t)**2 * lon1 + 2*(1-t)*t * ctrl_lon + t**2 * lon2
    return list(zip(curve_lat, curve_lon))


def plot_network_map(
    nodes_csv,
    flows_csv,
    prod_csv,
    demand_rigid_csv,
    demand_ship_ports_csv,
    output_html,
    zoom_start=3,
    tiles="CartoDB positron",
):
    """
    Plot the green-ammonia network.

    Node sizes:
      - Production  : proportional to green ammonia *produced*
      - Steel/Fert  : proportional to green ammonia *delivered*  (not total demand)
      - Shipping    : proportional to green ammonia *delivered*
      - Transit     : proportional to total green inflow

    Flow lines:
      - Maritime    : deep-magenta  (#8b1a4a)
      - Onshore     : dark-grey     (#4d4d4d)

    The Folium LayerControl is intentionally omitted so the legend can be
    reproduced in LaTeX/TikZ alongside the exported figure.
    """

    # ── Load data ─────────────────────────────────────────────────────────────
    nodes_df     = pd.read_csv(nodes_csv)
    flows_df     = pd.read_csv(flows_csv)
    prod_df      = pd.read_csv(prod_csv)
    demand_rigid = pd.read_csv(demand_rigid_csv)
    demand_ship  = pd.read_csv(demand_ship_ports_csv)

    # Keep only GREEN ammonia flows / production (drop fossil pf-nodes)
    flows_df = flows_df[~flows_df["commodity"].astype(str).str.startswith("pf")]
    prod_df  = prod_df[~prod_df["node_id"].astype(str).str.startswith("pf")]

    nodes = {
        str(r["node_id"]): {
            "lat":      float(r["lat"]),
            "lon":      float(r["lon"]),
            "industry": str(r.get("industry", "")),
        }
        for _, r in nodes_df.iterrows()
    }

    def is_port(nid):
        return nid.startswith("t")

    def get_route(from_id, to_id):
        o, d = nodes[from_id], nodes[to_id]
        if is_port(from_id) and is_port(to_id):
            try:
                route  = sr.searoute([o["lon"], o["lat"]], [d["lon"], d["lat"]])
                coords = [(c[1], c[0]) for c in route["geometry"]["coordinates"]]
                return duplicate_for_antimeridian(coords), "ship"
            except Exception as e:
                print(f"Searoutes failed {from_id}->{to_id}: {e}")
        return [curved_line(o["lat"], o["lon"], d["lat"], d["lon"])], "land"

    # ── Aggregate flows ───────────────────────────────────────────────────────
    edge_flows = (
        flows_df[flows_df["flow"] > 1e-6]
        .groupby(["from_id", "to_id"])["flow"]
        .sum()
        .reset_index()
    )
    max_edge_flow = edge_flows["flow"].max() or 1

    transit_inflow = (
        flows_df[flows_df["to_id"].astype(str).str.startswith("t")]
        .groupby("to_id")["flow"].sum()
        .rename_axis("node_id").reset_index()
    )
    max_inflow = transit_inflow["flow"].max() or 1

    # ── Build map ─────────────────────────────────────────────────────────────
    m = folium.Map(
        location=[nodes_df["lat"].mean(), nodes_df["lon"].mean()],
        zoom_start=zoom_start,
        tiles=tiles,
        zoom_snap=0.25,
        zoom_delta=0.5,
        wheel_debounce_time=80,
        wheel_pxPerZoomLevel=120,
    )

    ship_layer         = folium.FeatureGroup(name="Shipping Routes",           show=True)
    land_layer         = folium.FeatureGroup(name="Onshore Transport",         show=True)
    transit_layer      = folium.FeatureGroup(name="Active Transit Nodes",      show=True)
    prod_layer         = folium.FeatureGroup(name="Production Nodes",          show=True)
    demand_rigid_layer = folium.FeatureGroup(name="Rigid Demand (Steel/Fert)", show=True)
    demand_ship_layer  = folium.FeatureGroup(name="Shipping Bunkering Ports",  show=True)

    for layer in [ship_layer, land_layer, transit_layer,
                  prod_layer, demand_rigid_layer, demand_ship_layer]:
        layer.add_to(m)

    # ── Flow lines ────────────────────────────────────────────────────────────
    for _, row in edge_flows.iterrows():
        from_id = str(row["from_id"])
        to_id   = str(row["to_id"])
        flow    = float(row["flow"])
        if from_id not in nodes or to_id not in nodes:
            continue

        route_segments, mode = get_route(from_id, to_id)
        weight = 1.5 + 6 * (flow / max_edge_flow)
        color  = FLOW_SHIP_COLOR if mode == "ship" else FLOW_LAND_COLOR
        tip    = f"{from_id} → {to_id} | Flow: {flow:,.2f} Mt"
        target = ship_layer if mode == "ship" else land_layer

        for seg in route_segments:
            folium.PolyLine(
                seg, color=color, weight=weight,
                opacity=0.85, tooltip=tip,
            ).add_to(target)

    # ── Transit nodes (sized by green inflow) ─────────────────────────────────
    for _, row in transit_inflow.iterrows():
        nid = str(row["node_id"])
        if nid not in nodes:
            continue
        node   = nodes[nid]
        radius = 3 + 10 * (row["flow"] / max_inflow)
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=radius,
            color=TRANSIT_COLOR, fill=True,
            fill_color=TRANSIT_COLOR, fill_opacity=0.75,
            tooltip=f"{nid}<br>Green inflow: {row['flow']:,.2f} Mt",
        ).add_to(transit_layer)

    # ── Production nodes (sized by green produced) ────────────────────────────
    max_prod = prod_df["produced"].max() or 1
    for _, row in prod_df.iterrows():
        nid = str(row["node_id"])
        if nid not in nodes:
            continue
        node   = nodes[nid]
        radius = 3 + 12 * (row["produced"] / max_prod)
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=radius,
            color=PROD_COLOR, fill=True,
            fill_color=PROD_COLOR, fill_opacity=0.85,
            tooltip=(
                f"{nid}<br>"
                f"Produced: {row['produced']:,.2f} Mt<br>"
                f"Capacity: {row['capacity']:,.2f} Mt<br>"
                f"Util: {100*row['produced']/row['capacity']:.1f}%"
            ),
        ).add_to(prod_layer)

    # ── Rigid demand nodes (sized by GREEN delivered, not total demand) ────────
    industry_colors = {"Fertiliser": FERT_COLOR, "Steel": STEEL_COLOR}
    max_delivered_rigid = demand_rigid["delivered"].max() or 1   # ← green delivered

    for _, row in demand_rigid.iterrows():
        nid = str(row["node_id"])
        if nid not in nodes:
            continue
        node     = nodes[nid]
        industry = node.get("industry", "")
        color    = industry_colors.get(industry, "#888888")
        radius   = 3 + 12 * (row["delivered"] / max_delivered_rigid)  # ← green delivered
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=radius,
            color=color, fill=True,
            fill_color=color, fill_opacity=0.92,
            tooltip=(
                f"{nid} ({industry})<br>"
                f"Demand:    {row['demand']:,.2f} Mt<br>"
                f"Delivered: {row['delivered']:,.2f} Mt<br>"
                f"Unmet:     {row['unmet']:,.2f} Mt<br>"
                f"Served:    {row['served_pct']:.1f}%"
            ),
        ).add_to(demand_rigid_layer)

    # ── Shipping bunkering ports (sized by GREEN delivered) ───────────────────
    delivered_ship = demand_ship[demand_ship["delivered"] > 1e-6].copy()
    max_ship = delivered_ship["delivered"].max() if not delivered_ship.empty else 1

    for _, row in delivered_ship.iterrows():
        nid = str(row["node_id"])
        if nid not in nodes:
            continue
        node   = nodes[nid]
        radius = 3 + 12 * (row["delivered"] / max_ship)
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=radius,
            color=SHIP_COLOR, fill=True,
            fill_color=SHIP_COLOR, fill_opacity=0.85,
            tooltip=f"{nid} (bunkering)<br>Delivered: {row['delivered']:,.2f} Mt",
        ).add_to(demand_ship_layer)
    # Add this after the production loop to get legend reference values
    print(f"Max produced: {max_prod:.2f} Mt  → radius 15")
    print(f"50% of max:   {max_prod*0.5:.2f} Mt → radius {3 + 12*0.5:.1f}")
    print(f"25% of max:   {max_prod*0.25:.2f} Mt → radius {3 + 12*0.25:.1f}")
    # ── Save (NO LayerControl — legend goes in LaTeX) ─────────────────────────
    m.save(output_html)
    print(f"Saved: {output_html}")
    return m


def print_underutilized_production(results_production_csv, threshold=100.0):
    prod = pd.read_csv(results_production_csv)
    prod["utilization_pct"] = 100.0 * prod["produced"] / prod["capacity"]
    under = prod[prod["utilization_pct"] < threshold - 1e-6].copy()
    under = under.sort_values("utilization_pct")

    if under.empty:
        print(f"All production nodes at {threshold}% capacity.")
        return under

    print(f"{len(under)} of {len(prod)} nodes below {threshold}% utilization:\n")
    print(f"{'node_id':<10} {'produced':>12} {'capacity':>12} {'util %':>8}")
    print("-" * 46)
    for _, row in under.iterrows():
        print(
            f"{row['node_id']:<10} "
            f"{row['produced']:>12,.2f} "
            f"{row['capacity']:>12,.2f} "
            f"{row['utilization_pct']:>7.2f}%"
        )
    return under


# ── Usage ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    results_base = Path("Results_final/fixed_steel")
    nodes_csv    = "model_work/DataFiles_flexible/nodes.csv"

    scenarios = ["T3-S7", "T3-S9"]   # high-cost vs low-cost at medium cap

    for scen_name in scenarios:
        results_dir = results_base / scen_name
        print(f"\n=== {scen_name} ===")

        print_underutilized_production(results_dir / "results_production.csv")

        plot_network_map(
            nodes_csv             = nodes_csv,
            flows_csv             = results_dir / "results_flows.csv",
            prod_csv              = results_dir / "results_production.csv",
            demand_rigid_csv      = results_dir / "results_demand.csv",
            demand_ship_ports_csv = results_dir / "results_demand_ship_ports.csv",
            output_html           = results_dir / "network_flows.html",
        )