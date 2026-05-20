"""
Production cost vs volume per region.

For each production region, shows:
  - bars: total production volume (Mt) — left y-axis
  - dots: average production cost per tonne (USD/t) — right y-axis

Regions are sorted ascending by cost, so the visual pattern reveals
whether low-cost regions are fully exploited or bottlenecked.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def plot_prodcost_vs_volume(nodes_csv, prod_csv, prodcost_csv, output_path,
                            title=None, figsize=(12, 6)):
    """
    Two-axis plot: production volume bars + cost per tonne markers, by region.

    Parameters
    ----------
    nodes_csv : path to nodes.csv (node_id, region, type, ...).
    prod_csv : path to results_production_*.csv (node_id, produced, capacity).
    prodcost_csv : path to prodcost.csv (region, prod_cost) where prod_cost
        is in millions USD per Mt (i.e. USD/tonne when you scale).
    output_path : where to save the figure.
    title : plot title.
    figsize : figure size.
    """
    nodes = pd.read_csv(nodes_csv)
    prod  = pd.read_csv(prod_csv)
    costs = pd.read_csv(prodcost_csv)

    # Join production results with region via node metadata
    prod["node_id"] = prod["node_id"].astype(str)
    nodes["node_id"] = nodes["node_id"].astype(str)

    df = prod.merge(nodes[["node_id", "region"]], on="node_id", how="left")

    # Aggregate produced volume and capacity by region
    agg = (df.groupby("region", as_index=False)
             .agg(produced=("produced", "sum"),
                  capacity=("capacity", "sum")))
    agg["utilization_pct"] = 100 * agg["produced"] / agg["capacity"].replace(0, 1)

    # Attach production cost per region
    agg = agg.merge(costs[["region", "prod_cost"]], on="region", how="left")

    # Drop regions with no production capacity
    agg = agg[agg["capacity"] > 0].copy()

    # Sort by cost ascending (cheapest on the left)
    agg = agg.sort_values("prod_cost", ascending=True).reset_index(drop=True)

    # Compute bar colors: utilization-based
    def util_color(pct):
        if pct >= 99:   return "#2E7D32"   # green: fully used
        if pct >= 50:   return "#F9A825"   # amber: partial
        return "#C62828"                    # red: barely used

    bar_colors = [util_color(p) for p in agg["utilization_pct"]]

    # Figure
    fig, ax1 = plt.subplots(figsize=figsize)

    x = range(len(agg))
    bars = ax1.bar(x, agg["produced"], color=bar_colors,
                   edgecolor="white", linewidth=0.5,
                   label="Production volume (Mt)")

    # Utilization % on top of each bar
    for bar, pct in zip(bars, agg["utilization_pct"]):
        ax1.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + agg["produced"].max() * 0.015,
                 f"{pct:.0f}%", ha="center", va="bottom",
                 fontsize=8, color="#555")

    ax1.set_ylabel("Production volume (Mt)", fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(agg["region"], rotation=35, ha="right", fontsize=9)
    ax1.set_ylim(0, agg["produced"].max() * 1.18)
    ax1.spines["top"].set_visible(False)

    # Right axis: cost per tonne
    ax2 = ax1.twinx()
    ax2.plot(x, agg["prod_cost"], color="#1A365D", marker="o",
             markersize=8, linewidth=2, markeredgecolor="white",
             markeredgewidth=1.5, label="Production cost")
    ax2.set_ylabel("Production cost (USD/tonne)", fontsize=11, color="#1A365D")
    ax2.tick_params(axis="y", colors="#1A365D")
    ax2.spines["top"].set_visible(False)

    # Legend
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Patch(facecolor="#2E7D32", label="≥ 99% utilized"),
        Patch(facecolor="#F9A825", label="50–99% utilized"),
        Patch(facecolor="#C62828", label="< 50% utilized"),
        Line2D([0], [0], color="#1A365D", marker="o", linewidth=2,
               markersize=7, label="Cost per tonne"),
    ]
    ax1.legend(handles=legend_elements, loc="upper left", frameon=False,
               fontsize=9, ncol=2)

    ax1.set_title(title or "Production volume vs. cost per region",
                  fontsize=13, pad=15)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"Chart saved to {output_path}")
    plt.show()
    return agg
"""
Demand coverage by region.

Horizontal bar chart showing served % per offtake region.
Red bars = unsupplied or partially supplied regions.
Green bars = fully supplied regions.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def plot_region_coverage(nodes_csv, demand_csv, output_path,
                         title=None, figsize=(10, 6)):
    """
    Horizontal bar chart of demand served % per offtake region.

    Parameters
    ----------
    nodes_csv : path to nodes.csv (node_id, region, ...).
    demand_csv : path to results_demand_*.csv (node_id, demand, delivered, unmet).
    output_path : where to save the figure (.png).
    title : optional plot title.
    figsize : matplotlib figure size.
    """
    nodes  = pd.read_csv(nodes_csv)
    demand = pd.read_csv(demand_csv)

    demand["node_id"] = demand["node_id"].astype(str)
    nodes["node_id"]  = nodes["node_id"].astype(str)

    df = demand.merge(nodes[["node_id", "region"]], on="node_id", how="left")

    # Aggregate demand, delivered, unmet per region
    agg = (df.groupby("region", as_index=False)
             .agg(demand=("demand", "sum"),
                  delivered=("delivered", "sum"),
                  unmet=("unmet", "sum")))
    agg = agg[agg["demand"] > 0].copy()
    agg["served_pct"] = 100 * agg["delivered"] / agg["demand"]

    # Sort ascending so worst-served is at the top
    agg = agg.sort_values("served_pct", ascending=True).reset_index(drop=True)

    # Color by served %
    def color_for(pct):
        if pct >= 99:  return "#2E7D32"    # green
        if pct >= 50:  return "#F9A825"    # amber
        return "#C62828"                    # red

    colors = [color_for(p) for p in agg["served_pct"]]

    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.barh(agg["region"], agg["served_pct"], color=colors,
                   edgecolor="white", linewidth=0.5)

    # Value labels: served % + absolute delivered/demand
    for bar, row in zip(bars, agg.itertuples()):
        ax.text(bar.get_width() + 1,
                bar.get_y() + bar.get_height() / 2,
                f"{row.served_pct:.1f}%  ({row.delivered:,.1f} / {row.demand:,.1f} Mt)",
                va="center", ha="left", fontsize=9, color="#333")

    # 100% reference line
    ax.axvline(100, color="grey", linestyle="--", linewidth=0.8, alpha=0.6)

    ax.set_xlabel("Demand served (%)", fontsize=11)
    ax.set_xlim(0, 135)   # room for the value labels
    ax.set_title(title or "Demand coverage by offtake region",
                 fontsize=13, pad=15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2E7D32", label="Fully served (≥ 99%)"),
        Patch(facecolor="#F9A825", label="Partial (50–99%)"),
        Patch(facecolor="#C62828", label="Unsupplied (< 50%)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", frameon=False,
              fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"Region coverage chart saved to {output_path}")
    plt.show()
    total_delivered = agg["delivered"].sum()
    print(f"Total delivered: {total_delivered:.1f} Mt out of {agg['demand'].sum():.1f} Mt ")
    return agg



if __name__ == "__main__":
    from datetime import date
    today = "2026-04-23_1"
    capacity_levels = [8, 700, 1100]

    for cap in capacity_levels:
        results_dir = Path(f"Results/sensitivity_base/capacity_{cap}/{today}")

        prod_csv   = pd.read_csv(results_dir / "results_production.csv")
        demand_csv = pd.read_csv(results_dir / "results_demand.csv")

        plot_prodcost_vs_volume(
            nodes_csv    = "model_work/DataFiles_base/nodes.csv",
            prod_csv     = results_dir / "results_production.csv",
            prodcost_csv = "model_work/DataFiles_base/prodcost.csv",
            output_path  = results_dir / "prodcost_vs_volume.png",
            title        = f"Capacity {cap}: production volume vs. cost per region (2030)",
        )

        df = plot_region_coverage(
            nodes_csv   = "model_work/DataFiles_base/nodes.csv",
            demand_csv  = results_dir / "results_demand.csv",
            output_path = results_dir / "region_coverage.png",
            title       = f"Capacity {cap}: demand coverage by offtake region (2030)",
        )
        print(f"\n=== Capacity {cap} ===")
        print(df.to_string(index=False))

        total_produced  = prod_csv["produced"].sum()
        total_capacity  = prod_csv["capacity"].sum()
        total_demand    = demand_csv["demand"].sum()
        total_delivered = demand_csv["delivered"].sum()
        total_unmet     = demand_csv["unmet"].sum()

        print(f"  Total capacity:  {total_capacity:.2f}")
        print(f"  Total produced:  {total_produced:.2f}")
        print(f"  Utilization:     {100 * total_produced / total_capacity:.1f}%")
        print(f"  Total demand:    {total_demand:.2f}")
        print(f"  Delivered:       {total_delivered:.2f}")
        print(f"  Unmet:           {total_unmet:.2f}")