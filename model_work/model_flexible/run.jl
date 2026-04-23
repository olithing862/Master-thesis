include("DataPrep.jl")
include("model.jl")

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
costs_df       = CSV.read("model_work/DataFiles_flexible/cost_matrix.csv", DataFrame, missingstring=["inf","Inf",""])
production     = CSV.read("model_work/DataFiles_flexible/production_nodes.csv", DataFrame)
demand_df      = CSV.read("model_work/DataFiles_flexible/demand_nodes.csv", DataFrame)
globald        = CSV.read("model_work/DataFiles_flexible/2030_demand.csv", DataFrame)
productioncost = CSV.read("model_work/DataFiles_flexible/prodcost.csv", DataFrame)

total_capacity = 8
N, P, T, O, O_rigid, O_ship, costs, D_rigid, D_ship, MaxP, Prodcost, penalty, production =
    DataPrep.generate_data(total_capacity, nodes, costs_df, production, demand_df, globald, productioncost)

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
results_dir = next_results_dir()
println("Writing results to: $results_dir")

# ----------------------------
# Build + solve
# ----------------------------
model, f, q, u, u_ship, prod, valid_edges =
    Model_flexible.network_model_flexible(P, T, O_rigid, O_ship, N,
                                          costs, MaxP, Prodcost,
                                          D_rigid, D_ship, penalty)

optimize!(model)

# ----------------------------
# Console summary
# ----------------------------
println("\nRigid demand (steel + fertilizer):")
for o in O_rigid
    println(
        o,
        ": delivered = ", round(value(q[o]), digits=2),
        " / demand = ", D_rigid[o],
        " | unmet = ", round(value(u[o]), digits=2),
    )
end

println("\nShipping (aggregate):")
delivered_ship = sum(value(q[o]) for o in O_ship)
println("  total delivered across ", length(O_ship), " ports = ", round(delivered_ship, digits=2))
println("  demand = ", D_ship, " | unmet = ", round(value(u_ship), digits=2))

# ----------------------------
# Save results
# ----------------------------
function save_results(f, prod, q, u, u_ship, valid_edges, P, O_rigid, O_ship,
                      D_rigid, D_ship, MaxP, results_dir)

    # ── Flows ──────────────────────────────────────────────────
    flow_rows = []
    for p in P, (i,j) in valid_edges
        val = value(f[p,i,j])
        if val > 1e-6
            push!(flow_rows, (commodity=p, from_id=i, to_id=j, flow=val))
        end
    end
    CSV.write(joinpath(results_dir, "results_flows.csv"), DataFrame(flow_rows))

    # ── Production per node ────────────────────────────────────
    prod_rows = []
    for p in P
        push!(prod_rows, (
            node_id  = p,
            produced = value(prod[p]),
            capacity = MaxP[p]
        ))
    end
    CSV.write(joinpath(results_dir, "results_production.csv"), DataFrame(prod_rows))

    # ── Rigid demand per offtake node ──────────────────────────
    rigid_rows = []
    for o in O_rigid
        delivered = value(q[o])
        unmet     = value(u[o])
        push!(rigid_rows, (
            node_id    = o,
            demand     = D_rigid[o],
            delivered  = delivered,
            unmet      = unmet,
            served_pct = 100.0 * delivered / D_rigid[o],
        ))
    end
    CSV.write(joinpath(results_dir, "results_demand_rigid.csv"), DataFrame(rigid_rows))

    # ── Shipping demand per candidate port ─────────────────────
    ship_rows = []
    for o in O_ship
        push!(ship_rows, (
            node_id   = o,
            delivered = value(q[o]),
        ))
    end
    CSV.write(joinpath(results_dir, "results_demand_ship_ports.csv"), DataFrame(ship_rows))

    # ── Shipping aggregate summary ─────────────────────────────
    delivered_ship = sum(value(q[o]) for o in O_ship)
    ship_agg = DataFrame(
        demand        = [D_ship],
        delivered     = [delivered_ship],
        unmet         = [value(u_ship)],
        served_pct    = [100.0 * delivered_ship / D_ship],
        ports_used    = [count(o -> value(q[o]) > 1e-6, O_ship)],
        ports_total   = [length(O_ship)],
    )
    CSV.write(joinpath(results_dir, "results_demand_ship_aggregate.csv"), ship_agg)

    println("\nSaved:")
    println("  flows:             $(length(flow_rows)) entries")
    println("  production:        $(length(prod_rows)) nodes")
    println("  rigid demand:      $(length(rigid_rows)) nodes")
    println("  ship candidates:   $(length(ship_rows)) nodes")
end

save_results(f, prod, q, u, u_ship, valid_edges, P, O_rigid, O_ship,
             D_rigid, D_ship, MaxP, results_dir)
