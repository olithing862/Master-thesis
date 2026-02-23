import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from functionforedges import create_truck_edges, create_shipping_edges
from circlepoints import great_circle_points
# --- Load data ---
steel = pd.read_csv("steelnodes.csv")
shipping = pd.read_csv("shipping.csv")
transit = pd.read_csv("transit_points.csv")

# Add type column
steel["type"] = "Steel"
shipping["type"] = "Shipping"
transit["type"] = "Transit"
manual_fix = {
    "Luleå (Sweden)": "Europe",
    "Colón (Panama)": "North America",
    "Tangier (Morocco)": "Africa",
    "Durban (South Africa)": "Africa",
    "Mejillones (Chile)": "South America",
    "Mariehamn (Finland)": "Europe"
}


# Combine all
df = pd.concat([steel, shipping, transit], ignore_index=True)

# Convert to GeoDataFrame
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.Longitude, df.Latitude),
    crs="EPSG:4326"
)
# Load higher resolution world map
world = gpd.read_file(
    "https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_admin_0_countries.zip"
)

# Make sure CRS matches
world = world.to_crs("EPSG:4326")
gdf = gdf.to_crs("EPSG:4326")

# Spatial join
gdf = gpd.sjoin(
    gdf,
    world[["CONTINENT", "geometry"]],
    how="left",
    predicate="intersects"
)

gdf.rename(columns={"CONTINENT": "Continent"}, inplace=True)
gdf.loc[gdf["Location"].isin(manual_fix.keys()), "Continent"] = \
    gdf["Location"].map(manual_fix)

# Combine steel + shipping offtake for truck connections
offtake_df = pd.concat([steel, shipping], ignore_index=True)

# Create truck edges (Transit → Offtake)
truck_edges = create_truck_edges(transit, offtake_df)

# Create shipping edges (Transit → Transit)
shipping_edges = create_shipping_edges(transit)

# Combine all edges
edges = pd.concat([truck_edges, shipping_edges], ignore_index=True)

print(edges.head())

# edges = create_truck_edges(
#     gdf,
#     detour_factor=1.25,
#     truck_cost_per_km=2.0,
#     max_distance_km=6000   # optional
# )
print(edges.head())
# --- Create figure ---
fig, ax = plt.subplots(figsize=(14, 7))
ax.set_facecolor("#EAF2F8")

world.plot(
    ax=ax,
    color="#F4F6F7",
    edgecolor="#B3B6B7",
    linewidth=0.6
)

# --- Plot each type separately ---
colors = {
    "Steel": "#C0392B",      # red
    "Shipping": "#1F618D",   # blue
    "Transit": "#0D7C36"     # green
}

sizes = {
    "Steel": 100,
    "Shipping": 80,
    "Transit": 80
}
coord_lookup = gdf.set_index("Location")[["Latitude", "Longitude"]]
for _, row in edges.iterrows():

    lat1 = coord_lookup.loc[row["from"], "Latitude"]
    lon1 = coord_lookup.loc[row["from"], "Longitude"]
    lat2 = coord_lookup.loc[row["to"], "Latitude"]
    lon2 = coord_lookup.loc[row["to"], "Longitude"]

    if row["mode"] == "truck":
        ax.plot(
            [lon1, lon2],
            [lat1, lat2],
            color="#8D6E63",
            linewidth=0.8,
            alpha=0.9
        )

    else:  # shipping
        lats, lons = great_circle_points(lat1, lon1, lat2, lon2)

        ax.plot(
            lons,
            lats,
            color="#1F618D",
            linewidth=0.8,
            alpha=0.2
        )


for node_type in gdf["type"].unique():
    subset = gdf[gdf["type"] == node_type]
    subset.plot(
        ax=ax,
        markersize=sizes[node_type],
        color=colors[node_type],
        edgecolor="white",
        linewidth=0.8,
        alpha=0.9,
        label=node_type
    )
ax.set_xlim(-180, 180)
ax.set_ylim(-60, 100)

# Remove axes
ax.set_axis_off()

# Legend
plt.legend(frameon=True)

# Title
plt.title(
    "Global Steel, Shipping and Transit Nodes",
    fontsize=18,
    weight="bold",
    pad=20
)

plt.tight_layout()
plt.show()
