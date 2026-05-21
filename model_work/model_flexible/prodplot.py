import pandas as pd
import numpy as np
import folium

prod_df = pd.read_csv("/Users/oliviathingvad/Master-thesis/model_work/DataFiles_flexible/production_nodes_100.csv")

print(f"Nodes: {len(prod_df)}")

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