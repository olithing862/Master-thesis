

module ShippingModel2


using JuMP
using Gurobi

function build_model_with_penalty(data)
    model = Model(Gurobi.Optimizer)

    O = data.O
    P = data.P
    T = data.T
    A = data.A
    c = data.c
    N = data.N
    maxP = data.maxP
    maxT = data.maxT
    D = data.Dmax
    penalty = data.penalty
    spot_price = data.spot_price
    # Decision variables
    @variable(model, f[p in P, (i,j) in A] >= 0)
    @variable(model, q[o in O] >= 0)
    @variable(model, u[o in O] >= 0)  # Spot market purchases
    @variable(model, prod[p in P] >= 0)


    @objective(model, Min, sum(c[(i,j)] * f[p,(i,j)] for p in P for (i,j) in A) 
    + sum(penalty*(u[o]) for o in O))

    # Flow variables are zero for arcs that do not originate from the production node
    @constraint(model,
    [p in P, (i,j) in A; i in P && i != p],
    f[p,(i,j)] == 0
    )
    # Production capacity constraints
    @constraint(model,[p in P],sum(f[p,(p,t)] for t in T if (p,t) in A) <= maxP[p])

    # Transportation capacity constraints
    #@constraint(model,[(i,j) in A], sum(f[p,(i,j)] for p in P) <= maxT[(i,j)])

    #flow conservation constraints
    @constraint(model,
        [t in T, p in P],
        sum(f[p,(i,t)] for i in N if (i,t) in A)
        ==
        sum(f[p,(t,j)] for j in N if (t,j) in A)
    )

    @constraint(model,
    [p in P],
    prod[p] == sum(f[p,(p,t)] for t in T if (p,t) in A)
    )

    # Demand constraints
    @constraint(model, [o in O], q[o] + u[o] >= D[o])

    #q is the delivered quantity to each customer. 
    @constraint(model, [o in O], q[o] == sum(f[p,(t,o)] for p in P for t in T if (t,o) in A))
    #o1 must have atleast 90% 
    #@constraint(model, q["O1"] >= 0.5*D["O1"])
    return model, f, q, u, prod
end 
end 


