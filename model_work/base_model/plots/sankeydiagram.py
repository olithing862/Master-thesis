"""
Sankey diagram showing flow from production regions through transit
regions to offtake regions.

Reads results_flows_<date>.csv and nodes.csv, aggregates flows by
region at each stage, and renders an interactive Plotly Sankey.
"""

import pandas as pd
import plotly.graph_objects as go
from pathlib import Path


def plot_sankey(nodes_csv, flows_csv, output_html,
                title="Flow network: production → transit → offtake",
                min_flow=0.0, palette=None):
    """
    Build a three-column Sankey of regional flows.

    Parameters
    ----------
    nodes_csv : path to nodes CSV with columns node_id, region, type.
    flows_csv : path to flows CSV with columns from_id, to_id, flow.
    output_html : where to save the interactive figure.
    title : plot title.
    min_flow : flows below this threshold (Mt) are dropped before
        aggregation. Useful for filtering numerical noise.
    palette : optional list of hex colors for regions; auto if None.
    """
    nodes = pd.read_csv(nodes_csv)[["node_id", "region", "type"]]
    flows = pd.read_csv(flows_csv)
    flows["from_id"] = flows["from_id"].astype(str)
    flows["to_id"]   = flows["to_id"].astype(str)
    flows = flows[flows["flow"] > min_flow].copy()

    # Join region + type for both endpoints
    flows = (
        flows
        .merge(nodes.rename(columns={"node_id": "from_id",
                                     "region":  "from_region",
                                     "type":    "from_type"}),
               on="from_id", how="left")
        .merge(nodes.rename(columns={"node_id": "to_id",
                                     "region":  "to_region",
                                     "type":    "to_type"}),
               on="to_id", how="left")
    )

    # Identify the two flow stages
    #   stage A: production -> transit    (prod region -> transit region)
    #   stage B: transit    -> offtake    (transit region -> offtake region)
    # Direct production -> offtake (no transit hop) goes straight to stage B-style,
    # but labeled via a synthetic "Direct" middle column so it still renders.
    stage_a = flows[(flows["from_type"] == "production") &
                    (flows["to_type"]   == "transit")].copy()
    stage_b = flows[(flows["from_type"] == "transit") &
                    (flows["to_type"]   == "offtake")].copy()
    stage_tt = flows[(flows["from_type"] == "transit") &
                     (flows["to_type"]   == "transit")].copy()
    direct  = flows[(flows["from_type"] == "production") &
                    (flows["to_type"]   == "offtake")].copy()

    # Build labels from every region that appears in the relevant stage,
    # on either side of the arc. This catches transit regions that only
    # appear as the source of a transit->transit hop, for example.
    prod_labels = set(stage_a["from_region"].dropna()) \
                | set(direct["from_region"].dropna())

    transit_labels = set(stage_a["to_region"].dropna()) \
                   | set(stage_b["from_region"].dropna()) \
                   | set(stage_tt["from_region"].dropna()) \
                   | set(stage_tt["to_region"].dropna())

    off_labels = set(stage_b["to_region"].dropna()) \
               | set(direct["to_region"].dropna())

    prod_labels    = sorted(prod_labels)
    transit_labels = sorted(transit_labels)
    off_labels     = sorted(off_labels)

    # If any direct flows exist, add a synthetic transit label for them
    if not direct.empty:
        transit_labels = transit_labels + ["(direct)"]

    def idx_prod(r):    return prod_labels.index(r)
    def idx_trans(r):   return len(prod_labels) + transit_labels.index(r)
    def idx_off(r):     return len(prod_labels) + len(transit_labels) + off_labels.index(r)

    # Transit -> transit flows can't render as arrows within the same column.
    # Collapse them into stage B by re-attributing stage_b flows that start at
    # the destination of a t->t hop to the original source instead. For a chain
    # t_A -> t_B -> oft, we also render an explicit t_A -> t_B link at the end,
    # but only if the regions differ, so it stays readable.
    # Simple approach: render t->t arcs as a shaded self-link column by adding
    # an extra "intermediate" node is overkill; instead we just render them
    # below, after stage_b, with a light warning color so they're visible.
    agg_a = (stage_a.groupby(["from_region", "to_region"], as_index=False)["flow"]
                    .sum())
    agg_b = (stage_b.groupby(["from_region", "to_region"], as_index=False)["flow"]
                    .sum())
    agg_d = (direct.groupby(["from_region", "to_region"], as_index=False)["flow"]
                   .sum())
    # Only keep t->t hops that cross region boundaries (same-region t->t is noise)
    agg_tt = (stage_tt[stage_tt["from_region"] != stage_tt["to_region"]]
              .groupby(["from_region", "to_region"], as_index=False)["flow"]
              .sum())

    # Build link arrays
    sources, targets, values, link_labels = [], [], [], []

    for _, r in agg_a.iterrows():
        sources.append(idx_prod(r["from_region"]))
        targets.append(idx_trans(r["to_region"]))
        values.append(r["flow"])
        link_labels.append(f"{r['from_region']} → {r['to_region']}: {r['flow']:,.2f} Mt")

    for _, r in agg_b.iterrows():
        sources.append(idx_trans(r["from_region"]))
        targets.append(idx_off(r["to_region"]))
        values.append(r["flow"])
        link_labels.append(f"{r['from_region']} → {r['to_region']}: {r['flow']:,.2f} Mt")

    for _, r in agg_d.iterrows():
        # production -> (direct) -> offtake, two hops for rendering
        sources.append(idx_prod(r["from_region"]))
        targets.append(idx_trans("(direct)"))
        values.append(r["flow"])
        link_labels.append(f"{r['from_region']} → (direct): {r['flow']:,.2f} Mt")

        sources.append(idx_trans("(direct)"))
        targets.append(idx_off(r["to_region"]))
        values.append(r["flow"])
        link_labels.append(f"(direct) → {r['to_region']}: {r['flow']:,.2f} Mt")

    # Transit -> transit hops (cross-region only)
    for _, r in agg_tt.iterrows():
        sources.append(idx_trans(r["from_region"]))
        targets.append(idx_trans(r["to_region"]))
        values.append(r["flow"])
        link_labels.append(f"{r['from_region']} → {r['to_region']} (transit hop): {r['flow']:,.2f} Mt")

    # Node labels and colors
    all_labels = prod_labels + transit_labels + off_labels

    if palette is None:
        # Auto: one color per unique region, grey for (direct)
        import itertools
        base_colors = ["#4C72B0", "#DD8452", "#55A467", "#C44E52", "#8172B2",
                       "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD",
                       "#5A9BD4", "#E07B39", "#6FAE55", "#CF5C5E"]
        color_cycle = itertools.cycle(base_colors)
        region_color = {}
        for lbl in set(prod_labels) | set(off_labels) | (set(transit_labels) - {"(direct)"}):
            region_color[lbl] = next(color_cycle)
        region_color["(direct)"] = "#BBBBBB"
        node_colors = [region_color[lbl] for lbl in all_labels]
    else:
        node_colors = palette[:len(all_labels)]

    # Match link colors to their source node (translucent) for cleaner visual flow
    def hex_to_rgba(h, alpha=0.35):
        h = h.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    link_colors = [hex_to_rgba(node_colors[s]) for s in sources]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=18,
            thickness=18,
            line=dict(color="white", width=0.5),
            label=all_labels,
            color=node_colors,
            hovertemplate="%{label}<br>Total: %{value:,.2f} Mt<extra></extra>",
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            label=link_labels,
            color=link_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
    ))

    # Column annotations
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=15)),
        font=dict(size=11),
        height=700,
        margin=dict(l=10, r=10, t=70, b=30),
        annotations=[
            dict(x=0.01, y=1.08, xref="paper", yref="paper",
                 text="<b>Production region</b>", showarrow=False, font=dict(size=12)),
            dict(x=0.50, y=1.08, xref="paper", yref="paper",
                 text="<b>Transit region</b>", showarrow=False, font=dict(size=12)),
            dict(x=0.99, y=1.08, xref="paper", yref="paper",
                 text="<b>Offtake region</b>", showarrow=False, font=dict(size=12)),
        ],
    )

    fig.write_html(output_html)
    print(f"Sankey saved to {output_html}")
    return fig


if __name__ == "__main__":
    results_dir = Path("Results")
    date = "20043"
    flow = pd.read_csv(results_dir / f"results_flows_{date}.csv")
    #print flow out of and into t93
    print(flow[(flow['to_id'] == 'oft_steel12')])

    plot_sankey(
        nodes_csv   = "model_work/DataFiles_base/nodes.csv",
        flows_csv   = results_dir / f"results_flows_{date}.csv",
        output_html = results_dir / f"sankey_{date}.html",
    )
