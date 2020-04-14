import sys
import logging

class Logging:
    def __init__(self, loglevel=logging.DEBUG, logfile=None, stdout=False):
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('[%(asctime)s | %(levelname)s] %(message)s')
        root = logging.getLogger()
        root.setLevel(level=loglevel)

        file_logger = logfile and logging.FileHandler(logfile)
        stdout_logger = stdout and logging.StreamHandler(sys.stdout)

        stdout_logger and stdout_logger.setLevel(loglevel)
        stdout_logger and stdout_logger.setFormatter(formatter)
        stdout_logger and root.addHandler(stdout_logger)

        file_logger and file_logger.setLevel(loglevel)
        file_logger and file_logger.setFormatter(formatter)
        file_logger and root.addHandler(file_logger)

    @property
    def root(self):
        return logging.getLogger('root')


Logger = Logging(stdout=True).root
