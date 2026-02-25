import pandas as pd
import folium
import json

# -----------------------------
# Load data
# -----------------------------
nodes_df = pd.read_csv("nodes.csv")
edges_df = pd.read_csv("edges_complete_network1.csv")
flows_df = pd.read_csv("results_flows_1.csv")

# -----------------------------
# Build node dictionary
# -----------------------------
nodes = {}
for _, row in nodes_df.iterrows():
    nodes[row["node_id"]] = {
        "lat": float(row["Latitude"]),
        "lon": float(row["Longitude"]),
        "name": row["Location"]
    }

# -----------------------------
# Merge optimized flow with mode info
# -----------------------------
edges_used = flows_df.merge(
    edges_df[["from_id", "to_id", "mode"]],
    on=["from_id", "to_id"],
    how="left"
)

# -----------------------------
# Create map
# -----------------------------
mean_lat = nodes_df["Latitude"].mean()
mean_lon = nodes_df["Longitude"].mean()

m = folium.Map(location=[mean_lat, mean_lon], zoom_start=3)

# --- All possible routes ---
all_truck_layer = folium.FeatureGroup(name="All Routes - Truck", show=True)
all_ship_layer = folium.FeatureGroup(name="All Routes - Ship", show=True)

# --- Optimized flow routes ---
flow_truck_layer = folium.FeatureGroup(name="Optimized Flow - Truck", show=True)
flow_ship_layer = folium.FeatureGroup(name="Optimized Flow - Ship", show=True)

all_truck_layer.add_to(m)
all_ship_layer.add_to(m)
flow_truck_layer.add_to(m)
flow_ship_layer.add_to(m)

# -----------------------------
# 1️⃣ Plot ALL possible routes (thin grey)
# -----------------------------
for _, row in edges_df.iterrows():

    from_id = row["from_id"]
    to_id = row["to_id"]
    mode = row["mode"]

    if from_id not in nodes or to_id not in nodes:
        continue

    origin = nodes[from_id]
    dest = nodes[to_id]

    route_latlon = [
        (origin["lat"], origin["lon"]),
        (dest["lat"], dest["lon"])
    ]

    folium.PolyLine(
        route_latlon,
        color="red",
        weight=1,
        opacity=0.8,
        tooltip=f"{from_id} → {to_id}"
    ).add_to(all_truck_layer if mode == "truck" else all_ship_layer)

# -----------------------------
# 2️⃣ Plot OPTIMIZED FLOW routes (bold & colored)
# -----------------------------
for _, row in edges_used.iterrows():

    from_id = row["from_id"]
    to_id = row["to_id"]
    flow = row["flow"]
    mode = row["mode"]

    if flow <= 0:
        continue

    if from_id not in nodes or to_id not in nodes:
        continue

    origin = nodes[from_id]
    dest = nodes[to_id]

    route_latlon = [
        (origin["lat"], origin["lon"]),
        (dest["lat"], dest["lon"])
    ]

    folium.PolyLine(
        route_latlon,
        color="red" if mode == "truck" else "blue",
        weight=2 + 0.03 * flow,
        opacity=1,
        tooltip=f"{from_id} → {to_id} | Flow: {flow:.0f}"
    ).add_to(flow_truck_layer if mode == "truck" else flow_ship_layer)

# -----------------------------
# 3️⃣ Add nodes
# -----------------------------
for node_id, node in nodes.items():

    if node_id.startswith("ps"):
        color = "green"
    elif node_id.startswith("os"):
        color = "orange"
    elif node_id.startswith("t"):
        color = "blue"
    else:
        color = "gray"

    folium.CircleMarker(
        [node["lat"], node["lon"]],
        radius=5,
        color=color,
        fill=True,
        fill_opacity=0.9,
        popup=node_id
    ).add_to(m)

# -----------------------------
# Layer control
# -----------------------------
folium.LayerControl(collapsed=False).add_to(m)

# -----------------------------
# Save map
# -----------------------------
m.save("network_with_toggle.html")

print("Map saved as network_with_toggle.html")