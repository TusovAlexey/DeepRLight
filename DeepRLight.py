



from Utils.ArgParser import process_arguments
from Simularor import Simulator
#from Utils.Logging import Logger



if __name__ == '__main__':
    args = process_arguments()
    simulator = Simulator(args)

    simulator.run()
