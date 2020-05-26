import os
import traci
from Utils.AgentParams import AgentParams
from Agent import Double_DQN_Agent
import numpy as np
from Utils.Logging import Logging, LoggingCsv, GUIScreenShot
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
        self.cars = list()

    def __repr__(self):
        string = "  - Lane id: " + self.lid + ", length: " + str(self.length) + ", Edge: " + self.eid + "\n"
        return string

    def mean_speed(self):
        """ Returns the mean speed of vehicles that were on this lane within the last simulation step [m/s] """
        return traci.lane.getLastStepMeanSpeed(self.lid)

    def passenger_mean_speed(self):
        veh = [vid for vid in traci.lane.getLastStepVehicleIDs(self.lid) if traci.vehicle.getVehicleClass(vid)=='passenger']
        if len(veh)==0:
            return 0
        return np.mean([traci.vehicle.getSpeed(vid) for vid in veh])

    def bus_mean_speed(self):
        veh = [vid for vid in traci.lane.getLastStepVehicleIDs(self.lid) if
               traci.vehicle.getVehicleClass(vid) == 'bus']
        if len(veh) == 0:
            return 0
        return np.mean([traci.vehicle.getSpeed(vid) for vid in veh])

    def emergency_mean_speed(self):
        veh = [vid for vid in traci.lane.getLastStepVehicleIDs(self.lid) if
               traci.vehicle.getVehicleClass(vid) == 'emergency']
        if len(veh) == 0:
            return 0
        return np.mean([traci.vehicle.getSpeed(vid) for vid in veh])

    def max_waiting_time(self):
        """Returns the max waiting time for all vehicles on the lane [s]"""
        return max([float(0)] + [traci.vehicle.getAccumulatedWaitingTime(car_id) for car_id in traci.lane.getLastStepVehicleIDs(self.lid)])

    def num_cars(self):
        """The number of passenger vehicles on this lane within the last time step."""
        return len([vid for vid in traci.lane.getLastStepVehicleIDs(self.lid) if traci.vehicle.getVehicleClass(vid)=='passenger'])

    def num_buses(self):
        """The number of bus vehicles on this lane within the last time step."""
        return len([vid for vid in traci.lane.getLastStepVehicleIDs(self.lid) if
                    traci.vehicle.getVehicleClass(vid) == 'bus'])

    def num_emergency(self):
        """The number of emergency vehicles on this lane within the last time step."""
        return len([vid for vid in traci.lane.getLastStepVehicleIDs(self.lid) if
                    traci.vehicle.getVehicleClass(vid) == 'emergency'])

    def occupancy(self):
        """Returns the total lengths of vehicles on this lane during the last simulation step divided by the length of this lane"""
        return traci.lane.getLastStepOccupancy(self.lid)

    def halting_number(self):
        """Returns the total number of halting vehicles for the last time step on the given lane. A speed of less than 0.1 m/s is considered a halt."""
        return traci.lane.getLastStepHaltingNumber(self.lid)

    def departed_number(self):
        """Returns a list of ids of vehicles which departed (were inserted into the road network) in this time step."""
        current_cars = traci.lane.getLastStepVehicleIDs(self.lid)
        new_cars = [car for car in current_cars if car not in self.cars]
        self.cars = current_cars
        return len(new_cars)

    def get_edge_id(self):
        return self.eid

class Edge:
    def __init__(self, eid):
        self.eid = eid
        self.num_lanes = traci.edge.getLaneNumber(eid)

    def __repr__(self):
        string = "  - Edge id: " + self.eid + ", number of lanes: " + str(self.num_lanes) + "\n"
        return string

    def get_persons(self):
        return traci.edge.getLastStepPersonIDs(self.eid)

    def get_waiting_persons(self):
        return [person for person in self.get_persons() if traci.person.getStage(person)==1]

    def get_num_waiting_persons(self):
        return len(self.get_waiting_persons())

    def get_total_waiting_persons_time(self):
        return sum([traci.person.getWaitingTime(person) for person in self.get_persons() if traci.person.getStage(person)==1])


class Junction:
    keys = ['sim_time', 'phase', 'reward', 'cars', 'buses', 'mean_speed', 'passenger_mean_speed', 'bus_mean_speed', 'emergency_mean_speed', 'max_wt', 'occupancy', 'persons', 'waiting_persons']
    def __init__(self, jid, args, network_log_root, screenshots_logger):
        self.jid = jid
        self.lanes = [Lane(lid) for lid in set(traci.trafficlight.getControlledLanes(jid)) if 'pedestrian' not in traci.lane.getAllowed(lid)]
        self.walking_lanes = [Lane(lid) for lid in set(traci.trafficlight.getControlledLanes(jid)) if 'pedestrian' in traci.lane.getAllowed(lid)]
        self.edges = [Edge(eid) for eid in set([traci.lane.getEdgeID(lid) for lid in traci.trafficlight.getControlledLanes(jid)])]
        self.phases = traci.trafficlight.getCompleteRedYellowGreenDefinition(jid)[0].getPhases()
        self.default_program = traci.trafficlight.getProgram(jid)
        self.state = None
        self.args = args
        self.config_file = os.path.dirname(args.cfg) + "/parameters/" + self.jid + ".ini"
        self.agentParams = AgentParams(self.config_file)
        self.input_size = len(self.generate_state())
        self.num_actions = len(self.phases)
        self.agent = Double_DQN_Agent(self.input_size, self.num_actions, self.agentParams)
        self.steps_counter = 0
        self.reward = None
        self.last_state = None
        self.last_action = traci.trafficlight.getPhase(self.jid)
        self.network_log_root = network_log_root
        self.log_root = os.path.join(self.network_log_root, self.jid)
        self.logger = Logging(logfile=os.path.join(self.log_root, "prints"), name="Junction " + self.jid, stdout=True)
        self.csv_logger = LoggingCsv(os.path.join(self.log_root, "statistics"), self.jid + "statistics", Junction.keys)
        self.phase_logger = LoggingCsv(os.path.join(self.log_root, "phases"), self.jid + "phases", ['sim_time', 'phase'])
        self.screenshots_logger = screenshots_logger
        self.next_phase = None
        self.current_phase_state = self.phases[traci.trafficlight.getPhase(self.jid)].state
        self.yellow_steps_counter = 0
        self.episode = -1
        self.best_reward = -np.Inf
        self.episode_rewards = list()

    def __repr__(self):
        string = "- Junction id: " + self.jid + "\n"
        string += str(self.lanes)
        string += str(self.edges)
        return string

    def reset(self, episode):
        if self.episode != -1:
            current_mean = np.mean(self.episode_rewards)
            if current_mean > self.best_reward:
                self.best_reward = current_mean
                os.makedirs(os.path.join(self.log_root, "checkpoint"), exist_ok=True)
                self.agent.save_ckpt(os.path.join(self.log_root, "checkpoint"))
            self.logger.info_global("Episode " + str(self.episode) + " mean reward:" + str(current_mean))
            self.episode_rewards = list()
        self.episode = episode
        self.csv_logger.set_new_file("Episode_" + str(episode))
        self.phase_logger.set_new_file("Episode_" + str(episode))
        self.phase_logger.log(time.strftime('%H:%M:%S', time.gmtime(traci.simulation.getTime())),
                              self.phases[traci.trafficlight.getPhase(self.jid)].state)
        self.logger.set_new_file("Episode_" + str(episode))
        self.last_phase = traci.trafficlight.getPhase(self.jid)

    def save_results(self, prev_state, prev_action, new_state, reward):
        if self.last_action is not None and prev_state is not None:
            self.agent.add_to_memory(prev_state, prev_action, new_state, reward)

    def dump(self):
        result = dict()
        result['sim_time'] = time.strftime('%H:%M:%S', time.gmtime(traci.simulation.getTime()))
        result['time'] = int(traci.simulation.getTime())
        result['cars'] = sum([lane.num_cars() for lane in self.lanes])
        result['buses'] = sum([lane.num_buses() for lane in self.lanes])
        result['departed'] = sum([lane.departed_number() for lane in self.lanes])
        mean = [lane.mean_speed() for lane in self.lanes]
        result['mean_speed'] = np.mean(mean)
        result['passenger_mean_speed'] = np.mean([lane.passenger_mean_speed() for lane in self.lanes])
        result['bus_mean_speed'] = np.mean([lane.bus_mean_speed() for lane in self.lanes])
        result['emergency_mean_speed'] = np.mean([lane.emergency_mean_speed() for lane in self.lanes])
        result['max_wt'] = max([lane.max_waiting_time() for lane in self.lanes])
        result['halting_number'] = sum([lane.halting_number() for lane in self.lanes])
        result['occupancy'] = sum([lane.occupancy() for lane in self.lanes])
        result['phase'] = self.phases[traci.trafficlight.getPhase(self.jid)].state
        result['reward'] = self.calculate_reward()
        result['persons'] = sum([len(edge.get_persons()) for edge in self.edges])
        result['waiting_persons'] = sum([len(edge.get_waiting_persons()) for edge in self.edges])
        if self.args.capture and (self.episode % self.args.episode_capture) == 0:
            self.screenshots_logger.log(self.episode, result['reward'], result['cars'], result['mean_speed'], result['max_wt'])
        self.csv_logger.log(result['sim_time'], result['phase'], result['reward'], result['cars'], result['buses'], result['mean_speed'], result['passenger_mean_speed'], result['bus_mean_speed'], result['emergency_mean_speed'], result['max_wt'], result['occupancy'], result['persons'], result['waiting_persons'])
        return self.jid, result

    def set_yellow_phase(self, next_phase):
        current_phase_state = self.phases[self.last_action].state
        next_phase_state = self.phases[next_phase].state
        yellow_phase_state = ''.join(['y' if prev_light.lower()=='g' and new_light.lower()=='r' else prev_light for prev_light, new_light in zip(current_phase_state, next_phase_state)])
        self.phase_logger.log(time.strftime('%H:%M:%S', time.gmtime(traci.simulation.getTime())),
                              yellow_phase_state)
        traci.trafficlight.setRedYellowGreenState(self.jid, yellow_phase_state)
        self.current_phase_state = yellow_phase_state
        self.next_phase = next_phase
        self.yellow_steps_counter = 0

    def set_phase(self, phase):
        if self.last_action != phase:
            self.phase_logger.log(time.strftime('%H:%M:%S', time.gmtime(traci.simulation.getTime())),
                              self.phases[phase].state)
        traci.trafficlight.setProgram(self.jid, self.default_program)
        traci.trafficlight.setPhase(self.jid, phase)
        self.current_phase_state = self.phases[phase].state
        self.last_action = phase
        self.steps_counter = 0

    def generate_state(self):
        """ state = [num persons per edge] + [vehicle mean speed per lane] + [phases] """
        phase_state = np.eye(len(self.phases))[traci.trafficlight.getPhase(self.jid)]
        edges_persons_total_num_state = np.array([edge.get_num_waiting_persons() for edge in self.edges])
        lanes_mean_speed_state = np.array([lane.mean_speed() for lane in self.lanes])
        return np.concatenate((edges_persons_total_num_state , lanes_mean_speed_state, phase_state))

    def calculate_reward(self):
        # max waiting time
        reward = -1*max([lane.max_waiting_time() for lane in self.lanes])
        self.episode_rewards.append(reward)
        return reward
        #return max(np.mean([lane.mean_speed() for lane in self.lanes]) * sum([lane.num_cars() for lane in self.lanes]), 0)

    def step(self):
        if self.current_phase_state.count('y') > 0:
            # Current phase is yellow
            self.yellow_steps_counter += 1
            if self.yellow_steps_counter >= self.agentParams.yellow_duration:
                self.yellow_steps_counter = 0
                # Time to change to next phase
                self.set_phase(self.next_phase)
                return
            return

        self.steps_counter += 1
        # Do agent step once for sim_step simulator steps
        if self.steps_counter < self.agentParams.sim_step:
            return

        # Calculate reward for last previous action
        reward = self.calculate_reward()
        new_state = self.generate_state()
        self.save_results(self.last_state, self.last_action, new_state, reward)

        if self.steps_counter < self.agentParams.min_green_duration:
            return

        self.last_state = new_state
        action = self.agent.select_action(self.last_state)

        if self.last_action != action:
            # Yellow phase required
            self.set_yellow_phase(action)
        else:
            self.set_phase(action)

    def close(self):
        if self.args.capture:
            self.screenshots_logger.close()

    def learn(self):
        # Learn after number of sim_step done
        if self.steps_counter == 0:
            self.agent.optimize_model()


class TrafficNetwork:
    def __init__(self, args, views_dict):
        self.args = args
        self.time = time.strftime('%Y_%m_%d__%H_%M_%S', time.localtime())
        self.network_log_root = os.path.join(os.path.join(args.network, 'logs'), self.time)
        self.junctions = [Junction(jid, args, self.network_log_root, GUIScreenShot(os.path.join(self.network_log_root, "captures"), jid, views_dict[jid])) for jid in list(traci.trafficlight.getIDList())]
        self.dump_data = dict()
        self.seconds_update = 600
        self.seconds_counter = 0
        self.episode = 0
        if args.animation:
            self.create_plot_animation()

    def create_plot_animation(self):
        self.communicator = Queue()
        for junction in self.junctions:
            jid, results = junction.dump()
            self.dump_data[jid] = dict((k, results[k]) for k in ('time', 'cars', 'max_wt', 'mean_speed'))
        self.plot_process = Process(target=animation_process, args=(self.dump_data, self.communicator)).start()
        self.dump_list = dict()
        for junction in self.junctions:
            self.dump_list[junction.jid] = list()

    def close(self):
        #self.network_screen_logger.close()
        for juntion in self.junctions:
            juntion.close()

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
        #self.network_screen_logger.log(self.episode)
        if self.args.animation:
            self.communicator.put(self.dump_data)

    def reset(self, episode):
        self.episode = episode
        for junction in self.junctions:
            junction.reset(episode)

    def __repr__(self):
        string = "Traffic Network: \n"
        string += str(self.junctions)
        return string
