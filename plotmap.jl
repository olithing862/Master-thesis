using CSV
using DataFrames
using CairoMakie
using GeoMakie
using NaturalEarth

df = CSV.read("steel_sites__City_and_Country_separated_.csv", DataFrame)

fig = Figure(resolution = (1100, 600))
ax = GeoAxis(fig[1, 1],
             title = "Global Steel Production Sites")

# This already returns a FeatureCollection
world = naturalearth("admin_0_countries", 110)

# Draw country outlines
for feature in world.features
    poly!(ax,
          feature.geometry.coordinates;
          color = :transparent,
          strokecolor = :gray40,
          strokewidth = 0.3)
end

# Plot steel sites
for c in unique(df.Country)
    sub = df[df.Country .== c, :]
    scatter!(ax,
             sub.Longitude,
             sub.Latitude,
             markersize = 10,
             label = c)
end

axislegend(ax, position = :rb)

fig
