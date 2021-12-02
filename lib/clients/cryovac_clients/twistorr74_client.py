import os
import time
import datetime as datetime

from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks

from EGGS_labrad.lib.clients.cryovac_clients.twistorr74_gui import twistorr74_gui

class twistorr74_client(twistorr74_gui):

    name = 'Twistorr74 Client'
    ID = 694321

    def __init__(self, reactor, cxn=None, parent=None):
        super().__init__()
        self.cxn = cxn
        self.gui = self
        self.reactor = reactor
        d = self.connect()
        d.addCallback(self.initializeGUI)

    @inlineCallbacks
    def connect(self):
        """
        Creates an asynchronous connection to pump servers
        and relevant labrad servers
        """
        if not self.cxn:
            import os
            LABRADHOST = os.environ['LABRADHOST']
            from labrad.wrappers import connectAsync
            self.cxn = yield connectAsync(LABRADHOST, name=self.name)

        try:
            self.reg = self.cxn.registry
            self.dv = self.cxn.data_vault
            self.tt = self.cxn.twistorr74_server
        except Exception as e:
            print(e)
            raise

        # get polling time
        # yield self.reg.cd(['Clients', self.name])
        # self.poll_time = yield float(self.reg.get('poll_time'))
        self.poll_time = 5.0

        # set recording stuff
        self.c_record = self.cxn.context()
        self.recording = False
        #create and start loop to poll server for temperature
        self.poll_loop = LoopingCall(self.poll)
        from twisted.internet.reactor import callLater
        callLater(2.0, self.start_polling)

        yield self.tt.signal__emitted_signal(self.ID)
        yield self.tt.addListener(listener=self.thkim, source=None, ID=self.ID)

        return self.cxn

    def thkim(self, c, val):
        #print(val)
        pass

    #@inlineCallbacks
    def initializeGUI(self, cxn):
        #startup data
        #todo
        #connect signals to slots
        self.gui.twistorr_lockswitch.toggled.connect(lambda status: self.lock_twistorr(status))
        self.gui.twistorr_power.toggled.connect(lambda status: self.toggle_twistorr(status))
        self.gui.twistorr_record.toggled.connect(lambda status: self.record_pressure(status))

    #Slot functions
    @inlineCallbacks
    def record_pressure(self, status):
        """
        Creates a new dataset to record pressure and tells polling loop
        to add data to data vault
        """
        self.recording = status
        if self.recording:
            self.starttime = time.time()
            date = datetime.datetime.now()
            year = str(date.year)
            month = '%02d' % date.month  # Padded with a zero if one digit
            day = '%02d' % date.day  # Padded with a zero if one digit
            hour = '%02d' % date.hour  # Padded with a zero if one digit
            minute = '%02d' % date.minute  # Padded with a zero if one digit

            trunk1 = year + '_' + month + '_' + day
            trunk2 = self.name + '_' + hour + ':' + minute
            yield self.dv.cd(['', year, month, trunk1, trunk2], True, context=self.c_record)
            yield self.dv.new('Twistorr 74 Pump Controller', [('Elapsed time', 't')],
                              [('Pump Pressure', 'Pressure', 'mbar')], context=self.c_record)

    @inlineCallbacks
    def toggle_twistorr(self, status):
        """
        Sets pump power on or off.
        """
        yield self.tt.toggle(status)

    def lock_twistorr(self, status):
        """
        Locks power status of pump.
        """
        self.gui.twistorr_power.setEnabled(status)

    #Polling functions
    def start_polling(self):
        self.poll_loop.start(self.poll_time)

    def stop_polling(self):
        self.poll_loop.stop()

    @inlineCallbacks
    def poll(self):
        pressure = yield self.tt.read_pressure()
        self.gui.twistorr_display.setText(str(pressure))
        if self.recording == True:
            elapsedtime = time.time() - self.starttime
            yield self.dv.add(elapsedtime, pressure, context=self.c_record)

    def closeEvent(self, event):
        self.cxn.disconnect()
        if self.reactor.running:
            self.reactor.stop()


if __name__ == "__main__":
    from EGGS_labrad.lib.clients import runClient
    runClient(twistorr74_client)
