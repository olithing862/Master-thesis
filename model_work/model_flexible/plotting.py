import searoute as sr
import pandas as pd
import numpy as np
import folium
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.patches as mpatches


def curved_line(lat1, lon1, lat2, lon2, curvature=0.15, n_points=30):
    mid_lat = (lat1 + lat2) / 2
    mid_lon = (lon1 + lon2) / 2
    dlat, dlon = lat2 - lat1, lon2 - lon1
    ctrl_lat = mid_lat - dlon * curvature
    ctrl_lon = mid_lon + dlat * curvature
    t = np.linspace(0, 1, n_points)
    curve_lat = (1 - t) ** 2 * lat1 + 2 * (1 - t) * t * ctrl_lat + t ** 2 * lat2
    curve_lon = (1 - t) ** 2 * lon1 + 2 * (1 - t) * t * ctrl_lon + t ** 2 * lon2
    return list(zip(curve_lat, curve_lon))


def plot_network_map(nodes_csv, flows_csv, prod_csv,
                     demand_rigid_csv, demand_ship_ports_csv,
                     output_html, zoom_start=3, tiles="CartoDB positron"):
    # ---------- Load ----------
    nodes_df     = pd.read_csv(nodes_csv)
    flows_df     = pd.read_csv(flows_csv)
    prod_df      = pd.read_csv(prod_csv)
    demand_rigid = pd.read_csv(demand_rigid_csv)
    demand_ship  = pd.read_csv(demand_ship_ports_csv)

    nodes = {
        str(r["node_id"]): {"lat": float(r["lat"]), "lon": float(r["lon"]),
                            "industry": str(r.get("industry", ""))}
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
        zoom_start=zoom_start, tiles=tiles,
        zoom_snap=0.25, zoom_delta=0.5,
        wheel_debounce_time=80, wheel_pxPerZoomLevel=120,
    )

    ship_layer         = folium.FeatureGroup(name="Shipping Routes",           show=True)
    land_layer         = folium.FeatureGroup(name="Onshore Transport",         show=True)
    transit_layer      = folium.FeatureGroup(name="Active Transit Nodes",      show=True)
    all_transit_layer  = folium.FeatureGroup(name="All Transit Nodes",         show=False)
    prod_layer         = folium.FeatureGroup(name="Production Nodes",          show=True)
    demand_rigid_layer = folium.FeatureGroup(name="Rigid Demand (Steel/Fert)", show=True)
    demand_ship_layer  = folium.FeatureGroup(name="Shipping Bunkering Ports",  show=True)

    for layer in [ship_layer, land_layer, transit_layer, all_transit_layer,
                  prod_layer, demand_rigid_layer, demand_ship_layer]:
        layer.add_to(m)

    # ---------- Transit nodes ----------
    for node_id, node in nodes.items():
        if not node_id.startswith("t"):
            continue
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=3, color="grey", fill=True,
            fill_color="grey", fill_opacity=0.5,
            tooltip=f"{node_id} (transit)",
        ).add_to(all_transit_layer)

        if node_id in active_nodes:
            flow_through = (
                flows_df.loc[flows_df["from_id"] == node_id, "flow"].sum()
                + flows_df.loc[flows_df["to_id"] == node_id, "flow"].sum()
            )
            folium.CircleMarker(
                location=[node["lat"], node["lon"]],
                radius=5, color="#2ca1b0", fill=True,
                fill_color="#2ca1b0", fill_opacity=0.7,
                tooltip=f"{node_id}<br>Flow through: {flow_through:,.2f} Mt",
            ).add_to(transit_layer)

    # ---------- Flows (aggregated per edge) ----------
    edge_flows = (flows_df.groupby(["from_id", "to_id"])["flow"]
                  .sum().reset_index())
    max_edge_flow = edge_flows["flow"].max() or 1

    for _, row in edge_flows.iterrows():
        from_id, to_id = str(row["from_id"]), str(row["to_id"])
        flow = float(row["flow"])
        if from_id not in nodes or to_id not in nodes:
            continue
        route, mode = get_route(from_id, to_id)
        weight = 1.5 + 6 * (flow / max_edge_flow)
        folium.PolyLine(
            route,
            color="#0f3d64" if mode == "ship" else "#e83b20",
            weight=weight, opacity=1,
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
            radius=radius, color="#b8860b", fill=True,
            fill_color="#b8860b", fill_opacity=0.8,
            tooltip=(
                f"{node_id}<br>"
                f"Produced: {row['produced']:,.2f} Mt<br>"
                f"Capacity: {row['capacity']:,.2f} Mt"
            ),
        ).add_to(prod_layer)

    # ---------- Rigid demand (steel + fert) ----------
    industry_colors = {
        "Fertilizer": "#e58250",
        "Steel":      "#5780b6",
    }
    max_demand_rigid = demand_rigid["demand"].max() or 1
    for _, row in demand_rigid.iterrows():
        node_id = str(row["node_id"])
        if node_id not in nodes:
            continue
        node = nodes[node_id]
        industry = node.get("industry", "")
        color = industry_colors.get(industry, "#888888")
        pct = row["served_pct"]
        radius = 3 + 12 * (row["demand"] / max_demand_rigid)
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=radius, color=color, fill=True,
            fill_color=color, fill_opacity=0.92,
            tooltip=(
                f"{node_id} ({industry})<br>"
                f"Demand:    {row['demand']:,.2f} Mt<br>"
                f"Delivered: {row['delivered']:,.2f} Mt<br>"
                f"Unmet:     {row['unmet']:,.2f} Mt<br>"
                f"Served:    {pct:.1f}%"
            ),
        ).add_to(demand_rigid_layer)

    # ---------- Shipping bunkering ports ----------
    delivered_ship = demand_ship[demand_ship["delivered"] > 1e-6].copy()
    max_ship = delivered_ship["delivered"].max() if not delivered_ship.empty else 1
    for _, row in delivered_ship.iterrows():
        node_id = str(row["node_id"])
        if node_id not in nodes:
            continue
        node = nodes[node_id]
        radius = 3 + 12 * (row["delivered"] / max_ship)
        folium.CircleMarker(
            location=[node["lat"], node["lon"]],
            radius=radius, color="#008a65", fill=True,
            fill_color="#008a65", fill_opacity=0.8,
            tooltip=(
                f"{node_id} (bunkering port)<br>"
                f"Delivered: {row['delivered']:,.2f} Mt"
            ),
        ).add_to(demand_ship_layer)

    # ---------- Save ----------
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(output_html)
    print(f"Map saved to {output_html}")
    return m


def plot_industry_share(demand_rigid_csv, demand_ship_aggregate_csv, nodes_csv,
                        value_col="delivered", title=None, save_path=None):
    rigid    = pd.read_csv(demand_rigid_csv)
    ship_agg = pd.read_csv(demand_ship_aggregate_csv)
    nodes    = pd.read_csv(nodes_csv)[["node_id", "industry"]]

    rigid = rigid.merge(nodes, on="node_id", how="left")
    rigid_shares = rigid.groupby("industry")[value_col].sum()

    ship_value = float(ship_agg[value_col].iloc[0])
    industry_df = rigid_shares.reset_index()
    industry_df.columns = ["industry", value_col]
    industry_df = pd.concat([industry_df,
                             pd.DataFrame({"industry": ["Shipping"], value_col: [ship_value]})],
                            ignore_index=True)
    industry_df = industry_df[industry_df[value_col] > 0]
    industry_df = industry_df.sort_values(value_col, ascending=True)

    industries = industry_df["industry"].tolist()
    volumes    = industry_df[value_col].tolist()
    total      = sum(volumes)
    shares     = [v / total * 100 for v in volumes]

    colors = {
        "Shipping":   "#008a65",
        "Fertilizer": "#e58250",
        "Steel":      "#5780b6",
    }
    bar_colors = [colors.get(ind, "#888888") for ind in industries]

    fig, ax = plt.subplots(figsize=(7, 3))
    bars = ax.barh(industries, volumes, color=bar_colors, height=0.55,
                   edgecolor="white", linewidth=0.5)

    for bar, vol, share in zip(bars, volumes, shares):
        ax.text(bar.get_width() + total * 0.02, bar.get_y() + bar.get_height() / 2,
                f"{vol:.2f} Mt  ({share:.1f}%)",
                va="center", ha="left", fontsize=10, color="#333333")

    ax.set_xlim(0, max(volumes) * 1.45)
    ax.set_title(title or f"Delivered share by industry (total: {total:,.2f} Mt)",
                 fontsize=12, pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(left=False, labelsize=10)
    ax.xaxis.set_visible(False)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.show()
    return industry_df


def print_underutilized_production(results_production_csv, threshold=100.0):
    prod = pd.read_csv(results_production_csv)
    prod["utilization_pct"] = 100.0 * prod["produced"] / prod["capacity"]
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


# -------------------- Usage --------------------
if __name__ == "__main__":
    results_dir = Path("Results/flexible_demand/2026-05-05_2")
    nodes_csv   = "model_work/DataFiles_flexible/nodes.csv"

    print_underutilized_production(results_dir / "results_production.csv")

    plot_network_map(
        nodes_csv             = nodes_csv,
        flows_csv             = results_dir / "results_flows.csv",
        prod_csv              = results_dir / "results_production.csv",
        demand_rigid_csv      = results_dir / "results_demand.csv",
        demand_ship_ports_csv = results_dir / "results_demand_ship_ports.csv",
        output_html           = results_dir / "network_flows.html",
    )

    plot_industry_share(
        demand_rigid_csv          = results_dir / "results_demand.csv",
        demand_ship_aggregate_csv = results_dir / "results_demand_ship_aggregate.csv",
        nodes_csv                 = nodes_csv,
        save_path                 = results_dir / "industry_share.png",
    )