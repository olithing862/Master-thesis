module Model_flexible

using JuMP
using Gurobi


function network_model_flexible(P_fossil,P_green, T, O_steel, O_fert, O_ship, N,
                            c,           # Dict or matrix: c[i,j]
                            MaxP,        # Dict: MaxP[p]
                            Prodcost,    # Dict: Prodcost[p]
                            D,           # Dict: D[o] for o in O_steel and O_fert
                            D_ship,      # Scalar: aggregate shipping demand
                            fossil_price, co2_tax, conversion,GRB_ENV, min_coverage)

    model = Model(() -> Gurobi.Optimizer(GRB_ENV))
    set_optimizer_attribute(model, "NumericFocus", 3)
    set_optimizer_attribute(model, "ScaleFlag", 2)
    set_optimizer_attribute(model, "BarHomogeneous", 1)
    set_optimizer_attribute(model, "TimeLimit", 180)
    set_optimizer_attribute(model, "OutputFlag", 0)   # silence per-scenario logs if you want

    # Full offtake set (union of rigid and shipping candidates)
    O = union(O_steel,O_fert,O_ship)
    O_industry = union(O_steel, O_fert)
    industry_sets = Dict(
        "steel" => O_steel,
        "fertiliser" => O_fert
    )
    P = union(P_fossil, P_green)
      # same penalty for rigid and shipping unmet demand (can be different if desired)
    # ----------------------
    # Decision variables
    # ----------------------
    valid_edges = Set((i,j) for i in N for j in N if isfinite(c[i,j]))

    @variable(model, f[p in P, i in N, j in N; (i,j) in valid_edges] >= 0)
    @variable(model, prod[p in P_green] >= 0)
    @variable(model, q[o in O] >= 0)
    @variable(model, u[o in O] >= 0)   # per-node unmet for rigid offtakers

    # ----------------------
    # Objective
    # ----------------------
    @objective(model, Min,
        sum(c[i,j] * f[p,i,j] for p in P, (i,j) in valid_edges)
        + sum(Prodcost[p] * prod[p] for p in P_green)
        + sum(fossil_price[o] * u[o] for o in O)
        + sum(co2_tax[o] * u[o] * conversion[o] for o in O)
    )

    # Production node outflow
    @constraint(model, [p in P_green],
        sum(f[p,p,j] for j in N if (p,j) in valid_edges) == prod[p]
    )

    # Production capacity
    @constraint(model, [p in P_green],
        prod[p] <= MaxP[p]
    )

    # Delivered quantity at every offtake node (rigid and ship candidates)
    @constraint(model, [o in O],
        sum(f[p,i,o] for p in P_green, i in N if (i,o) in valid_edges) == q[o]
    )

    @constraint(model, [o in O],
        sum(f[p,i,o] for p in P_fossil, i in N if (i,o) in valid_edges) == u[o]
    )
    # Rigid demand: per-node satisfaction for steel + fert
    @constraint(model, [o in vcat(O_steel, O_fert)],
        q[o] + u[o] >= D[o]
    )
    # Flexible shipping demand: aggregate across all candidate ports
    @constraint(model,
        sum(q[o] + u[o] for o in O_ship) >= D_ship
    )

    # Flow conservation at transit nodes
    @constraint(model, [p in P, t in T],
        sum(f[p,t,j] for j in N if (t,j) in valid_edges)
        ==
        sum(f[p,i,t] for i in N if (i,t) in valid_edges)
    )

    # No flow of commodity p through other production nodes
    @constraint(model, [p in P, i in P, j in N; i != p && (i,j) in valid_edges],
        f[p,i,j] == 0
    )

    @constraint(model, [ind in keys(industry_sets), o in industry_sets[ind]],
        q[o] >= min_coverage[ind] * D[o]
    )
    @constraint(model,
        sum(q[o] for o in O_ship) >= min_coverage["ship"] * D_ship
    )

    return model, f, q, u, prod, valid_edges
end

end # module