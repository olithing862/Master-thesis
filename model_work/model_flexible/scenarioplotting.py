"""
plot_shippingtax.py
-------------------
Three thesis plots for the 45-scenario shipping CO₂ tax analysis.

Usage:
    python scenarioplotting.py --results /Users/oliviathingvad/Master-thesis/Results/flexible_demand/shippingtax_case
    python scenarioplotting.py --results /Users/oliviathingvad/Master-thesis/Results/flexible_demand/shippingtax_case --cap high --cost medium
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap

# ── palette ──────────────────────────────────────────────────────────────────
GREEN  = "#4a7c59"
FOSSIL = "#b5966d"
STEEL  = "#6b9e78"
FERT   = "#c97b38"
SHIP   = "#4a6fa5"

CAP_ORDER  = ["low", "medium", "high"]
COST_ORDER = ["high", "medium", "low"]
CAP_LABEL  = {"low": "Low cap", "medium": "Med. cap", "high": "High cap"}
COST_LABEL = {"high": "High cost", "medium": "Med. cost", "low": "Low cost"}


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_all_scenarios(results_dir, scenarios):
    records = []
    for _, row in scenarios.iterrows():
        sid    = row["scenario_id"]
        folder = os.path.join(results_dir, sid)
        if not os.path.isdir(folder):
            print(f"  [warn] missing folder: {folder}")
            continue

        ship = pd.read_csv(os.path.join(folder, "results_demand_ship_aggregate.csv"))
        dem  = pd.read_csv(os.path.join(folder, "results_demand.csv"))

        steel_del = dem.loc[dem.node_id.str.startswith("oft_steel"), "delivered"].sum()
        steel_dem = dem.loc[dem.node_id.str.startswith("oft_steel"), "demand"].sum()
        fert_del  = dem.loc[dem.node_id.str.startswith("oft_f"),     "delivered"].sum()
        fert_dem  = dem.loc[dem.node_id.str.startswith("oft_f"),     "demand"].sum()

        records.append({
            "scenario_id"      : sid,
            "cap_factor"       : row["cap_factor"],
            "cost_factor"      : row["cost_factor"],
            "co2_tax_shipping" : row["co2_tax_shipping"],
            "ship_demand"      : ship["demand"].iloc[0],
            "ship_delivered"   : ship["delivered"].iloc[0],
            "ship_served_pct"  : ship["served_pct"].iloc[0],
            "steel_demand"     : steel_dem,
            "steel_delivered"  : steel_del,
            "steel_served_pct" : 100 * steel_del / steel_dem if steel_dem > 0 else 0,
            "fert_demand"      : fert_dem,
            "fert_delivered"   : fert_del,
            "fert_served_pct"  : 100 * fert_del / fert_dem  if fert_dem  > 0 else 0,
        })

    df = pd.DataFrame(records)
    df["cap_factor"]  = pd.Categorical(df["cap_factor"],  categories=CAP_ORDER,  ordered=True)
    df["cost_factor"] = pd.Categorical(df["cost_factor"], categories=COST_ORDER, ordered=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# PLOT 1  ·  Shipping penetration heatmap
# ─────────────────────────────────────────────────────────────────────────────
def plot1_heatmap(df, outpath):
    taxes = sorted(df["co2_tax_shipping"].unique())
    cmap  = LinearSegmentedColormap.from_list(
        "green_pen", ["#f7f7f7", "#c6e8c5", "#4a7c59"], N=256
    )
 
    from matplotlib.gridspec import GridSpec
    fig = plt.figure(figsize=(9, 6))
    fig.subplots_adjust(left=0.10, right=0.88, top=0.82, bottom=0.12, hspace=0.55)
 
    gs_top = GridSpec(1, 2, figure=fig, left=0.195, right=0.785, top=0.82, bottom=0.50, wspace=0.08)
    gs_bot = GridSpec(1, 3, figure=fig, left=0.10,  right=0.88,  top=0.42, bottom=0.12, wspace=0.08)
 
    top_axes = [fig.add_subplot(gs_top[0, i]) for i in range(2)]
    bot_axes = [fig.add_subplot(gs_bot[0, i]) for i in range(3)]
 
    im = None
    for axes_row, row_taxes in [(top_axes, taxes[:2]), (bot_axes, taxes[2:])]:
        for ci, (ax, tax) in enumerate(zip(axes_row, row_taxes)):
            sub   = df[df["co2_tax_shipping"] == tax]
            pivot = (
                sub.pivot_table(index="cap_factor", columns="cost_factor", values="ship_served_pct")
                .reindex(index=CAP_ORDER, columns=COST_ORDER)
            )
            im = ax.imshow(pivot.values, vmin=0, vmax=100, cmap=cmap, aspect="auto")
 
            for r in range(3):
                for c in range(3):
                    val   = pivot.values[r, c]
                    color = "white" if val > 60 else "#333333"
                    ax.text(c, r, f"{val:.0f}%", ha="center", va="center",
                            fontsize=8, color=color, fontweight="bold")
 
            ax.set_xticks([0, 1, 2])
            ax.set_xticklabels([COST_LABEL[k] for k in COST_ORDER],
                               fontsize=7.5, rotation=30, ha="right")
            ax.set_yticks([0, 1, 2])
            if ci == 0:
                ax.set_yticklabels([CAP_LABEL[k] for k in CAP_ORDER], fontsize=7.5)
            else:
                ax.set_yticklabels([])
            ax.set_title(f"CO₂ tax  \${tax}/t", fontsize=8.5, pad=6)
 
    cbar_ax = fig.add_axes([0.90, 0.12, 0.022, 0.70])
    cb = fig.colorbar(im, cax=cbar_ax)
    cb.set_label("Green ammonia\nshare (%)", fontsize=8)
    cb.ax.tick_params(labelsize=7.5)
 
    fig.text(0.49, 0.95, "Green ammonia share of shipping demand",
             ha="center", fontsize=10, fontweight="bold")
    fig.text(0.49, 0.91, "by production capacity, cost, and CO₂ tax",
             ha="center", fontsize=9, color="#444")
    fig.text(0.49, 0.02, "Production cost level", ha="center", fontsize=8.5)
    fig.text(0.02, 0.50, "Production capacity level", va="center",
             rotation="vertical", fontsize=8.5)
 
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved → {outpath}")
# ─────────────────────────────────────────────────────────────────────────────
# PLOT 2  ·  3×3 line grid: green shipping % vs CO₂ tax
# ─────────────────────────────────────────────────────────────────────────────

def plot2_linegrid(df, outpath):
    taxes = sorted(df["co2_tax_shipping"].unique())

    fig, axes = plt.subplots(3, 3, figsize=(8, 6), sharex=True, sharey=True)
    fig.subplots_adjust(hspace=0.12, wspace=0.08, top=0.85, left=0.10, right=0.97, bottom=0.12)

    for ri, cap in enumerate(CAP_ORDER):
        for ci, cost in enumerate(COST_ORDER):
            ax  = axes[ri][ci]
            sub = df[(df["cap_factor"] == cap) & (df["cost_factor"] == cost)].sort_values(
                "co2_tax_shipping"
            )
            ax.plot(sub["co2_tax_shipping"], sub["ship_served_pct"],
                    color=GREEN, linewidth=2, marker="o", markersize=4, zorder=3)
            ax.axhline(50, color="#c93838", linewidth=0.8, linestyle="--", zorder=2)

            ax.set_ylim(-5, 105)
            ax.set_xlim(taxes[0] - 20, taxes[-1] + 20)
            ax.yaxis.set_major_locator(mticker.MultipleLocator(50))
            ax.set_xticks(taxes)
            ax.tick_params(labelsize=7)
            ax.spines[["top", "right"]].set_visible(False)
            ax.grid(axis="y", linewidth=0.35, alpha=0.5)

            if ri == 0:
                ax.set_title(COST_LABEL[cost], fontsize=8.5, pad=6)
            if ci == 2:
                ax.annotate(CAP_LABEL[cap], xy=(1.05, 0.5), xycoords="axes fraction",
                            fontsize=8.5, va="center", rotation=270)

    fig.text(0.53, 0.02, "CO₂ tax on shipping ($/t NH₃)", ha="center", fontsize=9)
    fig.text(0.02, 0.50, "Green ammonia share (%)", va="center",
             rotation="vertical", fontsize=9)
    fig.text(0.53, 0.95, "Green ammonia share for shipping by production scenario and CO₂ tax",
             ha="center", fontsize=10, fontweight="bold")
    fig.text(0.53, 0.91, "dashed line = 50% threshold",
             ha="center", fontsize=8, color="#666")

    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved → {outpath}")

def plot2_linegrid_nolow(df, outpath):
    taxes = sorted(df["co2_tax_shipping"].unique())
    cap_order_plot = ["medium", "high"]  # exclude low

    fig, axes = plt.subplots(2, 3, figsize=(8, 4.5), sharex=True, sharey=True)
    fig.subplots_adjust(hspace=0.12, wspace=0.08, top=0.85, left=0.10, right=0.97, bottom=0.12)

    for ri, cap in enumerate(cap_order_plot):
        for ci, cost in enumerate(COST_ORDER):
            ax  = axes[ri][ci]
            sub = df[(df["cap_factor"] == cap) & (df["cost_factor"] == cost)].sort_values(
                "co2_tax_shipping"
            )
            ax.plot(sub["co2_tax_shipping"], sub["ship_served_pct"],
                    color=GREEN, linewidth=2, marker="o", markersize=4, zorder=3)
            ax.axhline(50, color="#c93838", linewidth=0.8, linestyle="--", zorder=2)

            ax.set_ylim(-5, 105)
            ax.set_xlim(taxes[0] - 20, taxes[-1] + 20)
            ax.yaxis.set_major_locator(mticker.MultipleLocator(50))
            ax.set_xticks(taxes)
            ax.tick_params(labelsize=7)
            ax.spines[["top", "right"]].set_visible(False)
            ax.grid(axis="y", linewidth=0.35, alpha=0.5)

            if ri == 0:
                ax.set_title(COST_LABEL[cost], fontsize=8.5, pad=6)
            if ci == 2:
                ax.annotate(CAP_LABEL[cap], xy=(1.05, 0.5), xycoords="axes fraction",
                            fontsize=8.5, va="center", rotation=270)
                
    fig.text(0.53, 0.02, "CO₂ tax on shipping ($/t NH₃)", ha="center", fontsize=9)
    fig.text(0.02, 0.50, "Green ammonia share (%)", va="center",
            rotation="vertical", fontsize=9)
    fig.text(0.53, 0.95, "Green ammonia share for shipping by production scenario and CO₂ tax",
            ha="center", fontsize=10, fontweight="bold")
    fig.text(0.53, 0.91, "dashed line = 50% threshold",
            ha="center", fontsize=8, color="#666")

    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved → {outpath}")
# ─────────────────────────────────────────────────────────────────────────────
# PLOT 3  ·  Sector allocation under rising CO₂ tax
# ─────────────────────────────────────────────────────────────────────────────

def plot3_sector_allocation(df, outpath, cap="medium", cost="low"):
    sub = df[(df["cap_factor"] == cap) & (df["cost_factor"] == cost)].sort_values(
        "co2_tax_shipping"
    )
    if sub.empty:
        print(f"  [warn] no data for cap={cap} cost={cost}, skipping plot 3")
        return

    taxes = sub["co2_tax_shipping"].values
    x     = np.arange(len(taxes))

    steel_green  = sub["steel_delivered"].values
    steel_fossil = sub["steel_demand"].values - steel_green
    fert_green   = sub["fert_delivered"].values
    fert_fossil  = sub["fert_demand"].values - fert_green
    ship_green   = sub["ship_delivered"].values
    ship_fossil  = sub["ship_demand"].values - ship_green

    fig, axes = plt.subplots(1, 3, figsize=(10, 4))
    fig.subplots_adjust(wspace=0.38, top=0.68, bottom=0.14, left=0.07, right=0.97)

    def stacked_bars(ax, green_vals, fossil_vals, title, color):
        ax.bar(x, green_vals,  width=0.55, color=color,        zorder=3)
        ax.bar(x, fossil_vals, width=0.55, color=color, alpha=0.30,
               bottom=green_vals, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels([f"${t}" for t in taxes], fontsize=8)
        ax.set_xlabel("CO₂ tax ($/t NH₃)", fontsize=8.5)
        ax.set_title(title, fontsize=9.5, pad=18)
        ax.set_ylabel("Volume (Mt NH₃)", fontsize=8.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(5, integer=True))
        ax.grid(axis="y", linewidth=0.4, alpha=0.5, zorder=0)

        for i, (g, f) in enumerate(zip(green_vals, fossil_vals)):
            total = g + f
            if total > 0:
                pct = 100 * g / total
                ax.text(i, total + total * 0.02, f"{pct:.0f}%",
                        ha="center", va="bottom", fontsize=7, color="#333")

    stacked_bars(axes[0], steel_green, steel_fossil, "Steel",      STEEL)
    stacked_bars(axes[1], fert_green,  fert_fossil,  "Fertiliser", FERT)
    stacked_bars(axes[2], ship_green,  ship_fossil,  "Shipping",   SHIP)

    from matplotlib.patches import Patch
    import matplotlib.colors as mcolors
    def faded(hex_color, alpha=0.30):
        r, g, b = mcolors.to_rgb(hex_color)
        return (1-alpha) + alpha*r, (1-alpha) + alpha*g, (1-alpha) + alpha*b

    handles = [
        Patch(facecolor=STEEL,        label="Steel — green NH₃"),
        Patch(facecolor=faded(STEEL), label="Steel — fossil NH₃"),
        Patch(facecolor=FERT,         label="Fertiliser — green NH₃"),
        Patch(facecolor=faded(FERT),  label="Fertiliser — fossil NH₃"),
        Patch(facecolor=SHIP,         label="Shipping — green NH₃"),
        Patch(facecolor=faded(SHIP),  label="Shipping — fossil NH₃"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=3, fontsize=8,
               bbox_to_anchor=(0.5, 0.995), frameon=False, columnspacing=1.0)

    # fig.text(
    #     0.53, 0.84,
    #     f"Sector supply mix under rising CO₂ shipping tax  ·  "
    #     f"{CAP_LABEL[cap].lower()} capacity, {COST_LABEL[cost].lower()}",
    #     ha="center", fontsize=9.5, fontweight="bold"
    # )

    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved → {outpath}")


def plot4_demand_coverage(df, outpath, cap="medium", cost="low"):
    sub = df[(df["cap_factor"] == cap) & (df["cost_factor"] == cost)].sort_values(
        "co2_tax_shipping"
    )
    if sub.empty:
        print(f"  [warn] no data for cap={cap} cost={cost}, skipping plot 4")
        return

    taxes = sub["co2_tax_shipping"].values
    x     = np.arange(len(taxes))

    total_demand = (sub["steel_demand"] + sub["fert_demand"] + sub["ship_demand"]).values

    steel_pct = 100 * sub["steel_delivered"].values / total_demand
    fert_pct  = 100 * sub["fert_delivered"].values  / total_demand
    ship_pct  = 100 * sub["ship_delivered"].values  / total_demand
    unmet_pct = 100 - steel_pct - fert_pct - ship_pct

    fig, ax = plt.subplots(figsize=(6, 4.5))
    fig.subplots_adjust(top=0.91, bottom=0.14, left=0.12, right=0.97)

    width = 0.55
    ax.bar(x, steel_pct, width=width, color=STEEL,     zorder=3, label="Steel")
    ax.bar(x, fert_pct,  width=width, color=FERT,      zorder=3, label="Fertiliser",
           bottom=steel_pct)
    ax.bar(x, ship_pct,  width=width, color=SHIP,      zorder=3, label="Shipping",
           bottom=steel_pct + fert_pct)
    ax.bar(x, unmet_pct, width=width, color="#cccccc", zorder=3, label="Unmet demand",
           bottom=steel_pct + fert_pct + ship_pct)

    # percentage labels inside each segment
    bottoms = [np.zeros(len(taxes)), steel_pct, steel_pct + fert_pct,
               steel_pct + fert_pct + ship_pct]
    vals    = [steel_pct, fert_pct, ship_pct, unmet_pct]
    colors_label = ["white", "white", "white", "#666"]
    for bot, val, lc in zip(bottoms, vals, colors_label):
        for i, (b, v) in enumerate(zip(bot, val)):
            if v > 2:
                ax.text(i, b + v / 2, f"{v:.0f}%",
                        ha="center", va="center", fontsize=7.5,
                        color=lc, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([f"${t}" for t in taxes], fontsize=9)
    ax.set_xlabel("CO₂ tax on shipping ($/t NH₃)", fontsize=9)
    ax.set_ylabel("Share of total global demand (%)", fontsize=9)
    ax.set_ylim(0, 103)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", linewidth=0.4, alpha=0.5, zorder=0)

    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=STEEL,     label="Steel — green NH₃"),
        Patch(facecolor=FERT,      label="Fertiliser — green NH₃"),
        Patch(facecolor=SHIP,      label="Shipping — green NH₃"),
        Patch(facecolor="#cccccc", label="Unmet demand"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, fontsize=8,
               bbox_to_anchor=(0.5, 0.99), frameon=False)

    # fig.text(
    #     0.53, 0.82,
    #     f"Global demand coverage under rising CO₂ shipping tax  ·  "
    #     f"{CAP_LABEL[cap].lower()} capacity, {COST_LABEL[cost].lower()}",
    #     ha="center", fontsize=9, fontweight="bold"
    # )

    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved → {outpath}")



# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results",      required=True,
                        help="Path to shippingtax_case directory")
    parser.add_argument("--scenario-csv", default=None,
                        help="Path to Scenario.csv (default: <results>/Scenario.csv)")
    parser.add_argument("--outdir",       default=None,
                        help="Output directory (default: <results>)")
    parser.add_argument("--cap",          default="medium",
                        choices=["low", "medium", "high"],
                        help="Capacity level for plot 3 (default: medium)")
    parser.add_argument("--cost",         default="low",
                        choices=["low", "medium", "high"],
                        help="Cost level for plot 3 (default: low)")
    args = parser.parse_args()

    results_dir  = args.results
    scenario_csv = args.scenario_csv or os.path.join(results_dir, "Scenario.csv")
    outdir       = args.outdir or results_dir
    os.makedirs(outdir, exist_ok=True)

    print("Loading Scenario.csv …")
    scenarios = pd.read_csv(scenario_csv)

    print("Aggregating all scenarios …")
    df = load_all_scenarios(results_dir, scenarios)
    print(f"  loaded {len(df)} scenarios")

    # print("\nPlot 1: shipping share heatmap")
    # plot1_heatmap(df, os.path.join(outdir, "plot1_shipping_share_heatmap.png"))

    print("Plot 2: 3×3 line grid")
    plot2_linegrid_nolow(df, os.path.join(outdir, "plot2_shipping_share_lines_nolow.png"))

    # print(f"Plot 3: sector allocation (cap={args.cap}, cost={args.cost})")
    # plot3_sector_allocation(
    #     df, os.path.join(outdir, "plot3_sector_allocation.png"),
    #     cap=args.cap, cost=args.cost
    # )

    print(f"Plot 4: global demand coverage (cap={args.cap}, cost={args.cost})")
    plot4_demand_coverage(
        df, os.path.join(outdir, f"plot4_demand_coverage_{args.cap}_{args.cost}.png"),
        cap=args.cap, cost=args.cost
    )
    print("\nDone.")


if __name__ == "__main__":
    main()