from sys import stdout

import time

import subprocess

from config import Config
from mtdi import Mtdi
from utils import Utils
# 00-14-B1-02-9D-58


class Msdh(Mtdi, Utils):
    def __init__(self, parent):
        self.info = subprocess.STARTUPINFO()
        self.info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.info.wShowWindow = subprocess.SW_HIDE
        self.parent = parent
        self.config = Config(mainProg=parent)
        self.utils = Utils(self)
        self.msdh_test()

    def msdh_test(self):
        # self.getAvalIp()
        self.utils.getAvalIp(ip='11.0.0.100')
        if self.utils.ssh is None:
            raw_input("Press enter to continue")
            self.parent.menu()
        # self.waitUpTime(10)
        for n in range(5):
            self.utils.send_command('rm', '/tmp/SuperviseTheDaemons')
            stdout.write('\rRemove directory {}'.format(n))
            time.sleep(1)
        stdout.write("\n")

        self.killProc(['hw_watchdog.sh'])
        self.waitReboot()

        raw_input("Press enter to continue")
        self.parent.menu()