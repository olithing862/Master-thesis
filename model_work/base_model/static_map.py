"""
Industry share bar chart — replaces pie chart for thesis.
Run locally: python plot_industry_bar.py
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

# --- Config ---
RESULTS_DIR = Path("Results/sensitivity_base/capacity_8/2026-04-23")
DEMAND_CSV  = RESULTS_DIR / "results_demand.csv"

# --- Load and classify by industry ---
df = pd.read_csv(DEMAND_CSV)

def classify(node_id):
    if 'steel' in node_id: return 'Steel'
    if '_sh'   in node_id: return 'Shipping'
    if '_f'    in node_id: return 'Fertiliser'
    return 'Other'

df['industry'] = df['node_id'].apply(classify)
industry_df = df.groupby('industry')['delivered'].sum().reset_index()
industry_df = industry_df.sort_values('delivered', ascending=False)

industries = industry_df['industry'].tolist()
volumes    = industry_df['delivered'].tolist()
total      = sum(volumes)
shares     = [v / total * 100 for v in volumes]

# --- Colors ---
colors = ['#5b9f8d', '#e8956a', "#8cc47e"]  # teal, coral, muted blue

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 3))

bars = ax.barh(industries, volumes, color=colors, height=0.55, edgecolor='white', linewidth=0.5)

# Add labels to the right of each bar
for bar, vol, share in zip(bars, volumes, shares):
    ax.text(bar.get_width() + 0.08, bar.get_y() + bar.get_height() / 2,
            f'{vol:.2f} Mt  ({share:.1f}%)',
            va='center', ha='left', fontsize=10, color='#333333')

ax.set_xlim(0, max(volumes) * 1.45)
ax.set_xlabel('Delivered volume (Mt)', fontsize=10, color='#555555')
ax.set_title(f'Delivered ammonia by sector (total: {total:.2f} Mt)', fontsize=12, pad=10)

# Clean up
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(left=False, labelsize=10)
ax.xaxis.set_visible(False)

plt.tight_layout()

# --- Save ---
OUTPUT = RESULTS_DIR / "industry_share_bar.png"
plt.savefig(OUTPUT, dpi=200, bbox_inches='tight', facecolor='white')
print(f"Saved to {OUTPUT}")