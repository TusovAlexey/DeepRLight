
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

        # init state
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("please declare environment variable 'SUMO_HOME'")
        self.sumo_cmd = [checkBinary('sumo'), '-c', args.cfg,
                         '--no-warnings']  # ,'--no-step-log',
        traci.start(self.sumo_cmd, label='DeepRLight')
        self.traffic_network = TrafficNetwork(self.args)
        traci.close()
        if self.args.gui == False:
           self.sumo_cmd = [checkBinary('sumo'), '-c', self.args.cfg, '--no-warnings']
        else:
           self.sumo_cmd = [checkBinary('sumo-gui'), '-c', self.args.cfg, '--start', '--quit-on-end']

    def reset(self):
        """
        Reset before new episode
        :return:
        """
        traci.start(self.sumo_cmd, label='DeepRLight')
        for _ in range(random.randint(5, self.heatup)):
            traci.simulationStep()

    def close(self):
        traci.close()

    def step(self):
        self.traffic_network.step()
        traci.simulationStep()

    def learn(self):
        self.traffic_network.learn()

    def run(self):
        for episode in range(self.args.episodes):
            self.reset()
            while self.steps < self.args.max_steps:
                self.step()
                self.learn()
