import ast
import time
from sys import stdout
import datetime
from prettytable import PrettyTable
from config import Config

# /mnt/axell_cfg/etc/target/current/operators/band_1_filters_setting.dat
# /mnt/axell_cfg/etc/target/current/operators/filter_cell_res_list.dat
# axsh get nic eth0
# dobr_filters SET 1 1 - 0 GSM 1875 1880 24 73 3 0
# dobr_filters get all
# axsh set fft 1 -200
# axsh get fft 1
# dobr_pa_control SET 2 1
# imop_control SET 2 0
from instrument import Instrument
from ttfCalibration import TtfCalibrate


class Tests:
    def __init__(self, parent, utils):
        self.parent = parent
        self.utils = utils
        self.ssh = utils.ssh
        self.config = Config(parent)

    def test_ext_alarm(self):
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
        print('\nSW version and installed patch verification:')
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
        status = True
        bands = self.utils.get_bands()
        doubles = {}
        for i in bands:
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
        bands = self.utils.get_bands()
        tableResult = PrettyTable(["N", bands[0], bands[1], bands[2], bands[3]])
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
            tableResult.add_row(tmp[:len(bands) + 1])
            status.update({tmp[0].strip(): [x.strip() for x in tmp[1:]]})
        print(tableResult)
        for n, band in enumerate(bands):
            band_result = 'PASS'
            for key in status:
                if 'OK' not in status.get(key)[n] and 'Installed' not in status.get(key)[n]:
                    band_result = 'FAIL'
            print('Band status {}: {}'.format(band, band_result))

    def ttf_calibrate(self):
        ttf = TtfCalibrate(self.parent, self.utils)
        ttf.run_calibrate()

    def test_band_mute(self):
        bands = self.utils.get_bands()
        for band, val in enumerate(bands):
            pass

    def test_composite_power(self):
        test_status = 'PASS'
        try:
            print('Connect Generator to Base, Spectrum to Mobile using attenuators 30 dB')
            self.utils.wait_peak(self.utils.get_band_info(1)['center'])

            for n in range(1, len(self.utils.get_bands()) + 1):
                band_info = self.utils.get_band_info(n)
                gen = self.parent.instrument.genPreset(band_info['center'])
                sa = self.parent.instrument.saPreset(band_info['center'])
                gen.write("POW:AMPL -60 dBm")
                gen.write(":OUTP:STAT ON")
                sa.write(":CALC:MARK1:STAT ON")
                sa.write("CALC:MARK:CPE 1")
                time.sleep(5)
                gain = float(sa.query("CALC:MARK:Y?"))
                if gain > 16 or gain < 10:
                    status = 'Fail'
                    test_status = 'FAIL'
                else:
                    status = 'Pass'
                print('{} DL composite power = {} dB : {}'.format(band_info['name'], gain, status))
                gen.write(":OUTP:STAT OFF")
            self.parent.result_table.append(['Reading DL COMPOSITE Power', test_status])
        except Exception as e:
            print('test_composite_power: {}'.format(e))
            self.test_composite_power()

    def verify_connections(self):
        status = 'PASS'
        master = self.utils.send_command('axsh', 'get MDL').strip()
        slave =self.utils.send_command('send_msg', '-d 172.24.30.2 -c "axsh get mdl"').strip()
        if master != 'DOBR-M'  or slave != 'DOBR-S':
            status = 'FAIL'
        self.parent.result_table.append(["Verify connections to both SDR'S", status])

    def clear_log(self):
        self.utils.send_command('alarms', 'logsclear')
        logs = self.utils.send_command('alarms', 'logs').split('\n')
        status = 'PASS'
        if len(logs) > 2:
            status = 'FAIL'
        self.parent.result_table.append(['Delete Log Files', status])

    def gpr_gps_test(self):
        gde = int(self.utils.send_command('axsh', 'GET CDE').split(' ')[0])
        gpr = int(self.utils.send_command('axsh', 'GET GPR ENB'))
        apn = self.utils.send_command('axsh', 'GET GPR APN').strip()

        if gde != 1 or gpr != 1 or apn != self.config.getConfAttr('settings', 'apn'):
            print('gpr_gps_test: initialisation error')
            return
        else:
            start_time = time.time()
            print('gpr_gps_test: initialisation ok')

        while True:
            gps_status = 'FAIL'
            modem_status = 'FAIL'
            cur_time = time.time()
            delta_time = int(cur_time - start_time)
            if delta_time % 10 == 0:
                if int(self.utils.send_command('axsh', 'GET GPR STATUS')) == 1:
                    modem_status = 'PASS'
                tmp = self.utils.send_command('read_gps_coordinates.sh', '')
                gps_arr = ast.literal_eval(tmp)['coordinates'][0]
                if gps_arr['x'] + gps_arr['y'] > 0:
                    gps_status = 'PASS'
                if gps_status == 'PASS' and modem_status == 'PASS':
                    break
            if delta_time // 60 >= 2:
                modem_status = 'FAIL'
                break
            delta = str(datetime.timedelta(seconds=int(cur_time - start_time)))
            stdout.write('\rWaiting GPR and GPS connection: {}'.format(delta))
            stdout.flush()
            time.sleep(1)
        print('\nModem test: {}'.format(modem_status))
        print('\nGPS test: {}'.format(gps_status))
        self.parent.result_table.append(['Modem test', modem_status])
        self.parent.result_table.append(['GPS test', gps_status])
        print('Disable Remote and Modem Communication: {}'.format(self.utils.set_remote_communication(0)))

    def mute_test(self):
        bands = self.utils.get_bands()
        for band in range(1, len(bands) + 1):
            print('Set band {} Transmission: Disable'.format(bands[band - 1]))
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

        for band in range(1, len(bands) + 1):
            print('Set band {} Transmission: Enable'.format(bands[band - 1]))
            self.utils.set_filters_pa_status(band, 1)



