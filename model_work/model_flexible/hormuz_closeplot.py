import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd


def plot_hormuz_substitution(
    baseline_production_csv,
    hormuz_production_csv,
    nodes_csv,
    output_path,
    baseline_label='Baseline',
    hormuz_label='Hormuz closed',
    scenario_note='',
):
    # ── Load ─────────────────────────────────────────────────────────────────
    nodes      = pd.read_csv(nodes_csv)
    prod_t3    = pd.read_csv(baseline_production_csv)
    prod_h1    = pd.read_csv(hormuz_production_csv)

    prod_nodes = nodes[nodes['type'] == 'production'][['node_id', 'region']]

    t3 = prod_t3.merge(prod_nodes, on='node_id').groupby('region')['produced'].sum()
    h1 = prod_h1.merge(prod_nodes, on='node_id').groupby('region')['produced'].sum()

    all_regions   = sorted(set(t3.index) | set(h1.index))
    baseline_vals = np.array([t3.get(r, 0) for r in all_regions])
    hormuz_vals   = np.array([h1.get(r, 0) for r in all_regions])
    delta         = hormuz_vals - baseline_vals

    order      = np.argsort(delta)
    regions_s  = [all_regions[i] for i in order]
    baseline_s = baseline_vals[order]
    hormuz_s   = hormuz_vals[order]
    delta_s    = delta[order]

    # ── Colours ───────────────────────────────────────────────────────────────
    AMBER = '#b8860b'
    TEAL  = '#2a7b8c'
    INC   = '#4a9e6b'
    DEC   = '#c0504d'

    # ── Figure ────────────────────────────────────────────────────────────────
    n_regions  = len(regions_s)
    fig_height = max(7, n_regions * 0.55)

    fig, axes = plt.subplots(1, 2, figsize=(14, fig_height),
                             gridspec_kw={'width_ratios': [2, 1]})
    fig.patch.set_facecolor('white')

    y      = np.arange(n_regions)
    height = 0.38

    # ── Left: grouped bars ────────────────────────────────────────────────────
    ax = axes[0]
    ax.set_facecolor('white')

    bars_b = ax.barh(y + height/2, baseline_s, height, color=TEAL,  alpha=0.75, label=baseline_label)
    bars_h = ax.barh(y - height/2, hormuz_s,   height, color=AMBER, alpha=0.85, label=hormuz_label)

    ax.set_yticks(y)
    ax.set_yticklabels(regions_s, fontsize=9.5)
    ax.set_xlabel('Green NH₃ produced (Mt)', fontsize=10)
    ax.set_title('Production by region', fontsize=11, fontweight='bold', pad=10)
    ax.spines[['top', 'right']].set_visible(False)
    ax.xaxis.grid(True, linestyle='--', alpha=0.4, zorder=0)
    ax.set_axisbelow(True)

    for bar, val in zip(bars_h, hormuz_s):
        if val > 5:
            ax.text(val + 1.5, bar.get_y() + bar.get_height() / 2,
                    f'{val:.0f}', va='center', ha='left', fontsize=7.5, color='#444')

    ax.legend(loc='lower right', fontsize=9, framealpha=0.7)

    # ── Right: delta bars ─────────────────────────────────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor('white')

    colors_d = [INC if d >= 0 else DEC for d in delta_s]
    ax2.barh(y, delta_s, height=0.55, color=colors_d, alpha=0.85, zorder=3)
    ax2.axvline(0, color='#444', linewidth=0.8, zorder=4)

    ax2.set_yticks(y)
    ax2.set_yticklabels([])
    ax2.set_xlabel('Change vs baseline (Mt)', fontsize=10)
    ax2.set_title('Δ Production\n(Hormuz − Baseline)', fontsize=11, fontweight='bold', pad=10)
    ax2.spines[['top', 'right']].set_visible(False)
    ax2.xaxis.grid(True, linestyle='--', alpha=0.4, zorder=0)
    ax2.set_axisbelow(True)

    for yi, (d, c) in enumerate(zip(delta_s, colors_d)):
        ha  = 'left'  if d >= 0 else 'right'
        off = 0.5     if d >= 0 else -0.5
        ax2.text(d + off, yi, f'{d:+.0f}', va='center', ha=ha,
                 fontsize=8, color=c, fontweight='bold')

    inc_patch = mpatches.Patch(color=INC, alpha=0.85, label='Increase')
    dec_patch = mpatches.Patch(color=DEC, alpha=0.85, label='Decrease')
    ax2.legend(handles=[inc_patch, dec_patch], fontsize=9,
               loc='lower right', framealpha=0.7)

    # ── Caption & save ────────────────────────────────────────────────────────
    bottom_margin = 0.05 if scenario_note else 0.01

    if scenario_note:
        fig.text(0.5, 0.01, scenario_note, ha='center', va='bottom',
                 fontsize=8.5, color='#555', style='italic')

    plt.tight_layout(rect=[0, bottom_margin, 1, 1])
    plt.savefig(output_path, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {output_path}")


# ── Example usage ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    BASE   = '/Users/oliviathingvad/Master-thesis'
    NODES  = f'{BASE}/model_work/Datafiles_flexible/nodes.csv'
    T3     = f'{BASE}/Results_final/fixed_steel'
    H1     = f'{BASE}/Results_final/hormuz2'

    for s in ['S9']:
        cost = {'S7': 'high cost', 'S8': 'medium cost', 'S9': 'low cost'}[s]
        plot_hormuz_substitution(
            baseline_production_csv = f'{T3}/T3-{s}/results_production.csv',
            hormuz_production_csv   = f'{H1}/H1-{s}/results_production.csv',
            nodes_csv               = NODES,
            output_path             = f'hormuz_substitution_{s}.png',
            baseline_label          = f'Baseline (T3-{s})',
            hormuz_label            = f'Hormuz closed (H1-{s})',
            scenario_note           = (
                f'H1-{s} vs T3-{s}: high capacity, {cost}, '
                f'$300/t CO₂ tax on shipping, 50% steel mandate'
            ),
        )