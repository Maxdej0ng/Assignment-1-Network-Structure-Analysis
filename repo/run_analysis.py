from gtfspy import gtfs
import utils, networkx as nx, pickle, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

Path('output').mkdir(exist_ok=True)
NETWORK, MODE = 'prague', 'Subway'

# 1. Build L-space
g = gtfs.GTFS(f'./{NETWORK}.sqlite')
print('Modes:', [utils.mode_name[x] for x in g.get_modes()])
L = utils.generate_graph(g, MODE, start_hour=5, end_hour=24)
print(f'Raw: {L.number_of_nodes()} nodes, {L.number_of_edges()} edges')

# 2. Clean
L_merged = utils.merge_stops_with_same_name(L, delta=200)

# Fix Prague-specific issue: interchange stations have line suffixes in their names
# (e.g. "Muzeum - A" / "Muzeum - C") so they are NOT auto-merged but should be,
# because they are the same physical station on different lines.
# Merge them manually so all 3 lines form one connected graph.
def find_node_by_name(G, name):
    return next((n for n in G.nodes() if G.nodes[n].get('name') == name), None)

interchange_pairs = [
    ('Můstek - A',  'Můstek - B'),
    ('Muzeum - A',  'Muzeum - C'),
    ('Florenc - B', 'Florenc - C'),
]
for name_a, name_b in interchange_pairs:
    n_a = find_node_by_name(L_merged, name_a)
    n_b = find_node_by_name(L_merged, name_b)
    if n_a is not None and n_b is not None:
        utils.merge_nodes(L_merged, n_a, n_b)
        # Rename the merged node to the base name (without line suffix)
        base = name_a.rsplit(' - ', 1)[0]
        L_merged.nodes[n_a]['name'] = base
        print(f'Merged interchange: {name_a} + {name_b} → {base}')
    else:
        print(f'WARNING: could not find {name_a!r} or {name_b!r}')

isolates = list(nx.isolates(L_merged))
if isolates:
    L_merged.remove_nodes_from(isolates)
utils.sanity_check(L_merged)

# 3. Save L-space
G_int = nx.convert_node_labels_to_integers(L_merged)
with open(f'./{NETWORK}.pkl', 'wb') as f:
    pickle.dump(G_int, f)
print(f'L-space saved: {G_int.number_of_nodes()} nodes, {G_int.number_of_edges()} edges')

# 4. Build P-space
g = gtfs.GTFS(f'./{NETWORK}.sqlite')
with open(f'./{NETWORK}.pkl', 'rb') as f:
    L_graph = pickle.load(f)
P = utils.P_space(g, L_graph, mode=MODE)
print(f'P-space: {P.number_of_nodes()} nodes, {P.number_of_edges()} edges')
with open('output/Network.pkl', 'wb') as f:
    pickle.dump({'L_space': L_graph, 'P_space': P, 'city': NETWORK, 'mode': MODE}, f)
print('Saved output/Network.pkl')

# 5. Undirected for analysis
L_ud = L_graph.to_undirected().subgraph(
    max(nx.connected_components(L_graph.to_undirected()), key=len)).copy()
P_ud = P.to_undirected().subgraph(
    max(nx.connected_components(P.to_undirected()), key=len)).copy()
N_L, E_L = L_ud.number_of_nodes(), L_ud.number_of_edges()
N_P, E_P = P_ud.number_of_nodes(), P_ud.number_of_edges()

# 6. Global indicators
print('\nComputing global indicators...')
diam_L_uw = nx.diameter(L_ud)
diam_L_w  = nx.diameter(L_ud, weight='duration_avg')
diam_P_uw = nx.diameter(P_ud)
diam_P_w  = nx.diameter(P_ud, weight='avg_wait')
asp_L_uw  = nx.average_shortest_path_length(L_ud)
asp_L_w   = nx.average_shortest_path_length(L_ud, weight='duration_avg')
asp_P_uw  = nx.average_shortest_path_length(P_ud)
asp_P_w   = nx.average_shortest_path_length(P_ud, weight='avg_wait')
gamma = E_L / (3 * (N_L - 2))
alpha = (E_L - N_L + 1) / (2 * N_L - 5)

print(f'  N: L={N_L}, P={N_P}  |  E: L={E_L}, P={E_P}')
print(f'  Diameter  L: uw={diam_L_uw} hops, w={diam_L_w:.0f} s')
print(f'  Diameter  P: uw={diam_P_uw} hops, w={diam_P_w:.2f} min')
print(f'  ASP       L: uw={asp_L_uw:.4f}, w={asp_L_w:.1f} s')
print(f'  ASP       P: uw={asp_P_uw:.4f}, w={asp_P_w:.4f} min')
print(f'  Gamma={gamma:.4f}  Alpha={alpha:.4f}')

pd.DataFrame({
    'Indicator': ['N(L)', 'N(P)', 'E(L)', 'E(P)',
                  'Diam L uw (hops)', 'Diam L w (s)',
                  'Diam P uw (hops)', 'Diam P w (min)',
                  'ASP L uw', 'ASP L w (s)',
                  'ASP P uw', 'ASP P w (min)',
                  'Gamma', 'Alpha'],
    'Value': [N_L, N_P, E_L, E_P,
              diam_L_uw, diam_L_w, diam_P_uw, diam_P_w,
              asp_L_uw, asp_L_w, asp_P_uw, asp_P_w,
              gamma, alpha]
}).to_csv('output/global_indicators.csv', index=False)
print('Saved output/global_indicators.csv')

# 7. Local indicators
def local_stats(c_dict, G, label):
    vals = np.array(list(c_dict.values()))
    top3 = sorted(c_dict, key=c_dict.get, reverse=True)[:3]
    top3 = [(G.nodes[n].get('name', str(n)), round(c_dict[n], 6)) for n in top3]
    print(f'  {label}: mean={vals.mean():.4f} std={vals.std():.4f} '
          f'min={vals.min():.4f} max={vals.max():.4f}')
    print(f'    top3={top3}')

print('\nL-space local indicators:')
deg_L        = nx.degree_centrality(L_ud)
close_L_uw   = nx.closeness_centrality(L_ud)
close_L_w    = nx.closeness_centrality(L_ud, distance='duration_avg')
between_L_uw = nx.betweenness_centrality(L_ud, normalized=True)
between_L_w  = nx.betweenness_centrality(L_ud, weight='duration_avg', normalized=True)
local_stats(deg_L,        L_ud, 'Degree')
local_stats(close_L_uw,   L_ud, 'Closeness (uw)')
local_stats(close_L_w,    L_ud, 'Closeness (w)')
local_stats(between_L_uw, L_ud, 'Betweenness (uw)')
local_stats(between_L_w,  L_ud, 'Betweenness (w)')

print('\nP-space local indicators:')
deg_P        = nx.degree_centrality(P_ud)
close_P_uw   = nx.closeness_centrality(P_ud)
close_P_w    = nx.closeness_centrality(P_ud, distance='avg_wait')
between_P_uw = nx.betweenness_centrality(P_ud, normalized=True)
between_P_w  = nx.betweenness_centrality(P_ud, weight='avg_wait', normalized=True)
local_stats(deg_P,        P_ud, 'Degree')
local_stats(close_P_uw,   P_ud, 'Closeness (uw)')
local_stats(close_P_w,    P_ud, 'Closeness (w)')
local_stats(between_P_uw, P_ud, 'Betweenness (uw)')
local_stats(between_P_w,  P_ud, 'Betweenness (w)')

# 8. Save centrality CSV
nodes = list(L_ud.nodes())
df = pd.DataFrame({
    'stop_name':    [L_ud.nodes[n].get('name', str(n)) for n in nodes],
    'deg_L':        pd.Series(deg_L),
    'close_L_uw':   pd.Series(close_L_uw),
    'close_L_w':    pd.Series(close_L_w),
    'between_L_uw': pd.Series(between_L_uw),
    'between_L_w':  pd.Series(between_L_w),
    'deg_P':        pd.Series(deg_P),
    'close_P_uw':   pd.Series(close_P_uw),
    'close_P_w':    pd.Series(close_P_w),
    'between_P_uw': pd.Series(between_P_uw),
    'between_P_w':  pd.Series(between_P_w),
}, index=nodes)
df.to_csv('output/centrality_indicators.csv')
print('Saved output/centrality_indicators.csv')

# 9. Histograms
sets = [
    (deg_L, 'Degree L'), (close_L_uw, 'Closeness L uw'), (close_L_w, 'Closeness L w'),
    (between_L_uw, 'Betweenness L uw'), (between_L_w, 'Betweenness L w'),
    (deg_P, 'Degree P'), (close_P_uw, 'Closeness P uw'), (close_P_w, 'Closeness P w'),
    (between_P_uw, 'Betweenness P uw'), (between_P_w, 'Betweenness P w'),
]
fig, axes = plt.subplots(2, 5, figsize=(20, 7))
for ax, (c, t) in zip(axes.flat, sets):
    ax.hist(list(c.values()), bins=20, color='steelblue', edgecolor='white', lw=0.4)
    ax.set_title(t, fontsize=8)
    ax.set_xlabel('Value', fontsize=7)
    ax.set_ylabel('Count', fontsize=7)
    ax.tick_params(labelsize=6)
plt.suptitle('Prague Subway — Centrality Histograms', fontsize=12, y=1.01)
plt.tight_layout()
plt.savefig('output/histograms.png', bbox_inches='tight')
plt.close()
print('Saved output/histograms.png')

# 10. Pearson heatmaps
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
sns.heatmap(
    df[['deg_L', 'close_L_uw', 'close_L_w', 'between_L_uw', 'between_L_w']].corr(),
    annot=True, fmt='.2f', cmap='coolwarm', center=0, linewidths=0.5, ax=axes[0])
axes[0].set_title('Pearson — within L-space')
sns.heatmap(
    df[['deg_L', 'close_L_w', 'between_L_w', 'deg_P', 'close_P_w', 'between_P_w']].corr(),
    annot=True, fmt='.2f', cmap='coolwarm', center=0, linewidths=0.5, ax=axes[1])
axes[1].set_title('Pearson — L-space vs P-space')
plt.tight_layout()
plt.savefig('output/pearson_correlations.png', bbox_inches='tight')
plt.close()
print('Saved output/pearson_correlations.png')

# 11. Vulnerability & Redundancy
bc = np.array(list(between_L_w.values()))
vulnerability = bc.max() / bc.mean()
redundancy = alpha
print(f'\nVulnerability={vulnerability:.4f}  Redundancy={redundancy:.4f}')
fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter([redundancy], [vulnerability], s=80, color='steelblue')
ax.annotate('Prague', (redundancy, vulnerability),
            textcoords='offset points', xytext=(6, 3), fontsize=10)
ax.set_xlabel('Redundancy')
ax.set_ylabel('Vulnerability')
ax.set_title('Vulnerability vs Redundancy')
ax.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig('output/vulnerability_redundancy_scatter.png', bbox_inches='tight')
plt.close()
print('Saved output/vulnerability_redundancy_scatter.png')

print('\n=== ALL DONE ===')
