module ShippingData

using Random

function generate_data(; seed = 42)
    Random.seed!(seed)

    # Sets
    O = ["O1","O2","O3","O4","O5","O6","O7","O8","O9","O10"]
    P = ["P1","P2","P3","P4"]
    T = ["T1","T2","T3","T4","T5"]
    N = vcat(P, T, O)

    # Arc definitions
    PT = Dict(
        "P1" => ["T1","T2"],
        "P2" => ["T2"],
        "P3" => ["T3","T4"],
        "P4" => ["T5"]
    )

    TO = Dict(
        "T1" => ["O1","O2"],
        "T2" => ["O3","O4","O5"],
        "T3" => ["O6"],
        "T4" => ["O7","O8"],
        "T5" => ["O9","O10"]
    )

    TT = [
        ("T1","T2"),
        ("T2","T3"),
        ("T3","T4"),
        ("T4","T5")
    ]

    # Build arc set
    A = Set{Tuple{String,String}}()

    for (p, ts) in PT, t in ts
        push!(A, (p,t))
    end

    for (t, os) in TO, o in os
        push!(A, (t,o))
    end

    for (t1,t2) in TT
        push!(A, (t1,t2))
    end

    spot_price = Dict(
    "P1" => 15.0,
    "P2" => 15.0,
    "P3" => 15.0,
    "P4" => 15.0)

    # Production capacity
    maxP = Dict(
        "P1" => 100.0,
        "P2" => 9000.0,
        "P3" => 25.0,
        "P4" => 80.0
    )

    # Transport costs
    c = Dict{Tuple{String,String}, Float64}()

    for (i,j) in A
        if i in P && j in T
            c[(i,j)] = rand(8.0:1.0:15.0)
        elseif i in T && j in T
            c[(i,j)] = rand(12.0:1.0:25.0)
        elseif i in T && j in O
            c[(i,j)] = rand(20.0:1.0:45.0)
        end
    end

    # Transport capacities
    maxT = Dict{Tuple{String,String}, Float64}()

    for (i,j) in A
        if i in P && j in T
            maxT[(i,j)] = 100.0
        elseif i in T && j in T
            maxT[(i,j)] = 150.0
        elseif i in T && j in O
            maxT[(i,j)] = 70.0
        end
    end

    # Demand caps
    Dmax = Dict(
        "O1" => 80.0, "O2" => 50.0, "O3" => 70.0,
        "O4" => 40.0, "O5" => 90.0, "O6" => 55.0,
        "O7" => 65.0, "O8" => 90.0, "O9" => 80.0,
        "O10" => 75.0
    )
    WTP = Dict(
    "O1"  => 130.0,  # steel / chemicals
    "O2"  => 125.0,
    "O3"  => 110.0,  # shipping (high-end)
    "O4"  => 100.0,
    "O5"  => 95.0,
    "O6"  => 85.0,   # shipping (lower-end)
    "O7"  => 75.0,   # fertilizer
    "O8"  => 70.0,
    "O9"  => 60.0,
    "O10" => 55.0)
    penalty = 1000000
    return (
        O = O,
        P = P,
        T = T,
        N = N,
        A = A,
        c = c,
        WTP = WTP,
        maxP = maxP,
        maxT = maxT,
        Dmax = Dmax,
        spot_price = spot_price,
        penalty = penalty
    )
end

end # module
