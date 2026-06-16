import pandas as pd
from pathlib import Path

def assign_offtake_parameters(
    nodes_path: str,
    fossil_price_path: str,
    co2_tax_path: str,
    conversion_path: str,
) -> pd.DataFrame:

    nodes = pd.read_csv(nodes_path)
    nodes.columns = nodes.columns.str.strip()
    for col in ["industry", "region", "type", "node_id"]:
        nodes[col] = nodes[col].astype(str).str.strip()

    offtake = nodes[nodes["type"] == "offtake"].copy()
    #print(len(offtake))
    # Normalise industry
    industry_map = {
        "Fertilizer": "Fertiliser",
        "Fertiliser": "Fertiliser",
        "Steel":      "Steel",
        "Shipping":   "Shipping",
    }
    offtake["sector"] = offtake["industry"].map(industry_map)
    print(offtake)
    # Sector → column names
    fossil_col = {"Fertiliser": "ammonia", "Steel": "naturalgas", "Shipping": "lsfo"}
    tax_col    = {"Fertiliser": "tax_fert",   "Steel": "tax_steel",   "Shipping": "tax_shipping"}
    print(offtake["sector"].map(tax_col))
    # Load lookup tables
    fossil     = pd.read_csv(fossil_price_path).set_index("region")
    tax        = pd.read_csv(co2_tax_path).set_index("region")
    conversion = pd.read_csv(conversion_path).set_index("industry")

    # Assign
    offtake["co2_tax"]      = offtake.apply(lambda r: tax.loc[r["region"], tax_col[r["sector"]]], axis=1)
    offtake["fossil_price"] = offtake.apply(lambda r: fossil.loc[r["region"], fossil_col[r["sector"]]], axis=1)
    offtake["conversion"]   = offtake["sector"].map(conversion["tco2"])

    return offtake[["node_id", "co2_tax", "fossil_price", "conversion"]]



BASE = Path(__file__).resolve().parent.parent / "Datafiles_flexible"

if __name__ == "__main__":
    df = assign_offtake_parameters(
        BASE / "nodes.csv",
        BASE / "fossil_prices.csv",
        BASE / "co2_tax.csv",
        BASE / "conversion.csv",
    )
    df.to_csv(BASE / "offtake_parameters.csv", index=False)
    print(df)