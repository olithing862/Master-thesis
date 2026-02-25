module ShippingModelFinal

using JuMP
using Gurobi

function compute_arc_cost(i, j,
                          shipping_rate,
                          region_of,
                          mode_of,
                          distance_of,
                          truckcost)

    if mode_of[(i,j)] == "ship"
        return shipping_rate[(region_of[i], region_of[j])]
    else
        d = distance_of[(i,j)]

        if d < 200
            rate = truckcost[1]
        elseif d < 400
            rate = truckcost[2]
        elseif d < 600
            rate = truckcost[3]
        elseif d < 1000
            rate = truckcost[4]
        elseif d <= 1600
            rate = truckcost[5]
        else
            rate = truckcost[6]
        end

        return rate * 18.6   # convert $/GJ → $/ton
    end
end


function build_model_with_penalty(
    N, P, T, O, A,
    shipping_rate,
    maxP,
    Demand,
    penalty,
    region_of,
    mode_of,
    distance_of,
    truckcost
)

    model = Model(Gurobi.Optimizer)

    # ----------------------------
    # Variables
    # ----------------------------
    @variable(model, f[p in P, (i,j) in A] >= 0)
    @variable(model, prod[p in P] >= 0)
    @variable(model, u[o in O] >= 0)
    @variable(model, q[o in O] >= 0)

    # ----------------------------
    # Objective
    # ----------------------------
    @objective(model, Min,
        sum(
            compute_arc_cost(i,j,
                             shipping_rate,
                             region_of,
                             mode_of,
                             distance_of,
                             truckcost)
            * f[p,(i,j)]
            for p in P for (i,j) in A
        )
        + sum(penalty * u[o] for o in O)
    )
    @constraint(model,
    [p in P, (i,j) in A; i in P && i != p],
    f[p,(i,j)] == 0
    )

    # ----------------------------
    # Production capacity
    # ----------------------------
    @constraint(model,
        [p in P],
        sum(f[p,(p,j)] for j in N if (p,j) in A) <= maxP[p]
    )

    # ----------------------------
    # Flow conservation at terminals
    # ----------------------------
    @constraint(model,
        [p in P, t in T],
        sum(f[p,(i,t)] for i in N if (i,t) in A)
        ==
        sum(f[p,(t,j)] for j in N if (t,j) in A)
    )

    # ----------------------------
    # Define production variable
    # ----------------------------
    @constraint(model,
        [p in P],
        prod[p] ==
        sum(f[p,(p,j)] for j in N if (p,j) in A)
    )

    # ----------------------------
    # Demand accounting
    # ----------------------------
    @constraint(model,
        [o in O],
        q[o] ==
        sum(f[p,(i,o)] for p in P for i in N if (i,o) in A)
    )

    @constraint(model,
        [o in O],
        q[o] + u[o] == Demand[o]
    )

    return model, f, q, u, prod
end

end