
import argparse
import os

def process_arguments():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="DeepRLight\n" \
                                                 "\tAlexey Tusov, tusovalexey[at]gmail.com\n" \
                                                 "\tPavel Rastopchin, pavelr[at]gmail.com\n", \
                                                    epilog="")
    parser.add_argument("-n", "--network", type=str, default="Derech_akko", dest='network')
    parser.add_argument("-gm", "--gui-mode", type=bool, default=True, dest='gui')
    parser.add_argument("-e", "--episodes", type=int, default=10, dest='episodes',
                        help='Number of episodes for simulation, default: agent\'s default value')
    parser.add_argument("-s", "--steps", type=int, default=86400, dest='max_steps',
                        help='Number of steps')
    parser.add_argument("-a", "--animation", type=bool, default=False, dest='animation')
    parser.add_argument("-c", "--capture", type=bool, default=True, dest="capture")
    parser.add_argument("-ec", "--episode-capture", type=int, default=5, dest="episode_capture")
    args = parser.parse_args()
    args.network = os.path.join("Networks", args.network)
    args.cfg = os.path.join(args.network, "Config.sumocfg")

    return args
