import pandas as pd
import folium
import json
import numpy as np
from sklearn.cluster import KMeans

# =====================================================
# 1️⃣ LOAD DATA
# =====================================================
nodes_df_old = pd.read_csv("nodes.csv")
nodes_df = pd.read_csv("nodes_mmmczcs.csv")
edges_df = pd.read_csv("edges_complete_network1.csv")
flows_df = pd.read_csv("Results/results_02march_1.csv")
ammonia_df1 = pd.read_csv(r"/Users/oliviathingvad/Master-thesis/Public-Global-Port-Optimisation/Input Data/c_NH3_cost_2.6.csv")
newnodes = pd.read_csv("offtakenodes_1.csv")
ports = pd.read_csv("ports.csv")
# Filter
ammonia_df1 = ammonia_df1[ammonia_df1["Max_capacity"] > 0.5]
ammonia_df1 = ammonia_df1.nsmallest(4000, "LCOA")
print(ammonia_df1)
print(f"Total capacity before clustering: {ammonia_df1['Max_capacity'].sum():.0f} tonnes/year")
# Convert lat/lon to 3D cartesian coordinates on unit sphere
lat_rad = np.radians(ammonia_df1["Latitude"])
lon_rad = np.radians(ammonia_df1["Longitude"])
ammonia_df1["X"] = np.cos(lat_rad) * np.cos(lon_rad)
ammonia_df1["Y"] = np.cos(lat_rad) * np.sin(lon_rad)
ammonia_df1["Z"] = np.sin(lat_rad)

# Cluster on X, Y, Z
n_clusters = 25
kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
ammonia_df1["cluster"] = kmeans.fit_predict(ammonia_df1[["X", "Y", "Z"]])

# Pick cheapest site per cluster as representative
cheapest_idx = ammonia_df1.groupby("cluster")["LCOA"].idxmin()
best_ammonia = ammonia_df1.loc[cheapest_idx].copy()

# Sum all capacities in each cluster
best_ammonia["Max_capacity"] = ammonia_df1.groupby("cluster")["Max_capacity"].sum().values
best_ammonia = best_ammonia.reset_index(drop=True)

# Print total capacity
print(f"Total capacity: {best_ammonia['Max_capacity'].sum():.0f} tonnes/year")

# Drop helper columns before saving
best_ammonia = best_ammonia.drop(columns=["X", "Y", "Z", "cluster"])
best_ammonia.to_csv("production_sites_clustered.csv", index=False)


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
new_nodes = {}
for _, row in newnodes.iterrows():
    new_nodes[row["id"]] = {
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
        "name": row["name"]
    }
ports_nodes = {}
for _, row in ports.iterrows():
    ports_nodes[row["node_id"]] = {
        "lat": float(row["Latitude"]),
        "lon": float(row["Longitude"]),
        "name": row["Main Port Name"]
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

ammonia_layer = folium.FeatureGroup(name="Ammonia Production Possibilities", show=True)
ammonia_layer.add_to(m)

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

    if node_id.startswith("oft_f"):
        color = "green"
    elif node_id.startswith("oft_s"):
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

for node_id, node in ports_nodes.items():

    folium.CircleMarker(
        [node["lat"], node["lon"]],
        radius=5,
        color="red",
        fill=True,
        fill_opacity=0.9,
        popup=node_id
    ).add_to(m)

for _, row in best_ammonia.iterrows():

    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=4,
        color="purple",
        fill=True,
        fill_color="purple",
        fill_opacity=0.8,
        tooltip=f"Production: {row['Max_capacity']:.2f}"
    ).add_to(ammonia_layer)
# =====================================================
# 8️⃣ LAYER CONTROL
# =====================================================
folium.LayerControl(collapsed=False).add_to(m)

# =====================================================
# 9️⃣ SAVE MAP
# =====================================================
m.save("network_real_routes_1.html")

print("Map saved as network_real_routes.html")