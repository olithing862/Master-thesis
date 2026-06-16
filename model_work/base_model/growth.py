import pandas as pd

def scale_demand(demand_2024_mt, commodity, annual_growth_rate=None, years=6):

    defaults = {"steel": 0.009, "fertilizer": 0.0142}

    commodity = commodity.lower()
    if commodity not in defaults:
        raise ValueError("Commodity must be 'steel' or 'fertilizer'.")

    rate = defaults[commodity] if annual_growth_rate is None else annual_growth_rate
    multiplier = (1 + rate) ** years
    
    return demand_2024_mt * multiplier


# Example
# #demand = pd.read_csv("model_work_0904/DataFiles/globaldemand.csv")
# steel = demand.loc[demand["industry"] == "steel", "demand_mt"].values[0]
# fertilizer = demand.loc[demand["industry"] == "fertilizer", "demand_mt"].values[0]

# print(scale_demand(steel, "steel"))              # ~1858.9 Mt
# print(scale_demand(fertilizer, "fertilizer"))    # ~208.1 Mt
# #save to csv
# scaled_demand = pd.DataFrame({
#     "industry": ["steel", "fertilizer","shipping"],
#     "demand_mt": [scale_demand(steel, "steel"), scale_demand(fertilizer, "fertilizer"),290.12]
# })
# #scaled_demand.to_csv("model_work_0904/DataFiles/2030_demand.csv", index=False)
# # Custom growth rate, e.g. 2% annually
# print(scale_demand(steel, "steel", annual_growth_rate=0.02))  # ~1972.1 Mt


def implied_growth_rate(start_value, end_value, years):
    """
    Calculate the annual compound growth rate implied by a start and end value.
    
    Returns the rate as a decimal (e.g. 0.009 = 0.9% per year).
    
    Inverse of scale_demand(): if you know a 2024 and a 2030 forecast value,
    this gives you the annual_growth_rate that connects them.
    """
    if start_value <= 0 or years <= 0:
        raise ValueError("start_value and years must be positive.")
    return (end_value / start_value) ** (1 / years) - 1


# Real use case — if you find a 2030 forecast for, say, shipping bunker fuel:
shipping_2024 = 249.65   # Mt, current
shipping_2030 = 290.12   # Mt, from your CSV
r = implied_growth_rate(shipping_2024, shipping_2030, years=6)
print(f"Implied shipping growth: {r*100:.2f}% per year")
# → ~2.55% / year