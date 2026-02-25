import pandas as pd
import folium
import openrouteservice
import openrouteservice.exceptions
import os
import searoute as sr
import json
import time

# -----------------------------
# Load data
# -----------------------------
nodes_df = pd.read_csv("nodes.csv")
edges_df = pd.read_csv("edges_cleaned.csv")
flows_df = pd.read_csv("results_flows.csv")


# Build node dictionary
nodes = {}
for _, row in nodes_df.iterrows():
    nodes[row["node_id"]] = {
        "lat": float(row["Latitude"]),
        "lon": float(row["Longitude"]),
        "name": row["Location"]
    }

# Merge flow with mode info
edges_used = flows_df.merge(
    edges_df[["from_id", "to_id", "mode"]],
    on=["from_id", "to_id"],
    how="left"
)

# -----------------------------
# Cache file (so ORS not called again)
# -----------------------------
CACHE_FILE = "route_cache.json"

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        route_cache = json.load(f)
else:
    route_cache = {}

# ORS client
ors_client = openrouteservice.Client(key=os.getenv("ORS_API_KEY"))

# -----------------------------
# Create map
# -----------------------------
mean_lat = nodes_df["Latitude"].mean()
mean_lon = nodes_df["Longitude"].mean()

m = folium.Map(location=[mean_lat, mean_lon], zoom_start=3)

truck_layer = folium.FeatureGroup(name="Truck")
ship_layer = folium.FeatureGroup(name="Ship")

truck_layer.add_to(m)
ship_layer.add_to(m)

# -----------------------------
# Plot realistic routes
# -----------------------------
for _, row in edges_used.iterrows():

    from_id = row["from_id"]
    to_id = row["to_id"]
    flow = row["flow"]
    mode = row["mode"]

    key = f"{from_id}_{to_id}"

    origin = nodes[from_id]
    dest = nodes[to_id]

    # Use cached geometry if available
    if key in route_cache:
        route_latlon = route_cache[key]

    else:
        try:
            if mode == "truck":

                radiuses_to_try = [350, 1000, 5000, 10000]
                route = None

                for r in radiuses_to_try:
                    try:
                        route = ors_client.directions(
                            coordinates=[
                                (origin["lon"], origin["lat"]),
                                (dest["lon"], dest["lat"])
                            ],
                            profile="driving-hgv",
                            format="geojson",
                            radiuses=[r, r]
                        )

                        print(f"Truck route {from_id} → {to_id} succeeded with radius {r}m")
                        break

                    except openrouteservice.exceptions.ApiError as e:
                        if "Could not find routable point" in str(e):
                            print(f"Radius {r}m failed for {from_id} → {to_id}")
                            continue
                        else:
                            print(f"Truck routing error {from_id} → {to_id}: {e}")
                            break

                if route is None:
                    print(f"Truck route failed completely {from_id} → {to_id}")
                    continue

                coords = route["features"][0]["geometry"]["coordinates"]

            elif mode == "ship":
                route = sr.searoute(
                    [origin["lon"], origin["lat"]],
                    [dest["lon"], dest["lat"]]
                )
                coords = route["geometry"]["coordinates"]

            route_latlon = [(lat, lon) for lon, lat in coords]

            # Save to cache
            route_cache[key] = route_latlon

            if mode == "truck":
                time.sleep(1)

        except Exception as e:
            print(f"Routing failed {from_id}->{to_id}: {e}")
            continue

    # Draw line
    folium.PolyLine(
        route_latlon,
        color="red" if mode == "truck" else "blue",
        weight=2 + 0.02 * flow,
        tooltip=f"{from_id} → {to_id} | Flow: {flow:.0f}"
    ).add_to(truck_layer if mode == "truck" else ship_layer)

# Save cache
with open(CACHE_FILE, "w") as f:
    json.dump(route_cache, f)

# -----------------------------
# Add nodes
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

folium.LayerControl().add_to(m)

m.save("optimized_realistic_network.html")

print("Map saved as optimized_realistic_network.html")