import pandas as pd

# Load your two datasets
df1 = pd.read_csv("model_work/DataFiles_base/production_sites_clustered_4.csv")  # contains Index + Max_capacity
df2 = pd.read_csv(r"/Users/oliviathingvad/Master-thesis/model_work/DataFiles_base/nodes.csv")  # contains node info
df2 = df2[df2["node_id"].str.startswith("p")]
# Merge on matching keys
merged = df2.merge(df1[['Index', 'Max_capacity']],
                   left_on='Location',
                   right_on='Index',
                   how='left')

# Drop duplicate key column
merged = merged.drop(columns=['Index'])

# Reorder columns
merged = merged[['node_id','Location','lat','lon','region',
                 'industry','type','landmass','Max_capacity']]


#remove region = other
merged = merged[merged["region"] != "Other"].copy()
#compute percent capacity of each node relative to total
total_capacity = merged["Max_capacity"].sum()
merged["capacity_share_percent"] = merged["Max_capacity"] / total_capacity * 100
#drop the Max_capacity column
merged = merged.drop(columns=["Max_capacity"])
#make a df for the node csv without capacity share, and max capacity, to be used for the nodes.csv file merge it with existing data in the csv

nodes_df = merged.drop(columns=["capacity_share_percent",])

nodes_df.to_csv(
    "model_work/DataFiles_base/nodes copy.csv",
    mode="a",          # append instead of overwrite
    index=False,
    header=False       # don't write header again
)
#save to csv
merged.to_csv("model_work/DataFiles_base/production_nodes.csv", index=False)