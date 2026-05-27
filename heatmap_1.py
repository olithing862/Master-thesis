import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


def plot_unmet_base(results_base_dir, scenarios_csv, nodes_csv, save_dir=None):

    scenarios = pd.read_csv(scenarios_csv)
    nodes_df  = pd.read_csv(nodes_csv)[["node_id", "industry"]]
    nodes_df["node_id"] = nodes_df["node_id"].astype(str)

    cost_order = ["low", "medium", "high"]
    cap_order  = ["low", "medium", "high"]
    industries = ["Steel", "Fertiliser", "Shipping"]
    ind_colors = {"Steel": "Greens", "Fertiliser": "Oranges", "Shipping": "Blues"}

    data = {ind: np.full((3, 3), np.nan) for ind in industries}

    for _, scen in scenarios.iterrows():
        if scen["cost_factor"] not in cost_order or scen["cap_factor"] not in cap_order:
            continue

        i = cost_order.index(scen["cost_factor"])
        j = cap_order.index(scen["cap_factor"])
        scen_dir = Path(results_base_dir) / scen["scenario_id"]

        if not scen_dir.exists():
            print(f"Missing: {scen_dir}")
            continue

        rigid = pd.read_csv(scen_dir / "results_demand.csv")
        rigid["node_id"] = rigid["node_id"].astype(str)
        rigid = rigid.merge(nodes_df, on="node_id", how="left")

        for ind in ["Steel", "Fertiliser"]:
            unmet  = rigid[rigid["industry"] == ind]["unmet"].sum()
            demand = rigid[rigid["industry"] == ind]["demand"].sum()
            data[ind][i, j] = (unmet / demand * 100) if demand > 0 else 0

        ship_file = scen_dir / "results_demand_ship_aggregate.csv"
        if ship_file.exists():
            ship = pd.read_csv(ship_file)
            ship_unmet  = float(ship["unmet"].iloc[0])
            ship_demand = float(ship["demand"].iloc[0])
            data["Shipping"][i, j] = (ship_unmet / ship_demand * 100) if ship_demand > 0 else 0

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    fig.suptitle("Unmet demand (%) by scenario — Base cases S1–S9", fontsize=13)

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
    plt.subplots_adjust(top=0.88)

    if save_dir:
        out = Path(save_dir) / "heatmap_base.png"
        plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
        print(f"Saved to {out}")

    plt.show()


import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def plot_industry_allocation(results_base_dir, scenarios_csv, nodes_csv, save_dir=None):

    scenarios = pd.read_csv(scenarios_csv)
    nodes_df  = pd.read_csv(nodes_csv)[["node_id", "industry"]]
    nodes_df["node_id"] = nodes_df["node_id"].astype(str)

    scenario_order = [f"S{i}" for i in range(1, 10)]
    scenarios = scenarios[scenarios["scenario_id"].isin(scenario_order)]
    scenarios["_order"] = scenarios["scenario_id"].map({s: i for i, s in enumerate(scenario_order)})
    scenarios = scenarios.sort_values("_order")

    industries = ["Steel", "Fertiliser", "Shipping"]
    colors     = {"Steel": "#6b9e78", "Fertiliser": "#c97b38", "Shipping": "#4a6fa5"}
    cap_groups = ["low", "medium", "high"]
    cap_titles = {"low": "Low capacity", "medium": "Medium capacity", "high": "High capacity"}
    cost_order = ["high", "medium", "low"]  # left to right: most to least constrained

    records = []

    for _, scen in scenarios.iterrows():
        scen_dir = Path(results_base_dir) / scen["scenario_id"]
        if not scen_dir.exists():
            print(f"Missing: {scen_dir}")
            continue

        rigid = pd.read_csv(scen_dir / "results_demand.csv")
        rigid["node_id"] = rigid["node_id"].astype(str)
        rigid = rigid.merge(nodes_df, on="node_id", how="left")

        row = {"scenario_id": scen["scenario_id"],
               "cap_factor":  scen["cap_factor"],
               "cost_factor": scen["cost_factor"]}

        for ind in ["Steel", "Fertiliser"]:
            row[f"{ind}_delivered"] = rigid[rigid["industry"] == ind]["delivered"].sum()
            row[f"{ind}_demand"]    = rigid[rigid["industry"] == ind]["demand"].sum()

        ship_file = scen_dir / "results_demand_ship_aggregate.csv"
        if ship_file.exists():
            ship = pd.read_csv(ship_file)
            row["Shipping_delivered"] = float(ship["delivered"].iloc[0])
            row["Shipping_demand"]    = float(ship["demand"].iloc[0])
        else:
            row["Shipping_delivered"] = 0.0
            row["Shipping_demand"]    = 0.0

        prod_file = scen_dir / "results_production.csv"
        if prod_file.exists():
            prod = pd.read_csv(prod_file)
            row["total_capacity"] = prod["capacity"].sum()
        else:
            row["total_capacity"] = None

        records.append(row)

    df = pd.DataFrame(records)

    fig, axes = plt.subplots(1, 3, figsize=(13, 5), sharey=False)

    for ax, cap in zip(axes, cap_groups):
        cap_df = df[df["cap_factor"] == cap].copy()
        cap_df["_cost_order"] = cap_df["cost_factor"].map(
            {c: i for i, c in enumerate(cost_order)})
        cap_df = cap_df.sort_values("_cost_order")

        bottoms = [0.0] * len(cap_df)

        bar_tops = [0.0] * len(cap_df)

        for ind in industries:
            vals = cap_df[f"{ind}_delivered"].values
            bars = ax.bar(cap_df["cost_factor"], vals, bottom=bottoms,
                        color=colors[ind], label=ind, width=0.5)

            for bar, val, bottom, demand in zip(
                    bars, vals, bottoms, cap_df[f"{ind}_demand"].values):
                if val > 0 and demand > 0:
                    pct = val / demand * 100
                    y_center = bottom + val / 2
                    ax.text(bar.get_x() + bar.get_width() / 2,
                            y_center, f"{pct:.0f}%",
                            ha="center", va="center",
                            fontsize=8, color="white", fontweight="bold")

            bottoms = [b + v for b, v in zip(bottoms, vals)]
            bar_tops = bottoms[:]

        # total Mt on top of each bar
        for bar, total in zip(bars, bar_tops):
            if total > 0:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        total + cap_df["total_capacity"].iloc[0] * 0.01,
                        f"{total:.0f} Mt",
                        ha="center", va="bottom",
                        fontsize=7, color="black")

        # capacity line — same for all bars in this panel
        cap_val = cap_df["total_capacity"].iloc[0]
        if cap_val is not None:
            ax.axhline(cap_val, color="black", linewidth=1.5,
                       linestyle="--", alpha=0.8)
            ax.text(2.45, cap_val * 1.02, f"{cap_val:.0f} Mt",
                    ha="right", va="bottom", fontsize=7, color="black")

        ax.set_title(cap_titles[cap], fontsize=10)
        ax.set_xlabel("Cost level")
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xticklabels(["High cost", "Med. cost", "Low cost"], fontsize=8)

    axes[0].set_ylabel("Delivered ammonia (Mt)")

    # single legend
    handles, labels = axes[0].get_legend_handles_labels()
    from matplotlib.lines import Line2D
    handles.append(Line2D([0], [0], color="black", linewidth=1.5, linestyle="--"))
    labels.append("Production capacity")
    fig.legend(handles, labels, loc="upper center", ncol=4,
               frameon=False, fontsize=8, bbox_to_anchor=(0.5, 1.02))

    fig.suptitle("Industry allocation of delivered green ammonia",
                 fontsize=12, y=1.06)
    plt.tight_layout()

    if save_dir:
        out = Path(save_dir) / "industry_allocation_S1_S9.png"
        plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
        print(f"Saved to {out}")

    plt.show()


def plot_summary_table(results_base_dir, scenarios_csv, nodes_csv, save_dir=None):

    scenarios = pd.read_csv(scenarios_csv)
    nodes_df  = pd.read_csv(nodes_csv)[["node_id", "industry"]]
    nodes_df["node_id"] = nodes_df["node_id"].astype(str)

    scenario_order = scenarios["scenario_id"].unique().tolist()
    scenarios = scenarios[scenarios["scenario_id"].isin(scenario_order)]
    scenarios["_order"] = scenarios["scenario_id"].map({s: i for i, s in enumerate(scenario_order)})
    scenarios = scenarios.sort_values("_order")

    records = []

    for _, scen in scenarios.iterrows():
        scen_dir = Path(results_base_dir) / scen["scenario_id"]
        if not scen_dir.exists():
            continue

        rigid = pd.read_csv(scen_dir / "results_demand.csv")
        rigid["node_id"] = rigid["node_id"].astype(str)
        rigid = rigid.merge(nodes_df, on="node_id", how="left")

        ship_file = scen_dir / "results_demand_ship_aggregate.csv"
        s_del, s_dem = 0.0, 0.0
        if ship_file.exists():
            ship = pd.read_csv(ship_file)
            s_del = float(ship["delivered"].iloc[0])
            s_dem = float(ship["demand"].iloc[0])

        steel_del = rigid[rigid["industry"] == "Steel"]["delivered"].sum()
        steel_dem = rigid[rigid["industry"] == "Steel"]["demand"].sum()
        fert_del  = rigid[rigid["industry"] == "Fertiliser"]["delivered"].sum()
        fert_dem  = rigid[rigid["industry"] == "Fertiliser"]["demand"].sum()
        total_del = steel_del + fert_del + s_del
        total_dem = steel_dem + fert_dem + s_dem

        prod_file = scen_dir / "results_production.csv"
        if prod_file.exists():
            prod = pd.read_csv(prod_file)
            total_cap  = prod["capacity"].sum()
            total_prod = prod["produced"].sum()
            prod_util  = f"{total_prod/total_cap*100:.0f}%" if total_cap > 0 else "0%"
        else:
            prod_util = "—"

        records.append({
            "Scenario":   scen["scenario_id"],
            "Capacity":   scen["cap_factor"].capitalize(),
            "Cost":       scen["cost_factor"].capitalize(),
            "Steel":      f"{steel_del/steel_dem*100:.0f}%" if steel_dem > 0 else "0%",
            "Fertiliser": f"{fert_del/fert_dem*100:.0f}%"  if fert_dem  > 0 else "0%",
            "Shipping":   f"{s_del/s_dem*100:.0f}%"        if s_dem     > 0 else "0%",
            "Total":      f"{total_del/total_dem*100:.1f}%" if total_dem > 0 else "0%",
            "Prod. util.": prod_util,
        })

    df = pd.DataFrame(records)

    col_labels = ["Scenario", "Capacity", "Cost",
                  "Steel", "Fertiliser", "Shipping",
                  "Total", "Prod. util."]

    fig, ax = plt.subplots(figsize=(18,7))
    ax.axis("off")

    table = ax.table(
        cellText=df.values,
        colLabels=col_labels,
        cellLoc="center",
        loc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.7)

    # header
    for j in range(len(col_labels)):
        table[0, j].set_facecolor("#2d4a3e")
        table[0, j].set_text_props(color="white", fontweight="bold")

    # row shading by cost
    cost_colors = {"High": "#f5e6e6", "Medium": "#fef9e7", "Low": "#e8f5e9"}
    for i, row_data in enumerate(df.itertuples(), start=1):
        cost = row_data[3]
        bg = cost_colors.get(cost, "white")
        for j in range(len(col_labels)):
            table[i, j].set_facecolor(bg)

    # grey out shipping
    for i in range(1, len(df) + 1):
        table[i, 6].set_facecolor("#f0f0f0")
        table[i, 6].set_text_props(color="#aaaaaa")

    plt.title("Demand coverage (%) by industry and scenario — S1 to S9",
              fontsize=11, pad=10)
    plt.tight_layout()

    if save_dir:
        out = Path(save_dir) / "summary_table.png"
        plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"Saved to {out}")

    plt.show()

plot_summary_table(
    results_base_dir = "Results_final/fixed_steel",
    scenarios_csv    = "Results_final/fixed_steel/Scenario.csv",
    nodes_csv        = "model_work/DataFiles_flexible/nodes.csv",
    save_dir         = "Results_final/fixed_steel"
)

# plot_industry_allocation(
#     results_base_dir = "Results_final/fixed_steel",
#     scenarios_csv    = "Results_final/fixed_steel/Scenario.csv",
#     nodes_csv        = "model_work/DataFiles_flexible/nodes_1.csv",
#     save_dir         = "Results_final/fixed_steel"
# )
# plot_unmet_base(
#     results_base_dir = "Results_final/base_case",
#     scenarios_csv    = "Results_final/base_case/Scenario.csv",
#     nodes_csv        = "model_work/DataFiles_flexible/nodes.csv",
#     save_dir         = "Results_final/base_case"
# )