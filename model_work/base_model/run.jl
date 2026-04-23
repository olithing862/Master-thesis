include("DataPrep.jl")
include("model_5.jl")

using .DataPrep
using .Model_april_2
using JuMP
using CSV
using DataFrames
using Dates
# ----------------------------
# Generate data
# ----------------------------
nodes      = CSV.read("model_work/DataFiles_base/nodes.csv", DataFrame)
costs_df   = CSV.read("model_work/DataFiles_base/cost_matrix_5.csv", DataFrame,missingstring=["inf", "Inf",""])
production = CSV.read("model_work/DataFiles_base/production_nodes.csv", DataFrame)
demand_df  = CSV.read("model_work/DataFiles_base/demand_nodes.csv", DataFrame)
globald    = CSV.read("model_work/DataFiles_base/2030_demand.csv", DataFrame)
productioncost = CSV.read("model_work/DataFiles_base/prodcost.csv", DataFrame)
total_capacity = 8
N, P, T, O, costs, Demand, MaxP, Prodcost, penalty, production = DataPrep.generate_data(total_capacity,nodes,costs_df,production,demand_df,globald,productioncost)
#print the max number of costs

#print costs[t22,oft_sh1] and cost[t153,t22]

function next_results_dir(base::String = "Results")
    date = Dates.format(now(), "yyyy-mm-dd")
    candidate = joinpath(base, "Base $date")
    i = 1
    while isdir(candidate)
        candidate = joinpath(base, "Base $(date)_$i")
        i += 1
    end
    mkpath(candidate)
    return candidate
end
results_dir = next_results_dir()
println("Writing results to: $results_dir")
model, f,q,u,prod,valid_edges = Model_april_2.network_model(P, T, O, N,
                            costs,           
                            MaxP,       
                            Prodcost,    
                            Demand,           
                            penalty)


optimize!(model)
#print some results
println("\nDelivered quantities:")
for o in O
    println(
        o,
        ": delivered = ", round(value(q[o]), digits=2),
        " / Demand required = ", Demand[o],
        " | Unmet demand = ", round(value(u[o]), digits=2),
    )
end

function save_results(f, prod, q, u, valid_edges, P, O, N, model)
    
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
            node_id   = p,
            produced  = value(prod[p]),
            capacity  = MaxP[p]
        ))
    end
    CSV.write("$results_dir/results_production.csv", DataFrame(prod_rows))

    # ── Demand served per offtake node ─────────────────────────
    demand_rows = []
    for o in O
        delivered  = value(q[o])
        unmet      = value(u[o])
        push!(demand_rows, (
            node_id       = o,
            demand        = Demand[o],
            delivered     = delivered,
            unmet         = unmet,
            served_pct    = 100.0 * delivered / Demand[o]
        ))
    end
    CSV.write("$results_dir/results_demand.csv", DataFrame(demand_rows))

    println("Flows:      $(length(flow_rows)) entries")
    println("Production: $(length(prod_rows)) nodes")
    println("Demand:     $(length(demand_rows)) nodes")
end


save_results(f, prod, q, u, valid_edges, P, O, N, model)
