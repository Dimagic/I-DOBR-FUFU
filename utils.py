import ast
import re

import time

from config import Config
from sshConnect import SshConnect


class Utils:
    def __init__(self, parent):
        self.parent = parent
        self.config = Config(mainProg=parent)
        sshConnect = SshConnect(parent)
        self.ssh = sshConnect.connect(True)
        if self.ssh is None:
            sshConnect.setIp()
            self.ssh = sshConnect.connect(True)

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
        input("Press enter to continue")
        return self.parent.menu()

    def get_ext_alarm(self):
        alarms = {}
        tmp = self.send_command('get_ext_alarm.sh', '').split('\n')
        for i in tmp:
            if re.search(r'(EXT_ALM)', i) is None or i == '':
                continue
            alarms.update({re.search(r'(^\d)', i).group(): re.search(r'(\d$)', i).group()})
        return alarms

    def connect_ssh(self, host, user, password, port):
        # If host == None, use host from config
        # if host is None:
        #     host = self.config.getConfAttr('ssh_settings', 'host')
        # user = self.config.getConfAttr('ssh_settings', 'user')
        # password = self.config.getConfAttr('ssh_settings', 'secret')
        # port = int(self.config.getConfAttr('ssh_settings', 'port'))
        connection = SshConnect(parent=self.parent).connect(host=host, user=user, password=password, port=port)
        if connection.client is None:
            print("Can't establish connection with {}".format(host))
            input('Press enter for continue...')
            self.parent.menu()
        # else:
        #     return connection.client

    def get_bands(self):
        bands = []
        q = self.send_command('udp_bridge1', 'list').split('\n')
        for i in q:
            r = re.search('(ABCD\d\d)', i)
            if r is not None:
                bands.append(r.group(0))
        return bands

    def get_serial(self):
        return self.send_command('get_serial', '').strip()

    # def set_ip(self):
    #     host = self.config.getConfAttr('ssh_settings', 'host')
    #     usbHost = self.config.getConfAttr('ssh_settings', 'usbHost')
    #     self.ssh = self.connect_ssh(usbHost)
    #     curr_ip = self.send_command('axsh', 'get nic eth0').split(' ')
    #     if curr_ip[1] != host:
    #         print('Setting eth0 ip = {}'.format(host))
    #         self.ssh.exec_command('/sbin/ifconfig eth0 {} netmask 255.255.255.0 up'.format(host), timeout=5)
    #         # self.send_command('ifconfig', 'eth0 {} netmask 255.255.255.0 up'.format(host))
    #         self.ssh = self.connect_ssh(host)

    def set_filters(self):
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
            print('dobr_filters SET {} 1 1 1 {} {} {} 24 73 3 0'.format(band_index, tech, DL_start_freq, DL_stop_freq))
            res = ast.literal_eval(self.send_command('dobr_filters', 'SET {} 1 1 1 {} {} {} 24 73 3 0'.
                              format(band_index, tech, DL_start_freq, DL_stop_freq)))
            self.set_imop_status(n + 1, 0)
            print('Set filter {}: {}'.format(curr_filter[0], res['DOBR FILTER'][0]['Status']))
            print('-'*100)

    def set_filters_pa_status(self, status):
        for n, band in enumerate(self.get_bands()):
            try:
                self.send_command('dobr_pa_control', 'SET {} {}'.format(n + 1, status))
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