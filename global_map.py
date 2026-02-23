import pandas as pd
import folium
import searoute as sr

# --- 1. Load CSV ---
df = pd.read_csv("transit_points_1.csv")

# --- 2. Create lookup dictionary ---
ports = {}
for _, row in df.iterrows():
    ports[row["Nr"]] = {
        "name": row["Location"],
        "lat": row["Latitude"],
        "lon": row["Longitude"],
        "connections": row["connection_shipping"]
    }

# --- 3. Create map ---
m = folium.Map(location=[20, 0], zoom_start=2)

# --- 4. Add port markers ---
for port_id, port in ports.items():
    folium.Marker(
        [port["lat"], port["lon"]],
        popup=f"{port_id}: {port['name']}"
    ).add_to(m)

# --- 5. Plot sea routes ---
for port_id, port in ports.items():

    if pd.isna(port["connections"]):
        continue

    connections = str(port["connections"]).split(";")

    for conn in connections:
        conn = int(conn)

        # Avoid duplicate plotting (only plot if destination ID > origin ID)
        if conn <= port_id:
            continue

        origin = [port["lon"], port["lat"]]  # SeaRoute needs [lon, lat]
        dest = [ports[conn]["lon"], ports[conn]["lat"]]

        route = sr.searoute(origin, dest)
        coords = route["geometry"]["coordinates"]

        # Convert to (lat, lon) for Folium
        route_latlon = [(lat, lon) for lon, lat in coords]

        # Add exact port coordinates to force visual connection
        route_latlon.insert(0, (port["lat"], port["lon"]))
        route_latlon.append((ports[conn]["lat"], ports[conn]["lon"]))

        folium.PolyLine(route_latlon, weight=2).add_to(m)

# --- 6. Save ---
m.save("global_shipping_network.html")