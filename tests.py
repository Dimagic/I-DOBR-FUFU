import ast
import time
from sys import stdout
import datetime
from prettytable import PrettyTable
from config import Config

"""
/mnt/axell_cfg/etc/target/current/operators/band_1_filters_setting.dat
/mnt/axell_cfg/etc/target/current/operators/filter_cell_res_list.dat
axsh get nic eth0
dobr_filters SET 1 1 - 0 GSM 1875 1880 24 73 3 0
dobr_filters get all
axsh set fft 1 -200
axsh get fft 1
dobr_pa_control SET 2 1
imop_control SET 2 0
"""

from ttfCalibration import TtfCalibrate


class Tests:
    def __init__(self, parent, utils):
        self.parent = parent
        parent.test_start = time.time()
        self.utils = utils
        self.ssh = utils.ssh
        self.config = Config(parent)
        self.bands = utils.get_bands()
        try:
            self.gen = self.parent.instrument.genPreset()
            self.sa = self.parent.instrument.saPreset()
        except:
            raw_input('Instrument initialisation fail.\nPress enter for continue...')
            self.parent.instrument.menu()

    def test_ext_alarm(self):
        self.utils.print_testname('Alarms')
        self.utils.send_command('axsh', 'SET EXT 0 0 0 0')
        test_status = 'PASS'
        keys = ['7', '6', '5', '4']
        for pin in keys:
            print('Short pin {} to the chassis'.format(pin))
            while True:
                curr_status = False
                alarms = self.utils.get_ext_alarm()
                if alarms.get(pin) == '0':
                    curr_status = True
                    print('EXT{} alarm: PASS'.format(pin))
                    break
                time.sleep(1)
            if not curr_status:
                test_status = 'FAIL'
        self.parent.result_table.append(['External Alarm Test', test_status])

    def test_swv(self):
        self.utils.print_testname('Software verification')
        need_sw = self.config.getConfAttr('settings', 'swv').split(';')
        need_patch = self.config.getConfAttr('settings', 'patch').split(';')

        master_model = self.utils.send_command('axsh', 'get mdl').strip()
        master_versions = self.utils.send_command('axsh', 'get swv')
        master_patch = self.utils.send_command('get_patches.sh', '')
        res = 'PASS'
        if not self.check_sw(need_sw, master_versions) or not self.check_sw(need_patch, master_patch):
            res = 'FAIL'
        print('SW ver. verification on board {}: {}'.format(master_model, res))

        slave_model = self.utils.send_command('send_msg', '-d 172.24.30.2 -c "axsh get mdl"').strip()
        slave_versions = self.utils.send_command('send_msg', '-d 172.24.30.2 -c "axsh get swv"')
        slave_path = self.utils.send_command('send_msg', '-d 172.24.30.2 -c "get_patches.sh"')
        res = 'PASS'
        if not self.check_sw(need_sw, slave_versions) or not self.check_sw(need_patch, slave_path):
            res = 'FAIL'
        print('SW ver. verification on board {}: {}'.format(slave_model, res))

    def check_sw(self, need, current):
        for ver in need:
            if str(ver).upper() not in current.upper():
                print(need, current)
                return False
        return True

    def check_bands(self):
        self.utils.print_testname('Check bands')
        status = True
        doubles = {}
        for i in self.bands:
            if i in doubles:
                doubles.update({i: False})
            else:
                doubles.update({i: True})
        if not all(doubles.values()):
            status = False
            print('Bands has same names: {}'.format(doubles))
        if not status:
            raw_input('Press Enter for return to main menu...')
        return status

    def test_band_status(self):
        self.utils.print_testname('Bands status')
        tableResult = PrettyTable(["N", self.bands[0], self.bands[1], self.bands[2], self.bands[3]])
        status = {}
        start = False
        tmp = self.utils.send_command('dobrstatus', '').split('\n')
        for n, v in enumerate(tmp):
            if 'RF Boards' in v:
                start = True
            if start and v == '':
                break
            tmp = v.split('|')
            if len(tmp) != 6:
                continue
            tableResult.add_row(tmp[:len(self.bands) + 1])
            status.update({tmp[0].strip(): [x.strip() for x in tmp[1:]]})
        print(tableResult)
        for n, band in enumerate(self.bands):
            band_result = 'PASS'
            for key in status:
                if 'OK' not in status.get(key)[n] and 'Installed' not in status.get(key)[n]:
                    band_result = 'FAIL'
            print('Band status {}: {}'.format(band, band_result))

    def ttf_calibrate(self):
        self.utils.print_testname('TTF calibration')
        ttf = TtfCalibrate(self.parent, self.utils)
        ttf.run_calibrate()

    def test_composite_power(self):
        self.utils.print_testname('Composite power')
        test_status = 'PASS'
        try:
            print('Connect Generator to Base, Spectrum to Mobile using attenuators 30 dB')
            self.utils.wait_peak(self.utils.get_band_info(1)['center'])
            for n in range(1, len(self.bands) + 1):
                band_info = self.utils.get_band_info(n)
                self.sa.write(":SENSE:FREQ:center {} MHz".format(band_info['center']))
                self.gen.write(":FREQ:FIX {} MHz".format(band_info['center']))
                self.gen.write("POW:AMPL -60 dBm")
                self.gen.write(":OUTP:STAT ON")
                self.sa.write(":CALC:MARK1:STAT ON")
                time.sleep(5)
                self.sa.write("CALC:MARK1:MAX")
                gain = float(self.sa.query("CALC:MARK1:Y?"))
                if gain > 16 or gain < 10:
                    status = 'Fail'
                    test_status = 'FAIL'
                else:
                    status = 'Pass'
                print('{} DL composite power = {} dB : {}'.format(band_info['name'], gain, status))
                self.gen.write(":OUTP:STAT OFF")
            self.parent.result_table.append(['Reading DL COMPOSITE Power', test_status])
        except Exception as e:
            print('test_composite_power ERROR: {}'.format(e))
            print('Retrying test...')
            self.test_composite_power()

    def verify_connections(self):
        self.utils.print_testname('Connection DOBR')
        status = 'PASS'
        master = self.utils.send_command('axsh', 'get MDL').strip()
        slave =self.utils.send_command('send_msg', '-d 172.24.30.2 -c "axsh get mdl"').strip()
        if master != 'DOBR-M'  or slave != 'DOBR-S':
            status = 'FAIL'
        self.parent.result_table.append(["Verify connections to both SDR'S", status])

    def clear_log(self):
        self.utils.print_testname('Clear log')
        self.utils.send_command('alarms', 'logsclear')
        logs = self.utils.send_command('alarms', 'logs').split('\n')
        status = 'PASS'
        if len(logs) > 2:
            status = 'FAIL'
        self.parent.result_table.append(['Delete Log Files', status])

    def gpr_gps_test(self):
        self.utils.print_testname('GPR & GPS')
        gde = int(self.utils.send_command('axsh', 'GET CDE').split(' ')[0])
        gpr = int(self.utils.send_command('axsh', 'GET GPR ENB'))
        apn = self.utils.send_command('axsh', 'GET GPR APN').strip()

        if gde != 1 or gpr != 1 or apn != self.config.getConfAttr('settings', 'apn'):
            print('gpr_gps_test: initialisation error')
            return
        else:
            print('gpr_gps_test: initialisation ok')

        while True:
            gps_status = 'FAIL'
            modem_status = 'FAIL'
            time_wait = int(self.config.getConfAttr('settings', 'modem_wait'))
            cur_time = time.time()
            delta_time = int(cur_time - self.parent.test_start)
            if delta_time % 10 == 0:
                if int(self.utils.send_command('axsh', 'GET GPR STATUS')) == 1:
                    modem_status = 'PASS'
                tmp = self.utils.send_command('read_gps_coordinates.sh', '')
                gps_arr = ast.literal_eval(tmp)['coordinates'][0]
                if gps_arr['x'] + gps_arr['y'] > 0:
                    gps_status = 'PASS'
                if gps_status == 'PASS' and modem_status == 'PASS':
                    break
            if delta_time // 60 >= time_wait:
                modem_status = 'FAIL'
                break
            delta = str(datetime.timedelta(seconds=int(self.parent.test_start + time_wait * 60 - cur_time)))
            stdout.write('\rWaiting GPR and GPS connection: {}'.format(delta))
            stdout.flush()
            time.sleep(1)
        print('\nModem test: {}'.format(modem_status))
        print('IP address: {}'.format(self.utils.get_ip_by_iface('wwan0')))
        print('\nGPS test: {}'.format(gps_status))
        print('Coordinates: {} : {}'.format(gps_arr['x'], gps_arr['y']))
        self.parent.result_table.append(['Modem test', modem_status])
        self.parent.result_table.append(['GPS test', gps_status])
        print('Disable Remote and Modem Communication: {}'.format(self.utils.set_remote_communication(0)))

    def mute_test(self):
        self.utils.print_testname('System mute')
        for band in range(1, len(self.bands) + 1):
            print('Set band {} Transmission: Disable'.format(self.bands[band - 1]))
            self.utils.set_filters_pa_status(band, 0)
        self.utils.set_filters(0)
        while True:
            answer = raw_input('Make sure that all bands led is RED.\nType Y or N and press ENTER... ').upper()
            if answer == 'Y':
                status = 'PASS'
            elif answer == 'N':
                status = 'FAIL'
            else:
                continue
            self.parent.result_table.append(['RF information verification', status])
            break

        for band in range(1, len(self.bands) + 1):
            print('Set band {} Transmission: Enable'.format(self.bands[band - 1]))
            self.utils.set_filters_pa_status(band, 1)

    def set_dateTime(self):
        testResult = 'PASS' if self.utils.set_datetime() else 'FAIL'
        self.parent.result_table.append(['Set Date & Time', testResult])
        print('Set Date & Time: {}'.format(testResult))


