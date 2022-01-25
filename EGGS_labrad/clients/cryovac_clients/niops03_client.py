import time
from datetime import datetime

from twisted.internet.defer import inlineCallbacks

from EGGS_labrad.clients.cryovac_clients.niops03_gui import niops03_gui


class niops03_client(niops03_gui):

    name = 'NIOPS03 Client'
    PRESSUREID = 878352
    VOLTAGEID = 878353
    TEMPERATUREID = 878354
    IPPOWERID = 878355
    NPPOWERID = 878356

    def __init__(self, reactor, cxn=None, parent=None):
        super().__init__()
        self.cxn = cxn
        self.gui = self
        self.reactor = reactor
        self.servers = ['NIOPS03 Server', 'Data Vault']
        # initialization sequence
        d = self.connect()
        d.addCallback(self.initData)
        d.addCallback(self.initializeGUI)


    # SETUP
    @inlineCallbacks
    def connect(self):
        """
        Creates an asynchronous connection to labrad
        """
        # create labrad connection
        if not self.cxn:
            import os
            LABRADHOST = os.environ['LABRADHOST']
            from labrad.wrappers import connectAsync
            self.cxn = yield connectAsync(LABRADHOST, name=self.name)

        # try to get servers
        try:
            self.reg = self.cxn.registry
            self.dv = self.cxn.data_vault
            self.niops = self.cxn.niops03_server
        except Exception as e:
            print('Required servers not connected, disabling widget.')
            self.setEnabled(False)

        # set recording stuff
        self.c_record = self.cxn.context()
        self.recording = False

        # connect to signals
            # device signals
        yield self.niops.signal__pressure_update(self.PRESSUREID)
        yield self.niops.addListener(listener=self.updatePressure, source=None, ID=self.PRESSUREID)
        yield self.niops.signal__voltage_update(self.VOLTAGEID)
        yield self.niops.addListener(listener=self.updateVoltage, source=None, ID=self.VOLTAGEID)
        yield self.niops.signal__temperature_update(self.TEMPERATUREID)
        yield self.niops.addListener(listener=self.updateTemperature, source=None, ID=self.TEMPERATUREID)
        yield self.niops.signal__ip_power_update(self.IPPOWERID)
        yield self.niops.addListener(listener=self.updateIPPower, source=None, ID=self.IPPOWERID)
        yield self.niops.signal__np_power_update(self.NPPOWERID)
        yield self.niops.addListener(listener=self.updateNPPower, source=None, ID=self.NPPOWERID)
            # server connections
        yield self.cxn.manager.subscribe_to_named_message('Server Connect', 9898989, True)
        yield self.cxn.manager.addListener(listener=self.on_connect, source=None, ID=9898989)
        yield self.cxn.manager.subscribe_to_named_message('Server Disconnect', 9898989 + 1, True)
        yield self.cxn.manager.addListener(listener=self.on_disconnect, source=None, ID=9898989 + 1)

        # start device polling
        poll_params = yield self.niops.polling()
        # only start polling if not started
        if not poll_params[0]:
            yield self.niops.polling(True, 5.0)

        return self.cxn

    @inlineCallbacks
    def initData(self, cxn):
        """
        Get startup data from servers and show on GUI.
        """
        #IP/NP power
        device_status = yield self.niops.status()
        device_status = device_status.strip().split(', ')
        device_status = [text.split(' ') for text in device_status]
        device_status = {val[0]: val[1] for val in device_status}
        ip_on = True if device_status['IP'] == 'ON' else False
        np_on = True if device_status['NP'] == 'ON' else False
        self.gui.ip_power.setChecked(ip_on)
        self.gui.np_power.setChecked(np_on)
        #IP voltage
        v_ip = yield self.niops.ip_voltage()
        self.gui.ip_voltage_display.setText(str(v_ip))
        self.gui.ip_voltage.setEnabled(ip_on)
        return cxn

    @inlineCallbacks
    def initializeGUI(self, cxn):
        """
        Connect signals to slots and other initializations.
        """
        #ion pump
        self.gui.ip_lockswitch.toggled.connect(lambda status: self.lock_niops(status))
        self.gui.ip_power.clicked.connect(lambda status: self.toggle_niops(status))
        self.gui.ip_record.toggled.connect(lambda status: self.record_pressure(status))
        self.gui.ip_voltage.valueChanged.connect(lambda voltage: self.set_ip_voltage(voltage))
        #getter
        self.gui.np_lockswitch.toggled.connect(lambda status: self.lock_np(status))
        self.gui.np_mode.currentIndexChanged.connect(lambda index: self.mode_np(index))
        self.gui.np_power.clicked.connect(lambda status: self.toggle_np(status))


    # SIGNALS
    @inlineCallbacks
    def on_connect(self, c, message):
        server_name = message[1]
        if server_name in self.servers:
            print(server_name + ' reconnected, enabling widget.')
            yield self.initData(self.cxn)
            self.setEnabled(True)

    def on_disconnect(self, c, message):
        server_name = message[1]
        if server_name in self.servers:
            print(server_name + ' disconnected, disabling widget.')
            self.setEnabled(False)


    # SLOTS
    @inlineCallbacks
    def updatePressure(self, c, pressure):
        self.gui.ip_pressure_display.setText(str(pressure))
        if self.recording:
            elapsedtime = time.time() - self.starttime
            yield self.dv.add(elapsedtime, pressure, context=self.c_record)

    def updateVoltage(self, c, voltage):
        # set workingtime
        self.gui.ip_voltage_display.setText(str(voltage))

    def updateTemperature(self, c, temperatures):
        # set workingtime
        self.gui.ip_temperature_display.setText(str(temperatures[0]))
        self.gui.np_temperature_display.setText(str(temperatures[1]))

    def updateIPPower(self, c, power):
        # set IP power
        self.gui.ip_voltage.setEnabled(power)
        self.gui.ip_power.setChecked(power)

    def updateNPPower(self, c, power):
        # set NP power
        self.gui.np_power.setChecked(power)

    @inlineCallbacks
    def record_pressure(self, status):
        """
        Creates a new dataset to record pressure and
        tells polling loop to add data to data vault.
        """
        # set up datavault
        self.recording = status
        if self.recording == True:
            self.starttime = time.time()
            date = datetime.now()
            year = str(date.year)
            month = '{:02d}'.format(date.month)

            trunk1 = '{0:s}_{1:s}_{2:02d}'.format(year, month, date.day)
            trunk2 = '{0:s}_{1:02d}:{2:02d}'.format(self.name, date.hour, date.minute)
            yield self.dv.cd(['', year, month, trunk1, trunk2], True, context=self.c_record)
            yield self.dv.new('NIOPS03 Pump', [('Elapsed time', 's')], \
                                       [('Ion Pump', 'Pressure', 'mbar')], context=self.c_record)

    @inlineCallbacks
    def toggle_niops(self, status):
        """
        Sets ion pump power on or off.
        """
        #print('set: ' + str(status))
        self.gui.ip_voltage.setEnabled(status)
        yield self.niops.ip_toggle(status)

    def lock_niops(self, status):
        """
        Locks power status of ion pump.
        """
        self.gui.ip_voltage.setEnabled(status)
        self.gui.ip_power.setEnabled(status)

    @inlineCallbacks
    def set_ip_voltage(self, voltage):
        """
        Sets the ion pump voltage.
        """
        yield self.niops.ip_voltage(int(voltage))

    @inlineCallbacks
    def toggle_np(self, status):
        """
        Sets getter power on or off.
        """
        #print('state: ' + str(status))
        yield self.niops.np_toggle(status)

    def lock_np(self, status):
        """
        Locks power status of getter.
        """
        self.gui.np_power.setEnabled(status)

    def mode_np(self, index):
        """
        Set activation mode of getter.
        """
        self.niops.np_mode(index + 1)

    def closeEvent(self, event):
        self.cxn.disconnect()
        if self.reactor.running:
            self.reactor.stop()


if __name__ == "__main__":
    from EGGS_labrad.clients import runClient
    runClient(niops03_client)