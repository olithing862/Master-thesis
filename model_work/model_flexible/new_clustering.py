import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

ammonia_df1 = pd.read_csv(r"/Users/oliviathingvad/Master-thesis/Public-Global-Port-Optimisation/Input Data/c_NH3_cost_2.6.csv")
ammonia_df1 = ammonia_df1[ammonia_df1["Max_capacity"] > 0]

# --- Exclusion filter ---
def exclude_region(row):
    lat, lon = row["Latitude"], row["Longitude"]
    if lat > 55 and lon > 28:           # Russia
        return True
    if lat > 59 and -75 < lon < -10:    # Greenland
        return True
    if lat > 65 and -141 < lon < -60:   # North Canada
        return True
    if lat > 54 and lon < -130:         # Alaska
        return True
    if -1 < lat < 8 and 72 < lon < 74:  # Maldives
        return True
    if 38.8 < lat < 41.2 and 8.0 < lon < 10.0:  # Sardinia
        return True
    if -26 < lat < -12 and 43 < lon < 51:  # Madagascar
        return True
    if -22 < lat < -15 and -180 < lon < -170:  # Tonga
        return True
    # Indonesia - exclude everything except Java and Papua
    if -11 < lat <= 6 and 95 < lon < 141:
        if not (-9 < lat < -5.5 and 105 < lon < 115):  # Java
            if not (-9 < lat < 0 and 130 < lon < 141):  # Papua
                return True
    return False


before = len(ammonia_df1)
ammonia_df1 = ammonia_df1[~ammonia_df1.apply(exclude_region, axis=1)]
print(f"Removed {before - len(ammonia_df1)} rows in excluded regions")
print(f"Total capacity before clustering: {ammonia_df1['Max_capacity'].sum():.0f} tonnes/year")

# --- 3D cartesian coordinates ---
lat_rad = np.radians(ammonia_df1["Latitude"])
lon_rad = np.radians(ammonia_df1["Longitude"])
ammonia_df1["X"] = np.cos(lat_rad) * np.cos(lon_rad)
ammonia_df1["Y"] = np.cos(lat_rad) * np.sin(lon_rad)
ammonia_df1["Z"] = np.sin(lat_rad)

# --- Cluster ---
n_clusters = 100
kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=50)
ammonia_df1["cluster"] = kmeans.fit_predict(ammonia_df1[["X", "Y", "Z"]])

# --- Pick cheapest site per cluster as representative ---
cheapest_idx = ammonia_df1.groupby("cluster")["LCOA"].idxmin()
best_ammonia = ammonia_df1.loc[cheapest_idx].copy()

# --- Sum all capacities in each cluster ---
best_ammonia["Max_capacity"] = ammonia_df1.groupby("cluster")["Max_capacity"].sum().values
best_ammonia = best_ammonia.reset_index(drop=True)
best_ammonia["capacity_share_percent"] = (
    best_ammonia["Max_capacity"] / best_ammonia["Max_capacity"].sum() * 100
)
print(f"Total capacity: {best_ammonia['Max_capacity'].sum():.0f} tonnes/year")
best_ammonia.to_csv("model_work/Datafiles_flexible/production_sites_clustered_100.csv", index=False)