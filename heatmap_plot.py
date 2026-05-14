import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_unmet_heatmap(results_base_dir, cost_levels, cap_levels, 
                       nodes_csv, save_path=None):
    import seaborn as sns

    cost_labels = ["low", "medium", "high"]
    cap_labels  = ["low", "medium", "high"]

    # ---- collect unmet demand for each scenario ----
    industries = ["Steel", "Fertiliser", "Shipping"]
    
    # One dict per industry: rows=cost, cols=cap
    data = {ind: np.zeros((len(cost_levels), len(cap_levels))) for ind in industries}

    nodes_df = pd.read_csv(nodes_csv)[["node_id", "industry"]]
    nodes_df["node_id"] = nodes_df["node_id"].astype(str)

    for i, cost in enumerate(cost_levels):
        for j, cap in enumerate(cap_levels):
            scen_dir = Path(results_base_dir) / f"cost_{cost}__cap_{cap}"

            # --- rigid demand (steel + fertilizer) ---
            rigid = pd.read_csv(scen_dir / "results_demand.csv")
            rigid["node_id"] = rigid["node_id"].astype(str)
            rigid = rigid.merge(nodes_df, on="node_id", how="left")

            for ind in ["Steel", "Fertiliser"]:
                unmet = rigid[rigid["industry"] == ind]["unmet"].sum()
                demand = rigid[rigid["industry"] == ind]["demand"].sum()
                data[ind][i, j] = (unmet / demand * 100) if demand > 0 else 0

            # --- shipping ---
            ship = pd.read_csv(scen_dir / "results_demand_ship_aggregate.csv")
            ship_unmet  = float(ship["unmet"].iloc[0])
            ship_demand = float(ship["demand"].iloc[0])
            data["Shipping"][i, j] = (ship_unmet / ship_demand * 100) if ship_demand > 0 else 0

    # ---- plot ----
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    fig.suptitle("Unmet demand by industry (Mt)", fontsize=13, y=1.02)

    ind_colors = {
        "Steel":      "Blues",
        "Fertiliser": "Oranges",
        "Shipping":   "Greens",
    }

    for ax, ind in zip(axes, industries):
        matrix = data[ind]
        vmax = matrix.max() if matrix.max() > 0 else 1

        sns.heatmap(
            matrix,
            ax=ax,
            annot=True,
            fmt=".1f",          # e.g. "34.5"
            cmap=ind_colors[ind],
            xticklabels=cap_labels,
            yticklabels=cost_labels,
            vmin=0,
            vmax=100,           # always 0-100% scale
            linewidths=0.5,
            linecolor="white",
            cbar_kws={"label": "Unmet (%)", "shrink": 0.8},
        )
        ax.set_title(ind, fontsize=11)
        ax.set_xlabel("Capacity level")
        ax.set_ylabel("Cost level")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.show()

plot_unmet_heatmap(
results_base_dir = "Results/flexible_demand/2026-05-11_1",
cost_levels      = ["low", "medium", "high"],
cap_levels       = ["low", "medium", "high"],
nodes_csv        = "model_work/DataFiles_flexible/nodes.csv",
save_path        = "Results/flexible_demand/2026-05-11_1/heatmap_unmet.png"
)