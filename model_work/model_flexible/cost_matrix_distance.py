import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from math import radians, sin, cos, sqrt, atan2

# --- Config ---
MAX_LAND_DISTANCE_KM = 3219  # set to None to disable the cap
BLOCK_HORMUZ = True  # set to True to block t80
HORMUZ_NODES = ["t80"]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    c = 2*atan2(sqrt(a), sqrt(1-a))
    return R * c

# --- Load nodes (with landmass column) ---
nodes = pd.read_csv("model_work/DataFiles_flexible/nodes.csv").set_index('node_id')


# --- Distance-to-cost interpolation (onshore) ---
distance_cost_df = pd.read_csv("model_work/DataFiles_flexible/onshore_cost.csv")
interp_cost = interp1d(distance_cost_df['distance'],
                       distance_cost_df['cost'],
                       fill_value='extrapolate')

# --- Sea cost matrix (T -> T, region-based) ---
sea_cost = pd.read_csv("model_work/DataFiles_flexible/shippingcost.csv", index_col='Cluster')
sea_cost = sea_cost.combine_first(sea_cost.T)

# --- Initialize ---
N = nodes.index.tolist()
c = pd.DataFrame(np.inf, index=N, columns=N)

# --- Helper: land-transport cost between two nodes ---
def land_cost(i, j):
    """Land cost if same landmass and within MAX_LAND_DISTANCE_KM. Else inf."""
    if nodes.loc[i, 'landmass'] != nodes.loc[j, 'landmass']:
        return np.inf
    d = haversine(nodes.loc[i, 'lat'], nodes.loc[i, 'lon'],
                  nodes.loc[j, 'lat'], nodes.loc[j, 'lon'])
    if MAX_LAND_DISTANCE_KM is not None and d > MAX_LAND_DISTANCE_KM:
        return np.inf
    return float(interp_cost(d))

# --- Fill costs ---
for i in N:
    for j in N:
        if i == j:
            continue

        ti, tj = nodes.loc[i, 'type'], nodes.loc[j, 'type']

        # Infeasible by design
        if ti == 'production' and tj == 'production':  continue
        if ti == 'transit'    and tj == 'production':  continue
        if ti == 'offtake'    and tj in ('offtake', 'transit'):  continue

        # Land edges: P->T, P->O, T->O  (same landmass, haversine-based, distance-capped)
        if (ti == 'production' and tj in ('transit', 'offtake')) or \
           (ti == 'transit'    and tj == 'offtake'):
            c.loc[i, j] = land_cost(i, j)
            continue

        # Sea edges: T->T (still region-based)
        if ti == 'transit' and tj == 'transit':
            try:
                val = sea_cost.loc[nodes.loc[i, 'region'], nodes.loc[j, 'region']]
                c.loc[i, j] = float(val) if not pd.isna(val) else np.inf
            except KeyError:
                c.loc[i, j] = np.inf
            continue

# --- Apply manual overrides ---
unavailable   = pd.read_csv("model_work/DataFiles_flexible/illegalconnection.csv")
transit_only  = pd.read_csv("model_work/DataFiles_flexible/transit_only_production.csv")

for _, row in unavailable.iterrows():
    c.loc[row['i'], row['j']] = np.inf

offtake_nodes = nodes.index[nodes['type'] == 'offtake'].tolist()
for node_id in transit_only['node_id']:
    c.loc[node_id, offtake_nodes] = np.inf


# --- Summary ---
n_finite = np.isfinite(c.values).sum()
print(f"Finite arcs: {n_finite} / {c.size} "
      f"(land cap: {MAX_LAND_DISTANCE_KM} km)")

# --- Hormuz blocking ---
if BLOCK_HORMUZ:
    for node in HORMUZ_NODES:
        if node in N:
            for j in N:
                c.loc[node, j] = np.inf
                c.loc[j, node] = np.inf
print("\nt80 row (t80 -> j), finite only:")
row = c.loc["t80"]
print(row[np.isfinite(row)].to_string())

print("\nt80 column (i -> t80), finite only:")
col = c["t80"]
print(col[np.isfinite(col)].to_string())

c.to_csv("model_work/DataFiles_flexible/cost_matrix_hormuz.csv")