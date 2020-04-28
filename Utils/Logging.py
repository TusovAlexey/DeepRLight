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
    def __init__(self, path, name, keys):
        self.keys = keys
        self.csv_root = path
        os.makedirs(self.csv_root, exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.file_handler = None

    def set_new_file(self, name):
        if self.logger.hasHandlers():
            self.logger.removeHandler(self.file_handler)
        self.file_handler = logging.FileHandler(
            self.csv_root + name + ".csv")
        self.file_handler.setLevel(logging.DEBUG)
        file_format = CsvFormatter()
        self.file_handler.setFormatter(file_format)
        self.logger.addHandler(self.file_handler)
        header = "#" + ",".join(self.keys)
        self.logger.info(header)

    def log(self, *args):
        msg = ""
        for arg in args:
            msg += str(arg) + ","
        self.logger.info(msg[:-1])

class Logging:
    def __init__(self, loglevel=logging.DEBUG, logfile=None, stdout=False, name='root'):
        assert logfile is not None or stdout is True
        self.level = loglevel
        self.logger = logging.getLogger(name)
        self.logger.setLevel(loglevel)
        self.root_dir = logfile
        self.file_handler = None
        if logfile is not None:
            os.makedirs(self.root_dir, exist_ok=True)
        if stdout:
            stdout_format = logging.Formatter('[%(asctime)s | %(levelname)s | %(name)s] %(message)s')
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setLevel(loglevel)
            stdout_handler.setFormatter(stdout_format)
            self.logger.addHandler(stdout_handler)

        logging.addLevelName(logging.INFO, logging.getLevelName(logging.INFO))
        logging.addLevelName(logging.ERROR, logging.getLevelName(logging.ERROR))

    def set_new_file(self, name):
        if self.logger.hasHandlers():
            self.logger.removeHandler(self.file_handler)
        self.file_handler = logging.FileHandler(self.root_dir + name + ".log")
        self.file_handler.setLevel(self.level)
        file_format = logging.Formatter('%(message)s')
        self.file_handler.setFormatter(file_format)
        self.logger.addHandler(self.file_handler)

    def info(self, msg):
        self.logger.info(msg)



Logger = Logging(stdout=True)
