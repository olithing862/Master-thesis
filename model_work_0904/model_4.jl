module Model_april

using JuMP
using Gurobi


function network_model(P, T, O, N,
                            c,           # Dict or matrix: c[i,j]
                            MaxP,        # Dict: MaxP[p]
                            Prodcost,    # Dict: Prodcost[p]
                            D,           # Dict: D[o]
                            π)           # scalar

    model = Model()

    # ----------------------
    # Decision variables
    # ----------------------
    @variable(model, f[p in P, i in N, j in N] >= 0)
    @variable(model, prod[p in P] >= 0)
    @variable(model, q[o in O] >= 0)
    @variable(model, u[o in O] >= 0)

    # ----------------------
    # Objective
    # ----------------------
    @objective(model, Min,
        sum(c[i,j] * f[p,i,j] for p in P, i in N, j in N)
        + sum(Prodcost[p] * prod[p] for p in P)
        + sum(π * u[o] for o in O)
    )

    # ----------------------
    # Constraints
    # ----------------------

    # Production equals outgoing flow from production node
    @constraint(model,
        [p in P],
        sum(f[p, p, j] for j in N) == prod[p]
    )

    # Production capacity
    @constraint(model,
        [p in P],
        prod[p] <= MaxP[p]
    )

    # Delivered quantity at offtake nodes
    @constraint(model,
        [o in O],
        sum(f[p, i, o] for p in P, i in N) == q[o]
    )

    # Demand satisfaction
    @constraint(model,
        [o in O],
        q[o] + u[o] >= D[o]
    )

    # Flow conservation at transit nodes
    @constraint(model,
        [p in P, t in T],
        sum(f[p, t, j] for j in N)
        ==
        sum(f[p, i, t] for i in N)
    )

    # No flow of commodity p from other production nodes
    @constraint(model,
        [p in P, i in P, j in N; i != p],
        f[p, i, j] == 0
    )

    return model, f, q, u, prod
end
end # module