import xml.etree.ElementTree as ET
from xml.dom import minidom

class TrafficLightLogicPhase:
    def __init__(self, duration, state):
        self._duration = duration
        self._state = state

class TrafficLightLogic:
    def __init__(self, type, programId, offset, phases):
        self._type = type
        self._programId = programId
        self._offset = offset
        self._phases = phases

class Junction:
    def __init__(self, id, type, x, y, incLanes, intLanes, logic):
        self._id = id
        self._type = type
        self._x = x
        self._y = y
        self._incLanes = incLanes.split(" ")
        self._intLanes = intLanes.split(" ")
        self._logif = logic

    def get_id(self):
        return self._id

    def get_type(self):
        return self._type

    def get_edges(self):
        edges = set()
        for lane in self._incLanes:
            edge = lane.rsplit('_', 1)[0]
            edges.add(edge)
        return edges

    def __repr__(self):
        return "Id: " + self._id + ", Type: " + self._type

class Lane:
    def __init__(self, id, index, speed, length, shape):
        self._id = id
        self._index = index
        self._speed = speed
        self._length = length
        self._shape = shape

    def get_id(self):
        return self._id


class Edge:
    def __init__(self, id, source, destination, priority, lanes):
        self._id = id
        self._source = source
        self._destination = destination
        self._priority = priority
        self._lanes = lanes
        self._connectionTo = dict()

    def get_id(self):
        return self._id

    def get_source(self):
        return self._source

    def get_destination(self):
        return self._destination

    def add_connection_to(self, edge):
        self._connectionTo[edge.get_id()] = edge

    def has_connection_to(self, edge_id):
        if edge_id==self._id:
            return False
        if edge_id in self._connectionTo.keys():
            return True
        for edge in self._connectionTo.values():
            if edge.has_connection_to(edge_id):
                return True
        return False

    # returns set of lists
    def routes_to(self):
        routes_list = list()
        if len(self._connectionTo)==0:
            return [self._id]
        for destination_edge in self._connectionTo.values():
            routes_list.append([self._id] + destination_edge.routes_to())
        return routes_list

    def get_lanes(self):
        return self._lanes

class TrafficNetwork:
    def __init__(self, net_xml):
        self._net_xml = net_xml
        self._net_tree = ET.parse(self._net_xml)
        self._net_root = self._net_tree.getroot()
        self._edges = dict()
        self.junctions = dict()

    def _parse_junctions(self):
        for junction in self._net_root.findall('junction'):
            if 'function' in junction.attrib:
                continue
            junction_logic = None
            for logic in self._net_root.findall('tlLogic'):
                phases = list()
                if logic.get('id')==junction.get('id'):
                    for phase in logic.findall("phase"):
                        phases.append(TrafficLightLogicPhase(phase.get('duration'), phase.get('state')))
                junction_logic = TrafficLightLogic(logic.get('type'), logic.get('programId'), logic.get('offset'), phases)
            self.junctions[junction.get('id')] = (Junction(junction.get('id'),
                                                           junction.get('type'),
                                                           junction.get('x'),
                                                           junction.get('y'),
                                                           junction.get('incLanes'),
                                                           junction.get('intLanes'),
                                                           junction_logic))

    def _parse_edges(self):
        for edge in self._net_root.findall('edge'):
            if 'function' in edge.attrib:
                continue
            lanes_list = list()
            for lane in edge.findall('lane'):
                lanes_list.append(Lane(lane.get('id'),
                                       lane.get('index'),
                                       lane.get('speed'),
                                       lane.get('length'),
                                       lane.get('shape')))
            self._edges[edge.get('id')] = (Edge(edge.get('id'),
                                                edge.get('from'),
                                                edge.get('to'),
                                                edge.get('priority'),
                                                lanes_list))

    def _parse_connections(self):
        for connection in self._net_root.findall('connection'):
            if connection.get('from') not in self._edges.keys():
                continue
            edge_from = self._edges[connection.get('from')]
            edge_to = self._edges[connection.get('to')]
            edge_from.add_connection_to(edge_to)

    def parse(self):
        self._parse_junctions()
        self._parse_edges()
        self._parse_connections()

    def start_edges(self):
        end_junctions = [junction.get_id() for junction in self.junctions.values() if junction.get_type()=='dead_end']
        start_edges = [edge.get_id() for edge in self._edges.values() if (edge.get_source() in end_junctions)]
        return start_edges

    def find_routes(self):
        routes = list()
        start_edges = self.start_edges()
        for edge_id in start_edges:
            routes = routes + self._edges[edge_id].routes_to()
        return routes

    def edge_lanes(self, edge):
        return self._edges[edge].get_lanes()


class TrafficGenerator:
    def __init__(self, network):
        self._network = network

    def prettify(self, elem):
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def generate_types(self):
        types = list()
        types.append(ET.Element('vType', id="car", vClass="passenger", color="255,255,255"))
        return types

    def generate_routes(self):
        routes = list()
        for route in self._network.find_routes():
            edges = ' '.join(route)
            element = ET.Element('route', id=edges.replace(' ', '_'), edges=edges)
            routes.append(element)
        return routes

    def time_probability(self, hour):
        if hour < 6 :
            return 1
        if hour < 7 :
            return 4
        if hour < 9 :
            return 15
        if hour < 12:
            return 7
        if hour < 17:
            return 9
        if hour < 19:
            return 7
        if hour < 24:
            return 2
        return 1

    def probability_function(self, vtype, route, hour):
        start_edge_lanes = len(self._network.edge_lanes(route.split(' ')[0]))
        #end_edge_lanes = len(self._network.edge_lanes(route.split(' ')[1:]))
        end_edge_lanes = 1
        return start_edge_lanes * end_edge_lanes * self.time_probability(hour)

    def generate_flow(self):
        flows = list()
        routes = self._network.find_routes()
        one_hour = 7200
        for start_hour in range(0, 24):
            for route in routes:
                route = ' '.join(route)
                vtype = "car"
                # probability function should return number of vehicles from defined type, defined route and for defined time
                vehicles_per_hour = self.probability_function(vtype, route, start_hour)
                #vehicles_per_hour = 5

                element = ET.Element('flow',type=vtype, id=vtype+"_"+route.replace(' ', '_')+"_"+str(start_hour), route=route.replace(' ', '_'), begin=str(one_hour*start_hour), end=str(one_hour*start_hour+one_hour), vehsPerHour=str(vehicles_per_hour))
                flows.append(element)
        return flows

    def generate_xml(self, name):
        root = ET.Element('routes')
        root.extend(self.generate_types())
        root.extend(self.generate_routes())
        root.extend(self.generate_flow())
        tree= ET.ElementTree(root)
        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ", encoding='UTF-8')
        with open(name, "w") as f:
            f.write(str(xmlstr.decode('UTF-8')))
            f.close()

        #print(self.prettify(root))




if __name__ == '__main__':
    network_file = '../Networks/simple/simple.net.xml'
    flow_file = '../Networks/simple/flows/simple.rou.xml'
    network = TrafficNetwork(network_file)
    network.parse()
    generator = TrafficGenerator(network)
    generator.generate_xml(flow_file)
