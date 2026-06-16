"""
Top trade lanes bar chart.

Aggregates flows at the node-pair level, sorts descending, and plots
the top N as a horizontal bar chart. Bars are colored by whether the
lane is intra-region (grey) or inter-region (blue).
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def plot_top_lanes(nodes_csv, flows_csv, output_path,
                   top_n=15, title=None, figsize=(10, 7)):
    """
    Plot top-N flows as a horizontal bar chart.

    Parameters
    ----------
    nodes_csv : path to nodes.csv with columns node_id, region, Location.
    flows_csv : path to results_flows_*.csv with columns from_id, to_id, flow.
    output_path : where to save the figure (.png).
    top_n : number of lanes to show (default 15).
    title : optional plot title.
    figsize : matplotlib figure size.
    """
    nodes = pd.read_csv(nodes_csv)
    flows = pd.read_csv(flows_csv)

    flows["from_id"] = flows["from_id"].astype(str)
    flows["to_id"]   = flows["to_id"].astype(str)

    # Aggregate flows at the node-pair level (sum across commodities if any)
    lanes = (flows.groupby(["from_id", "to_id"], as_index=False)["flow"]
                  .sum()
                  .sort_values("flow", ascending=False)
                  .head(top_n))

    # Attach region + location info for both endpoints
    meta = nodes[["node_id", "region", "Location"]]
    lanes = (lanes
             .merge(meta.rename(columns={"node_id": "from_id",
                                         "region":  "from_region",
                                         "Location": "from_loc"}),
                    on="from_id", how="left")
             .merge(meta.rename(columns={"node_id": "to_id",
                                         "region":  "to_region",
                                         "Location": "to_loc"}),
                    on="to_id", how="left"))

    # Intra vs inter region
    lanes["intra"] = lanes["from_region"] == lanes["to_region"]
    lanes["label"] = (lanes["from_loc"].fillna(lanes["from_id"])
                      + " → "
                      + lanes["to_loc"].fillna(lanes["to_id"]))

    # Sort so the biggest bar is at the top
    lanes = lanes.sort_values("flow", ascending=True).reset_index(drop=True)

    colors = ["#888888" if intra else "#3A6EA5" for intra in lanes["intra"]]

    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.barh(lanes["label"], lanes["flow"], color=colors,
                   edgecolor="white", linewidth=0.5)

    # Value labels at the end of each bar
    max_flow = lanes["flow"].max()
    for bar, val in zip(bars, lanes["flow"]):
        ax.text(bar.get_width() + max_flow * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,.2f}",
                va="center", ha="left", fontsize=9, color="#333")

    # Cosmetic
    ax.set_xlabel("Flow (Mt)", fontsize=11)
    ax.set_title(title or f"Top {top_n} trade lanes by flow volume",
                 fontsize=13, pad=15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, max_flow * 1.15)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#3A6EA5", label="Inter-region"),
        Patch(facecolor="#888888", label="Intra-region"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", frameon=False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"Top lanes chart saved to {output_path}")
    plt.show()
    return lanes


if __name__ == "__main__":
    results_dir = Path("Results")
    date = "20043"

    top = plot_top_lanes(
        nodes_csv   = "model_work/DataFiles_base/nodes.csv",
        flows_csv   = results_dir / f"results_flows_{date}.csv",
        output_path = results_dir / f"top_lanes_{date}.png",
        top_n       = 15,
        title       = "Base model: top 15 trade lanes (2030)",
    )
    print(top[["label", "flow", "intra"]].to_string(index=False))