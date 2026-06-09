import searoute as sr
import pandas as pd
import numpy as np
import folium
from pathlib import Path


# ── Colour palette ────────────────────────────────────────────────────────────
PROD_COLOR      = "#c03a2ba3"
TRANSIT_COLOR   = "#7b5ea7a4"
STEEL_COLOR     = "#6b9e78"
FERT_COLOR      = "#c97b38"
SHIP_COLOR      = "#4a6fa5"
FLOW_SHIP_COLOR = "#3a8db4ba"
FLOW_LAND_COLOR = "#4d4d4d"


def duplicate_for_antimeridian(coords):
    if not coords:
        return [coords]
    shifted_east = [(lat, lon + 360) for lat, lon in coords]
    shifted_west = [(lat, lon - 360) for lat, lon in coords]
    return [coords, shifted_east, shifted_west]


def curved_line(lat1, lon1, lat2, lon2, curvature=0.15, n_points=30):
    mid_lat = (lat1 + lat2) / 2
    mid_lon = (lon1 + lon2) / 2
    dlat, dlon = lat2 - lat1, lon2 - lon1
    ctrl_lat = mid_lat - dlon * curvature
    ctrl_lon = mid_lon + dlat * curvature
    t = np.linspace(0, 1, n_points)
    curve_lat = (1 - t)**2 * lat1 + 2*(1-t)*t * ctrl_lat + t**2 * lat2
    curve_lon = (1 - t)**2 * lon1 + 2*(1-t)*t * ctrl_lon + t**2 * lon2
    return list(zip(curve_lat, curve_lon))


def compute_global_maxima(scenarios_dirs):
    """
    Compute maxima across all scenarios so node sizes are comparable
    across maps. Pass the returned dict into plot_network_map.

    Parameters
    ----------
    scenarios_dirs : list of Path or str

    Returns
    -------
    dict with keys: max_prod, max_delivered_rigid, max_ship, max_inflow, max_edge_flow
    """
    all_prod, all_delivered, all_ship, all_inflow, all_edge = [], [], [], [], []

    for d in scenarios_dirs:
        d = Path(d)
        prod   = pd.read_csv(d / "results_production.csv")
        demand = pd.read_csv(d / "results_demand.csv")
        ship   = pd.read_csv(d / "results_demand_ship_ports.csv")
        flows  = pd.read_csv(d / "results_flows.csv")

        prod  = prod[~prod["node_id"].astype(str).str.startswith("pf")]
        flows = flows[~flows["commodity"].astype(str).str.startswith("pf")]
        flows = flows[flows["flow"] > 1e-6]

        all_prod.append(prod["produced"].max() if not prod.empty else 0)
        all_delivered.append(demand["delivered"].max() if not demand.empty else 0)
        all_ship.append(ship["delivered"].max() if not ship.empty else 0)

        inflow = (
            flows[flows["to_id"].astype(str).str.startswith("t")]
            .groupby("to_id")["flow"].sum()
        )
        all_inflow.append(inflow.max() if not inflow.empty else 0)

        edge = flows.groupby(["from_id", "to_id"])["flow"].sum()
        all_edge.append(edge.max() if not edge.empty else 0)

    return {
        "max_prod":            max(all_prod)      or 1,
        "max_delivered_rigid": max(all_delivered) or 1,
        "max_ship":            max(all_ship)       or 1,
        "max_inflow":          max(all_inflow)     or 1,
        "max_edge_flow":       max(all_edge)       or 1,
    }


def plot_network_map(
    nodes_csv,
    flows_csv,
    prod_csv,
    demand_rigid_csv,
    demand_ship_ports_csv,
    output_html,
    zoom_start=2,
    location=None,
    tiles="CartoDB positron",
    global_maxima=None,
):
    """
    Plot the green-ammonia network.

    Parameters
    ----------
    zoom_start : int
        Initial zoom level. Set identically across all scenario calls
        to ensure comparable screenshots.
    location : [lat, lon] or None
        Map centre. Set identically across all scenario calls to ensure
        identical viewport. If None, centres on mean node position.
    global_maxima : dict or None
        Output of compute_global_maxima(). If provided, node sizes are
        scaled consistently across all maps. If None, each map scales
        to its own maximum — only use this for standalone maps.
    """

    # ── Load data ─────────────────────────────────────────────────────────────
    nodes_df     = pd.read_csv(nodes_csv)
    flows_df     = pd.read_csv(flows_csv)
    prod_df      = pd.read_csv(prod_csv)
    demand_rigid = pd.read_csv(demand_rigid_csv)
    demand_ship  = pd.read_csv(demand_ship_ports_csv)

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

    transit_inflow = (
        flows_df[flows_df["to_id"].astype(str).str.startswith("t")]
        .groupby("to_id")["flow"].sum()
        .rename_axis("node_id").reset_index()
    )

    delivered_ship = demand_ship[demand_ship["delivered"] > 1e-6].copy()

    # ── Scaling ───────────────────────────────────────────────────────────────
    if global_maxima is not None:
        max_prod            = global_maxima["max_prod"]
        max_delivered_rigid = global_maxima["max_delivered_rigid"]
        max_ship            = global_maxima["max_ship"]
        max_inflow          = global_maxima["max_inflow"]
        max_edge_flow       = global_maxima["max_edge_flow"]
    else:
        max_prod            = prod_df["produced"].max() or 1
        max_delivered_rigid = demand_rigid["delivered"].max() or 1
        max_ship            = delivered_ship["delivered"].max() if not delivered_ship.empty else 1
        max_inflow          = transit_inflow["flow"].max() or 1
        max_edge_flow       = edge_flows["flow"].max() or 1

    # ── Build map ─────────────────────────────────────────────────────────────
    map_centre = location if location is not None else [
        nodes_df["lat"].mean(), nodes_df["lon"].mean()
    ]

    m = folium.Map(
        location=map_centre,
        zoom_start=zoom_start,
        tiles=tiles,
        min_zoom=1,
        zoom_snap=0.1,
        zoom_delta=0.25,
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

    # ── Transit nodes ─────────────────────────────────────────────────────────
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

    # ── Production nodes ──────────────────────────────────────────────────────
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

    # ── Rigid demand nodes ────────────────────────────────────────────────────
    industry_colors = {"Fertiliser": FERT_COLOR, "Steel": STEEL_COLOR}

    for _, row in demand_rigid.iterrows():
        nid = str(row["node_id"])
        if nid not in nodes:
            continue
        node     = nodes[nid]
        industry = node.get("industry", "")
        color    = industry_colors.get(industry, "#888888")
        radius   = 3 + 12 * (row["delivered"] / max_delivered_rigid)
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

    # ── Shipping bunkering ports ──────────────────────────────────────────────
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
    results_base = Path("Results_final/hormuz3")
    nodes_csv    = "model_work/DataFiles_flexible/nodes.csv"
    scenarios    = ["H1-S7","H1-S9"]

    # Fixed viewport — set once, used for every map so screenshots are identical
    FIXED_LOCATION = [20, 20]
    FIXED_ZOOM     = 2

    # Compute shared scale across all scenarios before plotting
    scenario_dirs = [results_base / s for s in scenarios]
    global_maxima = compute_global_maxima(scenario_dirs)
    print("Global maxima used for node sizing:")
    for k, v in global_maxima.items():
        print(f"  {k}: {v:.2f}")

    for scen_name in scenarios:
        d = results_base / scen_name
        print(f"\n=== {scen_name} ===")

        print_underutilized_production(d / "results_production.csv")

        plot_network_map(
            nodes_csv             = nodes_csv,
            flows_csv             = d / "results_flows.csv",
            prod_csv              = d / "results_production.csv",
            demand_rigid_csv      = d / "results_demand.csv",
            demand_ship_ports_csv = d / "results_demand_ship_ports.csv",
            output_html           = d / "network_flows.html",
            zoom_start            = FIXED_ZOOM,
            location              = FIXED_LOCATION,
            global_maxima         = global_maxima,
        )