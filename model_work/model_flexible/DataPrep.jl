module DataPrep
using CSV
using DataFrames

function generate_data(total_capacity, nodes, costs_df, production, demand_df,
    globald, productioncost, penalty_df, config_df, scen=nothing)

    # Scenario parameters
    cost_map = Dict(r.level => r.factor for r in eachrow(filter(r -> r.type == "cost", config_df)))
    cap_map  = Dict(r.level => r.factor for r in eachrow(filter(r -> r.type == "cap",  config_df)))

    cap_factor          = isnothing(scen) ? 1.0 : cap_map[scen.cap_factor]
    cost_factor         = isnothing(scen) ? 1.0 : cost_map[scen.cost_factor]
    co2_tax_region_name = (isnothing(scen) || ismissing(scen.co2_tax_region_name)) ? "none" : scen.co2_tax_region_name
    co2_tax_region      = isnothing(scen) ? 0.0 : scen.co2_tax_region
    co2_tax_shipping    = isnothing(scen) ? 0.0 : scen.co2_tax_shipping
    fossil_price_factor = isnothing(scen) ? 1.0 : scen.fossil_price_factor
    demand_factor_Steel = isnothing(scen) ? 1.0 : scen.demand_factor_Steel
    demand_factor_Fert  = isnothing(scen) ? 1.0 : scen.demand_factor_Fertiliser
    demand_factor_Ship  = isnothing(scen) ? 1.0 : scen.demand_factor_Shipping
    min_coverage_Steel = isnothing(scen) ? 0.0 : scen.min_coverage_steel
    min_coverage_Fert  = isnothing(scen) ? 0.0 : scen.min_coverage_fertiliser
    min_coverage_Ship  = isnothing(scen) ? 0.0 : scen.min_coverage_shipping

    # Demand
    global_demand_dict = Dict(r.industry => r.demand_mt for r in eachrow(globald))
    demand_factors = Dict("Steel" => demand_factor_Steel, "Fertiliser" => demand_factor_Fert, "Shipping" => demand_factor_Ship)

    D = Dict(
        r.node_id => global_demand_dict[r.industry] * r.demand_percent * get(demand_factors, r.industry, 1.0)
        for r in eachrow(demand_df) if r.industry != "Shipping"
    )
    D_ship = global_demand_dict["Shipping"] * demand_factor_Ship

    # Node sets
    N        = nodes.node_id
    P_ids    = filter(r -> r.type == "production", nodes).node_id
    P_fossil = filter(r -> r.type == "production" && r.industry == "Fossil", nodes).node_id
    P_green  = filter(r -> r.type == "production" && r.industry == "Green Ammonia", nodes).node_id
    T_ids    = filter(r -> r.type == "transit", nodes).node_id
    O_ids    = filter(r -> r.type == "offtake", nodes).node_id
    O_Steel  = filter(r -> r.type == "offtake" && r.industry == "Steel", nodes).node_id
    O_fert   = filter(r -> r.type == "offtake" && r.industry == "Fertiliser", nodes).node_id
    O_ship   = filter(r -> r.type == "offtake" && r.industry == "Shipping", nodes).node_id

    # Cost matrix
    row_nodes = string.(costs_df[!, 1])
    col_nodes = names(costs_df)[2:end]
    cost_dict = Dict{Tuple{String,String}, Float64}(
        (from, to) => ismissing(costs_df[i, to]) ? Inf :
                      Float64(costs_df[i, to])
        for (i, from) in enumerate(row_nodes)
        for to in col_nodes
    )

    # Capacity and production cost
    MaxP = Dict(
        string(r.node_id) => total_capacity * (r.capacity_share_percent / 100.0) * cap_factor
        for r in eachrow(production)
    )
    region_cost = Dict(r.region => r.prod_cost for r in eachrow(productioncost))
    Prodcost = Dict(string(r.node_id) => region_cost[r.region] * cost_factor for r in eachrow(nodes))

    # Penalties
    region_nodes = co2_tax_region_name == "none" ? [] :
                   filter(r -> r.region == co2_tax_region_name, nodes).node_id

    fossil_price = Dict(r.node_id => r.fossil_price * fossil_price_factor for r in eachrow(penalty_df))
    conversion   = Dict(r.node_id => r.conversion for r in eachrow(penalty_df))
    co2_tax = Dict(
        r.node_id =>
            if r.node_id in O_ship
                co2_tax_shipping
            elseif r.node_id in region_nodes
                co2_tax_region
            else
                r.co2_tax
            end
        for r in eachrow(penalty_df)
    )
    min_coverage = Dict(
    "steel"      => min_coverage_Steel,
    "fertiliser" => min_coverage_Fert,
    "ship"       => min_coverage_Ship   # was "shipping"
    )


    return (
        N=N, P=P_ids, P_fossil=P_fossil, P_green=P_green, T=T_ids, O=O_ids,
        O_Steel=O_Steel, O_fert=O_fert, O_ship=O_ship,
        costs=cost_dict, D=D, D_ship=D_ship, MaxP=MaxP, Prodcost=Prodcost,
        fossil_price=fossil_price, co2_tax=co2_tax, conversion=conversion,
        production=production,min_coverage=min_coverage
    )
end

end # module