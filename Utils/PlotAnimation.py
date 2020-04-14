import time

import matplotlib
import multiprocessing
matplotlib.use("TkAgg")
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
#matplotlib.rc('text', usetex = False)
#matplotlib.rc('font', family = 'serif')
#plt.gca().set_aspect('equal', adjustable='box')
#plt.style.use(['ggplot','dark_background'])

class PlotAnimation:
    def __init__(self, dump, communicator):

        self.data = dict()
        self.fig = plt.figure()
        self.communicator = communicator
        self.updater = None
        self.xlim_max = 1
        self.ylim_max = 1
        for i, name in enumerate(dump.keys()):
            self.data[name] = dict()
            self.data[name]['ax'] = self.fig.add_subplot(len(list(dump.keys())), 1, i+1)

            plt.xlabel("Seconds")
            self.data[name]['ax'].set_title("Junction " + name)
            self.data[name]['ax'].set_xlim(0, 3600*24)
            self.data[name]['ax'].set_ylim(0, 100)
            self.data[name]['lines'] = dict()
            for field in dump[name].keys():
                if field == 'time':
                    continue
                line, = self.data[name]['ax'].plot([], [], label=field)
                plt.legend()
                plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
                self.data[name]['lines'][field] = line
            if i == 0:
                self.updater = name
            for field in dump[name].keys():
                self.data[name][field] = list()
        plt.subplots_adjust(hspace=0.5)
        ani = animation.FuncAnimation(self.fig, self.update, fargs=(communicator,), interval=10, blit=True)
        plt.show()

    def update(self, frame, communicator):
        lines = []
        dump = communicator.get()
        for name in dump.keys():
            for field in dump[name].keys():
                self.data[name][field].append(dump[name][field])
                if field == 'time':
                    continue
                self.data[name]['lines'][field].set_data(self.data[name]['time'], self.data[name][field])
                lines.append(self.data[name]['lines'][field])
        return lines

def animation_process(data, communicators):
    PlotAnimation(data, communicators)

