import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from math import radians, sin, cos, sqrt, atan2

# --- Haversine function ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    c = 2*atan2(sqrt(a), sqrt(1-a))
    return R * c

# --- Load nodes ---
nodes = pd.read_csv("model_work_0904/nodes.csv")  # node_id,name,lat,lon,type,industry,region
nodes = nodes.set_index('node_id')

# --- Distance-to-cost interpolation (P -> T, P -> O, T -> O) ---
distance_cost_df = pd.read_csv("model_work_0904/onshore_cost.csv")  # distance,cost
interp_cost = interp1d(distance_cost_df['distance'],
                       distance_cost_df['cost'],
                       fill_value='extrapolate')

# --- Sea cost matrix (T -> T) ---
sea_cost = pd.read_csv("model_work_0904/shippingcost.csv", index_col='Cluster')
sea_cost = sea_cost.combine_first(sea_cost.T)

# --- Initialize cost matrix ---
N = nodes.index.tolist()
c = pd.DataFrame(np.inf, index=N, columns=N)

# --- Fill costs ---
for i in N:
    for j in N:
        if i == j:
            continue

        type_i   = nodes.loc[i, 'type']
        type_j   = nodes.loc[j, 'type']
        region_i = nodes.loc[i, 'region']
        region_j = nodes.loc[j, 'region']
        lat_i, lon_i = nodes.loc[i, 'lat'], nodes.loc[i, 'lon']
        lat_j, lon_j = nodes.loc[j, 'lat'], nodes.loc[j, 'lon']

        # P -> P or T -> P: infeasible
        if (type_i == 'production' and type_j == 'production') or \
           (type_i == 'transit'    and type_j == 'production'):
            c.loc[i, j] = np.inf
            continue

        # P -> T: same region only, haversine distance cost
        if type_i == 'production' and type_j == 'transit':
            if region_i != region_j:
                c.loc[i, j] = np.inf
            else:
                d = haversine(lat_i, lon_i, lat_j, lon_j)
                c.loc[i, j] = float(interp_cost(d))
            continue

        # P -> O: same region only, haversine distance cost
        if type_i == 'production' and type_j == 'offtake':
            if region_i != region_j:
                c.loc[i, j] = np.inf
            else:
                d = haversine(lat_i, lon_i, lat_j, lon_j)
                c.loc[i, j] = float(interp_cost(d))
            continue

        # T -> T: sea region cost matrix
        if type_i == 'transit' and type_j == 'transit':
            try:
                val = sea_cost.loc[region_i, region_j]
                c.loc[i, j] = float(val) if not pd.isna(val) else np.inf
            except KeyError:
                c.loc[i, j] = np.inf
            continue

        # O -> O or O -> T: infeasible
        if type_i == 'offtake' and type_j in ['offtake', 'transit']:
            c.loc[i, j] = np.inf
            continue

        # T -> O: same region only, haversine distance cost
        if type_i == 'transit' and type_j == 'offtake':
            if region_i != region_j:
                c.loc[i, j] = np.inf
            else:
                d = haversine(lat_i, lon_i, lat_j, lon_j)
                c.loc[i, j] = float(interp_cost(d))
            continue

# --- Save cost matrix ---
c.to_csv("model_work_0904/cost_matrix.csv") 

def compute_capacity_shares(filepath):
    # Read CSV
    df = pd.read_csv(filepath)
    
    # Sum total capacity
    total_capacity = df["Max_capacity"].sum()
    
    # Compute percentage share
    df["capacity_share"] = df["Max_capacity"] / total_capacity
    
    # Optional: percentage in %
    df["capacity_share_percent"] = df["capacity_share"] * 100
    
    return df, total_capacity

filepath = 'production_sites_clustered2050.csv'
capacity_shares_df, total_capacity = compute_capacity_shares(filepath)
nodes = pd.read_csv("model_work_0904/nodes.csv")  # node_id,name,lat,lon,type,industry,region

# Filter only production nodes
p_nodes = nodes[nodes['type'] == 'production'].copy()

# Merge capacity shares on location/index
# Make sure keys match: e.g., Index in capacity_shares_df and name/location in nodes
p_nodes = p_nodes.merge(capacity_shares_df[["Index", "capacity_share_percent"]],
                        left_on='Location', right_on='Index',
                        how='left')

# Keep only relevant columns for your production CSV
production_csv = p_nodes[['node_id', 'Location', 'lat', 'lon', 'region', 'industry', 'type', 'capacity_share_percent']]

# Save
production_csv.to_csv("model_work_0904/production_nodes.csv", index=False)