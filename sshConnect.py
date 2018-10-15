import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException, BadHostKeyException
from config import Config


class SshConnect:
    def __init__(self, parent):
        self.parent = parent
        self.settings = Config(parent).getSection('ssh_settings')

    def connect(self, use_eth):
        try:
            host = self.settings['host'] if use_eth else self.settings['usbhost']
            print('Trying connect to {}'.format(host))
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host,
                           username=self.settings['user'],
                           password=self.settings['password'],
                           port=int(self.settings['port']), timeout=5)
            print('Connected to the host: {}'.format(self.settings['host']))
            return client
        except AuthenticationException:
            print("Authentication failed, please verify your credentials: %s")
        except SSHException as sshException:
            print("Unable to establish SSH connection: %s" % sshException)
        except BadHostKeyException as badHostKeyException:
            print("Unable to verify server's host key: %s" % badHostKeyException)
        except Exception as e:
            print("Operation error: %s" % e)

    def setIp(self):
        client = self.connect(False)
        if client is None:
            return
        client.exec_command('/sbin/ifconfig eth0 {} netmask 255.255.255.0 up'.
                                         format(self.settings['host']), timeout=5)
        self.connect(True)

    # def sendCommand(self, command):
    #     try:
    #         stdin, stdout, stderr = self.client.exec_command(command, timeout=5)
    #         return stdout.read() + stderr.read()
    #     except Exception as e:
    #         print("Run command error: {}".format(str(e)))
    #         return None

    # def getIdProcByName(self, name):
    #     data = self.sendCommand('ps')
    #     answer = data.decode("utf-8").split('\n')
    #     for i in answer:
    #         if name not in i:
    #             continue
    #         else:
    #             return self.pIdProc.search(i).group(0)
    #     return None
    #
    # def getDeviceName(self):
    #     listDir = list(self.sendCommand('ls /mnt/axell/etc/target').decode('utf-8').split('\n'))
    #     for i in listDir:
    #         if i not in ('current', ''):
    #             return i
    #     return None
    #
    # def getDeviceMac(self):
    #     ifaces = self.sendCommand("/sbin/ifconfig -a |awk '/^[a-z]/ { iface=$1; mac=$NF; next }/inet addr:/ { print iface, mac }'").decode('utf-8').split('\n')
    #     for i in ifaces:
    #         if 'eth0' in i.lower():
    #             return self.pMacAddress.search(i).group(0)
    #     return None