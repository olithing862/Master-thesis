import pandas as pd
import itertools
import openrouteservice
import os
import time

# ---------------------------------
# Load nodes
# ---------------------------------
nodes_df = pd.read_csv("shipping.csv", dtype=str)

nodes = {}
for _, row in nodes_df.iterrows():
    nodes[row["node_id"]] = {
        "lat": float(row["Latitude"]),
        "lon": float(row["Longitude"])
    }

all_nodes = list(nodes.keys())
harbours = [n for n in nodes if n.startswith("t")]

# ---------------------------------
# Initialize ORS
# ---------------------------------
ors = openrouteservice.Client(key=os.getenv("ORS_API_KEY"))

# ---------------------------------
# 1️⃣ Create FULL SHIPPING NETWORK
# ---------------------------------
ship_edges = pd.DataFrame(
    list(itertools.permutations(harbours, 2)),
    columns=["from_id", "to_id"]
)
ship_edges["mode"] = "ship"

print(f"Shipping edges created: {len(ship_edges)}")

# ---------------------------------
# 2️⃣ Create LAND-CONNECTED TRUCK NETWORK
# ---------------------------------

valid_truck_edges = []

candidate_pairs = list(itertools.combinations(all_nodes, 2))

print("Testing land connectivity...")

for from_id, to_id in candidate_pairs:

    origin = nodes[from_id]
    dest = nodes[to_id]

    # Quick geographic filter
    approx_lat_diff = abs(origin["lat"] - dest["lat"])
    approx_lon_diff = abs(origin["lon"] - dest["lon"])

    if approx_lat_diff > 40 or approx_lon_diff > 60:
        continue

    try:
        route = ors.directions(
            coordinates=[(origin["lon"], origin["lat"]),
                         (dest["lon"], dest["lat"])],
            profile="driving-car",
            format="geojson"
        )

        distance_km = route["features"][0]["properties"]["summary"]["distance"] / 1000

        # Reject absurd detours
        if distance_km < 2000:

            print(f"Truck OK: {from_id} ↔ {to_id} ({distance_km:.0f} km)")

            # Add BOTH directions using same distance
            valid_truck_edges.append({
                "from_id": from_id,
                "to_id": to_id,
                "mode": "truck",
                "distance_km": distance_km
            })

            valid_truck_edges.append({
                "from_id": to_id,
                "to_id": from_id,
                "mode": "truck",
                "distance_km": distance_km
            })

        time.sleep(1)

    except:
        continue

truck_edges = pd.DataFrame(valid_truck_edges)

print(f"Truck edges created: {len(truck_edges)}")

# ---------------------------------
# 3️⃣ Combine Networks
# ---------------------------------

edges_final = pd.concat([truck_edges, ship_edges], ignore_index=True)

edges_final.to_csv("edges_complete_network.csv", index=False)

print("Network successfully built.")

import pandas as pd
import searoute as sr
# -----------------------------
# Load data
# -----------------------------
nodes_df = pd.read_csv("shipping.csv", dtype=str)
edges_df = pd.read_csv("edges_complete_network.csv")

# Build node dictionary
nodes = {}
for _, row in nodes_df.iterrows():
    nodes[row["node_id"]] = {
        "lat": float(row["Latitude"]),
        "lon": float(row["Longitude"])
    }

# -----------------------------
# Add shipping distances only
# -----------------------------
for idx, row in edges_df.iterrows():

    # Only process ship edges
    if row["mode"] != "ship":
        continue

    # Skip if distance already exists
    if pd.notna(row["distance_km"]):
        continue

    from_id = row["from_id"]
    to_id = row["to_id"]

    origin = nodes[from_id]
    dest = nodes[to_id]

    try:
        route = sr.searoute(
            [origin["lon"], origin["lat"]],
            [dest["lon"], dest["lat"]]
        )

        distance_km = route["properties"]["length"]

        edges_df.loc[idx, "distance_km"] = distance_km

        print(f"Ship {from_id} → {to_id}: {distance_km:.0f} km")

    except Exception as e:
        print(f"Shipping failed {from_id} → {to_id}: {e}")

# -----------------------------
# Save updated file
# -----------------------------
edges_df.to_csv("edges_complete_network.csv", index=False)

print("Shipping distances successfully added.")