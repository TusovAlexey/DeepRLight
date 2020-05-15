import random as rand
import xml.etree.ElementTree as ET
from xml.dom import minidom
from sumolib import checkBinary, net
import traci
import matplotlib.pyplot as plt
#from pylab import *
import numpy as np
from scipy import stats

class TrafficNetwork:
    def __init__(self, net_xml, routes_xml):
        self.network = net.readNet(net_xml)
        self.routes = set([node.attributes['edges'].value for node in minidom.parse(routes_xml).getElementsByTagName('route')])
        self.junctions = None

    def parse(self):
        self.junctions = [node for node in self.network.getNodes() if str(node.getType()).startswith('traffic_light')]
        self.start_edges = [edge for edge in self.network.getEdges(withInternal=False) if len(edge.getIncoming())==0]
        self.end_edges = [edge for edge in self.network.getEdges(withInternal=False) if len(edge.getOutgoing()) == 0]

    def find_routes(self):
        start = [edge.getID() for edge in self.start_edges]
        end = [edge.getID() for edge in self.end_edges]
        routes = []
        for route in self.routes:
            edges = route.split(" ")
            start_point = edges[0]
            end_point = edges[-1]
            if start_point in start and end_point in end:
                routes.append(route)
        return routes

    def get_lanes_number(self, edge):
        return self.network.getEdge(edge).getLaneNumber()

class VType:
    default = {'passenger': {'minGap_min': 1.0, 'minGap_max': 1.5,
                             'length_min': 3.0, 'length_max': 5.0,
                             'accel_min': 2.6, 'accel_max': 3.0,
                             'decel_min': 4.0, 'decel_max': 7.5,
                             'maxSpeed_min': 30.0, 'maxSpeed_max': 40.0,
                             'sigma_min': 0.35, 'sigma_max': 0.5,
                             'guiShape': 'passenger',
                             'perHour' : 1},
               'emergency': {'minGap_min': 1.0, 'minGap_max': 1.5,
                             'length_min': 3.0, 'length_max': 5.0,
                             'accel_min': 2.6, 'accel_max': 3.0,
                             'decel_min': 4.0, 'decel_max': 7.5,
                             'maxSpeed_min': 30.0, 'maxSpeed_max': 40.0,
                             'sigma_min': 0.35, 'sigma_max': 0.5,
                             'guiShape': 'emergency',
                             'perHour' : 0.1},
               'truck':     {'minGap_min': 1.0, 'minGap_max': 1.5,
                             'length_min': 10.0, 'length_max': 15.0,
                             'accel_min': 1.0, 'accel_max': 2.0,
                             'decel_min': 4.0, 'decel_max': 7.5,
                             'maxSpeed_min': 30.0, 'maxSpeed_max': 40.0,
                             'sigma_min': 0.5, 'sigma_max': 0.8,
                             'guiShape': 'truck',
                             'perHour' : 0.2}
               }
    def __init__(self, id, vclass):
        self.parsed = dict()
        self.parsed['id'] = str(vclass) + "_" + str(id)
        self.parsed['vClass'] = str(vclass)
        self.parsed['accel'] = str(round(rand.uniform(VType.default[vclass]['accel_min'], VType.default[vclass]['accel_max']), 2))
        self.parsed['decel'] = str(round(rand.uniform(VType.default[vclass]['decel_min'], VType.default[vclass]['decel_max']), 2))
        self.parsed['minGap'] = str(round(rand.uniform(VType.default[vclass]['minGap_min'], VType.default[vclass]['minGap_max']), 2))
        self.parsed['length']  = str(round(rand.uniform(VType.default[vclass]['length_min'], VType.default[vclass]['length_max']), 2))
        self.parsed['maxSpeed'] = str(round(rand.uniform(VType.default[vclass]['maxSpeed_min'], VType.default[vclass]['maxSpeed_max']), 2))
        self.parsed['sigma'] = str(round(rand.uniform(VType.default[vclass]['sigma_min'], VType.default[vclass]['sigma_max']), 2))
        self.parsed['guiShape'] = str(VType.default[vclass]['guiShape'])


class TrafficGenerator:
    def __init__(self, network):
        self._network = network

    def prettify(self, elem):
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def generate_types(self):
        typeElements = list()
        types = list()
        for vclass in VType.default.keys():
            for id in range(0, 1):
                generated = VType(id, vclass).parsed
                types.append(generated)
                typeElements.append(ET.Element('vType', generated))
        return typeElements, types

    def generate_routes(self):
        routes = list()
        for route in self._network.find_routes():
            edges = ' '.join(route)
            element = ET.Element('route', id=edges.replace(' ', '_'), edges=edges)
            routes.append(element)
        return routes

    def time_probability(self, hour):
        if hour < 6 :
            return rand.randint(0, 1)
        if hour < 7 :
            return rand.randint(1, 4)
        if hour < 9 :
            return rand.randint(12, 15)
        if hour < 12:
            return rand.randint(5, 7)
        if hour < 17:
            return rand.randint(7, 10)
        if hour < 19:
            return rand.randint(10, 12)
        if hour < 24:
            return rand.randint(1, 2)
        return 0

    def gen_vehicles_per_hour(self, vtype, start, end, hour):
        factor = 1
        if start.split("_")[0]=='Main':
            factor += 1
        if end.split("_")[0]=='Main':
            factor += 1
        if start.split("_")[0]=='Main' and end.split("_")[0]=='Main':
            factor += 5
        start_edge_lanes = self._network.get_lanes_number(start)
        end_edge_lanes = self._network.get_lanes_number(end)
        vClassParam = VType.default[vtype]['perHour']
        return int(0.25 * factor * start_edge_lanes * vClassParam * end_edge_lanes * self.time_probability(hour))

    def generate_flow(self, types):
        counter = 0
        flows = list()
        routes = self._network.find_routes()
        hours = np.linspace(start=0, stop=23*3600, num=24, dtype=int)
        for start_hour in hours:
            for route in routes:
                for vehicle in types:
                    num_vehicles = self.gen_vehicles_per_hour(vehicle['vClass'], route.split(" ")[0], route.split(" ")[-1], start_hour/3600)
                    departure_times = stats.randint.rvs(start_hour, start_hour+3600, size=num_vehicles)
                    for time in departure_times:
                        vehicle_element = ET.Element('vehicle', attrib={'id': vehicle['id'] + "_" + route.split(" ")[0] + "_" + route.split(" ")[-1]+ "_" + str(time) + "_" + str(counter),
                                                                        'depart': str(time),
                                                                        'type' : vehicle['id']
                                                                        })
                        ET.SubElement(vehicle_element, 'route', edges=route)
                        flows.append(vehicle_element)
                        counter += 1
        flows.sort(key=lambda x: int(x.get('depart')))
        return flows

    def generate_xml(self, name):
        root = ET.Element('routes')
        typeElements, types = self.generate_types()
        root.extend(typeElements)
        #root.extend(self.generate_routes())
        root.extend(self.generate_flow(types))
        tree= ET.ElementTree(root)
        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ", encoding='UTF-8')
        with open(name, "w") as f:
            f.write(str(xmlstr.decode('UTF-8')))
            f.close()


def extractRoutes(file):
    array = []
    with open(file, "r") as ins:
        for line in ins:
            if "<route edges=" in line:
                array.append(line)
    with open(file, "w") as out:
        out.write("<routes>\n")
        for item in array:
            out.write("%s\n" % item)
        out.write("</routes>")


def plot_generated(file):
    array = []
    edges = set()
    types = set()
    vehicles = minidom.parse(file).getElementsByTagName('vehicle')
    for vehicle in vehicles:
        type = vehicle.getAttribute('type').split("_")[0]
        time = int(vehicle.getAttribute('depart'))
        edge = vehicle.getElementsByTagName('route')[0].getAttribute('edges').split(" ")[0]
        array.append((edge, time, type))
        edges.add(edge)
        types.add(type)
    edges_dict = dict()
    edges_types_dict = dict()
    for edge in edges:
        edges_types_dict[edge] = dict()
        edges_dict[edge] = list()
        for type in types:
            edges_types_dict[edge][type] = list()
    for edge, time, type in array:
        edges_types_dict[edge][type].append(time)
        edges_dict[edge].append(time)

    edge_hour = dict()
    labels = None
    for edge in edges_dict.keys():
        edge_hour[edge] = dict()
        time_vector = np.array(edges_dict[edge])
        for start_hour in range(0, 23):
            a = len(np.where(np.logical_and(time_vector >= (start_hour * 3600), time_vector <= ((start_hour + 1) * 3600)))[0])
            edge_hour[edge][str(start_hour) + '-' + str(start_hour+1)] = a
    # Pavel need your help with plotting


if __name__ == '__main__':
    routes_file = '../Networks/Derech_akko_small/routes/routes.xml'
    network_file = '../Networks/Derech_akko_small/Network.net.xml'
    extractRoutes(routes_file)
    flow_file = '../Networks/Derech_akko_small/flows/generated/Routes.rou.xml'
    network = TrafficNetwork(network_file, routes_file)
    network.parse()
    generator = TrafficGenerator(network)
    generator.generate_xml(flow_file)
    plot_generated(flow_file)


