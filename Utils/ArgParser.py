
import argparse


def process_arguments():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="DeepRLight\n" \
                                                 "\tAlexey Tusov, tusovalexey[at]gmail.com\n" \
                                                 "\tPavel Rastopchin, pavelr[at]gmail.com\n", \
                                                    epilog="")
    parser.add_argument("-sc", "--sumo-cfg", type=str, default="./Networks/double/double.sumocfg", dest='cfg')
    parser.add_argument("-gm", "--gui-mode", type=bool, default=True, dest='gui')
    parser.add_argument("-e", "--episodes", type=int, default=100, dest='episodes',
                        help='Number of episodes for simulation, default: agent\'s default value')
    parser.add_argument("-s", "--steps", type=int, default=100000, dest='max_steps',
                        help='Number of steps')
    parser.add_argument("-a", "--animation", type=bool, default=False, dest='animation')
    return parser.parse_args()
