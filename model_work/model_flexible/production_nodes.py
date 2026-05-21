import sys
sys.path.append("/Users/oliviathingvad/Master-thesis/model_work")
import pandas as pd
import folium

prod_df = pd.read_csv("/Users/oliviathingvad/Master-thesis/model_work/DataFiles_flexible/production_nodes_100.csv")

def assign_region(lat, lon): 
    if -45 < lat < -9 and 112 < lon < 129:
        return "West Australia"
    if -45 < lat < -9 and 129 < lon < 155:
        return "East Australia"
    if 48 < lat < 72 and -141 < lon < -114:
        return "NA West Coast"
    if 41 < lat < 84 and -114 < lon < -50:
        return "NA East Coast"
    if 50 < lat < 72 and -180 < lon < -129:
        return "NA West Coast"
    if 31 < lat < 50 and -125 < lon < -114:
        return "NA West Coast"
    if 25 < lat < 31 and -107 < lon < -80.5:
        return "Gulf of Mexico"
    if 31 < lat < 50 and -114 < lon < -66:
        return "NA East Coast"
    if 14 < lat < 33 and -118 < lon < -103:
        return "NA West Coast"
    if 14 < lat < 33 and -103 < lon < -86:
        return "Gulf of Mexico"
    if 0 < lat < 25 and -90 < lon < -58:
        return "N Latin America"
    if -56 < lat < 13 and -82 < lon < -34:
        return "S Latin America"
    if 55 < lat < 72 and 4 < lon < 32:
        return "Nordics"
    if 28 < lat < 48 and -10 < lon < 42:
        return "Mediterranean"
    if 12 < lat < 32 and 32 < lon < 50:
        return "Red Sea"
    if 5 < lat < 50 and 42 < lon < 82:
        return "Middle East & India"
    if 30 < lat < 46 and 125 < lon < 146:
        return "Japan & South Korea"
    if 18 < lat < 55 and 73 < lon < 135:
        return "China & Hong Kong"
    if -10 < lat < 28 and 92 < lon < 129:
        return "South-east Asia"
    if -35 < lat < 22 and 22 < lon < 52:
        return "East Africa"
    if -20 < lat < 22 and -18 < lon < 22:
        return "West Africa"
    if 35 < lat < 72 and -10 < lon < 32:
        return "Western Europe"
    if 48 < lat < 72 and -141 < lon <= -114:   # Canada West (fix boundary)
        return "NA West Coast"
    if -30 < lat < 28 and -18 < lon < 22:      # West Africa (extended)
        return "West Africa"
    if 18 < lat < 55 and 73 < lon < 155:       # China (extended east)
        return "China & Hong Kong"
    if -45 < lat < -9 and 129 < lon < 178:     # East Australia + NZ (extended)
        return "East Australia"
    if 14 < lat < 33 and -118 < lon < -86:     # Mexico combined
        return "Gulf of Mexico"
    return "Other"
def assign_landmass(lat, lon):
    if -45 < lat < -9 and 112 < lon < 155:
        return "Australia"
    if -47 < lat < -34 and 166 < lon < 178:
        return "NewZealand"
    if 30 < lat < 46 and 124 < lon < 146:
        return "Japan"
    if 4 < lat < 21 and 116 < lon < 127:
        return "Philippines"
    if -9 < lat < -5.5 and 105 < lon < 115:
        return "Indonesia_Java"
    if -9 < lat < 0 and 130 < lon < 141:
        return "Indonesia_Papua"
    if 15 < lat < 72 and -168 < lon < -52:
        return "NorthAmerica"
    if -56 < lat < 13 and -82 < lon < -34:
        return "SouthAmerica"
    return "Eurasia_Africa"

prod_df["landmass"] = prod_df.apply(lambda r: assign_landmass(r["lat"], r["lon"]), axis=1)
print(prod_df["landmass"].value_counts())
prod_df["region"] = prod_df.apply(lambda r: assign_region(r["lat"], r["lon"]), axis=1)
print(prod_df["region"].value_counts())
print(prod_df[prod_df["region"] == "Other"][["node_id", "lat", "lon"]])
prod_df.to_csv("/Users/oliviathingvad/Master-thesis/model_work/DataFiles_flexible/production_nodes_100.csv", index=False)
print("Saved updated nodes")
# --- Plot ---
m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB positron")
max_cap = prod_df["capacity_share_percent"].max() or 1

for _, row in prod_df.iterrows():
    radius = 3 + 12 * (row["capacity_share_percent"] / max_cap)
    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=radius,
        color="#b8860b", fill=True, fill_color="#b8860b", fill_opacity=0.8,
        tooltip=(
            f"{row['region']}<br>"
            f"Node: {row['node_id']}<br>"
            f"Capacity share: {row['capacity_share_percent']:.2f}%"
        ),
    ).add_to(m)

m.save("production_nodes.html")
print("Saved to production_nodes.html")

nodes_df = pd.read_csv("/Users/oliviathingvad/Master-thesis/model_work/Datafiles_flexible/nodes_1.csv")

# Keep only columns matching nodes format
prod_df = prod_df[["node_id", "Location", "lat", "lon", "region", "industry", "type", "landmass"]]

# Filter only green ammonia nodes
green_nodes = prod_df[prod_df["node_id"].str.match("^p\d")].copy()

# Create fossil copies
fossil_nodes = green_nodes.copy()
fossil_nodes["node_id"] = fossil_nodes["node_id"].str.replace("^p", "pf", regex=True)
fossil_nodes["industry"] = "Fossil"

# Combine all
combined = pd.concat([nodes_df, green_nodes, fossil_nodes], ignore_index=True)
combined.to_csv("/Users/oliviathingvad/Master-thesis/model_work/Datafiles_flexible/nodes_1.csv", index=False)
print(f"Total nodes: {len(combined)}")
print(combined["type"].value_counts())