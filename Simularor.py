
from sumolib import checkBinary
import traci
import os
import sys
from TrafficNetwork import TrafficNetwork
import random

class Simulator:
    def __init__(self, args):
        # init params
        self.args = args
        self.sumo_cmd = None
        self.traffic_network = None
        self.steps = 0
        self.heatup = 20
        self.episode = 0

        # init state
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("please declare environment variable 'SUMO_HOME'")
        self.sumo_cmd = [checkBinary('sumo'), '-c', args.cfg,
                         '--no-warnings']  # ,'--no-step-log',
        traci.start(self.sumo_cmd, label='DeepRLight')
        view_dict, view_paths = self.parse_gui_settings()
        self.traffic_network = TrafficNetwork(self.args, view_dict)
        traci.close()

        self.sumo_cli = [checkBinary('sumo'), '-c', self.args.cfg, '--no-warnings']
        self.sumo_gui = [checkBinary('sumo-gui'), '-c', self.args.cfg, '--start', '--quit-on-end']
        self.sumo_cmd = self.sumo_cli
        if self.args.gui:
            self.sumo_cmd = self.sumo_gui


    def parse_gui_settings(self):
        views_path = [os.path.abspath(file) for file in os.listdir(os.path.dirname(self.args.cfg) + "/Views/")]
        views_names = {file.split(".")[0] : i for i ,file in enumerate(os.listdir(os.path.dirname(self.args.cfg) + "/Views/"))}
        return views_names, views_path

    def reset(self):
        """
        Reset before new episode
        :return:
        """
        if self.args.capture and (self.episode % self.args.episode_capture) == 0 :
            self.sumo_cmd = self.sumo_gui
        else:
            self.sumo_cmd = self.sumo_cmd
        traci.start(self.sumo_cmd, label='DeepRLight')
        self.traffic_network.reset(self.episode)
        for _ in range(random.randint(5, self.heatup)):
            self.traffic_network.dump()
            traci.simulationStep()

    def close(self):
        self.traffic_network.close()
        traci.close()

    def step(self):
        self.traffic_network.step()
        self.traffic_network.dump()
        traci.simulationStep()

    def learn(self):
        self.traffic_network.learn()

    def run(self):
        for self.episode in range(self.args.episodes):
            self.reset()
            self.steps = 0
            while self.steps < self.args.max_steps:
                self.step()
                self.learn()
                self.steps += 1
            self.close()
