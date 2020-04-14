import sys
import logging
import time
import io
import csv
import os

class CsvFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(fmt='%(message)s')
        self.output = io.StringIO()
        self.writer = csv.writer(self.output)

    def format(self, record):
        self.writer.writerow(list(record.msg.split(",")))
        data = self.output.getvalue()
        self.output.truncate(0)
        self.output.seek(0)
        return data.strip()

class LoggingCsv:
    def __init__(self, path, name):
        os.makedirs(path + "/csv", exist_ok=True)

        self.logger = logging.getLogger(name + "_csv")
        self.logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(
            path + "/csv/" + time.strftime('%Y_%m_%d__%H_%M_%S', time.localtime()) + ".csv")
        file_handler.setLevel(logging.DEBUG)
        file_format = CsvFormatter()
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)

    def log(self, *args):
        msg = ""
        for arg in args:
            msg += str(arg) + ","
        self.logger.info(msg[:-1])

class Logging:
    def __init__(self, loglevel=logging.DEBUG, logfile=None, stdout=False, name='root'):
        assert logfile is not None or stdout is True

        self.logger = logging.getLogger(name)
        self.logger.setLevel(loglevel)

        if logfile is not None:
            os.makedirs(logfile + "/prints", exist_ok=True)
            file_format = logging.Formatter('%(message)s')
            file_handler = logging.FileHandler(logfile + "/prints/" + time.strftime('%Y_%m_%d__%H_%M_%S', time.localtime()) + ".log")
            file_handler.setLevel(loglevel)
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)

        if stdout:
            stdout_format = logging.Formatter('[%(asctime)s | %(levelname)s | %(name)s] %(message)s')
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setLevel(loglevel)
            stdout_handler.setFormatter(stdout_format)
            self.logger.addHandler(stdout_handler)

        logging.addLevelName(logging.INFO, logging.getLevelName(logging.INFO))
        logging.addLevelName(logging.ERROR, logging.getLevelName(logging.ERROR))


    def info(self, msg):
        self.logger.info(msg)



Logger = Logging(stdout=True)
