module ShippingData
using CSV 
using DataFrames
using Random

function generate_data(; seed=42)

    nodes = CSV.read("nodes.csv", DataFrame)
    edges = CSV.read("edges_complete_network1.csv", DataFrame)
    costs = CSV.read("shippingcost.csv", DataFrame)

    # ----------------------------
    # Sets
    # ----------------------------
    N = unique(nodes.node_id)

    P = filter(x -> startswith(x, "ps"), N)
    O = filter(x -> startswith(x, "os"), N)
    T = filter(x -> startswith(x, "t"), N)

    A = Set((row.from_id, row.to_id) for row in eachrow(edges))

    # ----------------------------
    # Region mapping
    # ----------------------------
    region_of = Dict(row.node_id => row.region for row in eachrow(nodes))

    # ----------------------------
    # Mode + distance
    # ----------------------------
    mode_of = Dict(
        (row.from_id, row.to_id) => row.mode
        for row in eachrow(edges)
    )

    distance_of = Dict(
        (row.from_id, row.to_id) => row.distance_km
        for row in eachrow(edges)
    )

    # ----------------------------
    # Shipping cost matrix
    # ----------------------------
    clusters = names(costs)[2:end]
    shipping_rate = Dict{Tuple{String,String}, Float64}()

    for row in eachrow(costs)
        i = row.Cluster
        for j in clusters
            val_ij = row[j]
            if !ismissing(val_ij)
                shipping_rate[(i,j)] = val_ij
                shipping_rate[(j,i)] = val_ij
            end
        end
    end

    Random.seed!(seed)

    Demand = Dict(o => rand(300.0:10.0:800.0) for o in O)
    maxP = Dict(p => rand(450.0:10.0:1000.0) for p in P)

    penalty = 10000000

    truck_cost_per_km = 0.08   # example €/ton/km (choose realistic value)
    truckcost = [5, 15.0, 20.0, 25, 30,40] # example cost per ton based on distance brackets
    
    return N, P, T, O, A,
           shipping_rate,
           maxP, Demand,
           penalty,
           region_of,
           mode_of,
           distance_of,
           truck_cost_per_km,
            truckcost
end
end # module