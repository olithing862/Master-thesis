import pandas as pd
import itertools
import openrouteservice
import searoute as sr
import os
import json
import math
import time

# =====================================================
# 1️⃣ LOAD NODES
# =====================================================
nodes_df = pd.read_csv("shipping.csv", dtype=str)
nodes_df["region"] = nodes_df["region"].str.replace(",", "", regex=False)

nodes = {}
for _, row in nodes_df.iterrows():
    nodes[row["node_id"]] = {
        "lat": float(row["Latitude"]),
        "lon": float(row["Longitude"]),
        "region": row["region"]
    }

all_nodes = list(nodes.keys())
harbours = [n for n in nodes if n.startswith("t")]

# =====================================================
# 2️⃣ DISTANCE FUNCTION
# =====================================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# =====================================================
# 3️⃣ INITIALIZE ORS
# =====================================================
ors = openrouteservice.Client(key=os.getenv("ORS_API_KEY"))

# =====================================================
# 4️⃣ SHIPPING NETWORK (ONE DIRECTION ONLY)
# =====================================================
shipping_edges = []

print("Building maritime routes...")

for from_id, to_id in itertools.combinations(harbours, 2):

    origin = nodes[from_id]
    dest = nodes[to_id]

    try:
        route = sr.searoute(
            [origin["lon"], origin["lat"]],
            [dest["lon"], dest["lat"]]
        )

        distance_km = route["properties"]["length"]
        geometry = route["geometry"]

        shipping_edges.append({
            "from_id": from_id,
            "to_id": to_id,
            "mode": "ship",
            "distance_km": distance_km,
            "geometry": json.dumps(geometry)
        })

        print(f"Ship {from_id} → {to_id}: {distance_km:.0f} km")

    except Exception as e:
        print(f"Shipping failed {from_id} → {to_id}: {e}")

shipping_df = pd.DataFrame(shipping_edges)
print(f"Total shipping edges: {len(shipping_df)}")

# =====================================================
# 5️⃣ TRUCK NETWORK (≤ 400 km, ONE DIRECTION ONLY)
# =====================================================
valid_truck_edges = []

print("Testing truck connectivity (≤ 400 km)...")

for from_id, to_id in itertools.combinations(all_nodes, 2):

    origin = nodes[from_id]
    dest = nodes[to_id]

    # Pre-filter
    gc_dist = haversine(origin["lat"], origin["lon"],
                        dest["lat"], dest["lon"])

    if gc_dist > 500:
        continue

    try:
        route = ors.directions(
            coordinates=[
                (origin["lon"], origin["lat"]),
                (dest["lon"], dest["lat"])
            ],
            profile="driving-car",
            format="geojson"
        )

        distance_km = route["features"][0]["properties"]["summary"]["distance"] / 1000

        if distance_km <= 400:

            geometry = route["features"][0]["geometry"]

            valid_truck_edges.append({
                "from_id": from_id,
                "to_id": to_id,
                "mode": "truck",
                "distance_km": distance_km,
                "geometry": json.dumps(geometry)
            })

            print(f"Truck OK: {from_id} → {to_id} ({distance_km:.0f} km)")

        time.sleep(1)

    except:
        continue

truck_df = pd.DataFrame(valid_truck_edges)
print(f"Total truck edges (≤400 km): {len(truck_df)}")

# =====================================================
# 6️⃣ COMBINE
# =====================================================
edges_final = pd.concat([shipping_df, truck_df], ignore_index=True)
edges_final.to_csv("edges_complete_network.csv", index=False)

print("Directed multimodal network successfully built.")