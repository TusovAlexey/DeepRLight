import xml.etree.ElementTree as ET
from xml.dom import minidom
from sumolib import checkBinary, net
import traci


class TrafficNetwork:
    def __init__(self, net_xml):
        self.network = net.readNet(net_xml)
        self.junctions = None

    def parse(self):
        self.junctions = [node for node in self.network.getNodes() if str(node.getType()).startswith('traffic_light')]
        self.start_edges = [edge for edge in self.network.getEdges(withInternal=False) if len(edge.getIncoming())==0]
        self.end_edges = [edge for edge in self.network.getEdges(withInternal=False) if len(edge.getOutgoing()) == 0]

    def find_routes(self):
        self.routes = []
        for source in self.start_edges:
            self.routes += [(source, destination) for destination in self.end_edges if source.getFromNode()!=destination.getToNode()]
        return self.routes


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

    def probability_function(self, vtype, start, hour):
        start_edge_lanes = start.getLaneNumber()
        #end_edge_lanes = len(self._network.edge_lanes(route.split(' ')[1:]))
        end_edge_lanes = 1
        return start_edge_lanes * end_edge_lanes * self.time_probability(hour)

    def generate_flow(self):
        flows = list()
        routes = self._network.find_routes()
        one_hour = 3600
        for start_hour in range(0, 24):
            for start, end in routes:
                vtype = "car"
                # probability function should return number of vehicles from defined type, defined route and for defined time
                vehicles_per_hour = self.probability_function(vtype, start, start_hour)
                #vehicles_per_hour = 5

                element = ET.Element('flow',attrib={'type':vtype,
                                                    'id':vtype+"_"+start.getID()+"_"+end.getID()+"_"+str(start_hour),
                                                    'from': start.getID(),
                                                    'to': end.getID(),
                                                    'begin': str(one_hour*start_hour),
                                                    'end': str(one_hour*start_hour+one_hour),
                                                    'number' : vehicles_per_hour})
                flows.append(element)
        return flows

    def generate_xml(self, name):
        root = ET.Element('routes')
        root.extend(self.generate_types())
        #root.extend(self.generate_routes())
        root.extend(self.generate_flow())
        tree= ET.ElementTree(root)
        #xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ", encoding='UTF-8')
        #with open(name, "w") as f:
        #    f.write(str(xmlstr.decode('UTF-8')))
        #    f.close()

        print(self.prettify(root))



if __name__ == '__main__':
    network_file = '../Networks/simple/simple.net.xml'
    flow_file = '../Networks/simple/flows/simple.rou.xml'
    network = TrafficNetwork(network_file)
    network.parse()
    generator = TrafficGenerator(network)
    generator.generate_xml(flow_file)
