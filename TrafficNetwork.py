import os
import traci
from Utils.AgentParams import AgentParams
from Agent import Double_DQN_Agent
import numpy as np
from Utils.Logging import Logging, LoggingCsv
import time

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

    def get_last_step_mean_speed(self):
        return traci.lane.getLastStepMeanSpeed(self.lid)

    def get_lane_cars_waiting_time(self):
        return max([float(0)] + [traci.vehicle.getAccumulatedWaitingTime(car_id) for car_id in traci.lane.getLastStepVehicleIDs(self.lid)])

    def get_edge_id(self):
        return self.eid

    def get_cars_amount(self):
        return len(traci.lane.getLastStepVehicleIDs(self.lid))

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

    def get_cars_amount(self):
        return sum([lane.get_cars_amount() for lane in self.lanes])

    def get_mean_speed(self):
        return np.mean([lane.get_last_step_mean_speed() for lane in self.lanes])

    def get_max_waiting_time(self):
        return max([lane.get_lane_cars_waiting_time() for lane in self.lanes])

    def dump_information(self):
        sim_time = time.strftime('%H:%M:%S', time.gmtime(traci.simulation.getTime()))
        cars = self.get_cars_amount()
        mean_speed = self.get_mean_speed()
        max_wt = self.get_max_waiting_time()
        phase = self.phases[traci.trafficlight.getPhase(self.jid)].state
        self.logger.info("Time: " + str(sim_time) +
                         ", cars: " + str(cars) +
                         ", Mean speed: " + str(mean_speed) +
                         ", Max waiting time: " + str(max_wt) +
                         ", Phase: " + str(phase))
        self.csv_logger.log(sim_time, cars, mean_speed, max_wt, phase)
        #self.csv_logger.log(str(sim_time) + "," +
        #                    str(cars) + "," +
        #                    str(mean_speed) + "," +
        #                    str(max_wt) + "," +
        #                    str(phase))


    def set_phase(self, phase):
        self.last_action = phase
        traci.trafficlight.setPhase(self.jid, phase)

    def generate_state(self):
        phase_state = np.eye(len(self.phases))[traci.trafficlight.getPhase(self.jid)]
        lanes_mean_speed_state = np.array([lane.get_last_step_mean_speed() for lane in self.lanes])
        return np.concatenate((lanes_mean_speed_state, phase_state))

    def calculate_reward(self):
        # max waiting time
        return -1*self.get_max_waiting_time()

    def dump(self):
        self.dump_information()

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

    def step(self):
        for junction in self.junctions:
            junction.step()

    def learn(self):
        for junction in self.junctions:
            junction.learn()

    def dump(self):
        for junction in self.junctions:
            junction.dump()

    def __repr__(self):
        string = "Traffic Network: \n"
        string += str(self.junctions)
        return string
