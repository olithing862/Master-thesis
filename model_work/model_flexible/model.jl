module Model_flexible

using JuMP
using Gurobi


function network_model_flexible(P, T, O_rigid, O_ship, N,
                            c,           # Dict or matrix: c[i,j]
                            MaxP,        # Dict: MaxP[p]
                            Prodcost,    # Dict: Prodcost[p]
                            D_rigid,     # Dict: D_rigid[o] for o in O_rigid
                            D_ship,      # Scalar: aggregate shipping demand
                            π)           # scalar penalty

    model = Model(Gurobi.Optimizer)

    # Full offtake set (union of rigid and shipping candidates)
    O = union(O_rigid, O_ship)
    pi = [π, π, 400_000_000]  # same penalty for rigid and shipping unmet demand (can be different if desired)
    # ----------------------
    # Decision variables
    # ----------------------
    valid_edges = Set((i,j) for i in N for j in N if isfinite(c[i,j]))

    @variable(model, f[p in P, i in N, j in N; (i,j) in valid_edges] >= 0)
    @variable(model, prod[p in P] >= 0)
    @variable(model, q[o in O] >= 0)
    @variable(model, u[o in O_rigid] >= 0)   # per-node unmet for rigid offtakers
    @variable(model, u_ship >= 0)             # single scalar unmet for shipping

    # ----------------------
    # Objective
    # ----------------------
    @objective(model, Min,
        sum(c[i,j] * f[p,i,j] for p in P, (i,j) in valid_edges)
        + sum(Prodcost[p] * prod[p] for p in P)
        + sum(pi[1] * u[o] for o in O_rigid)
        + pi[3] * u_ship
    )

    # Production node outflow
    @constraint(model, [p in P],
        sum(f[p,p,j] for j in N if (p,j) in valid_edges) == prod[p]
    )

    # Production capacity
    @constraint(model, [p in P],
        prod[p] <= MaxP[p]
    )

    # Delivered quantity at every offtake node (rigid and ship candidates)
    @constraint(model, [o in O],
        sum(f[p,i,o] for p in P, i in N if (i,o) in valid_edges) == q[o]
    )

    # Rigid demand: per-node satisfaction for steel + fert
    @constraint(model, [o in O_rigid],
        q[o] + u[o] >= D_rigid[o]
    )

    # Flexible shipping demand: aggregate across all candidate ports
    @constraint(model,
        sum(q[o] for o in O_ship) + u_ship >= D_ship
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

    return model, f, q, u, u_ship, prod, valid_edges
end

end # module