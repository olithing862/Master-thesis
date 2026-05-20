import os
os.chdir(r"C:\Users\mille\OneDrive\Dokumenter\DTU\Kandidat\Master-thesis")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path


# ── shared config ────────────────────────────────────────────────────────────
RESULTS_BASE = Path("Results/flexible_demand/base_case")
SCENARIOS_CSV = RESULTS_BASE / "Scenario.csv"
NODES_CSV     = Path("model_work/DataFiles_flexible/nodes.csv")
SAVE_DIR      = RESULTS_BASE

cost_order = ["low", "medium", "high"]
cap_order  = ["low", "medium", "high"]


def load_scenarios():
    return pd.read_csv(SCENARIOS_CSV)


def load_nodes():
    df = pd.read_csv(NODES_CSV)[["node_id", "industry"]]
    df["node_id"] = df["node_id"].astype(str)
    return df


# ── 1. Stacked bar – produktionsmix ─────────────────────────────────────────
def plot_production_mix(save_dir=None):
    """
    For hvert scenarie: total produced vs. total capacity, 
    brudt ned på produktionsknuder (p0, p1, ...).
    Viser udnyttelsesgrad som stacked bar.
    """
    scenarios = load_scenarios()

    scen_ids   = []
    produced   = []
    unused     = []

    for _, scen in scenarios.iterrows():
        scen_dir = RESULTS_BASE / scen["scenario_id"]
        if not scen_dir.exists():
            continue

        prod = pd.read_csv(scen_dir / "results_production.csv")
        total_produced = prod["produced"].sum()
        total_capacity = prod["capacity"].sum()
        total_unused   = total_capacity - total_produced

        scen_ids.append(scen["scenario_id"])
        produced.append(total_produced)
        unused.append(total_unused)

    x = np.arange(len(scen_ids))
    width = 0.6

    fig, ax = plt.subplots(figsize=(11, 5))
    bars1 = ax.bar(x, produced, width, label="Produced",  color="#2196F3")
    bars2 = ax.bar(x, unused,   width, bottom=produced,   label="Unused capacity", color="#BBDEFB", alpha=0.8)

    # utilisation % label
    for i, (p, u) in enumerate(zip(produced, unused)):
        total = p + u
        pct   = p / total * 100 if total > 0 else 0
        ax.text(i, total + total * 0.01, f"{pct:.0f}%", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(scen_ids, rotation=45)
    ax.set_ylabel("Energy / volume [unit]")
    ax.set_title("Production mix – capacity utilisation per scenario")
    ax.legend()
    plt.tight_layout()

    if save_dir:
        plt.savefig(Path(save_dir) / "production_mix.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.show()


# ── 2. Tornado-diagram – følsomhed ───────────────────────────────────────────
def plot_tornado(save_dir=None):
    """
    Viser hvor meget unmet demand ændrer sig når cost_factor eller 
    cap_factor varierer, mens den anden holdes fast på 'medium'.
    """
    scenarios = load_scenarios()
    nodes_df  = load_nodes()

    industries = ["Steel", "Fertiliser", "Shipping"]
    factors    = ["cost_factor", "cap_factor"]
    levels     = ["low", "medium", "high"]

    # baseline = medium/medium
    baseline = {}
    base_scen = scenarios[(scenarios["cost_factor"] == "medium") &
                           (scenarios["cap_factor"]  == "medium")].iloc[0]
    base_dir  = RESULTS_BASE / base_scen["scenario_id"]

    rigid = pd.read_csv(base_dir / "results_demand.csv")
    rigid["node_id"] = rigid["node_id"].astype(str)
    rigid = rigid.merge(nodes_df, on="node_id", how="left")

    for ind in ["Steel", "Fertiliser"]:
        unmet  = rigid[rigid["industry"] == ind]["unmet"].sum()
        demand = rigid[rigid["industry"] == ind]["demand"].sum()
        baseline[ind] = (unmet / demand * 100) if demand > 0 else 0

    ship = pd.read_csv(base_dir / "results_demand_ship_aggregate.csv")
    baseline["Shipping"] = (float(ship["unmet"].iloc[0]) /
                             float(ship["demand"].iloc[0]) * 100
                             if float(ship["demand"].iloc[0]) > 0 else 0)

    # per industri: min og max unmet når én faktor varierer
    fig, axes = plt.subplots(1, len(industries), figsize=(14, 5), sharey=False)
    colors = {"cost_factor": ("#EF5350", "#42A5F5"),
              "cap_factor":  ("#FF9800", "#66BB6A")}

    for ax, ind in zip(axes, industries):
        rows = []
        for factor in factors:
            fixed = "cap_factor" if factor == "cost_factor" else "cost_factor"
            vals  = []
            for level in levels:
                sub = scenarios[(scenarios[factor] == level) &
                                 (scenarios[fixed]  == "medium")]
                if sub.empty:
                    continue
                s_dir = RESULTS_BASE / sub.iloc[0]["scenario_id"]
                if not s_dir.exists():
                    continue

                if ind in ["Steel", "Fertiliser"]:
                    r = pd.read_csv(s_dir / "results_demand.csv")
                    r["node_id"] = r["node_id"].astype(str)
                    r = r.merge(nodes_df, on="node_id", how="left")
                    u = r[r["industry"] == ind]["unmet"].sum()
                    d = r[r["industry"] == ind]["demand"].sum()
                    vals.append((u / d * 100) if d > 0 else 0)
                else:
                    sh = pd.read_csv(s_dir / "results_demand_ship_aggregate.csv")
                    vals.append(float(sh["unmet"].iloc[0]) /
                                float(sh["demand"].iloc[0]) * 100
                                if float(sh["demand"].iloc[0]) > 0 else 0)

            if vals:
                rows.append({"factor": factor, "min": min(vals), "max": max(vals)})

        rows_df = pd.DataFrame(rows).sort_values("max", ascending=True)
        base    = baseline[ind]

        for i, row in enumerate(rows_df.itertuples()):
            lo_col, hi_col = colors[row.factor]
            ax.barh(i, row.min - base, left=base, color=lo_col, height=0.5)
            ax.barh(i, row.max - base, left=base, color=hi_col, height=0.5)

        ax.axvline(base, color="black", linewidth=1.2, linestyle="--")
        ax.set_yticks(range(len(rows_df)))
        ax.set_yticklabels([r.factor.replace("_", " ") for r in rows_df.itertuples()])
        ax.set_xlabel("Unmet demand (%)")
        ax.set_title(ind)
        ax.set_xlim(0, 105)

    # legend
    patches = [
        mpatches.Patch(color="#EF5350", label="cost low"),
        mpatches.Patch(color="#42A5F5", label="cost high"),
        mpatches.Patch(color="#FF9800", label="cap low"),
        mpatches.Patch(color="#66BB6A", label="cap high"),
    ]
    fig.legend(handles=patches, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.05))
    fig.suptitle("Tornado – sensitivity to cost & capacity factor\n(baseline = medium/medium)", fontsize=12)
    plt.tight_layout()

    if save_dir:
        plt.savefig(Path(save_dir) / "tornado.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.show()


# ── 3. Netværkskort – worst vs. best case ────────────────────────────────────
def plot_worst_vs_best(save_dir=None):
    """
    Identificerer worst (højeste unmet) og best (laveste unmet) scenarie
    og kalder din eksisterende plot_network_map for begge side om side.
    Kræver at plot_network_map er importeret i din plotting.py.
    """
    scenarios = load_scenarios()
    nodes_df  = load_nodes()

    totals = []
    for _, scen in scenarios.iterrows():
        scen_dir = RESULTS_BASE / scen["scenario_id"]
        if not scen_dir.exists():
            continue
        rigid = pd.read_csv(scen_dir / "results_demand.csv")
        ship  = pd.read_csv(scen_dir / "results_demand_ship_aggregate.csv")
        total_unmet  = rigid["unmet"].sum() + float(ship["unmet"].iloc[0])
        total_demand = rigid["demand"].sum() + float(ship["demand"].iloc[0])
        pct = total_unmet / total_demand * 100 if total_demand > 0 else 0
        totals.append({"scenario_id": scen["scenario_id"],
                       "cost_factor": scen["cost_factor"],
                       "cap_factor":  scen["cap_factor"],
                       "unmet_pct":   pct})

    totals_df = pd.DataFrame(totals).sort_values("unmet_pct")
    best  = totals_df.iloc[0]
    worst = totals_df.iloc[-1]

    print(f"Best:  {best['scenario_id']}  "
          f"(cost={best['cost_factor']}, cap={best['cap_factor']})  "
          f"→ {best['unmet_pct']:.1f}% unmet")
    print(f"Worst: {worst['scenario_id']}  "
          f"(cost={worst['cost_factor']}, cap={worst['cap_factor']})  "
          f"→ {worst['unmet_pct']:.1f}% unmet")

    # kalder plot_network_map to gange – tilpas import hvis nødvendigt
    try:
        from model_work.model_flexible.plotting import plot_network_map
        for label, scen in [("Best case", best), ("Worst case", worst)]:
            d = RESULTS_BASE / scen["scenario_id"]
            print(f"\nGenerating network map: {label}")
            plot_network_map(
                nodes_csv             = str(NODES_CSV),
                flows_csv             = d / "results_flows.csv",
                prod_csv              = d / "results_production.csv",
                demand_rigid_csv      = d / "results_demand.csv",
                demand_ship_ports_csv = d / "results_demand_ship_ports.csv",
                output_html           = d / f"network_{label.lower().replace(' ', '_')}.html",
            )
            print(f"  Saved: {d / f'network_{label.lower().replace(chr(32), chr(95))}.html'}")
    except ImportError:
        print("\nKunne ikke importere plot_network_map – kør netværkskortene manuelt:")
        for label, scen in [("Best", best), ("Worst", worst)]:
            print(f"  {label}: {RESULTS_BASE / scen['scenario_id']}")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    plot_production_mix(save_dir=SAVE_DIR)
    plot_tornado(save_dir=SAVE_DIR)
    plot_worst_vs_best(save_dir=SAVE_DIR)