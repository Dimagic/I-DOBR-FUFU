import os
import threading
import time

import pywinauto
from pywinauto import Application, application
from pywinauto.controls.win32_controls import ComboBoxWrapper, ButtonWrapper, ListBoxWrapper
from pywinauto.timings import Timings

from config import Config


class CheckStorm(threading.Thread):
    def __init__(self, band):
        super(CheckStorm, self).__init__()
        self.band = band
        old_band = self.band
        while old_band == self.band:
            print(self.band)
            time.sleep(1)


class Storm:
    def __init__(self, parent):
        self.parent = parent
        Timings.window_find_timeout = 60
        self.count_bands = 0
        self.stormpath = 'c:\Documents and Settings\Axell\Desktop\STORM interface\StormInterface.exe'
        self.conn_loc_ip = '192.168.1.2'
        self.conn_rem_ip = '192.168.1.253'

    def save_setfile(self, place, band):
        app, wnd_main = self.run_storm()
        # check = CheckStorm(band)
        # check.run()
        if place <= 1:
            port = '30000'
        else:
            port = '30001'
        ComboBoxWrapper(wnd_main[u'Port ConnectionComboBox']).select('UDP')
        wnd_main[u'Local addEdit'].set_text(self.conn_loc_ip)
        wnd_main[u'Local portEdit'].set_text(port)
        wnd_main[u'Remote addEdit'].set_text(self.conn_rem_ip)
        wnd_main[u'Remote portEdit'].set_text(port)
        wnd_main[u'Rx Address:Edit'].set_text(band)
        ComboBoxWrapper(wnd_main[u'Rx Address:ComboBox']).select(band)
        wnd_main[u'Connect'].click()
        wnd_main.wait('ready')
        if not self.is_connected(wnd_main=wnd_main):
            print('Connection fail. Reconnect')
            self.save_setfile(place, band)
        wnd_main[u'Create SetFile'].click()
        self.save_file(band)
        try:
            wnd_main.wait('ready')
        except pywinauto.findwindows.ElementAmbiguousError:
            window = app.Dialog
            msg = window[u'Static2'].window_text()
            if msg != u'Finished to create setfile':
                app.kill()
            window[u'OK'].click()
        wnd_main[u'Disconnect'].click()
        print('Save set file for band {} - OK'.format(band))
        self.count_bands += 1
        if self.count_bands == len(self.parent.utils.get_bands()):
            app.kill()

    def save_file(self, band):
        path = self.parent.wk_dir + '\\I-DOBR\\' + self.parent.utils.get_serial() +'\\'
        try:
            os.stat(path)
        except:
            os.mkdir(path)

        while len(application.findwindows.find_windows(title=u'Save As')) == 0:
            time.sleep(.5)

        try:
            app = Application().connect(title=u'Save As')
            wnd_save = app.Dialog

            wnd_save[u'File &name:Edit'].set_text(path + band)
            wnd_save.wait('ready')
            wnd_save[u'&Save'].click()
        except Exception as e:
            print(str(e))

    def is_connected(self, wnd_main):
        if wnd_main[u'Button3'].texts()[0] == 'Disconnect':
            return True

    def set_param(self, name, val):
        pass

    def get_param(self, name):
        pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def run_storm(self):
        try:
            app = Application().connect(title_re="StormInterface")
            Wnd_Main = app.window(title_re="StormInterface")
            Wnd_Main.wait('ready')
        except:
            config = Config(self.parent)
            app = Application().start(config.getConfAttr('settings', 'stormpath'))
            Wnd_Main = app.window(title_re="StormInterface")
            Wnd_Main.wait('ready')
        finally:
            return app, Wnd_Main




    # def run_storm(self):
    #     app = Application(backend="uia")
    #     wnd_handle = application.findwindows.find_windows(title_re="StormInterface")
    #
    #     if len(wnd_handle) == 0:
    #         app.start(self.stormpath)
    #         wnd_main = app.window(title_re="StormInterface")
    #         wnd_main.wait('ready')
    #     else:
    #         wnd_main = app.connect(handle=wnd_handle[0])
    #         # wnd_main = Application(backend="uia").Connect(pid=wnd_handle[0])
    #         # wnd_main.wait('ready')
    #         for i in wnd_handle:
    #             wnd_main = app.connect(handle=wnd_handle[0])
    #             wnd_main.kill()
    #         self.run_storm()
    #     return app, wnd_main

    # def save_setfiles(self, bands):
    #     app, Wnd_Main = self.run_storm_interface()
    #     self.currentWindow = app.windows(title='StormInterface')[0]
    #     ComboBoxWrapper(Wnd_Main.ComboBox).select('UDP')
    #
    #     Wnd_Main[u'Connect'].click()
    #     try:
    #         Wnd_Main.wait('ready')
    #         self.stormConnection(Wnd_Main)
    #     except pywinauto.findwindows.ElementAmbiguousError:
    #         window = app.Dialog
    #         msg = window[u'Static2'].window_text()
    #         app.kill()
    #         try:
    #             raw_input("{}. Press enter for continue...".format(msg))
    #         except SyntaxError:
    #             pass



