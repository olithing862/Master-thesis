module Model_april_2

using JuMP
using Gurobi


function network_model(P, T, O, N,
                            c,           # Dict or matrix: c[i,j]
                            MaxP,        # Dict: MaxP[p]
                            Prodcost,    # Dict: Prodcost[p]
                            D,           # Dict: D[o]
                            π)           # scalar

    model = Model(Gurobi.Optimizer)

    # ----------------------
    # Decision variables
    # ----------------------
    


    # Valid edges as a Set of tuples
    valid_edges = Set((i,j) for i in N for j in N if isfinite(c[i,j]))

    # Index f as f[p,i,j] using a SparseAxisArray via @variable with a condition
    @variable(model, f[p in P, i in N, j in N; (i,j) in valid_edges] >= 0)
    @variable(model, prod[p in P] >= 0)
    @variable(model, q[o in O] >= 0)
    @variable(model, u[o in O] >= 0)

    # Objective
    @objective(model, Min,
        sum(c[i,j] * f[p,i,j] for p in P, (i,j) in valid_edges)
        + sum(Prodcost[p] * prod[p] for p in P)
        + sum(π * u[o] for o in O)
    )

    # Production node outflow
    @constraint(model, [p in P],
        sum(f[p,p,j] for j in N if (p,j) in valid_edges) == prod[p]
    )

    # Production capacity
    @constraint(model, [p in P],
        prod[p] <= MaxP[p]
    )

    # Delivered quantity at offtake nodes
    @constraint(model, [o in O],
        sum(f[p,i,o] for p in P, i in N if (i,o) in valid_edges) == q[o]
    )

    # Demand satisfaction
    @constraint(model, [o in O],
        q[o] + u[o] >= D[o]
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
    return model, f, q, u, prod,valid_edges
end
end # module