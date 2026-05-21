import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

# --- Load landmass polygons ---
# --- Load landmass polygons ---
landmasses = gpd.read_file("/Users/oliviathingvad/Master-thesis/ne_10m_land/ne_10m_land.shp")

# Project to metric CRS for buffering, then back to WGS84
landmasses_buffered = landmasses.to_crs("EPSG:3857")
landmasses_buffered["geometry"] = landmasses_buffered.geometry.buffer(10000)  # 10km in metres
landmasses_buffered = landmasses_buffered.to_crs("EPSG:4326")
landmasses_buffered["polygon_id"] = landmasses_buffered.index

# --- Load nodes ---
nodes_df = pd.read_csv("/Users/oliviathingvad/Master-thesis/model_work/Datafiles_flexible/nodes.csv")

# --- Spatial join ---
nodes_gdf = gpd.GeoDataFrame(
    nodes_df,
    geometry=[Point(lon, lat) for lat, lon in zip(nodes_df["lon"], nodes_df["lat"])],
    crs="EPSG:4326"
)

# Use nearest instead of within — assigns each node to its closest polygon
joined = gpd.sjoin_nearest(nodes_gdf, landmasses_buffered[["geometry", "polygon_id"]], how="left")
# --- Assign polygon_id as new landmass ---
nodes_df["landmass"] = joined["polygon_id"].values

# --- Save ---
nodes_df.to_csv("/Users/oliviathingvad/Master-thesis/model_work/Datafiles_flexible/nodes_1.csv", index=False)
print(nodes_df["landmass"].value_counts())
print(f"Saved nodes_1.csv with {len(nodes_df)} nodes")