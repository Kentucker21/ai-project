# Strip surrounding single-quotes from Prolog atom strings (e.g. "'Kingston'" -> "Kingston")
def to_plain_value(value):
    text = str(value)
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    return text


# Convert a raw Prolog path list to a plain Python list of place name strings
def normalize_path(path_values):
    return [to_plain_value(item) for item in path_values]


# Given an ordered list of nodes on a route, look up the edge details for each leg.
# Returns a list of dicts with road attributes (distance, condition, travel time, etc.)
def build_route_edge_details(path_nodes, edges):
    if not path_nodes or len(path_nodes) < 2:
        return []

    # Build a lookup dict so we can find an edge by (from, to) in O(1)
    edge_lookup = {}
    for edge in edges:
        key = (edge['from'], edge['to'])
        edge_lookup[key] = edge

    route_edges = []
    for index in range(len(path_nodes) - 1):
        start = path_nodes[index]
        end = path_nodes[index + 1]
        edge = edge_lookup.get((start, end))
        if not edge:
            continue

        route_edges.append({
            'from': start,
            'to': end,
            'distance': edge['distance'],
            'roadType': edge['roadType'],
            'condition': edge['condition'],
            'potholeDepth': edge.get('potholeDepth', '0'),
            'travelTime': edge['travelTime'],
            'status': edge['status'],
            'direction': edge.get('direction', 'two_way')
        })

    return route_edges


# Query Prolog for all places and roads and build the graph data the map needs.
# Returns (nodes, edges) where nodes are dicts with position/type info
# and edges are dicts with road attributes.
def build_road_network_graph(prolog):
    nodes = {}
    edges = []
    seen_edges = set()  # prevents adding the same edge twice

    # Build place type and coordinate lookups from Prolog
    type_map = {}
    for row in prolog.query("place_type(Name, Type)"):
        type_map[to_plain_value(row['Name'])] = to_plain_value(row['Type']).lower()

    coord_map = {}
    for row in prolog.query("coords(Name, X, Y)"):
        coord_map[to_plain_value(row['Name'])] = {
            'x': int(row['X']),
            'y': int(row['Y'])
        }

    # Create a node entry for every place, merging in its coordinates and type
    for place in prolog.query("place(Name)"):
        name = to_plain_value(place['Name'])
        pos = coord_map.get(name, {})
        nodes[name] = {'id': name, 'label': name, 'placeType': type_map.get(name, 'parish'), **pos}

    # Create edge entries from every road/9 fact in Prolog
    for road in prolog.query("road(From,To,Distance,Type,Condition,PotholeDepth,TravelTime,Status,Direction)"):
        start = to_plain_value(road['From'])
        end = to_plain_value(road['To'])
        distance = to_plain_value(road['Distance'])
        road_type = to_plain_value(road['Type'])
        condition = to_plain_value(road['Condition'])
        pothole_depth = to_plain_value(road['PotholeDepth'])
        travel_time = to_plain_value(road['TravelTime'])
        status = to_plain_value(road['Status'])
        direction = to_plain_value(road['Direction'])

        # Add nodes for any place that appears in a road but has no place/1 fact
        if start not in nodes:
            nodes[start] = {'id': start, 'label': start, 'placeType': type_map.get(start, 'parish')}
        if end not in nodes:
            nodes[end] = {'id': end, 'label': end, 'placeType': type_map.get(end, 'parish')}

        edge_data = {
            'from': start,
            'to': end,
            'distance': distance,
            'roadType': road_type,
            'condition': condition,
            'potholeDepth': pothole_depth,
            'travelTime': travel_time,
            'status': status,
            'direction': direction
        }

        # Add the forward edge if not already seen
        forward_key = (start, end)
        if forward_key not in seen_edges:
            edges.append(edge_data)
            seen_edges.add(forward_key)

        # For two_way roads, also add the reverse edge
        if direction == 'two_way':
            reverse_key = (end, start)
            if reverse_key not in seen_edges:
                reverse_edge = dict(edge_data)
                reverse_edge['from'] = end
                reverse_edge['to'] = start
                edges.append(reverse_edge)
                seen_edges.add(reverse_key)

    return list(nodes.values()), edges
