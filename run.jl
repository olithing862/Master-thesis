include("ShippingData.jl")
include("model_3.jl")

using .ShippingData
using .ShippingModelFinal
using JuMP
using CSV
using DataFrames

# ----------------------------
# Generate data
# ----------------------------
N, P, T, O, A,
shipping_rate,
maxP, Demand,
penalty,
region_of,
mode_of,
distance_of,
truck_cost_per_km,truckcost,Demand_rand,Prodcost =
    ShippingData.generate_data()
print(Demand_rand)
print(Demand)
print(maxP)

# ----------------------------
# Build model
# ----------------------------
model2, f2,q2, u2, prod2 =
    ShippingModelFinal.build_model_with_penalty(
    N, P, T, O, A,
    shipping_rate,
    maxP,
    Demand,
    penalty,
    region_of,
    mode_of,
    distance_of,
    truckcost,
    Prodcost
)

optimize!(model2)


flow_rows = DataFrame(
    from_id = String[],
    to_id = String[],
    flow = Float64[]
)

for (i,j) in A
    total_flow = sum(value(f2[p,(i,j)]) for p in P)

    if total_flow > 1e-6
        push!(flow_rows, (i, j, total_flow))
    end
end

println("Flows saved to optimized_flows.csv")
# ----------------------------
# Print results
# ----------------------------
println("\nDelivered quantities:")
for o in O
    println(
        o,
        ": delivered = ", round(value(q2[o]), digits=2),
        " / Demand required = ", Demand[o],
        " | Unmet demand = ", round(value(u2[o]), digits=2),
    )
end

println("\nProduction quantities:")
for p in P
    println(
        p,
        ": produced = ", round(value(prod2[p]), digits=2),
        " | Capacity = ", maxP[p]
    )
end

println("\nFlow on arcs (non-zero only):")
for p in P, (i,j) in A
    val = value(f2[p,(i,j)])
    if val > 1e-6
        println(
            "Origin ", p, ": ",
            i, " → ", j,
            " | flow = ", round(val, digits=2)
        )
    end
end
println("\nCustomer supply routes:")

for o in O
    for p in P

        # Check ALL incoming arcs to o
        for i in N
            if (i,o) in A && value(f2[p,(i,o)]) > 1e-6

                if i == p
                    println("Customer ", o,
                            " receives DIRECT flow from ", p)
                else
                    println("Customer ", o,
                            " receives flow from ", p,
                            " via ", i)
                end

            end
        end

    end
end
#delivered to customer from production site via terminal and directly from production site

flow_rows = DataFrame(
    from_id = String[],
    to_id   = String[],
    flow    = Float64[]
)

for (i,j) in A
    total_flow = sum(value(f2[p,(i,j)]) for p in P)

    if total_flow > 1e-6
        push!(flow_rows, (i, j, total_flow))
    end

end

#I want to write a description name and use as name for csv file 
#and i want to save it here /Users/oliviathingvad/Master-thesis/Results
description = "results_02march_1"


CSV.write("/Users/oliviathingvad/Master-thesis/Results/$(description).csv", flow_rows)
println("Saved: $(description).csv")