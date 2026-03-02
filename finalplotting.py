import pandas as pd
import folium
import json
import numpy as np

# =====================================================
# 1️⃣ LOAD DATA
# =====================================================
nodes_df = pd.read_csv("nodes.csv")
edges_df = pd.read_csv("edges_complete_network1.csv")
flows_df = pd.read_csv("Results/results_02march_1.csv")

# =====================================================
# 2️⃣ BUILD NODE DICTIONARY
# =====================================================
nodes = {}
for _, row in nodes_df.iterrows():
    nodes[row["node_id"]] = {
        "lat": float(row["Latitude"]),
        "lon": float(row["Longitude"]),
        "name": row["Location"]
    }

# =====================================================
# 3️⃣ MERGE FLOWS WITH MODE + GEOMETRY
# =====================================================
edges_used = flows_df.merge(
    edges_df[["from_id", "to_id", "mode", "geometry"]],
    on=["from_id", "to_id"],
    how="left"
)

# Remove zero flows
edges_used = edges_used[edges_used["flow"] > 0].copy()

# =====================================================
# 4️⃣ CREATE MAP
# =====================================================
mean_lat = nodes_df["Latitude"].mean()
mean_lon = nodes_df["Longitude"].mean()

m = folium.Map(location=[mean_lat, mean_lon], zoom_start=3)

# Layers
flow_truck_layer = folium.FeatureGroup(name="Optimized Flow - Truck", show=True)
flow_ship_layer  = folium.FeatureGroup(name="Optimized Flow - Ship", show=True)

flow_truck_layer.add_to(m)
flow_ship_layer.add_to(m)

# =====================================================
# 5️⃣ NORMALIZE FLOW THICKNESS
# =====================================================
max_flow = edges_used["flow"].max()

# =====================================================
# 6️⃣ PLOT OPTIMIZED FLOWS USING REAL GEOMETRY
# =====================================================
for _, row in edges_used.iterrows():

    from_id = row["from_id"]
    to_id   = row["to_id"]
    flow    = row["flow"]
    mode    = row["mode"]

    if from_id not in nodes or to_id not in nodes:
        continue

    origin = nodes[from_id]
    dest   = nodes[to_id]

    # ---- Use stored geometry if available ----
    if pd.notna(row.get("geometry")):
        try:
            geometry = json.loads(row["geometry"])
            coords = geometry["coordinates"]
            route_latlon = [(c[1], c[0]) for c in coords]
        except:
            # fallback
            route_latlon = [
                (origin["lat"], origin["lon"]),
                (dest["lat"], dest["lon"])
            ]
    else:
        route_latlon = [
            (origin["lat"], origin["lon"]),
            (dest["lat"], dest["lon"])
        ]

    # ---- Normalize thickness ----
    weight = 2 + 8 * (flow / max_flow)

    folium.PolyLine(
        route_latlon,
        color="red" if mode == "truck" else "blue",
        weight=weight,
        opacity=0.9,
        tooltip=f"{from_id} → {to_id} | Flow: {flow:,.0f}"
    ).add_to(flow_truck_layer if mode == "truck" else flow_ship_layer)

# =====================================================
# 7️⃣ ADD NODES
# =====================================================
for node_id, node in nodes.items():

    if node_id.startswith("ps"):
        color = "green"
    elif node_id.startswith("os") or node_id.startswith("ost"):
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

# =====================================================
# 8️⃣ LAYER CONTROL
# =====================================================
folium.LayerControl(collapsed=False).add_to(m)

# =====================================================
# 9️⃣ SAVE MAP
# =====================================================
m.save("network_real_routes.html")

print("Map saved as network_real_routes.html")