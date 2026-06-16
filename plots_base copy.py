import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────
RESULTS_BASE  = Path(r"C:\Users\mille\OneDrive\Dokumenter\DTU\Kandidat\Master-thesis\Results\flexible_demand\base_case")
SCENARIOS_CSV = RESULTS_BASE / "Scenario.csv"
NODES_CSV     = Path(r"C:\Users\mille\OneDrive\Dokumenter\DTU\Kandidat\Master-thesis\model_work\Datafiles_flexible\nodes.csv")
SAVE_DIR      = RESULTS_BASE


def plot_regional_capacity(save_dir=None):
    scenarios = pd.read_csv(SCENARIOS_CSV)
    nodes_df  = pd.read_csv(NODES_CSV)[["node_id", "region", "type"]]
    nodes_df["node_id"] = nodes_df["node_id"].astype(str)

    # kun produktionsknuder
    prod_nodes = nodes_df[nodes_df["type"] == "production"].copy()

    # ── byg records ──────────────────────────────────────────────────────────
    records = []
    for _, scen in scenarios.iterrows():
        scen_dir = RESULTS_BASE / scen["scenario_id"]
        if not scen_dir.exists():
            print(f"Mangler: {scen_dir}")
            continue

        prod = pd.read_csv(scen_dir / "results_production.csv")
        prod["node_id"] = prod["node_id"].astype(str)
        prod = prod.merge(prod_nodes, on="node_id", how="inner")

        for region, grp in prod.groupby("region"):
            cap      = grp["capacity"].sum()
            produced = grp["produced"].sum()
            util_pct = (produced / cap * 100) if cap > 0 else 0
            records.append({
                "scenario_id": scen["scenario_id"],
                "cost_factor": scen["cost_factor"],
                "cap_factor":  scen["cap_factor"],
                "region":      region,
                "utilisation": util_pct,
                "produced":    produced,
                "capacity":    cap,
            })

    df = pd.DataFrame(records)
    regions  = sorted(df["region"].unique())
    scen_ids = scenarios["scenario_id"].tolist()

    # ── Plot 1: Grouped bar ───────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 6))

    n_scen    = len(scen_ids)
    bar_width = 0.08
    group_gap = 0.3
    colors    = cm.tab10(np.linspace(0, 0.9, n_scen))

    for s_idx, scen_id in enumerate(scen_ids):
        scen_data = df[df["scenario_id"] == scen_id]
        x_vals, y_vals = [], []
        for r_idx, region in enumerate(regions):
            row = scen_data[scen_data["region"] == region]
            x_vals.append(r_idx * (n_scen * bar_width + group_gap) + s_idx * bar_width)
            y_vals.append(float(row["utilisation"].values[0]) if len(row) else 0)

        ax.bar(x_vals, y_vals, width=bar_width, color=colors[s_idx],
               label=scen_id, alpha=0.9)

    tick_positions = [r * (n_scen * bar_width + group_gap) + (n_scen * bar_width) / 2
                      for r in range(len(regions))]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(regions, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Capacity utilisation (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Production capacity utilisation by region – all scenarios")
    ax.legend(title="Scenario", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    ax.axhline(100, color="red", linestyle="--", linewidth=0.8, alpha=0.5)
    plt.tight_layout()
    if save_dir:
        plt.savefig(Path(save_dir) / "regional_capacity_bar.png",
                    dpi=200, bbox_inches="tight", facecolor="white")
    plt.show()

    # ── Plot 2: Heatmap ───────────────────────────────────────────────────────
    pivot = df.pivot(index="region", columns="scenario_id", values="utilisation")
    col_order = [s for s in [f"S{i}" for i in range(1, 10)] if s in pivot.columns]
    pivot = pivot.reindex(columns=col_order)

    fig2, ax2 = plt.subplots(figsize=(11, 6))
    im = ax2.imshow(pivot.values, aspect="auto", cmap="YlGn", vmin=0, vmax=100)

    ax2.set_xticks(range(len(pivot.columns)))
    ax2.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax2.set_yticks(range(len(pivot.index)))
    ax2.set_yticklabels(pivot.index)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            txt = f"{val:.0f}" if not np.isnan(val) else ""
            color = "white" if val > 60 else "black"
            ax2.text(j, i, txt, ha="center", va="center", fontsize=9, color=color)

    plt.colorbar(im, ax=ax2, label="Utilisation (%)", shrink=0.8)
    ax2.set_title("Production capacity utilisation by region – heatmap")
    plt.tight_layout()
    if save_dir:
        plt.savefig(Path(save_dir) / "regional_capacity_heatmap.png",
                    dpi=200, bbox_inches="tight", facecolor="white")
    plt.show()


if __name__ == "__main__":
    plot_regional_capacity(save_dir=SAVE_DIR)
