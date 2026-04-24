import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

ammonia_df1 = pd.read_csv(r"/Users/oliviathingvad/Master-thesis/Public-Global-Port-Optimisation/Input Data/c_NH3_cost_2.6.csv")

# Filter
ammonia_df1 = ammonia_df1[ammonia_df1["Max_capacity"] > 0]
#ammonia_df1 = ammonia_df1.nsmallest(4000, "LCOA")
print(ammonia_df1)
print(f"Total capacity before clustering: {ammonia_df1['Max_capacity'].sum():.0f} tonnes/year")
# Convert lat/lon to 3D cartesian coordinates on unit sphere

lat_rad = np.radians(ammonia_df1["Latitude"])
lon_rad = np.radians(ammonia_df1["Longitude"])
ammonia_df1["X"] = np.cos(lat_rad) * np.cos(lon_rad)
ammonia_df1["Y"] = np.cos(lat_rad) * np.sin(lon_rad)
ammonia_df1["Z"] = np.sin(lat_rad)

# Cluster on X, Y, Z
n_clusters = 50

kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=50)
ammonia_df1["cluster"] = kmeans.fit_predict(ammonia_df1[["X", "Y", "Z"]])

print(ammonia_df1.head())
# Pick cheapest site per cluster as representative
cheapest_idx = ammonia_df1.groupby("cluster")["LCOA"].idxmin()
best_ammonia = ammonia_df1.loc[cheapest_idx].copy()

# Sum all capacities in each cluster
best_ammonia["Max_capacity"] = ammonia_df1.groupby("cluster")["Max_capacity"].sum().values
best_ammonia = best_ammonia.reset_index(drop=True)

# Capacity share as percentage of total
# best_ammonia["capacity_share_percent"] = (
#     best_ammonia["Max_capacity"] / best_ammonia["Max_capacity"].sum() * 100
# )

# Print total capacity
print(f"Total capacity: {best_ammonia['Max_capacity'].sum():.0f} tonnes/year")

# Drop helper columns before saving
#best_ammonia = best_ammonia.drop(columns=["X", "Y", "Z", "cluster"])
best_ammonia.to_csv("model_work/Datafiles_base/production_sites_clustered.csv", index=False)

