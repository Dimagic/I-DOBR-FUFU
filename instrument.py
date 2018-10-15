import os
import visa
import time
from config import Config
from prettytable import PrettyTable


class Instrument:
    def __init__(self, mainProg):
        self.parent = mainProg
        self.config = Config(mainProg)

        self.sa = None
        self.gen = None
        self.sw = None
        try:
            self.rm = visa.ResourceManager()
            self.rm.timeout = 50000
        except Exception as e:
            print('Error: {}'.format(str(e)))
            raw_input('Press enter for return continue...')
            mainProg.mainMenu()

    def menu(self):
        os.system("cls")
        print("********************************")
        print("Current instruments:")
        print("********************************")
        self.fillMenuCurrInstr()
        print("1: Set instrument")
        print("0: Back")

        try:
            menu = int(input("Choose operation: "))
        except Exception:
            self.parent.menu()
        if menu == 1:
            self.menuSetInstrumentType()
        if menu == 0:
            self.parent.menu()
        else:
            self.menu()

    def menuSetInstrumentType(self):
        currInstr = sorted(dict(self.config.config.items('instruments')).keys())
        forSelect = {}
        os.system("cls")
        for i, j in enumerate(currInstr):
            j = j.upper()
            forSelect.update({i + 1: j.decode('utf-8')})
        self.fillMenuCurrInstr()
        try:
            instrType = int(raw_input('Choose instrument for changes: '))
            if instrType not in forSelect.keys():
                self.menuSetInstrumentType()
            else:
                listInstr = self.rm.list_resources()
                if len(listInstr) == 0:
                    raw_input('Available instruments not found. Press enter for return to main menu...')
                    self.parent.menu()
                dictInstr = {}
                os.system("cls")
                tableAvailInstr = PrettyTable(["#", "Address", "Manufacture", "Model", "Serial number", "Version"])
                for i, j in enumerate(listInstr):
                    i += 1
                    instr = self.rm.open_resource(j, send_end=False)
                    lineForParse = instr.query('*IDN?').strip().split(',')
                    tableAvailInstr.add_row([i, j, lineForParse[0], lineForParse[1], lineForParse[2], lineForParse[3]])
                    if len(lineForParse) != 0:
                        dictInstr.update({i: instr.query('*IDN?').split(',')[1]})
                tableAvailInstr.add_row(["0", "None", "-", "-", "-", "-"])
                print(tableAvailInstr)
                instrModel = int(raw_input('Choose instrument: '))
                if instrModel == 0:
                    self.config.setConfAttr('instruments', forSelect.get(instrType), '')
                else:
                    self.config.setConfAttr('instruments', forSelect.get(instrType), dictInstr.get(instrModel))
                self.menu()
        except Exception as e:
            raw_input(str(e))
            self.menuSetInstrumentType()

    def fillMenuCurrInstr(self):
        currInstr = dict(self.config.config.items('instruments'))
        listNameRes = self.getListInstrument()
        print(listNameRes)
        tableInstr = PrettyTable(["#", "Type", "Model", "Address", "Availability"])
        for n, i in enumerate(sorted(currInstr.keys())):
            if currInstr.get(i).decode('utf-8') in ('None', ''):
                tableInstr.add_row([n + 1, i.decode('utf-8').upper(), currInstr.get(i).decode('utf-8'), '', ''])
                continue
            if currInstr.get(i).decode('utf-8') in listNameRes.values():
                addr = listNameRes.keys()[listNameRes.values().index(currInstr.get(i).decode('utf-8'))]
                status = 'Availabe'
            else:
                addr = ''
                status = 'Not availabe'
            tableInstr.add_row([n + 1, i.decode('utf-8').upper(), currInstr.get(i).decode('utf-8'), addr, status])
        print(tableInstr)

    def getListInstrument(self):
        listRes = self.rm.list_resources()
        listNameRes = {}
        for i in listRes:
            instr = self.rm.open_resource(i, send_end=False)
            listNameRes.update({i: instr.query('*IDN?').split(',')[1].replace(' ', '')})
        return listNameRes

    def getInstr(self, val):
        listRes = self.rm.list_resources()
        for i in listRes:
            instr = self.rm.open_resource(i, send_end=False)
            currInstr = instr.query('*IDN?').split(',')[1].upper().replace(' ', '')
            if val.upper() == currInstr.upper():
                return instr
        return None

    def saPreset(self, freq):
        self.sa = self.getInstr(self.config.getConfAttr('instruments', 'sa'))
        self.sa.write(":SYST:PRES")
        self.sa.write(":CAL:AUTO OFF")
        self.sa.write(":SENSE:FREQ:center {} MHz".format(freq))
        self.sa.write(":SENSE:FREQ:span {} MHz".format(3.5))
        self.sa.write("DISP:WIND:TRAC:Y:RLEV:OFFS 30")
        self.sa.write(":BAND:VID 27 KHz")
        return self.sa

    def genPreset(self, freq):
        self.gen = self.getInstr(self.config.getConfAttr('instruments', 'gen'))
        self.gen.write("*RST")
        self.gen.write(":POW:OFFS -30 dB")
        self.gen.write(":OUTP:STAT OFF")
        self.gen.write(":OUTP:MOD:STAT OFF")
        self.gen.write(":FREQ:FIX {} MHz".format(freq))
        return self.gen

    def swPreset(self):
        pass

    def setGenPow(self, need):
        span = self.parent.limitsAmpl.get('freqstop') - self.parent.limitsAmpl.get('freqstart')
        center = self.parent.limitsAmpl.get('freqstart') + span / 2
        self.sa.write(":SENSE:FREQ:center {} MHz".format(center))
        self.sa.write("DISP:WIND:TRAC:Y:RLEV:OFFS {}".format(self.getOffset()))
        self.sa.write(":POW:ATT 0")
        self.sa.write(":DISP:WIND:TRAC:Y:RLEV {}".format(float(self.getOffset()) - 10))
        genList = (self.gen)
        for curGen, freq in enumerate([center - 0.3,  + 0.3]):
            self.sa.write(":CALC:MARK1:STAT ON")
            self.sa.write(":CALC:MARK1:X {} MHz".format(freq))
            gen = genList[curGen]
            gen.write(":FREQ:FIX {} MHz".format(freq))
            gen.write("POW:AMPL -65 dBm")
            gen.write(":OUTP:STAT ON")
            time.sleep(1)
            self.setGainTo(gen=gen, need=need)
            gen.write(":OUTP:STAT OFF")
        self.gen.write(":OUTP:STAT ON")
        time.sleep(1)

    def setGainTo(self, gen, need):
        gain = float(self.sa.query("CALC:MARK1:Y?"))
        genPow = float(gen.query("POW:AMPL?"))
        acc = 0.1
        while not (gain - acc <= need <= gain + acc):
            if genPow >= 0:
                gen.write("POW:AMPL -65 dBm")
                self.gen.write(":OUTP:STAT OFF")
                raw_input("Gain problem. Press enter for continue...")
                self.parent.menu()
            gen.write("POW:AMPL {} dBm".format(genPow))
            gain = float(self.sa.query("CALC:MARK1:Y?"))
            time.sleep(.1)
            delta = abs(need - gain)
            if delta <= 0.7:
                steep = 0.01
            elif delta <= 5:
                steep = 0.5
            elif delta <= 10:
                steep = 1
            else:
                steep = 5
            if gain < need:
                genPow += steep
            else:
                genPow -= steep

    def getOffset(self):
        try:
            offList = []
            span = self.parent.limitsAmpl.get('freqstop') - self.parent.limitsAmpl.get('freqstart')
            center = self.parent.limitsAmpl.get('freqstart') + span / 2
            f = open(self.config.getConfAttr('settings', 'calibrationFile'), "r")
            for line in f:
                off = line.strip().split(';')
                off[0] = float(off[0])/1000000
                offList.append(off)
            for n in offList:
                if n[0] <= center < n[0] + 70:
                    return n[1]
        except Exception as e:
            print(str(e))
            raw_input('Calibration data file open error. Press enter for continue...')
            self.parent.menu()
