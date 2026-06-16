import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────
RESULTS_BASE  = Path(r"C:\Users\mille\OneDrive\Dokumenter\DTU\Kandidat\Master-thesis\Results\flexible_demand\base_case")
SCENARIOS_CSV = RESULTS_BASE / "Scenario.csv"
NODES_CSV     = Path(r"C:\Users\mille\OneDrive\Dokumenter\DTU\Kandidat\Master-thesis\model_work\Datafiles_flexible\nodes.csv")
SAVE_DIR      = RESULTS_BASE

SCENARIO_ID   = "S9"        # ← skift her for andet scenarie
SCENARIO_LABEL = "low cost, high cap"  # ← skift label her


def plot_single_scenario_heatmap(scenario_id, scenario_label, save_dir=None):
    nodes_df = pd.read_csv(NODES_CSV)[["node_id", "region", "type"]]
    nodes_df["node_id"] = nodes_df["node_id"].astype(str)
    prod_nodes = nodes_df[nodes_df["type"] == "production"].copy()

    scen_dir = RESULTS_BASE / scenario_id
    if not scen_dir.exists():
        print(f"Mangler: {scen_dir}")
        return

    prod = pd.read_csv(scen_dir / "results_production.csv")
    prod["node_id"] = prod["node_id"].astype(str)
    prod = prod.merge(prod_nodes, on="node_id", how="inner")

    records = []
    for region, grp in prod.groupby("region"):
        cap      = grp["capacity"].sum()
        produced = grp["produced"].sum()
        util_pct = (produced / cap * 100) if cap > 0 else 0
        records.append({"region": region, "utilisation": util_pct})

    df = pd.DataFrame(records).set_index("region")
    df.columns = [scenario_label]
    df = df.sort_index()

    fig, ax = plt.subplots(figsize=(4, 7))
    sns.heatmap(df, ax=ax, annot=True, fmt=".0f",
                cmap="YlGn", vmin=0, vmax=100,
                linewidths=0.5, linecolor="white",
                cbar_kws={"label": "Utilisation (%)", "shrink": 0.8})
    ax.set_title(f"Production capacity utilisation\n{scenario_label}", fontsize=11)
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.tight_layout()

    if save_dir:
        fname = f"regional_capacity_{scenario_id}.png"
        plt.savefig(Path(save_dir) / fname, dpi=200, bbox_inches="tight", facecolor="white")
        print(f"Gemt: {Path(save_dir) / fname}")
    plt.show()


if __name__ == "__main__":
    plot_single_scenario_heatmap(SCENARIO_ID, SCENARIO_LABEL, save_dir=SAVE_DIR)