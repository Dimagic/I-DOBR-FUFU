import re
import sys
import socket
import threading
import subprocess
import ipaddress
from sys import stdout
import netaddr
import time

pIpAddress = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
pNetwork = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.)")
pMacAddress = re.compile(r"(([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))")


class RunScanner(threading.Thread):
    def __init__(self, parent, host, mac, all_hosts):
        threading.Thread.__init__(self)
        self.parent = parent
        self.host = host
        self.all_hosts = all_hosts
        self.mac = mac
        self.selfIp = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if ip.startswith("11.")][:1][0]
        self.info = subprocess.STARTUPINFO()
        self.info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.info.wShowWindow = subprocess.SW_HIDE

    def run(self):
        curr_host = self.host - 1
        output = subprocess.Popen(['ping', '-n', '1', '-w', '500', str(self.all_hosts[curr_host])],
                                  stdout=subprocess.PIPE, startupinfo=self.info).communicate()[0]
        if self.parent.ip_mtdi is not None:
            return
        stdout.write("\rSearching IP by MAC: {} {}".format(self.all_hosts[curr_host], threading.active_count()))
        stdout.flush()
        if "TTL=" in output.decode('utf-8') and self.parent.ip_mtdi is None:
            pid = subprocess.Popen(["arp", "-a", str(self.all_hosts[curr_host])], stdout=subprocess.PIPE)
            s = pid.communicate()[0].decode("utf-8").split('\n')
            for k in s:
                if pMacAddress.search(k) is not None:
                    if self.mac.upper() == pMacAddress.search(k).groups()[0].upper():
                        ip = pIpAddress.search(k).groups()[0]
                        # self.testResult.update({"ip": ip})
                        stdout.write("\rCurrent host is {}\n".format(ip))
                        stdout.flush()
                        self.parent.ip_mtdi = ip


class NetScanner:
    def __init__(self, mac):
        self.info = subprocess.STARTUPINFO()
        self.info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.info.wShowWindow = subprocess.SW_HIDE
        tmp = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if ip.startswith("11.")][:1][0]
        self.ip_addr = netaddr.IPAddress(tmp)
        ip_net = netaddr.IPNetwork(pNetwork.search(tmp).group(0) + '0/24')
        self.all_hosts = list(ip_net.iter_hosts())
        self.mac = mac
        self.ip_mtdi = None
        self.trying = False

    def start_scan(self):

        for i in range(254, 0, -1):
            if self.ip_mtdi is not None:
                break
            thread1 = RunScanner(parent=self, host=i, mac=self.mac, all_hosts=self.all_hosts)
            thread1.start()
        if self.ip_mtdi is None and not self.trying:
            self.trying = True
            self.start_scan()
        time.sleep(1)
        return self.ip_addr, self.ip_mtdi