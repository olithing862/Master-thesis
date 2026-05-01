import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    c = 2*atan2(sqrt(a), sqrt(1-a))
    return R * c

# --- Load nodes (now with landmass column) ---
nodes = pd.read_csv("model_work_0904/DataFiles/nodes.csv").set_index('node_id')

# --- Distance-to-cost interpolation (onshore) ---
distance_cost_df = pd.read_csv("model_work_0904/DataFiles/onshore_cost.csv")
interp_cost = interp1d(distance_cost_df['distance'],
                       distance_cost_df['cost'],
                       fill_value='extrapolate')

# --- Sea cost matrix (T -> T) ---
sea_cost = pd.read_csv("model_work_0904/DataFiles/shippingcost.csv", index_col='Cluster')
sea_cost = sea_cost.combine_first(sea_cost.T)

# --- Initialize ---
N = nodes.index.tolist()
c = pd.DataFrame(np.inf, index=N, columns=N)

# --- Helper: land-transport cost between two nodes ---
def land_cost(i, j):
    """Return land transport cost only if same landmass AND same region, else inf."""
    if nodes.loc[i, 'landmass'] != nodes.loc[j, 'landmass']:
        return np.inf
    if nodes.loc[i, 'region'] != nodes.loc[j, 'region']:
        return np.inf
    d = haversine(nodes.loc[i, 'lat'], nodes.loc[i, 'lon'],
                  nodes.loc[j, 'lat'], nodes.loc[j, 'lon'])
    return float(interp_cost(d))

# --- Fill costs ---
for i in N:
    for j in N:
        if i == j:
            continue

        ti, tj = nodes.loc[i, 'type'], nodes.loc[j, 'type']

        # Infeasible by design
        if ti == 'production' and tj == 'production':  continue  # stays inf
        if ti == 'transit'    and tj == 'production':  continue
        if ti == 'offtake'    and tj in ('offtake', 'transit'):  continue

        # Land edges: P->T, P->O, T->O  (same landmass AND same region, haversine)
        if (ti == 'production' and tj in ('transit', 'offtake')) or \
           (ti == 'transit'    and tj == 'offtake'):
            c.loc[i, j] = land_cost(i, j)
            continue

        # Sea edges: T->T (use region-based sea cost matrix)
        if ti == 'transit' and tj == 'transit':
            try:
                val = sea_cost.loc[nodes.loc[i, 'region'], nodes.loc[j, 'region']]
                c.loc[i, j] = float(val) if not pd.isna(val) else np.inf
            except KeyError:
                c.loc[i, j] = np.inf
            continue

# --- Apply manual overrides ---
unavailable   = pd.read_csv("model_work_0904/DataFiles/illegalconnection.csv")
transit_only  = pd.read_csv("model_work_0904/DataFiles/transit_only_production.csv")

for _, row in unavailable.iterrows():
    c.loc[row['i'], row['j']] = np.inf

offtake_nodes = nodes.index[nodes['type'] == 'offtake'].tolist()
for node_id in transit_only['node_id']:
    c.loc[node_id, offtake_nodes] = np.inf

c.to_csv("model_work_0904/DataFiles/cost_matrix_4.csv")