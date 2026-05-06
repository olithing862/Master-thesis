module save

using JuMP
using CSV
using DataFrames
using Dates

function save_results(f, prod, q, u, valid_edges,
             data,results_dir)

    # ── Flows ──────────────────────────────────────────────────
    flow_rows = []
    for p in data.P
        for (i,j) in valid_edges
            val = value(f[p,i,j])
            if val > 1e-6
                push!(flow_rows, (commodity=p, from_id=i, to_id=j, flow=val))
            end
        end
    end
    CSV.write(joinpath(results_dir, "results_flows.csv"), DataFrame(flow_rows))

    # ── Production per node ────────────────────────────────────
    prod_rows = []
    for p in data.P_green
        push!(prod_rows, (
            node_id  = p,
            produced = value(prod[p]),
            capacity = data.MaxP[p]
        ))
    end
    CSV.write(joinpath(results_dir, "results_production.csv"), DataFrame(prod_rows))

    # ── Rigid demand per offtake node ──────────────────────────
    rigid_rows = []
    for o in vcat(data.O_Steel, data.O_fert)
        delivered = value(q[o])
        unmet     = value(u[o])
        push!(rigid_rows, (
            node_id    = o,
            demand     = data.D[o],
            delivered  = delivered,
            unmet      = unmet,
            served_pct = 100.0 * delivered / data.D[o],
        ))
    end
    CSV.write(joinpath(results_dir, "results_demand.csv"), DataFrame(rigid_rows))

    # ── Shipping demand per candidate port ─────────────────────
    ship_rows = []
    for o in data.O_ship
        push!(ship_rows, (
            node_id   = o,
            delivered = value(q[o]),
            unmet     = value(u[o]),
        ))
    end
    CSV.write(joinpath(results_dir, "results_demand_ship_ports.csv"), DataFrame(ship_rows))

    # ── Shipping aggregate summary ─────────────────────────────
    delivered_ship = sum(value(q[o]) for o in data.O_ship)
    unmet_ship = sum(value(u[o]) for o in data.O_ship)
    ship_agg = DataFrame(
        demand        = [data.D_ship],
        delivered     = [delivered_ship],
        unmet         = [unmet_ship],
        served_pct    = [100.0 * delivered_ship / data.D_ship],
        ports_used    = [count(o -> value(q[o]) > 1e-6, data.O_ship)],
        ports_total   = [length(data.O_ship)],
    )
    CSV.write(joinpath(results_dir, "results_demand_ship_aggregate.csv"), ship_agg)

    println("\nSaved:")
    println("  flows:             $(length(flow_rows)) entries")
    println("  production:        $(length(prod_rows)) nodes")
    println("  rigid demand:      $(length(rigid_rows)) nodes")
    println("  ship candidates:   $(length(ship_rows)) nodes")
end


end # module