include("DataPrep.jl")
include("model_1.jl")
include("save_results.jl")

using .save
using .DataPrep
using .Model_flexible
using JuMP
using CSV
using DataFrames
using Dates

# ----------------------------
# Generate data
# ----------------------------
nodes          = CSV.read("model_work/DataFiles_flexible/nodes.csv", DataFrame)
costs_df       = CSV.read("model_work/DataFiles_flexible/cost_matrix_fossil.csv", DataFrame, missingstring=["inf","Inf",""])
production     = CSV.read("model_work/DataFiles_flexible/production_nodes.csv", DataFrame)
demand_df      = CSV.read("model_work/DataFiles_flexible/demand_nodes.csv", DataFrame)
globald        = CSV.read("model_work/DataFiles_flexible/2030_demand.csv", DataFrame)
productioncost = CSV.read("model_work/DataFiles_flexible/prodcost.csv", DataFrame)
penalty_df      = CSV.read("model_work/DataFiles_flexible/penalty_parameters.csv", DataFrame)

total_capacity = 180
N, P,P_fossil, P_green, T, O, O_Steel, O_fert, O_ship, costs, 
D, D_ship, MaxP, Prodcost, fossil_price, co2_tax, conversion, production =
    DataPrep.generate_data(total_capacity, nodes, costs_df, production, demand_df, globald, productioncost, penalty_df)
# After generate_data, before building model:

# ----------------------------
# Create dated results folder
# ----------------------------
function next_results_dir(base::String = "Results")
    date = Dates.format(now(), "yyyy-mm-dd")
    candidate = joinpath(base, date)
    i = 1
    while isdir(candidate)
        candidate = joinpath(base, "$(date)_$i")
        i += 1
    end
    mkpath(candidate)
    return candidate
end
results_dir = next_results_dir("Results/flexible_demand")
println("Writing results to: $results_dir")

cost_factors     = Dict("low" => 0.25, "medium" => 0.5, "high" => 0.7)
capacity_factors = Dict("low" => 1.0, "medium" => 2.1, "high" => 3.9)

for (cost_name, cost_factor) in cost_factors
    for (cap_name, cap_factor) in capacity_factors

        scen_name = "cost_$(cost_name)__cap_$(cap_name)"
        println("\n==============================")
        println("Running scenario: ", scen_name)
        println("==============================")

        Prodcost_scen = Dict(k => v * cost_factor for (k,v) in Prodcost)
        MaxP_scen     = Dict(k => v * cap_factor  for (k,v) in MaxP)

        scen_dir = joinpath(results_dir, scen_name)
        mkpath(scen_dir)

        model, f, q, u, prod, valid_edges =
            Model_flexible.network_model_flexible(
                P_fossil, P_green, T, O_Steel, O_fert, O_ship, N,
                costs, MaxP_scen, Prodcost_scen,
                D, D_ship, fossil_price, co2_tax, conversion
            )

        optimize!(model)

        println("Objective value: ", objective_value(model))

        println("\nLocked demand (steel + fertiliser):")
        for o in vcat(O_Steel, O_fert)
            println(
                o,
                ": delivered = ", round(value(q[o]), digits=2),
                " / demand = ", D[o],
                " | unmet = ", round(value(u[o]), digits=2),
            )
        end

        println("\nShipping (aggregate):")
        delivered_ship = sum(value(q[o]) for o in O_ship)
        unmet_ship     = sum(value(u[o]) for o in O_ship)
        println("  total delivered = ", round(delivered_ship, digits=2))
        println("  demand = ", D_ship, " | unmet = ", round(unmet_ship, digits=2))

        data = (
            P        = P,
            P_green  = P_green,
            P_fossil = P_fossil,
            T        = T,
            O_Steel  = O_Steel,
            O_fert   = O_fert,
            O_ship   = O_ship,
            D        = D,
            D_ship   = D_ship,
            MaxP     = MaxP_scen
        )
        save.save_results(f, prod, q, u, valid_edges, data, scen_dir)

    end
end


