import os
import threading
import time

import datetime
from sys import stdout

import pywinauto
from pywinauto import Application, application
from pywinauto.controls.win32_controls import ComboBoxWrapper
from pywinauto.timings import Timings

from config import Config


class CheckStorm(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self.app = kwargs['app']
        self.place = kwargs['place']
        self.band = kwargs['band']
        self.currTest = kwargs['currTest']
        return

    def run(self):
        startTime = time.time()
        while True:
            currTime = time.time()
            delta = str(datetime.timedelta(seconds=int(currTime - startTime)))
            tmp = application.findwindows.find_windows(title=u'StormInterface.exe')
            dialog = application.findwindows.find_windows(title=u'Save As')
            stdout.write('\rSaving set file for band {}: {}'.format(self.band, str(delta)))
            stdout.flush()
            time.sleep(.5)
            if len(tmp) > 0:
                window = self.app.Dialog
                button = window.Button
                button.Click()
                self.app.kill()
                self.currTest(self.place, self.band)
                break
            if len(dialog) > 0:
                break


class Storm:
    def __init__(self, parent):
        self.parent = parent
        Timings.window_find_timeout = 60
        self.count_bands = 0
        self.stormpath = Config(mainProg=parent).getConfAttr('settings', 'stormpath')
        self.conn_loc_ip = '192.168.1.2'
        self.conn_rem_ip = '192.168.1.253'
        self.parent.utils.print_testname('Save set file')

    def save_setfile(self, place, band):
        app, wnd_main = self.run_storm()
        if None in (app, wnd_main):
            raw_input("\nCan't start StormInterface\nPress enter for return... ")
            self.parent.menu()
        check = CheckStorm(kwargs={'currTest': self, 'app': app, 'place': place, 'band': band})
        check.start()
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
            print('\nConnection fail. Reconnect')
            self.save_setfile(place, band)
        wnd_main[u'Create SetFile'].click()
        self.save_file(band)
        try:
            wnd_main.wait('ready')
        except pywinauto.findwindows.ElementAmbiguousError:
            getAnswer = False
            while not getAnswer:
                window = app.Dialog
                msg = window[u'Static2'].window_text()
                if msg != u'Finished to create setfile':
                    app.kill()
                else:
                    getAnswer = True
                window[u'OK'].click()
        wnd_main[u'Disconnect'].click()
        print('\nSave set file for band {} - OK'.format(band))
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
            time.sleep(1)
        try:
            app = Application().connect(title=u'Save As')
            wnd_save = app.Dialog
            wnd_save[u'Edit'].set_text(path + band)
            wnd_save.wait('ready')
            while len(application.findwindows.find_windows(title=u'Save As')) != 0:
                wnd_save.set_focus()
                wnd_save[u'&SaveButton'].click()
                time.sleep(1)
        except Exception as e:
            print(str(e))

    def is_connected(self, wnd_main):
        if wnd_main[u'Button3'].texts()[0] == 'Disconnect':
            return True

    def run_storm(self):
        app, Wnd_Main = None, None
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




