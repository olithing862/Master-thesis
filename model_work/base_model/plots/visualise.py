

import searoute as sr
import pandas as pd
import numpy as np
import folium
from pathlib import Path
import matplotlib.pyplot as plt

def curved_line(lat1, lon1, lat2, lon2, curvature=0.15, n_points=30):
    """Quadratic bezier curve between two points for smoother land routes."""
    mid_lat = (lat1 + lat2) / 2
    mid_lon = (lon1 + lon2) / 2
    dlat, dlon = lat2 - lat1, lon2 - lon1
    ctrl_lat = mid_lat - dlon * curvature
    ctrl_lon = mid_lon + dlat * curvature
    t = np.linspace(0, 1, n_points)
    curve_lat = (1 - t) ** 2 * lat1 + 2 * (1 - t) * t * ctrl_lat + t ** 2 * lat2
    curve_lon = (1 - t) ** 2 * lon1 + 2 * (1 - t) * t * ctrl_lon + t ** 2 * lon2
    return list(zip(curve_lat, curve_lon))


def plot_network_map(nodes_csv, flows_csv, prod_csv, demand_csv,
                     output_html, clustered_sites_csv=None,
                     zoom_start=3, tiles="CartoDB positron"):
    """
    Build an interactive folium map of the optimization network results.

    Layers (toggleable):
      - Shipping Routes        (blue, sea-routed via searoute)
      - Onshore Transport      (red, curved land lines)
      - Active Transit Nodes   (blue circles, sized by flow-through)
      - All Transit Nodes      (grey, hidden by default)
      - Production Nodes       (purple, sized by production)
      - Clustered Sites        (teal, sized by capacity share) -- optional
      - Demand Served          (green/orange/red by served %)
    """
    # ---------- Load ----------
    nodes_df  = pd.read_csv(nodes_csv)
    flows_df  = pd.read_csv(flows_csv)
    prod_df   = pd.read_csv(prod_csv)
    demand_df = pd.read_csv(demand_csv)

    nodes = {
        str(r["node_id"]): {"lat": float(r["lat"]), "lon": float(r["lon"])}
        for _, r in nodes_df.iterrows()
    }
    active_nodes = set(flows_df["from_id"].astype(str)) | set(flows_df["to_id"].astype(str))

    def is_port(node_id):
        return node_id.startswith("t")

    def get_route(from_id, to_id):
        o, d = nodes[from_id], nodes[to_id]
        if is_port(from_id) and is_port(to_id):
            try:
                route = sr.searoute([o["lon"], o["lat"]], [d["lon"], d["lat"]])
                coords = route["geometry"]["coordinates"]
                return [(c[1], c[0]) for c in coords], "ship"
            except Exception as e:
                print(f"Searoutes failed for {from_id}->{to_id}: {e}")
        return curved_line(o["lat"], o["lon"], d["lat"], d["lon"]), "land"

    # ---------- Map + layers ----------
    m = folium.Map(
        location=[nodes_df["lat"].mean(), nodes_df["lon"].mean()],
        zoom_start=zoom_start,
        tiles=tiles,
    )

    ship_layer        = folium.FeatureGroup(name="Shipping Routes",      show=True)
    land_layer        = folium.FeatureGroup(name="Onshore Transport",    show=True)
    transit_layer     = folium.FeatureGroup(name="Active Transit Nodes", show=True)
    all_transit_layer = folium.FeatureGroup(name="All Transit Nodes",    show=False)
    prod_layer        = folium.FeatureGroup(name="Production Nodes",     show=True)
    clustered_layer   = folium.FeatureGroup(name="Clustered Sites",      show=True)
    demand_layer      = folium.FeatureGroup(name="Demand Served",        show=True)

    for layer in [ship_layer, land_layer, transit_layer, all_transit_layer,
                  prod_layer, clustered_layer, demand_layer]:
        layer.add_to(m)


    # ---------- Transit nodes (all + active) ----------
    for node_id, node in nodes.items():
        if not node_id.startswith("t"):
            continue

        # All transit (grey, hidden by default)
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=3, color="grey", fill=True,
            fill_color="grey", fill_opacity=0.5,
            tooltip=f"{node_id} (transit)",
        ).add_to(all_transit_layer)

        # Active transit (blue, larger, with flow info)
        if node_id in active_nodes:
            flow_through = (
                flows_df.loc[flows_df["from_id"] == node_id, "flow"].sum()
                + flows_df.loc[flows_df["to_id"] == node_id, "flow"].sum()
            )
            folium.CircleMarker(
                location=[node["lat"], node["lon"]],
                radius=5, color="blue", fill=True,
                fill_color="blue", fill_opacity=0.7,
                tooltip=f"{node_id}<br>Flow through: {flow_through:,.2f} Mt",
            ).add_to(transit_layer)

    # ---------- Flows ----------
    for _, row in flows_df.iterrows():
        from_id, to_id = str(row["from_id"]), str(row["to_id"])
        flow = float(row["flow"])
        if from_id not in nodes or to_id not in nodes:
            continue
        route, mode = get_route(from_id, to_id)
        weight = 2 + 8 * (flow / 10000)
        folium.PolyLine(
            route,
            color="blue" if mode == "ship" else "red",
            weight=weight, opacity=0.8,
            tooltip=f"{from_id} → {to_id} | Flow: {flow:,.2f} Mt",
        ).add_to(ship_layer if mode == "ship" else land_layer)

    # ---------- Production ----------
    max_prod = prod_df["produced"].max() or 1
    for _, row in prod_df.iterrows():
        node_id = str(row["node_id"])
        if node_id not in nodes:
            continue
        node = nodes[node_id]
        radius = 3 + 12 * (row["produced"] / max_prod)
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=radius, color="purple", fill=True,
            fill_color="purple", fill_opacity=0.8,
            tooltip=(
                f"{node_id}<br>"
                f"Produced: {row['produced']:,.2f} Mt<br>"
                f"Capacity: {row['capacity']:,.2f} Mt"
            ),
        ).add_to(prod_layer)

    # ---------- Offtake / demand ----------
    max_demand = demand_df["demand"].max() or 1
    for _, row in demand_df.iterrows():
        node_id = str(row["node_id"])
        if node_id not in nodes:
            continue
        node = nodes[node_id]
        pct = row["served_pct"]
        color = "green" if pct >= 99 else "orange" if pct >= 50 else "red"
        radius = 3 + 12 * (row["demand"] / max_demand)
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=radius, color=color, fill=True,
            fill_color=color, fill_opacity=0.8,
            tooltip=(
                f"{node_id}<br>"
                f"Demand:    {row['demand']:,.2f} Mt<br>"
                f"Delivered: {row['delivered']:,.2f} Mt<br>"
                f"Unmet:     {row['unmet']:,.2f} Mt<br>"
                f"Served:    {pct:.1f}%"
            ),
        ).add_to(demand_layer)
        # ---------- Clustered production sites (input, pre-optimization) ----------

    if clustered_sites_csv is not None:
        clustered_df = pd.read_csv(clustered_sites_csv)
        max_share = clustered_df["capacity_share_percent"].max() or 1
        for _, row in clustered_df.iterrows():
            radius = 3 + 15 * (row["capacity_share_percent"] / max_share)
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius,
                color="#008080", fill=True,
                fill_color="#008080", fill_opacity=0.6,
                tooltip=(
                    f"Clustered site<br>"
                    f"Lat/Lon: {row['Latitude']}, {row['Longitude']}<br>"
                    f"LCOA: {row['LCOA']:.2f}<br>"
                    f"Max capacity: {row['Max_capacity']:,.2f} Mt/yr<br>"
                    f"Share: {row['capacity_share_percent']:.2f}%"
                ),
            ).add_to(clustered_layer)

    # ---------- Save ----------
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(output_html)
    print(f"Map saved to {output_html}")
    return m



def plot_industry_share(results_demand_csv, nodes_csv, 
                         value_col="delivered", 
                         title=None, save_path=None):
    """
    Pie chart of demand share per industry.
    
    Parameters
    ----------
    results_demand_csv : str
        Path to results_demand_*.csv (with node_id, demand, delivered, ...).
    nodes_csv : str
        Path to nodes.csv (with node_id, industry, ...).
    value_col : str
        Which column to aggregate: "delivered", "demand", or "unmet".
    title : str, optional
        Plot title. Defaults based on value_col.
    save_path : str, optional
        If given, saves the figure to this path.
    """
    demand = pd.read_csv(results_demand_csv)
    nodes  = pd.read_csv(nodes_csv)[["node_id", "industry"]]
    
    df = demand.merge(nodes, on="node_id", how="left")
    shares = df.groupby("industry")[value_col].sum()
    shares = shares[shares > 0].sort_values(ascending=False)
    
    total = shares.sum()
    
    fig, ax = plt.subplots(figsize=(8, 8))
    colors = plt.cm.Set2(range(len(shares)))
    
    wedges, texts, autotexts = ax.pie(
        shares.values,
        labels=shares.index,
        autopct=lambda p: f"{p:.1f}%\n({p*total/100:,.2f} Mt)",
        startangle=90,
        colors=colors,
        wedgeprops=dict(edgecolor="white", linewidth=2),
        textprops=dict(fontsize=11),
    )
    
    for t in autotexts:
        t.set_fontsize(9)
        t.set_color("black")
    
    ax.set_title(title or f"{value_col.capitalize()} share by industry (total: {total:,.2f} Mt)",
                 fontsize=13, pad=20)
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.show()
    
    return shares
# -------------------- Usage --------------------

def print_underutilized_production(results_production_csv, threshold=100.0):
    """
    Print production nodes that are not producing at 100% of capacity.
    
    Parameters
    ----------
    results_production_csv : str
        Path to results_production_*.csv (with node_id, produced, capacity).
    threshold : float
        Utilization % threshold (default 100.0). Nodes below this are printed.
    """
    prod = pd.read_csv(results_production_csv)
    
    # Calculate utilization
    prod["utilization_pct"] = 100.0 * prod["produced"] / prod["capacity"]
    
    # Filter to below threshold (with small tolerance for float rounding)
    under = prod[prod["utilization_pct"] < threshold - 1e-6].copy()
    under = under.sort_values("utilization_pct")
    
    if under.empty:
        print(f"All production nodes are at {threshold}% capacity.")
        return under
    
    print(f"{len(under)} of {len(prod)} production nodes below {threshold}% utilization:\n")
    print(f"{'node_id':<10} {'produced':>12} {'capacity':>12} {'util %':>8}")
    print("-" * 46)
    for _, row in under.iterrows():
        print(f"{row['node_id']:<10} "
              f"{row['produced']:>12,.2f} "
              f"{row['capacity']:>12,.2f} "
              f"{row['utilization_pct']:>7.2f}%")
    
    return under



if __name__ == "__main__":
    results_dir = Path("Results/Base 2026-04-22")
    plot_network_map(
        nodes_csv           = "model_work/DataFiles_base/nodes.csv",
        flows_csv           = results_dir / "results_flows.csv",
        prod_csv            = results_dir / "results_production.csv",
        demand_csv          = results_dir / "results_demand.csv",
        clustered_sites_csv = "/Users/oliviathingvad/Master-thesis/model_work/DataFiles_base/production_sites_clustered_3.csv",
        output_html         = results_dir / "network_flows.html",
    )

    plot_industry_share(
        results_demand_csv       = results_dir / f"results_demand.csv",
        nodes_csv                 = "model_work/DataFiles_base/nodes.csv",
        save_path                 = results_dir / f"industry_share.png",
    )




