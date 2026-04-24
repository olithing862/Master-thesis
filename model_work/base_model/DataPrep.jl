using JuMP
using Gurobi
using CSV
using DataFrames

module DataPrep
using CSV
using DataFrames

function generate_data(total_capacity, nodes, costs_df, production, demand_df, globald, productioncost)

    # --- Filter first ---
    valid_regions = Set(productioncost.region)
    nodes = filter(row -> !(row.type == "production" && !(row.region in valid_regions)), nodes)
    production = filter(row -> row.region in valid_regions, production)

    # Global demand lookup
    global_demand_dict = Dict(row.industry => row.demand_mt for row in eachrow(globald))

    # Demand per offtake node
    Demand = Dict(
        row.node_id => global_demand_dict[row.industry] * row.demand_percent
        for row in eachrow(demand_df)
    )

    # Node ID sets (now built from filtered nodes)
    N     = nodes.node_id
    P_ids = filter(row -> row.type == "production", nodes).node_id
    T_ids = filter(row -> row.type == "transit",    nodes).node_id
    O_ids = filter(row -> row.type == "offtake",    nodes).node_id

    # Cost matrix
    row_nodes = string.(costs_df[!, 1])
    col_nodes = names(costs_df)[2:end]

    cost_dict = Dict{Tuple{String,String}, Float64}(
        (from, to) => ismissing(costs_df[i, to]) ? Inf : Float64(costs_df[i, to]) * 1_000_000
        for (i, from) in enumerate(row_nodes)
        for to in col_nodes
    )

    # Per-node production capacity
    MaxP = Dict(
        string(row.node_id) => total_capacity * (row.capacity_share_percent / 100.0)
        for row in eachrow(production)
    )

    # Regional production cost
    region_cost = Dict(
        row.region => row.prod_cost * 1_000_000
        for row in eachrow(productioncost)
    )

    # Only production nodes get a Prodcost entry
    prod_rows = filter(row -> row.type == "production", nodes)
    Prodcost = Dict(
        string(row.node_id) => region_cost[row.region]
        for row in eachrow(prod_rows)
    )

    penalty = 2_730_000_000.0

    return (
        N          = N,
        P          = P_ids,
        T          = T_ids,
        O          = O_ids,
        costs      = cost_dict,
        demand     = Demand,
        MaxP       = MaxP,
        Prodcost   = Prodcost,
        penalty    = penalty,
        production = production,
    )
end

end # module

