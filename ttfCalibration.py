import ast

import time


class TtfCalibrate:
    def __init__(self, parent, utils):
        self.parent = parent
        self.utils = utils
        self.ssh = utils.ssh
        self.test_status = 'PASS'
        # {band_number: [UL, DL]}
        self.band_fft = {1: [2, 3], 2: [0, 1], 3: [6, 7], 4: [4, 5]}
        # {DL center: UL center}
        self.uldl_table = {742.5: 707, 878: 833, 1962.5: 1882.5, 2145: 1745, 2355: 2310,
                           806: 847, 942.5: 897.5, 1842.5: 1747.5, 2140: 1950, 2655: 2535}

    def run_calibrate(self):
        for uldl in [1, 0]:
            band_info = self.parent.utils.get_band_info(band_number=1)
            if uldl == 0:
                print('Connect Spectrum to Base, Generator to Mobile using attenuators 30 dB')
                center_freq = self.uldl_table[band_info['center']]
            if uldl == 1:
                print('Connect Generator to Base, Spectrum to Mobile using attenuators 30 dB')
                center_freq = band_info['center']
            self.utils.wait_peak(center_freq)

            for band_number, band_name in enumerate(self.utils.get_bands()):
                self.get_peak(band_number=band_number + 1, uldl=uldl)
        self.parent.result_table.append(['Setting Spectrum Power Factor', self.test_status])

    def get_peak(self, band_number, uldl):
        # try:
            band_info = self.parent.utils.get_band_info(band_number=band_number)
            if uldl == 0:
                uldl_name = 'Uplink'
                center_freq = self.uldl_table[band_info['center']]
            else:
                uldl_name = 'Downlink'
                center_freq = band_info['center']

            gen = self.parent.instrument.genPreset(center_freq)
            sa = self.parent.instrument.saPreset(center_freq)


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
            print('\nBand: {} {}; FFT: {}; Gain: {}'.format(band_info['name'], uldl_name, fft, gain))
            fft_delta = abs(202 - abs(curr_fft))
            if fft_delta > 10:
                self.test_status = 'FAIL'

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








