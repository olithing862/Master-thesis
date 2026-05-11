using JuMP
using Gurobi
using CSV
using DataFrames
module DataPrep
using CSV
using DataFrames

function generate_data(total_capacity,nodes,costs_df,production,demand_df,
    globald,productioncost,penalty_df,
    )
    print(penalty_df)
    # Global demand lookup
    global_demand_dict = Dict(row.industry => row.demand_mt for row in eachrow(globald))

    # Demand per offtake node
    D = Dict(
    row.node_id => global_demand_dict[row.industry] * row.demand_percent
    for row in eachrow(demand_df) if row.industry != "Shipping"
    )   
    D_ship = global_demand_dict["Shipping"]  # Total shipping demand (aggregate)
    # Node ID sets
    N     = nodes.node_id
    P_ids = filter(row -> row.type == "production", nodes).node_id
    P_fossil = filter(row -> row.type == "production" && row.industry == "Fossil", nodes).node_id
    P_green = filter(row -> row.type == "production" && row.industry == "Green Ammonia", nodes).node_id
    T_ids = filter(row -> row.type == "transit",    nodes).node_id
    O_ids = filter(row -> row.type == "offtake",    nodes).node_id
    O_steel = filter(row -> row.type == "offtake" && row.industry == "Steel", nodes).node_id
    O_fert = filter(row -> row.type == "offtake" && row.industry == "Fertiliser", nodes).node_id
    O_ship  = filter(row -> row.type == "offtake" && row.industry == "Shipping", nodes).node_id

    # Cost matrix: Dict (i, j) => cost
    # Assumes cost_matrix.csv has columns: from_node, to_node, cost
    row_nodes = string.(costs_df[!, 1])       # row labels (first column)
    col_nodes = names(costs_df)[2:end]         # column labels

    cost_dict = Dict{Tuple{String,String}, Float64}(
        (from, to) => ismissing(costs_df[i, to]) ? Inf : Float64(costs_df[i, to]) * 1_000_000
        for (i, from) in enumerate(row_nodes)
        for to in col_nodes
    )

    # Per-node production capacity and cost (uniform here, easy to make node-specific)
    MaxP = Dict(
        string(row.node_id) => total_capacity * (row.capacity_share_percent / 100.0)
        for row in eachrow(production) 
    )
    region_cost = Dict(
    row.region => row.prod_cost * 1_000_000
    for row in eachrow(productioncost)
    )   
    Prodcost = Dict(
        string(row.node_id) => region_cost[row.region]
        for row in eachrow(nodes)
    )
    
    fossil_price = Dict(row.node_id => row.fossil_price* 1_000_000 for row in eachrow(penalty_df))
    co2_tax      = Dict(row.node_id => row.co2_tax * 1_000_000 for row in eachrow(penalty_df))
    conversion   = Dict(row.node_id => row.conversion for row in eachrow(penalty_df))
    return (
        N        = N,
        P        = P_ids,
        P_fossil = P_fossil,
        P_green  = P_green,
        T        = T_ids,
        O        = O_ids,
        O_steel  = O_steel,
        O_fert   = O_fert,
        O_ship   = O_ship,
        costs    = cost_dict,
        D        = D,
        D_ship   = D_ship,
        MaxP     = MaxP,
        Prodcost = Prodcost,
        fossil_price = fossil_price,
        co2_tax = co2_tax,
        conversion = conversion,
        production = production
    )
end

end # module
