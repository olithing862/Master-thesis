include("initial.jl")
include("model.jl")

using .ShippingData
using .ShippingModel
using Graphs
using CairoMakie
using GraphMakie
using JuMP


data = ShippingData.generate_data()
model,f,q,_,_,prod = ShippingModel.build_model(data)
O = data.O
WTP, Dmax = data.WTP, data.Dmax
P = data.P
T = data.T
A = data.A

optimize!(model)
println("\nDelivered quantities:")
for o in O
    println(
        o,
        ": delivered = ", round(value(q[o]), digits=2),
        " / Demand required = ", Dmax[o],
        " | WTP = ", WTP[o]
    )
end
#Production sites used
println("\nProduction quantities:")
for p in P
    println(
        p,
        ": produced = ", round(value(prod[p]), digits=2),
        " | Spot price = ", data.spot_price[p]
    )
end
println("\nFlow on arcs (non-zero only):")
for p in P, (i,j) in A
    val = value(f[p,(i,j)])
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
    flow_on_arc[(i,j)] = sum(value(f[p,(i,j)]) for p in P)
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
fig = Figure(size = (1000, 700))
ax = Axis(fig[1,1], title = "Shipping network (red = used, grey = unused)")

graphplot!(
    ax, g,
    node_labels = nodes,
    node_color = node_colors,
    edge_color = edge_colors,
    edge_width = edge_widths,
    arrow_size = 12
)

fig
