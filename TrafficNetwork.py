import os
import traci
from Utils.AgentParams import AgentParams
from Agent import Double_DQN_Agent
import numpy as np
from Utils.Logging import Logging, LoggingCsv
from Utils.PlotAnimation import PlotAnimation, animation_process
import time
import matplotlib;

matplotlib.use("TkAgg")
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from multiprocessing import Process, Queue

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

    def mean_speed(self):
        """ Returns the mean speed of vehicles that were on this lane within the last simulation step [m/s] """
        return traci.lane.getLastStepMeanSpeed(self.lid)

    def waiting_time(self):
        """Returns the waiting time for all vehicles on the lane [s]"""
        return max([float(0)] + [traci.vehicle.getAccumulatedWaitingTime(car_id) for car_id in traci.lane.getLastStepVehicleIDs(self.lid)])

    def num_cars(self):
        """The number of vehicles on this lane within the last time step."""
        return traci.lane.getLastStepVehicleNumber(self.lid)

    def occupancy(self):
        """Returns the total lengths of vehicles on this lane during the last simulation step divided by the length of this lane"""
        return traci.lane.getLastStepOccupancy(self.lid)

    def halting_number(self):
        """Returns the total number of halting vehicles for the last time step on the given lane. A speed of less than 0.1 m/s is considered a halt."""
        return traci.lane.getLastStepHaltingNumber(self.lid)

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
    def __init__(self, jid, args):
        self.jid = jid
        self.lanes = [Lane(lid) for lid in set(traci.trafficlight.getControlledLanes(jid))]
        self.edges = [Edge(eid) for eid in set([lane.get_edge_id() for lane in self.lanes])]
        self.phases = traci.trafficlight.getCompleteRedYellowGreenDefinition(jid)[0].getPhases()
        self.state = None
        self.config_file = os.path.dirname(args.cfg) + "/parameters/" + self.jid + ".ini"
        self.agentParams = AgentParams(self.config_file)
        self.input_size = len(self.lanes) + len(self.phases)
        self.num_actions = len(self.phases)
        self.agent = Double_DQN_Agent(self.input_size, self.num_actions, self.agentParams)
        self.steps_counter = 0
        self.reward = None
        self.last_state = None
        self.last_action = None
        self.log_file = os.path.dirname(args.cfg) + "/logs/junctions/" + self.jid
        self.logger = Logging(logfile=self.log_file, name="Junction " + self.jid, stdout=True)
        self.csv_logger = LoggingCsv(self.log_file, self.jid)

    def __repr__(self):
        string = "- Junction id: " + self.jid + "\n"
        string += str(self.lanes)
        string += str(self.edges)
        return string

    def save_results(self, prev_state, prev_action, new_state, reward):
        if self.last_action is not None:
            self.agent.add_to_memory(prev_state, prev_action, new_state, reward)

    def dump(self):
        result = dict()
        result['sim_time'] = time.strftime('%H:%M:%S', time.gmtime(traci.simulation.getTime()))
        result['time'] = int(traci.simulation.getTime())
        result['cars'] = sum([lane.num_cars() for lane in self.lanes])
        mean = [lane.mean_speed() for lane in self.lanes]
        result['mean_speed'] = np.mean(mean)
        result['max_wt'] = max([lane.waiting_time() for lane in self.lanes])
        result['halting_number'] = sum([lane.halting_number() for lane in self.lanes])
        result['occupancy'] = sum([lane.occupancy() for lane in self.lanes])
        result['phase'] = self.phases[traci.trafficlight.getPhase(self.jid)].state
        self.csv_logger.log(result['sim_time'], result['phase'], result['cars'], result['mean_speed'], result['max_wt'], result['halting_number'], result['occupancy'], result['time'])
        return self.jid, result

    def set_phase(self, phase):
        self.last_action = phase
        traci.trafficlight.setPhase(self.jid, phase)

    def generate_state(self):
        phase_state = np.eye(len(self.phases))[traci.trafficlight.getPhase(self.jid)]
        lanes_mean_speed_state = np.array([lane.mean_speed() for lane in self.lanes])
        return np.concatenate((lanes_mean_speed_state, phase_state))

    def calculate_reward(self):
        # max waiting time
        return -1*max([lane.waiting_time() for lane in self.lanes])

    def step(self):
        # Do agent step once for sim_step simulator steps
        self.steps_counter += 1
        if self.steps_counter < self.agentParams.sim_step:
            return
        self.steps_counter = 0

        # Calculate reward for last previous action
        reward = self.calculate_reward()
        new_state = self.generate_state()
        self.save_results(self.last_state, self.last_action, new_state, reward)

        self.last_state = new_state
        action = self.agent.select_action(self.last_state)
        self.set_phase(action)

    def learn(self):
        # Learn after number of sim_step done
        if self.steps_counter == 0:
            self.agent.optimize_model()


class TrafficNetwork:
    def __init__(self, args):
        self.junctions = [Junction(jid, args) for jid in list(traci.trafficlight.getIDList())]
        self.dump_data = dict()
        self.communicator = Queue()
        self.seconds_update = 600
        self.seconds_counter = 0
        for junction in self.junctions:
            jid, results = junction.dump()
            self.dump_data[jid] = dict((k, results[k]) for k in ('time', 'cars', 'max_wt', 'mean_speed'))

        self.plot_process = Process(target=animation_process, args=(self.dump_data, self.communicator)).start()
        self.dump_list = dict()
        for junction in self.junctions:
            self.dump_list[junction.jid] = list()

    def step(self):
        for junction in self.junctions:
            junction.step()

    def learn(self):
        for junction in self.junctions:
            junction.learn()

    def dump(self):
        for junction in self.junctions:
            jid, results = junction.dump()
            self.dump_data[jid] = dict((k, results[k]) for k in ('time', 'cars', 'max_wt', 'mean_speed'))
        self.communicator.put(self.dump_data)


    def __repr__(self):
        string = "Traffic Network: \n"
        string += str(self.junctions)
        return string
