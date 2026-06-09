import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── Data ──────────────────────────────────────────────────────────────────────
# Global GHG emissions (GtCO2e) 1990-2019
# Source: Global Carbon Project / Our World in Data (Friedlingstein et al. 2022)
years_global = np.array([
    1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
    2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
    2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019,
    2020, 2021, 2022, 2023
])
ghg_global = np.array([
    22.7, 22.4, 22.3, 22.5, 23.0, 23.5, 23.9, 24.3, 24.0, 24.0,
    25.0, 25.2, 25.8, 27.2, 28.5, 29.4, 30.0, 30.8, 31.4, 30.0,
    32.0, 33.1, 33.5, 34.0, 34.2, 34.0, 33.9, 34.4, 35.3, 35.0,
    33.1, 34.8, 36.1, 36.8
])

# International shipping CO2 (Mt CO2) 1990-2018
# Source: IMO Fourth Greenhouse Gas Study 2020
# IMO Fourth GHG Study 1990-2018, extended to 2023 via ICCT (2025)
years_ship = np.array([
    1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
    2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
    2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019,
    2020, 2021, 2022, 2023
])
co2_ship = np.array([
    456, 446, 447, 441, 450, 464, 473, 491, 477, 468,
    503, 502, 514, 542, 583, 615, 638, 676, 707, 586,
    637, 682, 671, 661, 669, 663, 764, 782, 800, 818,
    792, 818, 836, 857
])

# IMO targets (relative to 2008 baseline of 677 Mt)
imo_2030 = 677 * 0.80   # 20% reduction vs 2008
imo_2050 = 677 * 0.50   # 50% reduction vs 2008 (net zero ambition framing)

# ── Style ─────────────────────────────────────────────────────────────────────
BLUE      = '#2c5f8a'
ORANGE    = '#b8620a'
GREY_LINE = '#aaaaaa'
GREY_BG   = '#f7f7f7'
TEXT      = '#1a1a1a'

plt.rcParams.update({
    'font.family':       'serif',
    'font.size':         9,
    'axes.spines.top':   False,
    'axes.spines.right': False,
    'axes.linewidth':    0.7,
    'xtick.major.width': 0.7,
    'ytick.major.width': 0.7,
    'xtick.labelsize':   8,
    'ytick.labelsize':   8,
    'text.color':        TEXT,
    'axes.labelcolor':   TEXT,
    'xtick.color':       TEXT,
    'ytick.color':       TEXT,
})

fig, (ax1, ax2) = plt.subplots(
    1, 2,
    figsize=(7.5, 3.4),
    facecolor='white',
    gridspec_kw={'wspace': 0.38}
)

# ── Panel A: Global GHG ───────────────────────────────────────────────────────
ax1.fill_between(years_global, ghg_global, alpha=0.12, color=BLUE)
ax1.plot(years_global, ghg_global, color=BLUE, linewidth=1.8, zorder=3)

ax1.set_xlim(1990, 2023)
ax1.set_ylim(0,45)
ax1.set_xlabel('Year', labelpad=4)
ax1.set_ylabel('GtCO\u2082 per year', labelpad=4)
ax1.set_title('(a) Global GHG emissions', fontsize=9, loc='left', pad=6, fontweight='bold')
ax1.yaxis.set_major_locator(mticker.MultipleLocator(10))
ax1.yaxis.set_minor_locator(mticker.MultipleLocator(5))
ax1.xaxis.set_major_locator(mticker.MultipleLocator(10))

# annotation
ax1.annotate(
    f'+{((ghg_global[-1]/ghg_global[0])-1)*100:.0f}%\nsince 1990',
    xy=(2023, 38),
    xytext=(2010, 39),
    fontsize=7.5, color=BLUE,
    arrowprops=dict(arrowstyle='->', color=BLUE, lw=0.9),
    ha='center'
)

ax1.text(
    0.03, 0.06,
    'Source: Global Carbon Project\n(Friedlingstein et al. 2022)',
    transform=ax1.transAxes,
    fontsize=6.5, color='#666666', style='italic'
)

# ── Panel B: Shipping CO2 ─────────────────────────────────────────────────────
ax2.fill_between(years_ship, co2_ship, alpha=0.12, color=ORANGE)
ax2.plot(years_ship, co2_ship, color=ORANGE, linewidth=1.8, zorder=3, label='Historical')

# IMO target markers
ax2.axhline(imo_2030, xmin=0, xmax=1, color=GREY_LINE, linewidth=0.9,
            linestyle='--', zorder=2)
ax2.axhline(imo_2050, xmin=0, xmax=1, color=GREY_LINE, linewidth=0.9,
            linestyle=':', zorder=2)

ax2.text(2018.6, imo_2030 + 8,  'IMO 2030\n(\u221220%)', fontsize=6.8,
         color='#888888', ha='right', va='bottom')
ship_share = (co2_ship[-1] / 1000) / ghg_global[years_global == 2023][0] * 100

ax2.annotate(
    f'{ship_share:.1f}% of global\nGHG emissions (2023)',
    xy=(2023, co2_ship[-1]),
    xytext=(2016, 950),
    fontsize=7.5, color=ORANGE,
    arrowprops=dict(arrowstyle='->', color=ORANGE, lw=0.9),
    ha='center'
)


ax2.set_xlim(1990, 2023)
ax2.set_ylim(350, 1000)
ax2.set_xlabel('Year', labelpad=4)
ax2.set_ylabel('MtCO\u2082 per year', labelpad=4)
ax2.set_title('(b) International shipping CO\u2082 emissions', fontsize=9,
              loc='left', pad=6, fontweight='bold')

ax2.yaxis.set_major_locator(mticker.MultipleLocator(100))
ax2.xaxis.set_major_locator(mticker.MultipleLocator(10))

ax2.text(
    0.03, 0.06,
    'Source: IMO Fourth GHG Study (2020)',
    transform=ax2.transAxes,
    fontsize=6.5, color='#666666', style='italic'
)

# ── Save ──────────────────────────────────────────────────────────────────────
fig.savefig(
    '/Users/oliviathingvad/Master-thesis/emissions_figure.pdf',
    dpi=300, bbox_inches='tight', facecolor='white'
)
fig.savefig(
    '/Users/oliviathingvad/Master-thesis/emissions_figure.png',
    dpi=300, bbox_inches='tight', facecolor='white'
)

print("Saved: emissions_figure.pdf and emissions_figure.png")
plt.close()