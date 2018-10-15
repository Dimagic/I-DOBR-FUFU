import ast

import configparser


class Config:
    def __init__(self, mainProg):
        self.parent = mainProg
        self.config = configparser.ConfigParser()
        self.configFile = './config.ini'
        self.config.read(self.configFile, encoding='utf-8-sig')
        self.getSection('ssh_settings')

    def getConfAttr(self, blockName, attrName):
        try:
            self.config.read(self.configFile, encoding='utf-8-sig')
            return str(self.config.get(blockName, attrName))
        except Exception as e:
            print('ERROR: {}'.format(str(e)))
            raw_input("Press enter to continue...")
            self.parent.mainMenu()
            return False

    def setConfAttr(self, section, system, value):
        self.config.read(self.configFile)
        cfgfile = open(self.configFile, 'w')
        self.config.set(section, system, value)
        self.config.write(cfgfile)
        cfgfile.close()
        return True

    def getSection(self, arg):
        try:
            tmp = {}
            for i in self.config.items(arg):
                tmp.update(dict([i]))
            return tmp
        except configparser.NoSectionError:
            print('Section {} not found'.format(arg))