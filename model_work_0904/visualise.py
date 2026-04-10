import searoute as sr
import pandas as pd
import folium

# =====================================================
# 1. LOAD DATA
# =====================================================
nodes_df   = pd.read_csv("model_work_0904/nodes.csv")
flows_df   = pd.read_csv("Results/results_flows_10043.csv")
prod_df    = pd.read_csv("Results/results_production_10043.csv")
demand_df  = pd.read_csv("Results/results_demand_10043.csv")

nodes = {
    str(row["node_id"]): {"lat": float(row["lat"]), "lon": float(row["lon"])}
    for _, row in nodes_df.iterrows()
}

active_nodes = set(flows_df["from_id"].astype(str)) | set(flows_df["to_id"].astype(str))

# =====================================================
# 2. ROUTING
# =====================================================
def is_port(node_id):
    return node_id.startswith("t")

import numpy as np

def curved_line(lat1, lon1, lat2, lon2, curvature=0.15):
    """Returns a list of (lat, lon) points forming a curved line."""
    # Midpoint
    mid_lat = (lat1 + lat2) / 2
    mid_lon = (lon1 + lon2) / 2

    # Perpendicular offset
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Rotate 90 degrees and scale by curvature
    offset_lat = -dlon * curvature
    offset_lon =  dlat * curvature

    # Curved midpoint
    ctrl_lat = mid_lat + offset_lat
    ctrl_lon = mid_lon + offset_lon

    # Interpolate points along a quadratic bezier curve
    t = np.linspace(0, 1, 30)
    curve_lat = (1-t)**2 * lat1 + 2*(1-t)*t * ctrl_lat + t**2 * lat2
    curve_lon = (1-t)**2 * lon1 + 2*(1-t)*t * ctrl_lon + t**2 * lon2

    return list(zip(curve_lat, curve_lon))
   
def get_route(from_id, to_id):
    o = nodes[from_id]
    d = nodes[to_id]

    if is_port(from_id) and is_port(to_id):
        try:
            route  = sr.searoute([o["lon"], o["lat"]], [d["lon"], d["lat"]])
            coords = route["geometry"]["coordinates"]
            return [(c[1], c[0]) for c in coords], "ship"
        except Exception as e:
            print(f"Searoutes failed for {from_id}->{to_id}: {e}")

    # Curved land route
    return curved_line(o["lat"], o["lon"], d["lat"], d["lon"]), "land"

# =====================================================
# 3. BUILD MAP + LAYERS
# =====================================================
m = folium.Map(
    location=[nodes_df["lat"].mean(), nodes_df["lon"].mean()],
    zoom_start=3,
    tiles="CartoDB positron"
)

ship_layer    = folium.FeatureGroup(name="Shipping Routes",       show=True)
land_layer    = folium.FeatureGroup(name="Onshore Transport",     show=True)
transit_layer = folium.FeatureGroup(name="Active Transit Nodes",  show=True)
prod_layer    = folium.FeatureGroup(name="Production Nodes",      show=True)
demand_layer  = folium.FeatureGroup(name="Demand Served",         show=True)

for layer in [ship_layer, land_layer, transit_layer, prod_layer, demand_layer]:
    layer.add_to(m)

# =====================================================
# 4. PLOT FLOWS
# =====================================================
max_flow = flows_df["flow"].max()

for _, row in flows_df.iterrows():
    from_id = str(row["from_id"])
    to_id   = str(row["to_id"])
    flow    = float(row["flow"])

    if from_id not in nodes or to_id not in nodes:
        continue

    route, mode = get_route(from_id, to_id)
    weight = 2 + 8 * (flow / 10000)

    folium.PolyLine(
        route,
        color="blue" if mode == "ship" else "red",
        weight=weight,
        opacity=0.8,
        tooltip=f"{from_id} → {to_id} | Flow: {flow:,.2f} Mt"
    ).add_to(ship_layer if mode == "ship" else land_layer)

# =====================================================
# 5. PLOT TRANSIT NODES
# =====================================================
for node_id, node in nodes.items():
    if not node_id.startswith("t"):
        continue
    if node_id not in active_nodes:
        continue

    flow_through = (
        flows_df[flows_df["from_id"] == node_id]["flow"].sum() +
        flows_df[flows_df["to_id"]   == node_id]["flow"].sum()
    )

    folium.CircleMarker(
        location=[node["lat"], node["lon"]],
        radius=5,
        color="blue",
        fill=True,
        fill_color="blue",
        fill_opacity=0.7,
        tooltip=f"{node_id}<br>Flow through: {flow_through:,.2f} Mt"
    ).add_to(transit_layer)

# =====================================================
# 6. PLOT PRODUCTION NODES
# =====================================================
max_prod = prod_df["produced"].max()

for _, row in prod_df.iterrows():
    node_id  = str(row["node_id"])
    if node_id not in nodes:
        continue

    node     = nodes[node_id]
    produced = row["produced"]
    capacity = row["capacity"]
    radius   = 3 + 12 * (produced / max_prod)

    folium.CircleMarker(
        location=[node["lat"], node["lon"]],
        radius=radius,
        color="purple",
        fill=True,
        fill_color="purple",
        fill_opacity=0.8,
        tooltip=f"{node_id}<br>Produced: {produced:,.2f} Mt<br>Capacity: {capacity:,.2f} Mt"
    ).add_to(prod_layer)

# =====================================================
# 7. PLOT OFFTAKE NODES
# =====================================================
max_demand = demand_df["demand"].max()

for _, row in demand_df.iterrows():
    node_id   = str(row["node_id"])
    if node_id not in nodes:
        continue

    node      = nodes[node_id]
    delivered = row["delivered"]
    demand    = row["demand"]
    unmet     = row["unmet"]
    pct       = row["served_pct"]
    radius    = 3 + 12 * (demand / max_demand)

    color = "green" if pct >= 99 else "orange" if pct >= 50 else "red"

    folium.CircleMarker(
        location=[node["lat"], node["lon"]],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        tooltip=(
            f"{node_id}<br>"
            f"Demand:    {demand:,.2f} Mt<br>"
            f"Delivered: {delivered:,.2f} Mt<br>"
            f"Unmet:     {unmet:,.2f} Mt<br>"
            f"Served:    {pct:.1f}%"
        )
    ).add_to(demand_layer)

# =====================================================
# 8. SAVE
# =====================================================
folium.LayerControl(collapsed=False).add_to(m)
m.save("Results/network_flows_2.html")
print("Map saved.")