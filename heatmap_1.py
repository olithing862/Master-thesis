import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def plot_unmet_by_R(results_base_dir, scenarios_csv, nodes_csv, save_dir=None):
    import seaborn as sns

    scenarios = pd.read_csv(scenarios_csv)
    nodes_df  = pd.read_csv(nodes_csv)[["node_id", "industry"]]
    nodes_df["node_id"] = nodes_df["node_id"].astype(str)

    cost_order = ["low", "medium", "high"]
    cap_order  = ["low", "medium", "high"]
    industries = ["Steel", "Fertiliser", "Shipping"]
    ind_colors = {"Steel": "Greens", "Fertiliser": "Oranges", "Shipping": "Blues"}

    # group by R-level (R1, R2, ...)
    r_levels = sorted(scenarios["scenario_id"].str.extract(r"^(S\d+)")[0].dropna().unique())

    for r in r_levels:
        r_scenarios = scenarios[scenarios["scenario_id"] == r]
        #tax = int(r_scenarios["co2_tax_shipping"].iloc[0])

        data = {ind: np.full((3, 3), np.nan) for ind in industries}

        for _, scen in r_scenarios.iterrows():
            i = cost_order.index(scen["cost_factor"])
            j = cap_order.index(scen["cap_factor"])
            scen_dir = Path(results_base_dir) / scen["scenario_id"]

            if not scen_dir.exists():
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
        fig.suptitle(f"{r}", fontsize=13)
        plt.tight_layout()
        plt.subplots_adjust(top=0.88)

        for ax, ind in zip(axes, industries):
            matrix = data[ind]
            annot  = np.array([[f"{v:.1f}" if not np.isnan(v) else "" for v in row] for row in matrix])

            sns.heatmap(matrix, ax=ax, annot=annot, fmt="",
                cmap=ind_colors[ind],
                xticklabels=cap_order, yticklabels=cost_order,
                vmin=0, vmax=100, linewidths=0.5, linecolor="white",
                cbar_kws={"label": "Unmet (%)", "shrink": 0.8})
            ax.set_title(ind, fontsize=11)
            ax.set_xlabel("Capacity level")
            ax.set_ylabel("Cost level")

        plt.tight_layout()
        if save_dir:
            plt.savefig(Path(save_dir) / f"heatmap_{r}.png", dpi=200, bbox_inches="tight", facecolor="white")
        plt.show()


plot_unmet_by_R(
    results_base_dir = "Results/flexible_demand/base_case",
    scenarios_csv    = "Results/flexible_demand/base_case/Scenario.csv",
    nodes_csv        = "model_work/DataFiles_flexible/nodes.csv",
    save_dir         = "Results/flexible_demand/base_case"
)