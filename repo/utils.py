# Standard libraries
from collections import Counter
from itertools import islice
import os
import pickle
from statistics import mean

# Bokeh
from bokeh.io import show, export_png

# from bokeh.models import (CDSView, ColorBar, ColumnDataSource, CustomJS, CustomJSFilter, GeoJSONDataSource, HoverTool, LinearColorMapper, Slider, Circle, MultiLine, WheelZoomTool,GMapOptions, Range1d, Button, NodesAndLinkedEdges, EdgesAndLinkedNodes, ColorBar)
from bokeh.models import (
    Button,
    Circle,
    ColorBar,
    GMapOptions,
    HoverTool,
    LinearColorMapper,
    MultiLine,
    Range1d,
    WheelZoomTool,
)
from bokeh.layouts import column
from bokeh.palettes import RdYlGn11
from bokeh.plotting import figure, from_networkx, gmap
from bokeh.tile_providers import CARTODBPOSITRON, get_provider

# # GTFSpy package
from gtfspy import networks
# from gtfspy import import_gtfs, gtfs, networks, route_types, util
# from gtfspy.filter import FilterExtract

# Others
from IPython.display import clear_output
import pandas as pd
from pyproj import Proj, Transformer
from thefuzz import fuzz, process
import geopy.distance
import networkx as nx

# GTFS Modes
mode_name = {
    0: 'Tram',
    1: 'Subway',
    2: 'Rail', 
    3: 'Bus', 
    4: 'Ferry',
    5: 'Cable Car',
    6: 'Gondola', 
    7: 'Funicular',
    8: 'Horse Carriage',
    9: 'Intercity Bus',
    10: 'Commuter Train',
    11: 'Trolleybus', 
    12: 'Monorail', 
    99: 'Aircraft',
    100: 'Railway Service',
    101: 'High Speed Rail',
    102: 'Long Distance Trains',
    103: 'Inter Regional Rail Service',
    105: 'Sleeper Rail Service', 
    106: 'Regional Rail Service',
    107: 'Tourist Railway Service',
    108: 'Rail Shuttle', 
    109: 'Suburban Railway',
    200: 'CoachService', 
    201: 'InternationalCoach',
    202: 'NationalCoach',
    204: 'RegionalCoach',
    208: 'CommuterCoach',
    400: 'UrbanRailwayService',
    401: 'Metro', 
    402: 'Underground', 
    403: 'Urban Railway Service',
    405: 'Monorail', 
    700: 'BusService',
    701: 'RegionalBus',
    702: 'ExpressBus',
    704: 'LocalBus',
    715: 'Demand and Response Bus Service',
    717: 'Share Taxi Service', 
    800: 'TrolleybusService',
    900: 'TramService', 
    1000: 'WaterTransportService', 
    1100: 'AirService', 
    1300: 'TelecabinService', 
    1400: 'FunicularService', 
    1500: 'TaxiService',
    1501: 'CommunalTaxi',
    1700: 'MiscellaneousService',
    1701: 'CableCar', 
    1702: 'HorseDrawnCarriage'}

mode_code = {v: k for k, v in mode_name.items()}

def mode_to_string(mode):
    return mode_name[mode]

def mode_from_string(mode_str):
    return mode_code[mode_str]

#####################################################
# def load_gtfs(imported_database_path, gtfs_path=None, name=''):
#     if not os.path.exists(imported_database_path):  # reimport only if the imported database does not already exist
#         print('Importing gtfs zip file')
#         import_gtfs.import_gtfs([gtfs_path],  # input: list of GTFS zip files (or directories)
#                                 imported_database_path,  # output: where to create the new sqlite3 database
#                                 print_progress=True,  # whether to print progress when importing data
#                                 location_name=name)
#     return gtfs.GTFS(imported_database_path)
    
# def load_sqlite(imported_database_path):
#     return gtfs.GTFS(imported_database_path)

def generate_graph(gtfs_feed, mode, start_hour=5, end_hour=24):
    """Generates L-space graph considering the most suitable day from GTFS data. Parameters:
    gtfs_feed: a gtfspy gtfs feed object
    mode: string corresponding to the transport mode that we want to consider
    start_hour: integer with the earliest hour we want to consider (in 0..24)
    end_hour: integer with the latest hour we want to consider (in 0..24, larger that start_hour)"""
    assert isinstance(start_hour, int) and isinstance(end_hour, int), 'Start/end hours should be int'
    assert start_hour >= 0 and end_hour >= 0, 'Start/end hour should be larger or equal to 0'
    assert start_hour <= 24 and end_hour <= 24, 'Start/end hour should be smaller or equal to 24'
    assert start_hour < end_hour, 'Start hour should be smaller than end hour'
    assert mode in mode_code and mode_from_string(mode) in gtfs_feed.get_modes(),\
        'Mode is not available for the city'
    day_start = gtfs_feed.get_suitable_date_for_daily_extract(ut=True)
    range_start = day_start + start_hour*3600
    range_end = day_start + end_hour*3600-1
    print('Considering trips between {} and {}'.format(
        gtfs_feed.unixtime_seconds_to_gtfs_datetime(range_start),
        gtfs_feed.unixtime_seconds_to_gtfs_datetime(range_end)))
    
    G = networks.stop_to_stop_network_for_route_type(
        gtfs_feed,
        mode_from_string(mode),
        link_attributes=None,
        start_time_ut=range_start,
        end_time_ut=range_end
    )
    # Save original id in node attributes (to keep once we merge nodes)
    for n, data in G.nodes(data=True):
        data['original_ids'] = [n]
    print('Number of edges: ', len(G.edges()))
    print('Number of nodes: ', len(G.nodes()))
    return G


def plot_graph(G, space='L', back_map=False, MAPS_API_KEY=None, color_by='',edge_color_by='', export_name=''):
    """Plots a networkx graph.
    Parameters:
        - G: the nx graph
        - space: either 'L' or 'P' depending on which space you are plotting
        - back_map: either False (no map), 'GMAPS' (for Google Maps) or 'OSM' for OpenStreetMap
        - MAPS_API_KEY: a valid Google maps api key if back_map='GMAPS'
        - color_by: string with the name of an attribute in G.nodes that will be used to color the nodes
        - edge_color_by: string with the name of an attribute in G.edges that will be used to color the nodes"""
    if back_map == 'GMAPS':
        p = gmap(MAPS_API_KEY, GMapOptions(
            lat=list(G.nodes(data=True))[0][1]['lat'],
            lng=list(G.nodes(data=True))[0][1]['lon'], 
            map_type='roadmap', zoom=11))
    else:
        p = figure(height=600, width=950, toolbar_location='below',
                   tools='pan, wheel_zoom, box_zoom, reset, save')
    # Build dictionary of node positions for visualizations
    pos_dict = {}
    # Reproject for OSM
    transformer = Transformer.from_crs('epsg:4326', 'epsg:3857')
    for i, d in G.nodes(data=True):
        if back_map == 'OSM':
            x2, y2 = transformer.transform(float(d['lat']), float(d['lon']))
        else:
            x2, y2 = float(d['lon']), float(d['lat'])
        pos_dict[int(i)] = (x2, y2)
    # Plot updated graph
    graph = from_networkx(G, layout_function=pos_dict)
    # Add hover tools
    node_hover_tool = HoverTool(tooltips=[('index', '@index'), ('name', '@name')],
                                renderers=[graph.node_renderer])
    hover_edges = HoverTool(tooltips=[('duration_avg', '@duration_avg')],
                            renderers=[graph.edge_renderer], line_policy='interp')
    if space == 'P':
        hover_edges = HoverTool(tooltips=[('avg_wait', '@avg_wait')],
                                renderers=[graph.edge_renderer], line_policy='interp')
    p.add_tools(node_hover_tool,hover_edges)

    # Define the visualization
    if color_by:
        mapper = LinearColorMapper(palette=RdYlGn11)
        graph.node_renderer.glyph = Circle(size=7, fill_color={'field': color_by, 'transform': mapper})
    else:
        graph.node_renderer.glyph = Circle(size=7)
    if edge_color_by:
        mapper = LinearColorMapper(palette=RdYlGn11)
        graph.edge_renderer.glyph = MultiLine(line_width=4, line_alpha=.5,
                                              line_color={'field': edge_color_by, 'transform': mapper})
        color_bar = ColorBar(color_mapper=mapper, label_standoff=12, border_line_color=None, location=(0,0))
        p.add_layout(color_bar,'right')
    
    graph.node_renderer.selection_glyph = Circle(fill_color='blue')
    graph.node_renderer.hover_glyph = Circle(fill_color='red')
    p.toolbar.active_scroll = p.select_one(WheelZoomTool)
    
    # Different hover and select policies depending on the space
    if space == 'P':
        graph.edge_renderer.glyph = MultiLine(line_color = 'edge_color')
        graph.edge_renderer.selection_glyph = MultiLine(line_color='edge_color', line_width=5)
        graph.edge_renderer.hover_glyph = MultiLine(line_color='edge_color', line_width=10)
    if space == 'L':
        graph.edge_renderer.selection_glyph = MultiLine(line_color='blue', line_width=5)
        graph.edge_renderer.hover_glyph = MultiLine(line_color='red', line_width=5)
    p.renderers.append(graph)
    
    if back_map == 'OSM':
        p.add_tile('CartoDB Positron')
    if export_name:
        export_png(p, filename=export_name+'.png')
    else:
        show(p)


def distance(G, n1, n2):
    """Returns the distance in meters between two nodes in the graph."""
    coords_n1 = (G.nodes[n1]['lat'], G.nodes[n1]['lon'])
    coords_n2 = (G.nodes[n2]['lat'], G.nodes[n2]['lon'])
    return geopy.distance.geodesic(coords_n1, coords_n2).m


def merge_nodes(G, n1, n2):
    """Merges node n2 into n1, updates in/out edges, and merge attributes"""
    # Out edges
    for e in G.edges(n2, data=True):
        # If we get duplicated edges, average them. This should be a very odd case.
        if (n1, e[1]) in G.edges(n1):
            # Average travel time
            G[n1][e[1]]['duration_avg'] += e[2]['duration_avg']
            G[n1][e[1]]['duration_avg'] /= 2.0 
            # Sum total n_vehicles
            G[n1][e[1]]['n_vehicles'] += e[2]['n_vehicles'] 
            # Merge route counter
            # for col in ['route_I_counts', 'shape_id', 'direction_id', 'headsign']:
            #     G[n1][e[1]][col] = dict(Counter(G[n1][e[1]][col]) + Counter(e[2][col]))
            G[n1][e[1]]["route_I_counts"]=dict(Counter(G[n1][e[1]]["route_I_counts"]) + Counter(e[2]["route_I_counts"])) 
            G[n1][e[1]]["shape_id"]=dict(Counter(G[n1][e[1]]["shape_id"]) + Counter(e[2]["shape_id"])) 
            G[n1][e[1]]["direction_id"]=dict(Counter(G[n1][e[1]]["direction_id"]) + Counter(e[2]["direction_id"])) 
            G[n1][e[1]]["headsign"]=dict(Counter(G[n1][e[1]]["headsign"]) + Counter(e[2]["headsign"]))
        # Else, retain edge in the merged graph, except for self loops
        elif n1 != e[1]:
            G.add_edge(n1, e[1],
                       duration_avg=e[2]['duration_avg'],
                       n_vehicles=e[2]['n_vehicles'],
                       d=e[2]['d'], # We keep the original distance, which is not exactly right
                       route_I_counts=e[2]['route_I_counts'],
                       shape_id=e[2]['shape_id'],
                       direction_id=e[2]['direction_id'],
                       headsign=e[2]['headsign'])
    # In edges
    for e in G.in_edges(n2, data=True):
        # If we get duplicated edges, average them. This should be a very odd case.
        if (e[0], n1) in G.in_edges(n1):
            # Average travel time
            G[e[0]][n1]['duration_avg'] += e[2]['duration_avg']
            G[e[0]][n1]['duration_avg'] /= 2.0 
            # Sum total n_vehicles
            G[e[0]][n1]['n_vehicles'] += e[2]['n_vehicles'] 
            # Merge route counter
            # for col in ['route_I_counts', 'shape_id', 'direction_id', 'headsign']:
            #     G[n1][e[1]][col] = dict(Counter(G[n1][e[1]][col]) + Counter(e[2][col]))
            G[e[0]][n1]["route_I_counts"]=dict(Counter(G[e[0]][n1]["route_I_counts"]) + Counter(e[2]["route_I_counts"])) 
            #Merge direction, shape_id, and headsign
            G[e[0]][n1]["shape_id"]=dict(Counter(G[e[0]][n1]["shape_id"]) + Counter(e[2]["shape_id"])) 
            G[e[0]][n1]["direction_id"]=dict(Counter(G[e[0]][n1]["direction_id"]) + Counter(e[2]["direction_id"]))
            G[e[0]][n1]["headsign"]=dict(Counter(G[e[0]][n1]["headsign"]) + Counter(e[2]["headsign"]))
            
        # Else, retain edge in the merged graph
        elif e[0] != n1:
            G.add_edge(e[0], n1,
                       duration_avg=e[2]['duration_avg'],
                       n_vehicles=e[2]['n_vehicles'],
                       d=e[2]['d'], # We keep the original distance, which is not exactly right
                       route_I_counts=e[2]['route_I_counts'],
                       shape_id=e[2]['shape_id'],
                       direction_id=e[2]['direction_id'],
                       headsign=e[2]['headsign'])
    # Retain original ID before merging
    G.nodes[n1]['original_ids'] += G.nodes[n2]['original_ids']
    # Remove node
    G.remove_node(n2)


def merge_stops_with_same_name(G, delta=100, excepted=[]):
    """Merge stops that share the same name and are closer to delta meters."""
    # Dataframe of stops
    aux = list(zip(*G.nodes(data=True)))
    df_stops = pd.DataFrame(aux[1], index=aux[0]).reset_index()
    # Backup original graph
    G_res = G.copy()
    # Merge stations that share a name
    aux = list(df_stops.groupby('name').index.apply(list))
    aux2 = [a for a in aux if len(a) > 1]
    # Merge only nodes that are at most 100m away from the first node with the same name
    aux3 = []
    for group in aux2:
        clean_group = [group[0]]
        for n in group[1:]:
            if (not group[0] in excepted) and (not n in excepted):
                if distance(G, group[0], n) <= delta:
                    clean_group.append(n)
        if len(clean_group) > 1:
            aux3.append(clean_group)
    for repeated in aux3:
        for i in repeated[1:]:
            print(f"Merged {G_res.nodes[repeated[0]]['name']} — {G_res.nodes[i]['name']}")
            merge_nodes(G_res, repeated[0], i)
    return G_res


def check_islands(G):
    islands = list(nx.isolates(G))
    if islands:
        print(f'Found the following disconnected nodes: {islands}', flush=True)
        if input('Delete these nodes? (y/n)') == 'y':
            G.remove_nodes_from(islands)
            print(f'Removed the following disconnected nodes: {islands}')
        else:
            print('Islands were not removed. Make sure to manually create connecting edges with the appropriate labels')
    else:
        print('No disconnected nodes found')


def plot_graph_for_merge(G, n1, n2, delta=0.05):
    """Plot graph zoomed to stops n1 and n2, which are plotted with big red circles"""
    clear_output(wait=True)
    p = figure(height=600, width=950, toolbar_location='below',
               tools='pan, wheel_zoom, box_zoom, reset, save')
    # Build dictionary of node positions for visualizations
    pos_dict = {}
    for i, d in G.nodes(data=True):
        pos_dict[int(i)] = (float(d['lon']), float(d['lat']))
    # Plot updated graph
    graph = from_networkx(G, layout_function=pos_dict)
    # Create virtual graph with the two stops
    G_stops = nx.Graph()
    G_stops.add_node(n1)
    G_stops.add_node(n2)
    pos_dict_2 = {}
    pos_dict_2[n1] = pos_dict[n1]
    pos_dict_2[n2] = pos_dict[n2]
    graph_stops = from_networkx(G_stops, layout_function=pos_dict_2)
    p.add_tools(HoverTool(tooltips=[('index', '@index'), ('name', '@name')],
                          renderers=[graph.node_renderer, graph_stops.node_renderer]))
    graph_stops.node_renderer.glyph = Circle(fill_color = 'red', size=8)
    p.renderers.append(graph)
    p.renderers.append(graph_stops)
    # Title
    p.title = f"{G.nodes[n1]['name']} <-> {G.nodes[n2]['name']}"
    p.title.text_font_size = '10pt'
    p.title.align = 'center'
    # Zoom
    p.y_range = Range1d(min(G.nodes[n1]['lat'], G.nodes[n2]['lat']) - delta,
                        max(G.nodes[n1]['lat'], G.nodes[n2]['lat']) + delta)
    p.x_range = Range1d(min(G.nodes[n1]['lon'], G.nodes[n2]['lon'] - delta),
                        max(G.nodes[n1]['lon'], G.nodes[n2]['lon']) + delta)
    p.toolbar.active_scroll = p.select_one(WheelZoomTool)
    show(p)
    while True:
        ans = input('Merge? (y/n)')
        if ans == 'y':
            print(f"Merged {G.nodes[n1]['name']} - {G.nodes[n2]['name']}")
            merge_nodes(G, n1, n2)
            break
        elif ans == 'n':
            break


def merge_recommender(G, 
                      string_match=75, 
                      stop_distance=500):
    """Iteratively suggest stops to merge with names closer than string_match (0,100)
    and not farther away than 'distance' meters. Prompt y/n from user and merge or not."""
    # Dataframe of stops
    aux = list(zip(*G.nodes(data=True)))
    df_stops = pd.DataFrame(aux[1],index=aux[0]).reset_index()
    stop_names = list(df_stops[['index','name']].itertuples(index=False, name=None))
    for i, tuple_i in enumerate(stop_names):
        index_i, name_i = tuple_i
        for index_j, name_j in stop_names[i+1:]:
            # Check if node still exists (may have been merged already)
            if index_i in G.nodes() and index_j in G.nodes(): 
                # If names are similar
                if fuzz.ratio(name_i,name_j) > string_match: 
                    if distance(G, index_i, index_j) <=  stop_distance:
                        plot_graph_for_merge(G, index_i, index_j)


def manual_merge(G, jupyter_url='http://localhost:8888'):
    def bkapp(doc):
        # Build dictionary of node positions for visualizations
        pos_dict = {}
        for i, d in G.nodes(data=True):
            pos_dict[int(i)] = (float(d['lon']), float(d['lat']))
        # source
        global graph
        graph = from_networkx(G, layout_function=pos_dict)

        def create_figure():
            back_map = False
            if back_map:
                p = gmap(MAPS_API_KEY, GMapOptions(lat=list(G.nodes(data=True))[0][1]['lat'], 
                                                   lng=list(G.nodes(data=True))[0][1]['lon'], 
                                                   map_type='roadmap', zoom=11))
            else:
                p = figure(height=600, width=950, toolbar_location='below',
                           tools='pan, tap, wheel_zoom, box_zoom, box_select, reset, save')
            # Zoom is active by default
            p.toolbar.active_scroll = p.select_one(WheelZoomTool)
            # Plot updated graph
            global graph
            # Build dictionary of node positions for visualizations
            pos_dict_2 = {}
            for i, d in G.nodes(data=True):
                pos_dict_2[int(i)] = (float(d['lon']), float(d['lat']))
            graph = from_networkx(G, layout_function=pos_dict_2)
            # Hover tool
            p.add_tools(HoverTool(tooltips=[('index', '@index'), ('name', '@name')],
                                  renderers=[graph.node_renderer]))
            # Formatting
            graph.node_renderer.selection_glyph = Circle(fill_color='red')
            graph.node_renderer.glyph = Circle(size=8)
            p.renderers.append(graph)
            return p

        bt = Button(label='Merge nodes')
        # bt2 = Button(label='Delete edge')

        def change_click():
            #Get selected stops
            indices = graph.node_renderer.data_source.selected.indices
            if len(indices) == 2:
                n1 = graph.node_renderer.data_source.data['index'][indices[0]]
                n2 = graph.node_renderer.data_source.data['index'][indices[1]]
                name_n1 = graph.node_renderer.data_source.data['name'][indices[0]]
                name_n2 = graph.node_renderer.data_source.data['name'][indices[1]]
                merge_nodes(G, n1, n2)
                print(f'Merged {name_n1} - {name_n2}')
                p = figure(tools='reset,pan,wheel_zoom,lasso_select')
                layout.children[0] = create_figure()
                return p
            else:
                print('Select two nodes to merge')

        bt.on_click(change_click)
        layout = column(create_figure(),bt)
        doc.add_root(layout)
    show(bkapp, notebook_url=jupyter_url)


def sanity_check(G):
    print('Checking self loops...')
    for n in G.edges:
        if n[0] == n[1]:
            print(f'Self loop found: {n[0]}. Consider removing it manually.')
    print('---')
    print('Checking links only on one direction...')
    for n in G.edges: 
        if (n[1], n[0]) not in G.edges:
            print('Edge exists only in one direction: {} (node {}) to {} (node {}'
                  .format(G.nodes[n[0]]['name'], n[0], G.nodes[n[1]]['name'], n[1]))
    print('---')
    print('Checking edges with invalid duration...')
    for n in G.edges(data=True):
        if n[2]['duration_avg'] <= 0:
           message = f'Edge ({n[0]}, {n[1]}) has duration_avg of {n[2]["duration_avg"]}.'
           if (n[1], n[0]) in G.edges() and G[n[1]][n[0]]['duration_avg'] > 0:
               message += 'Consider setting up the duration manually, perhaps using the '
               message += 'duration of the opposite edge ({}, {}) = {}'.format(
                   n[1], n[0], G[n[1]][n[0]]['duration_avg'])
           else:
               message += 'Consider setting up the duration manually.'
           print(message)
    print('---')
    print('Number of edges: ', len(G.edges()))
    print('Number of nodes: ', len(G.nodes()))
    ncomp = nx.number_strongly_connected_components(G)
    print(f'Number of strongly connected components: {ncomp}')

# def save_graph(G,path):
#     G_res = nx.convert_node_labels_to_integers(G)
#     with open(path, 'wb') as f:
#         pickle.dump(G_res, f)
    

# def load_graph(path):
#     with open(path, 'rb') as f:
#         G = pickle.load(f)
#         return G

# Method to get the routeids of the subway lines
def get_routes_for_mode(g, mode):
    cur = g.conn.cursor()
    subway = 1
    routes = list()
    # Get all routes that are of the subway type (type = 1)
    mode = mode_from_string(mode)
    t_results = cur.execute(f'SELECT route_I FROM routes WHERE type={mode}')
    route_list = t_results.fetchall()
    for r in route_list:
        routes.append(r[0])
    return routes

# Method to get a corresponding color for each route
def get_color_per_route(graph, routes):
    colors = dict()
    for route in routes:
        cur = graph.conn.cursor()
        c_results = cur.execute(f'SELECT color FROM routes WHERE route_I={route}')
        color = c_results.fetchone()
        colors[route] = color[0]
    return colors

# Method creating P-space with inputs gtfs-data (g), L-Space (L), and time period of L-space (time)
def P_space(g, L, mode, start_hour=5, end_hour=24, dir_indicator=None):
    """
    Create P-space graph given:
    g: gtfs feed
    L: L-space
    Optional:
        start_hour: start hour considered when building L-space. Defaults to 5 am
    end_hour: end hour considered when building L-space. Defaults to midnight.
        dir_indicator: override which indicator direction_id,headsign,or shape_id should be used.
    """
    assert isinstance(start_hour, int) and isinstance(end_hour, int), 'Start/end hours should be int'
    assert start_hour >= 0 and end_hour >= 0, 'Start/end hour should be larger or equal to 0'
    assert start_hour <= 24 and end_hour <= 24, 'Start/end hour should be smaller or equal to 24'
    assert start_hour < end_hour, 'Start hour should be smaller than end hour'
    
    time = end_hour - start_hour
    # Create a list of backup colors
    backup_colors = (
        '0000FF', '008000', 'FF0000', '00FFFF', 'FF00FF', 'FFFF00', '800080',
        'FFC0CB', 'A52A2A', 'FFA500', 'FF7F50', 'ADD8E6', '00FF00', 'E6E6FA',
        '40E0D0', '006400', 'D2B48C', 'FA8072', 'FFD700',
    )
    # Create the P-space graph with the nodes from L-space
    P_G = nx.DiGraph()
    P_G.add_nodes_from(L.nodes(data=True))
    # Get a list of all routes of the network, with corresponding colors
    routes = get_routes_for_mode(g, mode)
    # Exception for Vienna metro network
    if g.get_location_name() == 'vienna' and mode == 'Subway':
        routes = routes[::2]
    colors = get_color_per_route(g, routes)
    if not dir_indicator:
        # Check to see if direction/headsign/shape exists
        dir_indicator = 'empty'
        edge_it = iter(L.edges(data=True))
        check_edge = next(edge_it, None)
        if check_edge:
            if check_edge[2]['direction_id']:
                dir_indicator = 'direction_id'    
            elif check_edge[2]['headsign']:
                dir_indicator = 'headsign'
            elif check_edge[2]['shape_id']:
                dir_indicator = 'shape_id'
            # Make some exceptions
            if g.get_location_name() == 'bilbao' and mode == 'Subway':
                dir_indicator = 'headsign'
            if (g.get_location_name() == 'philadelphia') and mode == 'Subway':
                dir_indicator = 'headsign'
            if g.get_location_name() == 'amsterdam' and mode == 'Subway':
                dir_indicator = 'headsign'
            if g.get_location_name() == 'paris' and mode_from_string(mode) ==2:
                dir_indicator = 'headsign'
    print(f'Using {dir_indicator} field as indicator for the direction of routes')
    # Loop through all routes
    for iter_n,r in enumerate(routes):
        # Get the route color (or a backup if unavailable)
        color = colors[r]
        if not color or len(color) != 6 \
           or g.get_location_name() == 'nuremburg' and mode == 'Subway':
            color = backup_colors[iter_n % len(backup_colors)]
        # Create a set of the directions/headsigns/shapes for this route
        dirs = set()
        for e in L.edges(data=True):
            if r in e[2]['route_I_counts']:
                for h in e[2][dir_indicator].keys():
                    dirs.add(h)
        # Create a subgraph for each direction and add the edges to P-space
        for d in dirs:
            # Create an empty (directional) subgraph
            sub = nx.DiGraph()
            # Add all edges (and corresponding nodes) that are on this route and direction
            for e in L.edges(data=True):
                if r in e[2]['route_I_counts'] and d in e[2][dir_indicator]:
                    sub.add_edges_from([(e)])
            # Loop through all nodes in the subgraph that have paths between them
            for n1 in sub:
                for n2 in sub:
                    if n1 != n2 and nx.has_path(sub, n1, n2):
                        aux_out = [(a, b, c) for a, b, c in sub.out_edges(n1, data=True)
                                   if a in nx.shortest_path(sub, n1, n2) and
                                   b in nx.shortest_path(sub, n1, n2)]
                        out_e = aux_out[0]
                        aux_in = [(a, b, c) for a, b, c in sub.in_edges(n2, data=True)
                                  if a in nx.shortest_path(sub, n1, n2) and
                                  b in nx.shortest_path(sub, n1, n2)]
                        in_e = aux_in[0]
                        # Take the lowest number of vehicles between the two edges
                        veh_out = out_e[2]['route_I_counts'][r]
                        veh_in = in_e[2]['route_I_counts'][r]
                        veh = min(veh_out, veh_in)
                        # Compute the average waiting time
                        veh_per_hour = veh / time
                        max_wait = 60 / veh_per_hour
                        avg_wait = max_wait / 2
                        # If the edge already exists, append the values
                        if P_G.has_edge(n1, n2):
                            # Change the color to black to signify a shared edge
                            P_G[n1][n2]['edge_color'] = '#000000'
                            # Add the vehicles per hour for this route + direction to the wait_dir
                            if r not in P_G[n1][n2]['veh']:
                                P_G[n1][n2]['veh'][r] = {d: veh_per_hour}
                            else:
                                P_G[n1][n2]['veh'][r][d] = veh_per_hour
                            # Update the average waiting time to be the total of all routes' waiting times
                            tot_veh = 0
                            for ro in P_G[n1][n2]['veh']:
                                for di in P_G[n1][n2]['veh'][ro]:
                                    tot_veh = tot_veh + P_G[n1][n2]['veh'][ro][di]
                            P_G[n1][n2]['avg_wait'] = (60 / tot_veh) / 2
                        else:
                            P_G.add_edge(n1, n2, veh={r: {d: veh_per_hour}}, 
                                         avg_wait=avg_wait, edge_color='#'+str(color))
    return P_G


def k_shortest_paths(G, source, target, k, weight=None):
    try:
        return list(islice(nx.shortest_simple_paths(G, source, target, weight=weight), k))
    except Exception:
        return []


def get_routes_dirs(P_space, n1, n2):
    """Given a P-space network and two nodes, retrieves all routes and corresponding directions"""
    orig_routes = []
    for ro in P_space[n1][n2]['veh']:
        for dr in P_space[n1][n2]['veh'][ro]:
            orig_routes.append(str(ro) + str(dr))
    return orig_routes


def get_all_GTC(L_space, P_space, k, wait_pen, transfer_pen):
    # Dict containing all shortest path information, indexed by node pairs
    shortest_paths = {}
    # Loop through all node combinations
    for n1 in L_space.nodes:
        if n1 % 10 == 0:
            print(f'{n1}/{len(L_space.nodes)}')
        shortest_paths[n1] = {}
        for n2 in L_space.nodes:
            if n1 == n2:
                continue
            # Retrieve the k shortest paths from L-space, using travel time/duration as a weight
            k_paths = k_shortest_paths(L_space, n1, n2, k,'duration_avg')
            # Two auxiliary datastructures to store the different shortest paths and corresponding attributes
            tt_paths = []
            only_tts = []
            # Loop through all k-shortest paths and record the different travel time components
            for p in k_paths:
                # Record the original route/line taken from the origin node
                possible_routes = get_routes_dirs(P_space, p[0], p[1])
                # Initialize the distance, (in-vehicle) travel time, waiting time and number of transfers as 0
                dist, tt, wait, tf = 0, 0, 0, 0
                # Record the list of transfer stations, having the origin as the first 'transfer station'
                t_stations = [n1]
                # Check the routes of all successive node pairs in the path,
                # if all routes of the original edge are not on the next edge, a transfer must have been made OR
                # if all routes of the previous edge are not on the next edge, a transfer must have been made
                # Route(s) on that edge become new route.
                # Also update the in-vehicle travel time for each edge passed.
                for l1, l2 in zip(p[::1], p[1::1]):
                    tt += L_space[l1][l2]['duration_avg']
                    dist += L_space[l1][l2]['d']
                    routes = get_routes_dirs(P_space, l1, l2)
                    possible_routes = set(possible_routes).intersection(set(routes))
                    if not possible_routes:
                        possible_routes = routes
                        tf += 1
                        t_stations.append(l1)
                # Add the destination node as the final transfer station
                t_stations.append(n2)
                # Change travel time to minutes and round to whole minutes
                tt = round(tt / 60)
                # Find the waiting times belonging to the different routes taken by looping through all transfer station pairs
                for t1, t2 in zip(t_stations[::1], t_stations[1::1]):
                    wait += P_space[t1][t2]['avg_wait']
                # Round the waiting time to whole minutes
                wait = round(wait)
                # Calculate the total travel time, take a penalty for the waiting time and per transfer
                transfer_cost = sum([transfer_pen[i] if i < len(transfer_pen) else 
                                     transfer_pen[-1] for i in range(tf)])
                total_tt = tt + wait * wait_pen + transfer_cost
                only_tts.append(total_tt)
                tt_paths.append(dict(path=p, GTC=total_tt, in_vehicle=tt,
                                     waiting_time=wait, n_transfers=tf,
                                     traveled_distance=dist))
            if k_paths:
                shortest_paths[n1][n2] = sorted(tt_paths, key=lambda x: x['GTC'])
            else:
                shortest_paths[n1][n2] = []
    print('All GTC computed!')
    return shortest_paths
    
    
def average_waiting_time_per_line_per_direction(P):
    routes = {}
    for e in P.edges(data=True):
        for r in e[2]['veh']:
            for d in e[2]['veh'][r]:
                if r not in routes:
                    routes[r] = {}
                if d not in routes[r]:
                    routes[r][d] = []
                routes[r][d].append(e[2]['veh'][r][d])
    #Average all number of vehicles per line per direction
    #Compute waiting time as half the headway
    for r in routes:
        for d in routes[r]:
            routes[r][d] = (60 / mean(routes[r][d])) / 2
    return routes

    
def average_speed_network(L):
    speeds = []
    for e in L.edges(data=True):
        dist_km = e[2]['d'] / 1000
        time_hr = e[2]['duration_avg'] / 3600
        speeds.append(dist_km / (time_hr + 1e-6))
    return mean(speeds)

    
def get_events(gtfs_feed, mode, start_hour=5, end_hour=24):
    """Gets all events for the most suitable day from GTFS data.
    ---
    Parameters:
    - gtfs_feed: a gtfspy gtfs feed object
    - mode: string corresponding to the transport mode that we want to consider
    - start_hour: integer with the earliest hour we want to consider (in 0..24)
    - end_hour: integer with the latest hour we want to consider (in 0..24, larger that start_hour)
    """
    assert isinstance(start_hour, int) and isinstance(end_hour, int), 'Start/end hours should be int'
    assert start_hour >= 0 and end_hour >= 0, 'Start/end hour should be larger or equal to 0'
    assert start_hour <= 24 and end_hour <= 24, 'Start/end hour should be smaller or equal to 24'
    assert start_hour < end_hour, 'Start hour should be smaller than end hour'
    if not (mode in mode_code and mode_from_string(mode) in gtfs_feed.get_modes()):
        raise AssertionError('Mode is not available for the city')
    
    day_start = gtfs_feed.get_suitable_date_for_daily_extract(ut=True)
    range_start = day_start + start_hour * 3600
    range_end = day_start + end_hour * 3600 - 1
    start_time = gtfs_feed.unixtime_seconds_to_gtfs_datetime(range_start)
    end_time = gtfs_feed.unixtime_seconds_to_gtfs_datetime(range_end)
    print(f'Considering trips between {start_time} and {end_time}')
    events = gtfs_feed.get_transit_events(
        start_time_ut=range_start,
        end_time_ut=range_end,
        route_type=mode_from_string(mode))
    return events
