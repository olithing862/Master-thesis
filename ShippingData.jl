module ShippingData

using CSV
using DataFrames
using Random
function generate_data(; seed=42)

    # ----------------------------
    # Load files
    # ----------------------------
    nodes = CSV.read("nodes.csv", DataFrame)
    edges = CSV.read("edges_complete_network.csv", DataFrame)
    costs = CSV.read("shippingcost.csv", DataFrame)
    # ----------------------------
    # Define sets
    # ----------------------------
    N = unique(nodes.node_id)

    P = filter(x -> startswith(x, "ps"), N)
    O = filter(x -> startswith(x, "os"), N)
    T = filter(x -> startswith(x, "t"), N)

    A = Set((row.from_id, row.to_id) for row in eachrow(edges))
    truck_cost = 20

    clusters = names(costs)[2:end]   # skip "Cluster" column

    shipping_rate = Dict{Tuple{String,String}, Float64}()

    for row in eachrow(costs)

        i = row.Cluster

        for j in clusters

            val_ij = row[j]

            # If upper triangle value exists
            if !ismissing(val_ij)
                shipping_rate[(i,j)] = val_ij
                shipping_rate[(j,i)] = val_ij
            end
        end
    end
    maxP = Dict(
        "ps1" => 100.0,
        "ps2" => 9000.0,
        "ps3" => 25.0,
        "ps4" => 80.0
        "ps5" => 100.0,
        "ps6" => 9000.0,
        "ps7" => 25.0
        "ps8" => 80.0
        "ps9" => 100.0,
        "ps10" => 9000.0,
    )
  
    Random.seed!(42)

    Demand = Dict(o => rand(300.0:10.0:800.0) for o in O)
    maxP = Dict(p => rand(50.0:10.0:1000.0) for p in P)
    penalty = 1000000
    return N, P, T, O, A, shipping_rate, maxP, Demand, penalty, truck_cost
end
N, P, T, O, A, shipping_rate, maxP, Demand, penalty, truck_cost = generate_data()
print(shipping_rate)