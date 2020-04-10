
import traci

class Lane:
    def __init__(self, lid):
        self.lid = lid
        self.length = traci.lane.getLength(lid)
        self.shape = traci.lane.getShape(lid)
        self.eid = traci.lane.getEdgeID(lid)
        self.width = traci.lane.getWidth(lid)

    def __repr__(self):
        string = "  - Lane id: " + self.lid + ", length: " + str(self.length) + ", Edge: " + self.eid + "\n"
        return string

    def get_edge_id(self):
        return self.eid


class Edge:
    def __init__(self, eid):
        self.eid = eid
        self.num_lanes = traci.edge.getLaneNumber(eid)

    def __repr__(self):
        string = "  - Edge id: " + self.eid + ", number of lanes: " + str(self.num_lanes) + "\n"
        return string


class Junction:
    def __init__(self, jid):
        self.jid = jid
        self.lanes = [Lane(lid) for lid in set(traci.trafficlight.getControlledLanes(jid))]
        self.edges = [Edge(eid) for eid in set([lane.get_edge_id() for lane in self.lanes])]
        self.phases = traci.trafficlight.getCompleteRedYellowGreenDefinition(jid)[0].getPhases()

    def __repr__(self):
        string = "- Junction id: " + self.jid + "\n"
        string += str(self.lanes)
        string += str(self.edges)
        return string

    def get_lanes(self):
        return self.lanes

    def get_edges(self):
        return self.edges

    def get_phases(self):
        return self.phases


class TrafficNetwork:
    def __init__(self):
        self.junctions = [Junction(jid) for jid in list(traci.trafficlight.getIDList())]

    def __repr__(self):
        string = "Traffic Network: \n"
        string += str(self.junctions)
        return string









