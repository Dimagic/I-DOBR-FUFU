import ast

import time


class TtfCalibrate:
    def __init__(self, parent, utils):
        self.parent = parent
        self.utils = utils
        self.ssh = utils.ssh
        self.band_fft = {1: [2, 3], 2: [0, 1], 3: [6, 7], 4: [4, 5]}
        self.uldl_table = {742.5: 707, 878: 833, 1962.5: 1882.5, 2145: 1745, 2355: 2310,
                           806: 847, 942.5: 897.5, 1842.5: 1747.5, 2140: 1950, 2655: 2535}

    def run_calibrate(self):
        for band_number, band_name in enumerate(self.utils.get_bands()):
            for uldl in [1, 0]:
                if uldl == 0:
                    continue
                self.get_peak(band_number=band_number + 1, uldl=uldl)

    def get_peak(self, band_number, uldl):
        # try:
            if uldl == 0:
                uldl_name = 'Uplink'
            else:
                uldl_name = 'Downlink'
            band_name = self.utils.send_command('dobr_filters', 'get {}'.format(band_number)).split('\n')
            freq_dl_band = [float(x) for x in band_name[1].split(':')[4:6]]
            freq_dl_center = freq_dl_band[0] + (freq_dl_band[1]-freq_dl_band[0])/2
            gen = self.parent.instrument.genPreset(freq_dl_center)
            sa = self.parent.instrument.saPreset(freq_dl_center)
            gen.write("POW:AMPL -60 dBm")
            gen.write(":OUTP:STAT ON")
            self.utils.send_command('axsh', 'SET fft {} -195'.format(self.band_fft[band_number][uldl])).strip()
            time.sleep(1)
            tmp_gain = self.utils.send_command('fft.lua', self.band_fft[band_number][uldl])
            res = ast.literal_eval(tmp_gain)
            curr_fft = (int(max(res['data'])) + 60) * (-1)
            self.utils.send_command('axsh', 'SET fft {} {}'.format(self.band_fft[band_number][uldl], curr_fft)).strip()
            time.sleep(1)
            res = ast.literal_eval(tmp_gain)
            fft = self.utils.send_command('axsh', 'GET fft {}'.format(self.band_fft[band_number][uldl])).strip()
            gain = int(fft) + int(max(res['data']))
            print('Band: {} {}; FFT: {}; Gain: {}'.format(band_name[0], uldl_name, fft, gain))

            gen.write(":OUTP:STAT OFF")

            # tmp = self.utils.send_command('fft.lua', band)
            # res = ast.literal_eval(tmp)
            # fft = self.utils.send_command('axsh', 'GET fft {}'.format(band))
            # print('Band: {}'.format(res.get('band')))
            # print('BW: {}-{}'.format(res.get('start'), res.get('stop')))
            # data = res.get('data')
            # print('Factor = {}'.format(fft))
            # print('Gain = {}'.format(int(fft) + int(max(data))))
        # except Exception as e:
        #     print('Get peak error: {}'.format(e))
        #     return False




