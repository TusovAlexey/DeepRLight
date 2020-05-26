import sys
import logging
import io
import csv
import os
import traci
from io import StringIO
import cv2
import glob
import time
import matplotlib
from PIL import Image, ImageDraw, ImageFont
import subprocess
from subprocess import Popen, PIPE
matplotlib.use('Agg')

FFMPEG_SOURCE = "ffmpeg\\bin\\ffmpeg.exe"

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
            os.path.join(self.csv_root,name + ".csv"))
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
        self.root_dir = logfile
        if logfile is not None:
            os.makedirs(self.root_dir, exist_ok=True)

        self.level = loglevel
        self.global_logger = logging.getLogger(name + "_global")
        self.global_logger.setLevel(loglevel)
        self.global_file_handler = logging.FileHandler(os.path.join(self.root_dir, "global.log"))
        self.global_file_handler.setLevel(self.level)
        global_file_format = logging.Formatter('%(message)s')
        self.global_file_handler.setFormatter(global_file_format)
        self.global_logger.addHandler(self.global_file_handler)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(loglevel)

        self.file_handler = None

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
        self.file_handler = logging.FileHandler(os.path.join(self.root_dir,name + ".log"))
        self.file_handler.setLevel(self.level)
        file_format = logging.Formatter('%(message)s')
        self.file_handler.setFormatter(file_format)
        self.logger.addHandler(self.file_handler)

    def info(self, msg):
        self.logger.info(msg)

    def info_global(self, msg):
        self.global_logger.info(msg)


class GUIScreenShot:
    def __init__(self, path, name, view_id):
        self.root = os.path.join(path, name)
        self.name = name
        self.picture = None
        self.video_path = os.path.join(self.root, self.name + ".mp4")
        os.makedirs(self.root, exist_ok=True)
        self.view = 'View #' + str(view_id)
        self.conter = 0

    def _handle_saved_pic(self):
        img = Image.open(self.picture)
        name = os.path.basename(self.picture).split(".")[0]
        pic_episode = name.split("__")[0]
        pic_time = name.split("__")[1].replace("_", ":")
        #pic_reward = name.split("__")[2].replace("_", ".")
        pic_cars = name.split("__")[3]
        pic_mean_speed = name.split("__")[4].replace("_", ".")
        pic_max_wt = name.split("__")[5].replace("_", ".")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("C:\\windows\\fonts\\stencil.ttf", 25, encoding="unic")
        draw.text((0, 0), "Episode  " + pic_episode, fill='Black', font=font)
        draw.text((0, 30), "Time  " + pic_time, fill='Black', font=font)
        #draw.text((0, 60), "Reward  " + pic_reward, fill='Black', font=font)
        img.save(os.path.join(self.root, "%08d" % self.conter + ".png"), quality=20, optimize=True)
        self.conter += 1
        os.remove(self.picture)


    def log(self, episode, reward=None, num_cars=None, mean_speed=None, max_wt=None):
        if self.picture is not None and os.path.exists(self.picture):
            self._handle_saved_pic()
        sim_time = time.strftime('%H_%M_%S', time.gmtime(traci.simulation.getTime()))
        self.picture = os.path.join(self.root, str(episode) + "__" + sim_time + "__" + str(reward).replace(".","_") + "__" + str(num_cars) + "__" + str(mean_speed).replace(".","_") + "__" + str(max_wt).replace(".","_") + ".png")
        if traci.gui.hasView(self.view):
            traci.gui.screenshot(self.view, self.picture)

    def close(self):
        cmd = FFMPEG_SOURCE + " -r 60 -start_number 0 -i " + os.path.join(self.root, "%08d.png") + " -vcodec libx264 " + self.video_path
        os.system(cmd)
        for f in os.listdir(self.root):
            if f.endswith(".png"):
                os.remove(os.path.join(self.root, f))


#Logger = Logging(stdout=True)
