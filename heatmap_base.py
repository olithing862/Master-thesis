import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_unmet_heatmap(results_base_dir, scenarios_csv, nodes_csv, save_dir=None):
    import seaborn as sns
    import numpy as np

    scenarios = pd.read_csv(scenarios_csv)
    nodes_df  = pd.read_csv(nodes_csv)[["node_id", "industry"]]
    nodes_df["node_id"] = nodes_df["node_id"].astype(str)

    cost_order = ["low", "medium", "high"]
    cap_order  = ["low", "medium", "high"]
    industries = ["Steel", "Fertiliser", "Shipping"]
    ind_colors = {"Steel": "Greens", "Fertiliser": "Oranges", "Shipping": "Blues"}

    data = {ind: np.full((3, 3), np.nan) for ind in industries}

    for _, scen in scenarios.iterrows():
        i = cost_order.index(scen["cost_factor"])
        j = cap_order.index(scen["cap_factor"])
        scen_dir = Path(results_base_dir) / scen["scenario_id"]

        if not scen_dir.exists():
            print(f"Mangler: {scen_dir}")
            continue

        rigid = pd.read_csv(scen_dir / "results_demand.csv")
        rigid["node_id"] = rigid["node_id"].astype(str)
        rigid = rigid.merge(nodes_df, on="node_id", how="left")

        for ind in ["Steel", "Fertiliser"]:
            unmet  = rigid[rigid["industry"] == ind]["unmet"].sum()
            demand = rigid[rigid["industry"] == ind]["demand"].sum()
            data[ind][i, j] = (unmet / demand * 100) if demand > 0 else 0

        ship = pd.read_csv(scen_dir / "results_demand_ship_aggregate.csv")
        ship_unmet  = float(ship["unmet"].iloc[0])
        ship_demand = float(ship["demand"].iloc[0])
        data["Shipping"][i, j] = (ship_unmet / ship_demand * 100) if ship_demand > 0 else 0

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    fig.suptitle("Unmet demand (%) – Base case", fontsize=13)

    for ax, ind in zip(axes, industries):
        matrix = data[ind]
        annot  = np.array([[f"{v:.1f}" if not np.isnan(v) else "" for v in row] for row in matrix])

        sns.heatmap(matrix, ax=ax, annot=annot, fmt="",
            cmap=ind_colors[ind],
            xticklabels=cap_order, yticklabels=cost_order,
            vmin=0, vmax=100, linewidths=0.5, linecolor="white",
            cbar_kws={"label": "Unmet (%)", "shrink": 0.8})
        ax.set_title(ind, fontsize=11)
        ax.set_xlabel("Capacity factor")
        ax.set_ylabel("Cost factor")

    plt.tight_layout()
    if save_dir:
        plt.savefig(Path(save_dir) / "heatmap_base_case.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.show()


plot_unmet_heatmap(
    results_base_dir = "Results/flexible_demand/base_case",
    scenarios_csv    = "Results/flexible_demand/base_case/Scenario.csv",
    nodes_csv        = "model_work/DataFiles_flexible/nodes.csv",
    save_dir         = "Results/flexible_demand/base_case"
)