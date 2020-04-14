

import configparser

class AgentParams:
    def __init__(self, file):
        self.file = file
        self.eps_start = 0
        self.eps_end = 0
        self.discount = 0
        self.replay_size = 0
        self.batch_size = 512
        self.target_update = 0
        self.optimizer = None
        self.layers = None
        self.eps_decay = 0
        self.grad_clip = 0
        self.config = configparser.ConfigParser()
        self.parse_config()

    def parse_config(self):
        self.config.read(self.file)
        self.eps_start = float(self.config.get('params','eps_start'))
        self.eps_end = float(self.config.get('params', 'eps_end'))
        self.discount = float(self.config.get('params', 'discount'))
        self.replay_size = int(self.config.get('params', 'replay_size'))
        self.batch_size = int(self.config.get('params', 'batch_size'))
        self.optimizer = self.config.get('params', 'optimizer')
        self.layers = list(map(int, self.config.get('params', 'layers').split(",")))
        self.eps_decay = int(self.config.get('params', 'eps_decay'))
        self.grad_clip = int(self.config.get('params', 'grad_clip'))
        self.target_update = float(self.config.get('params', 'target_update'))
        self.sim_step = int(self.config.get('params', 'sim_step'))



