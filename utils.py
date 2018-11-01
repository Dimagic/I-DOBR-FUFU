import ast
import re
import time

import sys

import datetime
from prettytable import PrettyTable
from config import Config
from net_scanner import NetScanner
from sshConnect import SshConnect


class Utils:
    pIpAddress = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
    pNetwork = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.)")
    pMacAddress = re.compile(r"(([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))")
    pIdProc = re.compile(r"^[0-9\s]+")
    pUptimeFull = re.compile(r"^[0-9a-z:\s]+")
    pUptime = re.compile(r"(\d){1,2}:(\d\d)$")

    def __init__(self, parent):
        self.parent = parent
        self.config = Config(mainProg=parent)
        self.ssh = None
        if sys._getframe(1).f_code.co_name == 'run_fufu':
            sshConnect = SshConnect(parent)
            self.set_ip(sshConnect)
            if self.ssh is None:
                parent.menu()

    def send_command(self, command, arg):
        # print('>> {} {}'.format(command, arg))
        stdin, stdout, stderr = self.ssh.exec_command('find / -name {}'.format(command), timeout=5)
        cmd_path = str(stdout.read() + stderr.read()).split('\n')
        cmd_path.remove('')
        for val in cmd_path:
            if re.search(r'({}$)'.format(command), val):
                # print(val)
                stdin, stdout, stderr = self.ssh.exec_command('{} {}'.format(val, arg), timeout=5)
                for_return = stdout.read() + stderr.read()
                return for_return
        print('{} not found'.format(command))
        raw_input("Press enter to continue")
        return self.parent.menu()

    def set_ip(self, sshConnect):
        settings = self.config.getSection('ssh_settings')
        self.ssh = sshConnect.connect(settings['host'])
        if self.ssh is not None:
            return
        self.ssh = sshConnect.connect(settings['usbhost'])
        if self.ssh is None:
            return
        self.send_command('axsh', 'SET NIC eth0 STATIC {} {} {}'.format(settings['host'],
                                                                        settings['mask'],
                                                                        settings['gtw']))
        self.send_command('ifconfig', 'eth0 {} netmask {} up'.format(settings['host'],
                                                                     settings['mask']))
        for_check = self.send_command('axsh', 'get nic eth0').strip().split(' ')
        for i in for_check[1:]:
            if i not in settings.values():
                print('Trying set static ip is FAIL')
                self.ssh.close()
                self.ssh = None
                return
        self.ssh.close()
        self.ssh = sshConnect.connect(settings['host'])

    def get_ext_alarm(self):
        alarms = {}
        tmp = self.send_command('get_ext_alarm.sh', '').split('\n')
        for i in tmp:
            if re.search(r'(EXT_ALM)', i) is None or i == '':
                continue
            alarms.update({re.search(r'(^\d)', i).group(): re.search(r'(\d$)', i).group()})
        return alarms

    def get_bands(self):
        bands = []
        q = self.send_command('udp_bridge1', 'list').split('\n')
        for i in q:
            r = re.search('(ABCD\d\d)', i)
            if r is not None:
                bands.append(r.group(0))
        if len(bands) != 4:
            print('Found only {} bands'.format(len(bands)))
            print(self.send_command('udp_bridge1', 'list'))
            raw_input('Press Enter for return...')
            self.parent.menu()
        return bands

    def get_serial(self):
        return self.send_command('get_serial', '').strip()

    def get_ip_by_iface(self, iface):
        tmp = self.send_command("ifconfig", "{} | grep 'inet addr:' | cut -d: -f2".format(iface)).replace('Bcast', '')
        return tmp

    def set_filters(self, enable_filter):
        # dobr_filters SET |band_index| |filter_num| |Tag| |Enable| |Tech| |DL_start_freq|
        #                  |DL_stop_freq| |DL_max_power| |DL_max_gain| |power_delta| |Gain_delta|
        for n, band in enumerate(self.get_bands()):
            curr_filter = self.send_command('dobr_filters', 'GET {}'.format(n + 1)).split('\n')
            conf_filter = self.config.getConfAttr('filters', curr_filter[0]).split(';')
            band_index = n + 1
            tech = 'GSM'
            center = float(conf_filter[0])
            bw = float(conf_filter[1])
            DL_start_freq = center - (bw / 2)
            DL_stop_freq = center + (bw / 2)
            print('Setting filter for {}'.format(curr_filter[0]))
            # print('dobr_filters SET {} 1 1 1 {} {} {} 24 73 3 0'.format(band_index, tech, DL_start_freq, DL_stop_freq))
            res = ast.literal_eval(self.send_command('dobr_filters', 'SET {} 1 1 {} {} {} {} 24 73 3 0'.
                              format(band_index, enable_filter, tech, DL_start_freq, DL_stop_freq)))
            self.set_imop_status(n + 1, 0)
            print('Set filter {}: {}'.format(curr_filter[0], res['DOBR FILTER'][0]['Status']))
            print('-'*50)

    def set_filters_pa_status(self, band, status):
        try:
            self.send_command('dobr_pa_control', 'SET {} {}'.format(band, status))
        except Exception as e:
            print(e)

    def get_filters_pa_status(self):
        res = []
        for i in range(len(self.get_bands())):
            status = int(self.send_command('dobr_pa_control', 'GET {}'.format(i + 1)).split()[0])
            res.append(status)
        return res

    def set_imop_status(self, band, status):
        try:
            self.send_command('imop_control', 'SET {} {}'.format(band, status))
        except Exception as e:
            print(e)

    def get_band_info(self, band_number):
        band_info = {}
        band_name = self.send_command('dobr_filters', 'get {}'.format(band_number)).split('\n')
        freq_dl_band = [float(x) for x in band_name[1].split(':')[4:6]]
        freq_dl_center = freq_dl_band[0] + (freq_dl_band[1] - freq_dl_band[0]) / 2
        band_info.update({'name': band_name[0], 'start': freq_dl_band[0],
                          'stop': freq_dl_band[1], 'center': freq_dl_center})
        return band_info

    def print_table(self, column_name, row_data):
        table = PrettyTable(["Section"] + column_name)
        for n, row in enumerate(row_data):
            n += 1
            table.add_row([n] + row)
        print(table)

    def set_remote_communication(self, status):
        # Remote Communication:    axsh SET CDE 1
        # Enable Modem Connection: axsh SET GPR ENB 0
        # Check Modem Connection: asch GET GPR STATUS
        self.send_command('axsh', 'SET CDE {}'.format(status))
        self.send_command('axsh', 'SET GPR ENB {}'.format(status))
        if status == 1:
            self.send_command('axsh', 'SET GPR APN {}'.format(self.config.getConfAttr('settings', 'apn')))
        else:
            self.send_command("axsh", "SET GPR APN ''")

        comm = int(self.send_command('axsh', 'GET CDE'.format(status)).split(' ')[0])
        modem = int(self.send_command('axsh', 'GET GPR ENB'))
        test = [int(comm), int(modem)]
        apn = self.send_command('axsh', 'GET GPR APN').strip()

        if status == 0 and apn == '':
            test.append(0)
        if status == 1 and apn == self.config.getConfAttr('settings', 'apn'):
            test.append(1)

        if status == 0 and sum(test) == 0:
            return True
        elif status == 1 and sum(test) == 3:
            return True
        else:
            return False

    def wait_peak(self, freq):
        try:
            gen = self.parent.instrument.genPreset(freq)
            sa = self.parent.instrument.saPreset(freq)
            sa.write(":CALC:MARK1:STAT ON")
            sa.write("CALC:MARK1:MAX")
            gen.write("POW:AMPL -60 dBm")
            gen.write(":OUTP:STAT ON")
            time.sleep(5)
            while float(sa.query("CALC:MARK:Y?")) < 0:
                sa.write("CALC:MARK1:MAX")
                time.sleep(1)
            return True
        except Exception as e:
            print('Wait_peak Error: {}'.format(e))
            self.wait_peak(freq)

    def getAvalIp(self, **kwargs):
        if kwargs['ip'] is not None:
            self.ssh = SshConnect(self).connect(kwargs['ip'])
            return

        macForSearch = raw_input('Input mac-address and press Enter: ').upper().replace(":", "-")
        try:
            # self.waiter(5)
            macForSearch = self.pMacAddress.search(macForSearch).group(0)
            print('MAC for connection: {}'.format(macForSearch))
            self.scanner = NetScanner(macForSearch)
            self_ip, mtdi_ip = self.scanner.start_scan()
            if mtdi_ip is None:
                print('\nSystem with mac-address: {} not found online'.format(macForSearch))
            else:
                return (mtdi_ip)
        except Exception as e:
            print('\ngetAvalIp error: {}'.format(e))
        raw_input('Press Enter for return...')
        return None

    def testsQueue(self):
        pass

    def set_datetime(self):
        now = datetime.datetime.now()
        dt = now.strftime("%d%m%y")
        tm = now.strftime("%H%M%S")
        self.send_command('axsh', 'SET DAT {}'.format(dt))
        self.send_command('axsh', 'SET TIM {}'.format(tm))
        remoteDT = self.send_command('axsh', 'GET DAT')
        remoteTM = self.send_command('axsh', 'GET TIM')
        if abs(int(dt) - int(remoteDT)) == 0 or abs(int(tm) - int(remoteTM)) < 5:
             return True

    def print_testname(self, name):
        print('*' * 50)
        print('Current test: {}'.format(name))
        print('*' * 50)
