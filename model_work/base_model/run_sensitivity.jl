include("DataPrep.jl")
include("model_5.jl")

using .DataPrep
using .Model_april_2
using JuMP
using CSV
using DataFrames
using Dates

# --- Static inputs ---
nodes          = CSV.read("model_work/DataFiles_base/nodes.csv", DataFrame)
costs_df       = CSV.read("model_work/DataFiles_base/cost_matrix.csv", DataFrame, missingstring=["inf","Inf",""])
production_df  = CSV.read("model_work/DataFiles_base/production_nodes.csv", DataFrame)
demand_df      = CSV.read("model_work/DataFiles_base/demand_nodes.csv", DataFrame)
globald        = CSV.read("model_work/DataFiles_base/2030_demand.csv", DataFrame)
productioncost = CSV.read("model_work/DataFiles_base/prodcost.csv", DataFrame)

function next_results_dir(base::String)
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

function save_results(f, prod, q, u, valid_edges, P, O, N, model, results_dir, MaxP, Demand)

    # ── Flows ──────────────────────────────────────────────────
    flow_rows = []
    for p in P, (i,j) in valid_edges
        val = value(f[p,i,j])
        if val > 1e-6
            push!(flow_rows, (commodity=p, from_id=i, to_id=j, flow=val))
        end
    end
    CSV.write("$results_dir/results_flows.csv", DataFrame(flow_rows))

    # ── Production per node ────────────────────────────────────
    prod_rows = []
    for p in P
        push!(prod_rows, (
            node_id  = p,
            produced = value(prod[p]),
            capacity = MaxP[p]
        ))
    end
    CSV.write("$results_dir/results_production.csv", DataFrame(prod_rows))

    # ── Demand served per offtake node ─────────────────────────
    demand_rows = []
    for o in O
        delivered = value(q[o])
        unmet     = value(u[o])
        push!(demand_rows, (
            node_id    = o,
            demand     = Demand[o],
            delivered  = delivered,
            unmet      = unmet,
            served_pct = 100.0 * delivered / Demand[o]
        ))
    end
    CSV.write("$results_dir/results_demand.csv", DataFrame(demand_rows))

    println("Flows:      $(length(flow_rows)) entries")
    println("Production: $(length(prod_rows)) nodes")
    println("Demand:     $(length(demand_rows)) nodes")
end

# --- Capacity sweep ---
capacity_levels = [8, 700, 1400]
summary_rows = []

for total_capacity in capacity_levels
    println("\n=== Running capacity = $total_capacity ===")

    N, P, T, O, costs, Demand, MaxP, Prodcost, penalty, production =
        DataPrep.generate_data(total_capacity, nodes, costs_df, production_df,
                               demand_df, globald, productioncost)

    model, f, q, u, prod, valid_edges =
        Model_april_2.network_model(P, T, O, N, costs, MaxP, Prodcost, Demand, penalty)

    optimize!(model)

    total_produced  = sum(value(prod[p]) for p in P)
    total_capacity_ = sum(MaxP[p] for p in P)
    total_demand    = sum(Demand[o] for o in O)
    total_delivered = sum(value(q[o]) for o in O)
    total_unmet     = sum(value(u[o]) for o in O)
    utilization     = 100.0 * total_produced / total_capacity_

    println("  Total capacity:  $(round(total_capacity_, digits=2))")
    println("  Total produced:  $(round(total_produced,  digits=2))")
    println("  Utilization:     $(round(utilization,     digits=1))%")
    println("  Total demand:    $(round(total_demand,    digits=2))")
    println("  Delivered:       $(round(total_delivered, digits=2))")
    println("  Unmet:           $(round(total_unmet,     digits=2))")

    push!(summary_rows, (
        total_capacity  = total_capacity_,
        total_produced  = total_produced,
        utilization_pct = utilization,
        total_demand    = total_demand,
        total_delivered = total_delivered,
        total_unmet     = total_unmet,
    ))

    results_dir = next_results_dir("Results/sensitivity_base/capacity_$(total_capacity)")
    save_results(f, prod, q, u, valid_edges, P, O, N, model, results_dir, MaxP, Demand)
end

mkpath("Results/sensitivity_base")
CSV.write("Results/sensitivity_base/capacity_sweep_summary.csv", DataFrame(summary_rows))
println("\n", DataFrame(summary_rows))