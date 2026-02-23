import pandas as pd
from itertools import product

from haversine import haversine

import numpy as np



def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi/2)**2 + \
        np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2

    return 2 * R * np.arcsin(np.sqrt(a))

def create_truck_edges_to_steel(transit_df, steel_df,
                                detour_factor=1.25,
                                cost_per_km=2.0):

    edges = []
    transit_lookup = transit_df.set_index("Nr")

    for _, steel in steel_df.iterrows():

        if pd.isna(steel["connection_truck"]):
            continue

        allowed_ids = [int(x) for x in str(steel["connection_truck"]).split(";")]

        for tid in allowed_ids:

            if tid not in transit_lookup.index:
                continue

            transit = transit_lookup.loc[tid]

            gc = haversine(
                transit["Latitude"], transit["Longitude"],
                steel["Latitude"], steel["Longitude"]
            )

            road_km = gc * detour_factor
            cost = road_km * cost_per_km

            edges.append({
                "mode": "truck",
                "from": transit["Location"],
                "to": steel["Location"],
                "distance_km": round(road_km, 2),
                "cost": round(cost, 2)
            })

    return pd.DataFrame(edges)


def create_truck_edges(transit_df, offtake_df,
                       detour_factor=1.25,
                       cost_per_km=2.0):

    edges = []
    transit_lookup = transit_df.set_index("Nr")

    for _, node in offtake_df.iterrows():

        if pd.isna(node["connection_truck"]):
            continue

        allowed_ids = [int(x) for x in str(node["connection_truck"]).split(";")]

        for tid in allowed_ids:

            if tid not in transit_lookup.index:
                continue

            transit = transit_lookup.loc[tid]

            gc = haversine(
                transit["Latitude"], transit["Longitude"],
                node["Latitude"], node["Longitude"]
            )

            road_km = gc * detour_factor
            cost = road_km * cost_per_km

            edges.append({
                "mode": "truck",
                "from": transit["Location"],
                "to": node["Location"],
                "distance_km": round(road_km, 2),
                "cost": round(cost, 2)
            })

    return pd.DataFrame(edges)

def create_shipping_edges(transit_df, cost_per_km=0.5):

    edges = []
    lookup = transit_df.set_index("Nr")

    for _, transit in transit_df.iterrows():

        if pd.isna(transit["connection_shipping"]):
            continue

        allowed_ids = [int(x) for x in str(transit["connection_shipping"]).split(";")]

        for tid in allowed_ids:

            if tid not in lookup.index:
                continue

            target = lookup.loc[tid]

            gc = haversine(
                transit["Latitude"], transit["Longitude"],
                target["Latitude"], target["Longitude"]
            )

            cost = gc * cost_per_km

            edges.append({
                "mode": "shipping",
                "from": transit["Location"],
                "to": target["Location"],
                "distance_km": round(gc, 2),
                "cost": round(cost, 2)
            })

    return pd.DataFrame(edges)
