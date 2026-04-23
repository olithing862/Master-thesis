
import pandas as pd
from pathlib import Path


def make_ship_offtake_nodes(
    transit_csv: str | Path,
    output_csv: str | Path,
    industry_label: str = "Shipping",
) -> pd.DataFrame:
    """
    Create an oft_shipX offtake node for each transit node.

    Parameters
    ----------
    transit_csv : path to CSV with columns:
        node_id, Location, lat, lon, region, industry, type, landmass
    output_csv : where to write the generated offtake rows.
    industry_label : value written in the 'industry' column for the
        generated rows (default "Ship").

    Returns
    -------
    DataFrame of the generated rows (also written to output_csv).
    """
    df = pd.read_csv(transit_csv)

    transit = df[df["type"].str.lower() == "transit"].reset_index(drop=True)
    if transit.empty:
        raise ValueError("No transit nodes found.")

    out = pd.DataFrame({
        "node_id": [f"oft_ship{i+1}" for i in range(len(transit))],
        "Location": transit["Location"],
        "lat": transit["lat"],
        "lon": transit["lon"],
        "region": transit["region"],
        "industry": industry_label,
        "type": "offtake",
        "landmass": transit["landmass"],
    })

    out.to_csv(output_csv, index=False)
    return out


if __name__ == "__main__":
    result = make_ship_offtake_nodes(
        transit_csv="/Users/oliviathingvad/Master-thesis/model_work/Datafiles_flexible/nodes.csv",
        output_csv="/Users/oliviathingvad/Master-thesis/model_work/Datafiles_flexible/ship_offtake_nodes.csv",
    )
    print(f"Generated {len(result)} oft_ship nodes.")
    print(result.head())