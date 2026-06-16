
def fuel_to_ammonia(global_production, industry, units="Mt"):
    """
    Convert annual global production to NH3 demand.

    Parameters
    ----------
    global_production : float
        Annual production of the industry (Mt for steel/fertilizer, Mt-fuel for shipping)
    industry : str
        'steel', 'fertilizer', or 'shipping'
    units : str
        Units of global production ('Mt' or 'ton-km' for shipping)
        
    Returns
    -------
    nh3_demand : float
        Required ammonia in Mt
    """
    
    # Lower heating value of ammonia [GJ/t]
    LHV_NH3 = 18.6
    
    # Energy intensity per industry [GJ per unit]
    energy_intensity = {
        "steel": 20,          # GJ per ton steel
        "fertilizer": 30,     # GJ per ton N
        "shipping": 50        # GJ per ton fuel (~example)
    }
    
    if industry not in energy_intensity:
        raise ValueError("Industry must be one of 'steel', 'fertilizer', 'shipping'")
    
    # Total energy requirement [GJ]
    if industry in ["steel", "fertilizer"]:
        # Assume production in Mt → convert to tons
        total_energy = global_production * 1e6 * energy_intensity[industry]
    elif industry == "shipping":
        # Assume global_production in Mt of fuel or ton-km; adjust accordingly
        total_energy = global_production * 1e6 * energy_intensity[industry]
    
    # NH3 required [t]
    nh3_required = total_energy / LHV_NH3
    
    # Return in Mt
    return nh3_required / 1e6
# Global steel production ~1.8 Gt/year
steel_nh3 = fuel_to_ammonia(1886, "steel")
print(f"Steel NH3 demand: {steel_nh3:.1f} Mt/year")

# Global fertilizer production ~110 Mt N/year
fert_nh3 = fuel_to_ammonia(189, "fertilizer")
print(f"Fertilizer NH3 demand: {fert_nh3:.1f} Mt/year")

# Shipping fuel ~300 Mt/year (as heavy fuel oil equivalent)
shipping_nh3 = fuel_to_ammonia(300, "shipping")
print(f"Shipping NH3 demand: {shipping_nh3:.1f} Mt/year")

#save these numbers as csv type, demand
import pandas as pd
demand_df = pd.DataFrame({
    "industry": ["steel", "fertilizer", "shipping"],
    "demand": [steel_nh3, fert_nh3, shipping_nh3]
})
print(demand_df)
demand_df.to_csv("model_work_0904/globaldemand.csv", index=False)