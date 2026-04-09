
import pandas as pd
import matplotlib.pyplot as plt

# Create dataframe
data = {
    'Distance_km': [200,400,600,800,1000,1200,1400,1600],
    'Rail':[4,4.67,5.33,6,6.25,6.5,6.75,7],
    'Nustar':[1.2,1.47,1.73,2,2.12,2.25,2.38,2.5],
    'Magellan':[2.95,2.92,2.88,2.85,2.76,2.67,2.59,2.5],
    'Short_truck':[2.1,3.5,4,None,None,None,None,None],
    'Long_truck':[None,3.6,6.8,9.5,13.12,16.75,20.38,24],
}

df = pd.DataFrame(data)


# Compute mean
df['Mean'] = df[['Rail','Nustar','Magellan','Short_truck','Long_truck']].mean(axis=1)

# Colors
neutral_colors = ['#bbbbbb','#999999','#777777','#555555','#333333']
mean_color = '#ff4500'  # bright orange

plt.figure(figsize=(10,6))

# Plot neutral transport modes
for col, col_color in zip(['Rail','Nustar','Magellan','Short_truck','Long_truck'], neutral_colors):
    plt.plot(df['Distance_km'], df[col], marker='o', label=col,
             color=col_color, linewidth=1)

# Highlight mean
plt.plot(df['Distance_km'], df['Mean'], marker='o', label='Mean',
         color=mean_color, linewidth=3)

plt.xlabel('Distance (km)')
plt.ylabel('Cost')
plt.title('Transport Cost by Mode vs Distance')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig('transport_plot_mean_highlight.png')
plt.show()
