import sys
import os

import time

from instrument import Instrument
from storm import Storm
from tests import Tests
from utils import Utils

__version__ = '0.1.2'


class Main:
    def __init__(self):
        self.wk_dir = os.path.dirname(os.path.realpath('__file__'))
        self.instrument = Instrument(self)
        self.utils = None
        self.result_table = None
        self.menu()

    def menu(self):
        os.system("cls")
        print(__version__)
        # print('Current system: {}'.format(platform.platform()))
        print("***************************")
        print("******** I-DOBR FUFU *******")
        print("***************************")
        print("1: Run FUFU test")
        print("9: Settings")
        print("0: Exit")
        try:
            menu = int(input("Choose operation: "))
        except Exception:
            self.menu()
        if menu == 1:
            self.run_fufu()
        elif menu == 9:
            self.instrument.menu()
        elif menu == 0:
            sys.exit(0)
        else:
            self.menu()

    def run_fufu(self):
        self.result_table = []
        # get ssh connection and reset eth0 ip address
        self.utils = Utils(self)
        if self.utils.ssh is None:
            self.result_table.append(['Connection to the system', 'FAIL'])
            print("Can't established ssh connection")
            raw_input('Press Enter for continue...')
            self.menu()
        else:
            self.result_table.append(['Connection to the system', 'PASS'])

        print('Enable Remote and Modem Communication: {}'.format(self.utils.set_remote_communication(1)))


        # # save set files
        # self.utils.send_command('udp_bridge1', 'start')
        # storm = Storm(self)
        # for place, band in enumerate(self.utils.get_bands()):
        #     storm.save_setfile(place=place, band=band)
        # self.result_table.append(['Save set file for IDOBR', 'PASS'])
        # self.utils.send_command('udp_bridge1', 'stop')

        tests = Tests(self, self.utils)

        # tests.verify_connections()
        # tests.test_composite_power()

        # test bands status
        tests.test_band_status()

        # test sw and patch version
        # tests.test_swv()

        # self.utils.set_filters_pa_status(1)

        # TTF calibration
        # tests.ttf_calibrate()

        # test alarm
        # tests.test_ext_alarm()

        tests.gpr_gps_test()
        print('Disable Remote and Modem Communication: {}'.format(self.utils.set_remote_communication(0)))
        tests.clear_log()

        self.utils.print_table(['Description', 'Status'], self.result_table)

        raw_input('Press Enter for continue...')
        self.menu()


if __name__ == '__main__':
    prog = Main()
    sys.exit(0)
