import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt

class TrafficVisualization:
    def __init__(self, xml_file):
        self._xml = xml_file
        self.root = ET.parse(self._xml)
        self.start_edges = dict()
        self.end_edges = dict()

    def parse(self):
        for route in self.root.findall('route'):
            edges = route.get('edges')
            start = edges.split(' ')[0]
            #end = edges.split(' ')[1:]
            self.start_edges[start] = dict()
            #self.end_edges[end] = dict()


        for hour in range(0, 24):
            for key in self.start_edges.keys():
                self.start_edges[key][hour] = 0
            #for key in self.end_edges.keys():
                #self.end_edges[key][hour] = 0

        for flow in self.root.findall('flow'):
            route = flow.get('route')
            vphour = int(flow.get('vehsPerHour'))
            hour = flow.get('begin')
            hour = int(hour) / 7200
            start = route.split(' ')[0]
            self.start_edges[start][hour] += vphour

    def get_start(self):
        return self.start_edges

    def plot(self):
        fig, axs = plt.subplots(len(self.start_edges.keys()), sharex=True, sharey=True)
        x = [i for i in range(0, 24)]
        for i, edge in enumerate(self.start_edges.keys()):
            y = list(self.start_edges[edge].values())
            axs[i].plot(x, y)
        for ax in axs:
            ax.label_outer()
        plt.show()
        plt.draw()

if __name__ == '__main__':
    flow_file = '../Networks/simple/flows/simple.rou.xml'
    traffic_visual = TrafficVisualization(flow_file)
    traffic_visual.parse()
    traffic_visual.plot()
