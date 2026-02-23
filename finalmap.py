import pandas as pd
import folium
import openrouteservice
import openrouteservice.exceptions
import os
import searoute as sr
import time

# -----------------------------
# Load files
# -----------------------------
nodes_df = pd.read_csv("shipping.csv", dtype=str)
edges_df = pd.read_csv("edges.csv", dtype=str)

# Ensure distance column exists
if "distance_km" not in edges_df.columns:
    edges_df["distance_km"] = None

# -----------------------------
# Build node dictionary
# -----------------------------
nodes = {}
for _, row in nodes_df.iterrows():
    nodes[row["node_id"]] = {
        "name": row["Location"],
        "lat": float(row["Latitude"]),
        "lon": float(row["Longitude"])
    }

# -----------------------------
# Initialize routing
# -----------------------------
ors_client = openrouteservice.Client(key=os.getenv("ORS_API_KEY"))

# -----------------------------
# Create map
# -----------------------------
m = folium.Map(location=[20, 0], zoom_start=2)

truck_layer = folium.FeatureGroup(name="Truck")
ship_layer = folium.FeatureGroup(name="Shipping")

truck_layer.add_to(m)
ship_layer.add_to(m)

# -----------------------------
# Add markers (different colors)
# -----------------------------
for node_id, node in nodes.items():

    if node_id.startswith("t"):
        color = "blue"      # Transit nodes
    elif node_id.startswith("os"):
        color = "red"    # Production (offtake) nodes
    elif node_id.startswith("p"):
        color = "green"
    else:
        color = "gray"   # Unknown type

    folium.Marker(
        [node["lat"], node["lon"]],
        icon=folium.Icon(color=color),
        popup=f"{node_id}: {node['name']}"
    ).add_to(m)

# -----------------------------
# Process edges
# -----------------------------
for idx, edge in edges_df.iterrows():

    # Skip if already computed
    if pd.notna(edge["distance_km"]):
        continue

    from_id = edge["from_id"]
    to_id = edge["to_id"]
    mode = edge["mode"]

    if from_id not in nodes or to_id not in nodes:
        print(f"Missing node in edge {from_id} → {to_id}")
        continue

    origin = nodes[from_id]
    dest = nodes[to_id]

    # =============================
    # TRUCK ROUTES
    # =============================
    if mode == "truck":
        try:
            route = ors_client.directions(
                coordinates=[(origin["lon"], origin["lat"]),
                             (dest["lon"], dest["lat"])],
                profile="driving-hgv",
                format="geojson"
            )

        except openrouteservice.exceptions.ApiError as e:
            if "Could not find routable point" in str(e):
                print(f"Retrying {from_id} → {to_id} with larger radius")

                try:
                    route = ors_client.directions(
                        coordinates=[(origin["lon"], origin["lat"]),
                                     (dest["lon"], dest["lat"])],
                        profile="driving-hgv",
                        format="geojson",
                        radiuses=[5000, 5000]
                    )
                except Exception as e2:
                    print(f"Truck route failed {from_id} → {to_id}: {e2}")
                    continue
            else:
                print(f"Truck route failed {from_id} → {to_id}: {e}")
                continue

        # Extract geometry
        coords = route["features"][0]["geometry"]["coordinates"]
        route_latlon = [(lat, lon) for lon, lat in coords]

        # Extract distance (meters → km)
        distance_km = route["features"][0]["properties"]["summary"]["distance"] / 1000
        edges_df.loc[idx, "distance_km"] = distance_km

        print(f"Truck {from_id} → {to_id}: {distance_km:.1f} km")

        # Plot
        folium.PolyLine(
            route_latlon,
            color="red",
            weight=3,
            tooltip=f"{origin['name']} → {dest['name']} ({distance_km:.0f} km)"
        ).add_to(truck_layer)

        # Respect rate limit
        time.sleep(1)

    # =============================
    # SHIPPING ROUTES
    # =============================
    elif mode == "ship":
        try:
            route = sr.searoute(
                [origin["lon"], origin["lat"]],
                [dest["lon"], dest["lat"]]
            )

            coords = route["geometry"]["coordinates"]
            route_latlon = [(lat, lon) for lon, lat in coords]

            distance_km = route["properties"]["length"]
            edges_df.loc[idx, "distance_km"] = distance_km

            print(f"Ship {from_id} → {to_id}: {distance_km:.1f} km")

            folium.PolyLine(
                route_latlon,
                color="blue",
                weight=2,
                tooltip=f"{origin['name']} → {dest['name']} ({distance_km:.0f} km)"
            ).add_to(ship_layer)

        except Exception as e:
            print(f"Shipping route failed {from_id} → {to_id}: {e}")

    # Save progressively (quota safe)
    edges_df.to_csv("edges_with_distances.csv", index=False)

# -----------------------------
# Finish map
# -----------------------------
folium.LayerControl().add_to(m)
m.save("multimodal_network.html")

print("Finished. Distances saved to edges_with_distances.csv")