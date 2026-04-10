include("DataPrep.jl")
include("model_5.jl")

using .DataPrep
using .Model_april_2
using JuMP
using CSV
using DataFrames

# ----------------------------
# Generate data
# ----------------------------
N, P, T, O, costs, Demand, MaxP, Prodcost, penalty, production = DataPrep.generate_data()

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

function save_results(f, prod, q, u, valid_edges, P, O, N, model,date)
    
    # ── Flows ──────────────────────────────────────────────────
    flow_rows = []
    for p in P, (i,j) in valid_edges
        val = value(f[p,i,j])
        if val > 1e-6
            push!(flow_rows, (commodity=p, from_id=i, to_id=j, flow=val))
        end
    end
    CSV.write("Results/results_flows_$(date).csv", DataFrame(flow_rows))

    # ── Production per node ────────────────────────────────────
    prod_rows = []
    for p in P
        push!(prod_rows, (
            node_id   = p,
            produced  = value(prod[p]),
            capacity  = MaxP[p]
        ))
    end
    CSV.write("Results/results_production_$(date).csv", DataFrame(prod_rows))

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
    CSV.write("Results/results_demand_$(date).csv", DataFrame(demand_rows))

    println("Flows:      $(length(flow_rows)) entries")
    println("Production: $(length(prod_rows)) nodes")
    println("Demand:     $(length(demand_rows)) nodes")
end



date = 1004_3

save_results(f, prod, q, u, valid_edges, P, O, N, model,date)