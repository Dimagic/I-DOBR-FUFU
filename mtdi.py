import re
import time
import datetime
import subprocess
from config import Config
from net_scanner import NetScanner
from sys import stdout
from sshConnect import SshConnect
from utils import Utils
# 00-14-B1-02-9C-C9


class Mtdi:
    def __init__(self, parent):
        # self.pIpAddress = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
        # self.pNetwork = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.)")
        # self.pMacAddress = re.compile(r"(([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))")
        # self.pIdProc = re.compile(r"^[0-9\s]+")
        # self.pUptimeFull = re.compile(r"^[0-9a-z:\s]+")
        # self.pUptime = re.compile(r"(\d){1,2}:(\d\d)$")
        self.info = subprocess.STARTUPINFO()
        self.info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.info.wShowWindow = subprocess.SW_HIDE
        self.parent = parent
        self.config = Config(mainProg=parent)
        self.utils = Utils(self)
        self.sn = None
        self.name = None
        self.scanner = None
        self.client = None
        self.mtdi_ip = None
        self.runMtdiDoha()

    def runMtdiDoha(self):
        self.getAvalIp()
        if not self.verifiDevice('MTDI'):
            raw_input('Device {} not support. Press enter to continue'.format(self.name))
            self.utils.ssh.close()
            self.parent.menu()
        self.waitUpTime(10)
        for n in range(5):
            self.utils.send_command('rm', '/tmp/SuperviseTheDaemons')
            stdout.write('\rRemove directory {}'.format(n))
            time.sleep(1)
        stdout.write("\n")

        self.killProc(('hw_watchdog.sh', 'xmasd -d'))
        self.waitReboot()
        # self.writeLog('MTDI DOHA')
        self.client.close()
        # self.testResult.update({'date': datetime.datetime.now()})
        # self.testResult.update('teststatus_id', )
        # try:
        #     Logger().setData('test_log', self.testResult)
        # except sqlalchemy.exc as e:
        #     print(str(e))
        raw_input("Press enter to continue")
        self.parent.menu()

    def getAvalIp(self):
        macForSearch = raw_input('Input mac-address or Ip and press Enter: ').upper().replace(":", "-")
        try:
            self.mtdi_ip = self.utils.pIpAddress.search(macForSearch).group(0)
            for i in list(self.mtdi_ip.split('.')):
                if int(i) > 255:
                    self.parent.menu()
            print('IP for connection: {}'.format(self.mtdi_ip))
        except Exception:
            try:
                self.waiter(5)
                macForSearch = self.utils.pMacAddress.search(macForSearch).group(0)
                print('MAC for connection: {}'.format(macForSearch))
                self.scanner = NetScanner(macForSearch)
                self_ip, self.mtdi_ip = self.scanner.start_scan()
            except Exception:
                self.parent.menu()

        if self.mtdi_ip is None:
            stdout.write('\rSystem not found in LAN.\n')
            stdout.flush()
            raw_input('Press enter for return...')
            self.parent.menu()
        self.utils.ssh = SshConnect(self).connect(self.mtdi_ip)
        self.client = self.utils.ssh
        if self.client is None:
            raw_input('Press enter for return...')
            self.parent.menu()

    def waiter(self, n):
        try:
            waitTime = n
            print('\nPress Ctrl+C for start now')
            while waitTime >= 0:
                stdout.write('\rContinue after {} seconds'.format(waitTime))
                time.sleep(1)
                waitTime -= 1
        except KeyboardInterrupt:
            pass
        finally:
            print('\n')

    def killProc(self, nameProcList):
        idDict = {}
        for proc in nameProcList:
            idDict.update({proc: self.getIdProcByName(proc)})
        if None in idDict.values():
            for i in reversed(range(60)):
                stdout.write("\rNot found all process. Waiting {} seconds".format(i))
                stdout.flush()
                time.sleep(1)
            stdout.write("\n")
            self.killProc(nameProcList)
        for idProcess in idDict:
            self.utils.send_command('kill', '-9 {}'.format(idDict.get(idProcess)))
            time.sleep(1)
            if self.getIdProcByName(idProcess) is not None:
                self.killProc(nameProcList)
            print('Kill process {} {}'.format(idDict.get(idProcess), idProcess))

    def getDeviceName(self):
        listDir = list(self.utils.send_command('ls', '/mnt/axell/etc/target').decode('utf-8').split('\n'))
        for i in listDir:
            if i not in ('current', ''):
                return i

    def verifiDevice(self, var):
        self.name = self.getDeviceName()
        cfg = list(self.config.getConfAttr('devices', var).split(';'))
        if self.name in cfg:
            return True
        return False

    def getDeviceMac(self):
        cmd = "/sbin/ifconfig -a |awk '/^[a-z]/ { iface=$1; mac=$NF; next }/inet addr:/ { print iface, mac }'"
        ifaces = self.utils.send_command(cmd).decode('utf-8').split('\n')
        for i in ifaces:
            if 'eth0' in i.lower():
                return self.utils.pMacAddress.search(i).group(0)

    def getIdProcByName(self, name):
        data = self.utils.send_command('ps', '')
        answer = data.decode("utf-8").split('\n')
        for i in answer:
            if name not in i:
                continue
            else:
                return self.utils.pIdProc.search(i).group(0)

    def waitReboot(self):
        w = 0
        while "TTL=" in subprocess.Popen(['ping', '-n', '1', '-w', '500', self.mtdi_ip],
                                         stdout=subprocess.PIPE,
                                         startupinfo=self.info).communicate()[0].decode('utf-8'):
            try:
                # answer = self.utils.send_command('uptime').decode('utf-8')
                # answer = self.pUptimeFull.search(answer).group(0)
                uptime = self.waitUpTime(0)
                stdout.write("\rUptime: {}".format(datetime.timedelta(seconds=uptime)))
                time.sleep(1)
            except Exception:
                if w == 0:
                    stdout.write('\n')
                    stdout.flush()
                w += 1
                stdout.write("\rDevice will reboot now: {} seconds".format(w))
                stdout.flush()
                time.sleep(1)
        stdout.write('\n')
        w = 0
        while "TTL=" not in subprocess.Popen(['ping', '-n', '1', '-w', '500', self.mtdi_ip],
                                         stdout=subprocess.PIPE,
                                         startupinfo=self.info).communicate()[0].decode('utf-8'):
            w += 1
            stdout.write("\rWaiting boot {} seconds".format(w))
            time.sleep(1)
        stdout.write('\n')
        print("Boot complete")

    def waitUpTime(self, needTime):
        if needTime != 0:
            print("Waiting uptime > {} minutes".format(needTime))
        while True:
            uptime = int(float(self.utils.send_command("awk",
                                                       "'{print $1}' /proc/uptime").decode('utf-8').replace('\n', '')))
            if needTime == 0:
                return uptime
            if uptime/60.0 > 13:
                self.client.exec_command('/sbin/reboot', timeout=5)
                self.waitReboot()
                self.utils.ssh = SshConnect(self).connect(self.mtdi_ip)
                self.client = self.utils.ssh
            stdout.write("\r{}".format(datetime.timedelta(seconds=uptime)))
            if uptime/60.0 > needTime:
                stdout.write("\n")
                break