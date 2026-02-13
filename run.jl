include("initial.jl")
include("model.jl")
include("model_2.jl")

using .ShippingData
using .ShippingModel
using Graphs
using CairoMakie
using GraphMakie
using JuMP


data = ShippingData.generate_data()
model,f,q,_,_,prod = ShippingModel.build_model(data)
model2, f2, q2, u2, prod2 = ShippingModel2.build_model_with_penalty(data)
O = data.O
WTP, Dmax,penalty = data.WTP, data.Dmax, data.penalty
P = data.P
T = data.T
A = data.A


optimize!(model2)
println("\nDelivered quantities:")
for o in O
    println(
        o,
        ": delivered = ", round(value(q2[o]), digits=2),
        " / Demand required = ", Dmax[o],
        " | Unmet demand = ", round(value(u2[o]), digits=2),
    )
end
#Production sites used
println("\nProduction quantities:")
for p in P
    println(
        p,
        ": produced = ", round(value(prod2[p]), digits=2),
        " | Spot price = ", data.spot_price[p]
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
nodes = vcat(P, T, O)
node_index = Dict(n => i for (i,n) in enumerate(nodes))
g = DiGraph(length(nodes))

for (i,j) in A
    add_edge!(g, node_index[i], node_index[j])
end
flow_on_arc = Dict{Tuple{String,String}, Float64}()

for (i,j) in A
    flow_on_arc[(i,j)] = sum(value(f2[p,(i,j)]) for p in P)
end

edge_colors = Vector{RGBAf}(undef, ne(g))
edge_widths = Vector{Float64}(undef, ne(g))

edges_list = collect(edges(g))

for (k, e) in enumerate(edges_list)
    i = nodes[src(e)]
    j = nodes[dst(e)]
    flow = flow_on_arc[(i,j)]

    if flow > 1e-6
        edge_colors[k] = RGBAf(1, 0, 0, 0.9)   # red = used
        edge_widths[k] = 2 + 0.05 * flow      # scale by flow
    else
        edge_colors[k] = RGBAf(0.7, 0.7, 0.7, 0.6)  # grey = unused
        edge_widths[k] = 1.0
    end
end
node_colors = [
    n in P ? :green :
    n in T ? :blue  :
             :orange
    for n in nodes
]
node_labels = [
    n in O ? n : ""
    for n in nodes
]
fig = Figure(size = (1000, 700))
ax = Axis(fig[1,1], title = "Shipping network (red = used, grey = unused)")

graphplot!(
    ax, g,
    node_labels = node_labels,
    node_color = node_colors,
    edge_color = edge_colors,
    edge_width = edge_widths,
    arrow_size = 12,
    node_size = 20,
    node_label_size = 18,   # increase label size
)
#Print the origin at which each o recieves the flow from
for o in O
    for p in P, t in T
        if (t,o) in A && value(f2[p,(t,o)]) > 1e-6
            println("Customer ", o, " receives flow from production site ", p, " via transit node ", t)
        end
    end
end 

fig
