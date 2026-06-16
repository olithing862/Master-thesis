import pandas as pd
regions = ['S America', 'Europe', 'Japan & South Korea', 'China & Hong Kong']

# Define costs manually (example)
# Diagonal = cost within same region
# Off-diagonal = cost between regions (example numbers)
costs = {
    'S America': {'S America': 10, 'Europe': 100, 'Japan & South Korea': 200, 'China & Hong Kong': 250},
    'Europe': {'S America': 100, 'Europe': 50, 'Japan & South Korea': 220, 'China & Hong Kong': 210},
    'Japan & South Korea': {'S America': 200, 'Europe': 220, 'Japan & South Korea': 20, 'China & Hong Kong': 30},
    'China & Hong Kong': {'S America': 250, 'Europe': 210, 'Japan & South Korea': 30, 'China & Hong Kong': 30}
}

# Convert to a DataFrame
sea_region_cost = pd.DataFrame(costs)
sea_region_cost.index.name = 'region_from'

print(sea_region_cost)