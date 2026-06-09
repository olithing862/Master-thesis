import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Colour palette ─────────────────────────────────────────────────────────
STEEL_COLOR = "#6b9e78"
FERT_COLOR  = "#c97b38"
SHIP_COLOR  = "#4a6fa5"

# ── Data ───────────────────────────────────────────────────────────────────
scenarios = {
    'SHL': ('Low',    'High',   1),
    'SML': ('Low',    'Medium', 2),
    'SLL': ('Low',    'Low',    3),
    'SHM': ('Medium', 'High',   4),
    'SMM': ('Medium', 'Medium', 5),
    'SLM': ('Medium', 'Low',    6),
    'SHH': ('High',   'High',   7),
    'SMH': ('High',   'Medium', 8),
    'SLH': ('High',   'Low',    9),
}

data = {}
for sid, (cap, cost, idx) in scenarios.items():
    rows      = list(csv.DictReader(open(f'/Users/oliviathingvad/Master-thesis/Results_final/base_case/S{idx}/s{idx}results_demand.csv')))
    prod_rows = list(csv.DictReader(open(f'/Users/oliviathingvad/Master-thesis/Results_final/base_case/S{idx}/s{idx}results_production.csv')))
    steel     = sum(float(r['delivered']) for r in rows if 'steel' in r['node_id'])
    fert      = sum(float(r['delivered']) for r in rows if r['node_id'].startswith('oft_f'))
    cap_total = sum(float(r['capacity']) for r in prod_rows)
    data[sid] = {'cap': cap, 'cost': cost, 'steel': steel, 'fert': fert, 'capacity': cap_total}

cap_groups  = ['Low', 'Medium', 'High']
cost_order  = ['High', 'Medium', 'Low']
cost_labels = ['High cost', 'Med. cost', 'Low cost']

TITLE_SIZE = 18
LABEL_SIZE = 18
TICK_SIZE  = 18
ANNOT_SIZE = 18

bar_width = 0.5
x = np.arange(len(cost_order))

cap_vals = {'Low': 179, 'Medium': 376, 'High': 699}
ylims    = {k: v * 1.15 for k, v in cap_vals.items()}

fig, axes = plt.subplots(1, 3, figsize=(14, 6))

for ax, cap_group in zip(axes, cap_groups):
    cap_scenarios = {k: v for k, v in data.items() if v['cap'] == cap_group}

    def get(cost_level, field, cs=cap_scenarios):
        key = [k for k, v in cs.items() if v['cost'] == cost_level][0]
        return cs[key][field]

    steels  = [get(c, 'steel') for c in cost_order]
    ferts   = [get(c, 'fert')  for c in cost_order]
    cap_val = cap_vals[cap_group]
    ylim    = ylims[cap_group]

    ax.bar(x, steels, width=bar_width, color=STEEL_COLOR)
    ax.bar(x, ferts,  width=bar_width, bottom=steels, color=FERT_COLOR)

    ax.axhline(cap_val, color='black', linestyle='--', linewidth=1.3, zorder=5)
    ax.text(x[-1] + bar_width/2, cap_val + ylim * 0.02,
            f'{cap_val:.0f} Mt',
            ha='right', va='bottom', fontsize=ANNOT_SIZE, color='black')

    for i, (s, f) in enumerate(zip(steels, ferts)):
        total = s + f
        if total > 0.5:
            ax.text(i, total + ylim * 0.02, f'{total:.0f} Mt',
                    ha='center', va='bottom', fontsize=ANNOT_SIZE)

    ax.set_title(f'{cap_group} capacity', fontsize=TITLE_SIZE)
    ax.set_xticks(x)
    ax.set_xticklabels(cost_labels, fontsize=TICK_SIZE)
    ax.set_xlabel('Cost level', fontsize=LABEL_SIZE)
    ax.set_ylim(0, ylim)
    ax.tick_params(axis='y', labelsize=TICK_SIZE)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # y-axis numbers on every panel
    ax.tick_params(labelleft=True)
    if cap_group == 'Low':
        ax.set_ylabel('Delivered ammonia (Mt)', fontsize=LABEL_SIZE)
    else:
        ax.set_ylabel('')

# ── Legend ─────────────────────────────────────────────────────────────────
steel_patch = mpatches.Patch(color=STEEL_COLOR, label='Steel')
fert_patch  = mpatches.Patch(color=FERT_COLOR,  label='Fertiliser')
ship_patch  = mpatches.Patch(color=SHIP_COLOR,  label='Shipping')
cap_line    = plt.Line2D([0], [0], color='black', linestyle='--',
                         linewidth=1.3, label='Production capacity')

fig.legend(
    handles=[steel_patch, fert_patch, ship_patch, cap_line],
    loc='upper center', ncol=4, fontsize=LABEL_SIZE,
    frameon=False, bbox_to_anchor=(0.5, 1.02)
)

fig.suptitle('Industry allocation of delivered green ammonia',
             fontsize=TITLE_SIZE + 1, y=1.06)

plt.tight_layout()

plt.savefig('/Users/oliviathingvad/Master-thesis/Results_final/base_case/industry_allocation_S1_S9.png',
            dpi=200, bbox_inches='tight', facecolor='white')
print("Saved.")