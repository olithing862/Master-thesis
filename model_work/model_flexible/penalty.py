import pandas as pd


def generate_penalty(nodes_path, co2_tax_shipping, co2_tax_fertilizer, co2_tax_steel, output_path=None):
    
    grey_fuel_price = {
        "Shipping":    400.0*1_000_000,
        "Fertilizer":  2730.0*1_000_000,
        "Steel":       2730.0*1_000_000,
    }
    
    co2_tax = {
        "Shipping":    co2_tax_shipping,
        "Fertilizer":  co2_tax_fertilizer,
        "Steel":       co2_tax_steel,
    }
    # ──────────────────────────────
    
    nodes = pd.read_csv(nodes_path)
    offtake = nodes[nodes["type"] == "offtake"].copy()
    
    offtake["grey_price"] = offtake["industry"].map(grey_fuel_price)
    offtake["co2_tax"] = offtake["industry"].map(co2_tax)
    offtake["penalty"] = offtake["grey_price"] + offtake["co2_tax"]
    
    result = offtake[["node_id", "industry", "grey_price", "co2_tax", "penalty"]].reset_index(drop=True)
    
    if output_path:
        result.to_csv(output_path, index=False)
    
    return result


if __name__ == "__main__":
    penalties = generate_penalty("model_work/DataFiles_flexible/nodes.csv",
                                 co2_tax_shipping=0.0,
                                 co2_tax_fertilizer=0.0,
                                 co2_tax_steel=0.0,
                                 output_path="model_work/DataFiles_flexible/penalty.csv")
    print(penalties.groupby("industry")["penalty"].first())