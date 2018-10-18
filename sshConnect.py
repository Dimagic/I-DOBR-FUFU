import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException, BadHostKeyException
from config import Config


class SshConnect:
    def __init__(self, parent):
        self.parent = parent
        self.config = Config(parent)
        self.settings = self.config.getSection('ssh_settings')

    def connect(self, host):
        status = 'FAIL'
        try:
            print('Trying connect to {}'.format(host))
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host,
                           username=self.settings['user'],
                           password=self.settings['password'],
                           port=int(self.settings['port']), timeout=5)
            if host == self.config.getConfAttr('ssh_settings', 'host'):
                status = 'PASS'
            print('Connected to the host: {}'.format(host))
            return client
        except AuthenticationException:
            print("Authentication failed, please verify your credentials: %s")
        except SSHException as sshException:
            print("Unable to establish SSH connection: %s" % sshException)
        except BadHostKeyException as badHostKeyException:
            print("Unable to verify server's host key: %s" % badHostKeyException)
        except Exception as e:
            print("Operation error: %s" % e)
        finally:
            self.parent.result_table.append(['Setting Default IP {}'.format(host), status])

    def set_ip(self):
        client = self.connect(False)
        if client is None:
            return
        client.exec_command('/sbin/ifconfig eth0 {} netmask 255.255.255.0 up'.
                                         format(self.settings['host']), timeout=5)
        # client.exec_command('axsh SET NIC eth0 STATIC 192.168.1.253 255.255.255.0 192.168.1.254')
        self.connect(True)
