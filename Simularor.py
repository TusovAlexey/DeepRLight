
from sumolib import checkBinary
import traci
import os
import sys
from TrafficNetwork import TrafficNetwork

class Simulator:
    def __init__(self, args):
        # init params
        self.args = args
        self.sumo_cmd = None
        self.network = None

        # init state
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("please declare environment variable 'SUMO_HOME'")
        self.sumo_cmd = [checkBinary('sumo'), '-c', './Networks/simple/simple.sumocfg',
                         '--no-warnings']  # ,'--no-step-log',
        traci.start(self.sumo_cmd, label='DeepRLight')
        self.network = TrafficNetwork()
        traci.close()
        if self.args.gui == False:
           self.sumo_cmd = [checkBinary('sumo'), '-c', self.args.sumo_cfg, '--no-warnings']
        else:
           self.sumo_cmd = [checkBinary('sumo-gui'), '-c', self.args.sumo_cfg, '--start', '--quit-on-end']
        


if __name__ == '__main__':
    simulation = Simulator(None)
