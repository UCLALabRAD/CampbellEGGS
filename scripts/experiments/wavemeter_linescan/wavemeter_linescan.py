import labrad
from Qsim.scripts.experiments.qsimexperiment import QsimExperiment
import time
import os


class wavemeter_linescan(QsimExperiment):

    name = 'Wavemeter Line Scan'

    exp_parameters = []
    exp_parameters.append(('wavemeterscan', 'lasername'))

    exp_parameters.append(('wavemeterscan', 'Port_369'))
    exp_parameters.append(('wavemeterscan', 'Port_399'))
    exp_parameters.append(('wavemeterscan', 'Port_935'))

    exp_parameters.append(('wavemeterscan', 'Center_Frequency_369'))
    exp_parameters.append(('wavemeterscan', 'Center_Frequency_399'))
    exp_parameters.append(('wavemeterscan', 'Center_Frequency_935'))


    def initialize(self, cxn, context, ident):

        self.ident = ident
        self.cxnwlm = labrad.connect('10.97.112.2',
                                     name='Wavemeter Scan',
                                     password=os.environ['LABRADPASSWORD'])
        self.wm = self.cxnwlm.multiplexerserver
        self.pmt = self.cxn.normalpmtflow
        self.init_mode = self.pmt.getcurrentmode()

    def run(self, cxn, context):

        should_break = self.update_progress(5.0)
        self.setup_parameters()
        self.pmt.set_mode('Normal')
        self.setup_datavault('Frequency (THz)', 'kcounts/sec')
        self.currentfreq = self.currentfrequency()
        tempdata = []
        while True:

            should_break = self.update_progress(5.0)

            if should_break:
                tempdata.sort()
                self.setup_grapher('Wavemeter Linescan')
                self.dv.add(tempdata)
                return

            counts = self.pmt.get_next_counts('ON', 1, False)[0]
            currentfreq = self.currentfrequency()

            if currentfreq and counts:
                tempdata.append([1e6*currentfreq, counts])

        if len(tempdata) > 0:
            tempdata.sort()
            self.setup_grapher('Wavemeter Linescan')
            self.dv.add(tempdata)

        time.sleep(1)

    def setup_parameters(self):
        self.laser = self.p.wavemeterscan.lasername

        if self.laser == '369':
            self.port = int(self.p.wavemeterscan.Port_369)
            self.centerfrequency = self.p.wavemeterscan.Center_Frequency_369

        elif self.laser == '399':
            self.port = int(self.p.wavemeterscan.Port_399)
            self.centerfrequency = self.p.wavemeterscan.Center_Frequency_399

        elif self.laser == '935':
            self.port = int(self.p.wavemeterscan.Port_935)
            self.centerfrequency = self.p.wavemeterscan.Center_Frequency_935

    def currentfrequency(self):
        try:
            absfreq = float(self.wm.get_frequency(self.port))
            currentfreq = absfreq - self.centerfrequency['THz']
            return currentfreq
        except:
            return None

    def finalize(self, cxn, context):
        self.pmt.set_mode(self.init_mode)
        self.cxnwlm.disconnect()

if __name__ == '__main__':
    cxn = labrad.connect()
    scanner = cxn.scriptscanner
    exprt = wavemeter_linescan(cxn=cxn)
    ident = scanner.register_external_launch(exprt.name)
    exprt.execute(ident)
