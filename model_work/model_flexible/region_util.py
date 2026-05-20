"""
plot_africa_utilisation.py
--------------------------
Horizontal bar chart of average production utilisation across all 9 base case
scenarios, with African nodes highlighted.

Usage:
    python plot_africa_utilisation.py \
        --results /path/to/base_case \
        --nodes   /path/to/nodes.csv
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

AFRICA_REGIONS = {"East Africa", "West Africa"}
COLOR_AFRICA   = "#c0392b"   # red
COLOR_OTHER    = "#aaaaaa"   # grey


def load_utilisation(results_dir, scenario_ids):
    dfs = []
    for sid in scenario_ids:
        path = os.path.join(results_dir, sid, "results_production.csv")
        if not os.path.exists(path):
            print(f"  [warn] missing: {path}")
            continue
        df = pd.read_csv(path)
        df["scenario"] = sid
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True,
                        help="Path to base_case directory")
    parser.add_argument("--nodes", required=True,
                        help="Path to nodes.csv")
    parser.add_argument("--outdir", default=None)
    args = parser.parse_args()

    outdir = args.outdir or args.results
    os.makedirs(outdir, exist_ok=True)

    # ── load nodes metadata ───────────────────────────────────────────────
    nodes = pd.read_csv(args.nodes)
    prod_nodes = nodes[nodes["type"] == "production"][["node_id", "Location", "region"]].copy()
    prod_nodes["is_africa"] = prod_nodes["region"].isin(AFRICA_REGIONS)

    # ── discover scenario folders ─────────────────────────────────────────
    scenario_ids = sorted([
        d for d in os.listdir(args.results)
        if os.path.isdir(os.path.join(args.results, d)) and d.startswith("Q")
    ])
    print(f"Found {len(scenario_ids)} scenarios: {scenario_ids}")

    # ── load and aggregate ────────────────────────────────────────────────
    raw = load_utilisation(args.results, scenario_ids)
    raw = raw.merge(prod_nodes, on="node_id", how="left")

    # per scenario: total model capacity
    scenario_capacity = raw.groupby("scenario")["capacity"].sum().rename("total_capacity")

    # per scenario per region: total produced / total model capacity
    region_scenario = raw.groupby(["scenario", "region"])["produced"].sum().reset_index()
    region_scenario = region_scenario.merge(scenario_capacity, on="scenario")
    region_scenario["share"] = 100 * region_scenario["produced"] / region_scenario["total_capacity"]

    # average share across all 9 scenarios
    avg = region_scenario.groupby("region")["share"].mean().reset_index()
    avg = avg.merge(prod_nodes[["region", "is_africa"]].drop_duplicates(), on="region", how="left")
    avg = avg.rename(columns={"share": "utilisation"})
    avg = avg.sort_values("utilisation", ascending=True)

    # ── plot: heatmap regions × scenarios ────────────────────────────────
    # pivot: rows = regions, columns = scenarios
    pivot = region_scenario.pivot(index="region", columns="scenario", values="share")

    # order rows by mean share ascending (lowest utilisers at top)
    pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=True).index]

    # mark african rows
    africa_rows = prod_nodes[prod_nodes["is_africa"]]["region"].unique()

    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("util", ["#f7f7f7", "#c6e8c5", "#4a7c59"], N=256)

    fig, ax = plt.subplots(figsize=(9, max(4, len(pivot) * 0.45)))
    fig.subplots_adjust(left=0.22, right=0.88, top=0.88, bottom=0.12)

    im = ax.imshow(pivot.values, cmap=cmap, aspect="auto", vmin=0,
                   vmax=pivot.values.max())

    # cell annotations
    for r in range(len(pivot)):
        for c in range(len(pivot.columns)):
            val = pivot.values[r, c]
            color = "white" if val > 0.6 * pivot.values.max() else "#333"
            ax.text(c, r, f"{val:.1f}%", ha="center", va="center",
                    fontsize=7, color=color)

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=8)
    ax.set_yticks(range(len(pivot)))

    # highlight african row labels in red
    ylabels = ax.set_yticklabels(pivot.index, fontsize=8)
    for label in ylabels:
        if label.get_text() in africa_rows:
            label.set_color(COLOR_AFRICA)
            label.set_fontweight("bold")

    cbar_ax = fig.add_axes([0.90, 0.12, 0.022, 0.76])
    cb = fig.colorbar(im, cax=cbar_ax)
    cb.set_label("Share of total\nmodel capacity (%)", fontsize=8)
    cb.ax.tick_params(labelsize=7.5)

    ax.set_xlabel("Scenario", fontsize=9)
    ax.set_title("Regional production as share of total model capacity — base case",
                 fontsize=10, fontweight="bold", pad=10)

    fig.text(0.91, 0.08, "Africa highlighted in red", fontsize=7,
             color=COLOR_AFRICA, ha="left")
    outpath = os.path.join(outdir, "plot_region_utilisation_heatmap.png")
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved → {outpath}")


if __name__ == "__main__":
    main()