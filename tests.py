import time
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
        test_status = 'PASS'
        keys = ['7', '6', '5', '4']
        alarms = self.utils.get_ext_alarm()
        if '0' in alarms.values():
            req = raw_input("Make sure that all Ext allarms in trigger low and press enter or Q for break test...")
            if req.upper() == 'Q':
                 self.test_ext_alarm()
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
        self.utils.set_filters()
        test_status = 'PASS'
        try:
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
            print('gpr_gps_test: initialisation ok')

        while True:
            if int(self.utils.send_command('axsh', 'GET GPR STATUS')) == 1:
                print('GPR : PASS')
                break
            print('Waiting GPR connection')
            time.sleep(10)

