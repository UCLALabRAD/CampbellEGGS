import numpy as np
from common.lib.clients.qtui.QCustomSpinBox import QCustomSpinBox
from twisted.internet.defer import inlineCallbacks
from PyQt4 import QtGui
from PyQt4.Qt import QPushButton
from config.dac_8718_config import dac_8718_config


class Electrode(object):

    def __init__(self, name):
        self.name = name
        self._set_number()
        # Nominally the self.currentvalues value below.
        self.value = None

    def _set_number(self):
        # TODO: more intelligently...
        if self.name == 'DAC 0':
            self.number = 0
        elif self.name == 'DAC 1':
            self.number = 1
        elif self.name == 'DAC 2':
            self.number = 2
        elif self.name == 'DAC 3':
            self.number = 3
        elif self.name == 'DAC 4':
            self.number = 4
        elif self.name == 'DAC 5':
            self.number = 5
        elif self.name == 'DAC 6':
            self.number = 6
        elif self.name == 'DAC 7':
            self.number = 7
        else:
            self.number = None

    def get_voltage(self):
        bit = self.value
        voltage = (2.2888e-4*bit - 7.5)
        return voltage

    @property
    def voltage(self):
        return self.get_voltage()


class Electrodes(object):
    def __init__(self):
        # Access electrodes by name.
        self._electrode_dict = {}
        self._populate_electrodes_dict()

        # Repetition of electrode collections
        self._set_electrode_collections()

    def _populate_electrodes_dict(self):
        # TODO: better way to populate this dictionary.
        electrode_0 = Electrode(name='DAC 0')
        self._electrode_dict[electrode_0.name] = electrode_0
        electrode_1 = Electrode(name='DAC 1')
        self._electrode_dict[electrode_1.name] = electrode_1
        electrode_2 = Electrode(name='DAC 2')
        self._electrode_dict[electrode_2.name] = electrode_2
        electrode_3 = Electrode(name='DAC 3')
        self._electrode_dict[electrode_3.name] = electrode_3
        electrode_4 = Electrode(name='DAC 4')
        self._electrode_dict[electrode_4.name] = electrode_4
        electrode_5 = Electrode(name='DAC 5')
        self._electrode_dict[electrode_5.name] = electrode_5
        electrode_6 = Electrode(name='DAC 6')
        self._electrode_dict[electrode_6.name] = electrode_6
        electrode_7 = Electrode(name='DAC 7')
        self._electrode_dict[electrode_7.name] = electrode_7

    def get_electrode_value(self, name=None):
        """
        Returns electrode bit value (float?) given the electrode name (str).
        """
        electrode = self._electrode_dict[name]
        return electrode.value

    def get_electrode_voltage(self, name=None):
        """
        Returns float for electrode voltage value given the electrode name.
        """
        electrode = self._electrode_dict[name]
        return electrode.voltage

    def set_electrode_value(self, name=None, value=None):
        """
        Set electrode value (float) given the electrode name (str).
        """
        # print "set_electrode_value:", name
        # print "\t value=", value
        self._electrode_dict[name].value = value

    def _set_electrode_collections(self):
        """
        Set list collections of the different electrode names for accessing
        various multipole moments of the electrodes.
        """
        self._top = ['DAC 0', 'DAC 1', 'DAC 2', 'DAC 3']
        self._bottom = ['DAC 4',  'DAC 5', 'DAC 6', 'DAC 7']
        self._x_minus = ['DAC 2', 'DAC 6']
        self._x_plus = ['DAC 0', 'DAC 4']
        self._y_minus = ['DAC 1', 'DAC 5']
        self._y_plus = ['DAC 3', 'DAC 7']

    @property
    def x_dipole_moment(self):
        return self._dipole_moment(self._x_plus, self._x_minus)

    @property
    def y_dipole_moment(self):
        return self._dipole_moment(self._y_plus, self._y_minus)

    @property
    def z_dipole_moment(self):
        # TODO: consider name changes for the z-electrode values
        return self._dipole_moment(self._top, self._bottom)

    def _dipole_moment(self, plus_electrodes, minus_electrodes):
        """
        Return the dipole moment between the plus and minus electrodes.

        Parameters
        ----------
        plus_electrodes: list of strs, plus electrode names.
        minus_electrodes: list of strs, minus electrode names.
        """
        plus_values = []
        for name in plus_electrodes:
            value = self.get_electrode_voltage(name=name)
            plus_values.append(value)
        plus_mean = np.mean(plus_values)

        minus_values = []
        for name in minus_electrodes:
            value = self.get_electrode_voltage(name=name)
            minus_values.append(value)
        minus_mean = np.mean(minus_values)

        dipole_moment = plus_mean - minus_mean
        return dipole_moment


class dacclient(QtGui.QWidget):

    def __init__(self, reactor, parent=None):
        """initializes the GUI creates the reactor
            and empty dictionary for channel widgets to
            be stored for iteration.
        """

        super(dacclient, self).__init__()
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.reactor = reactor
        self.d = {}
        self.e = {}
        self.topelectrodes = {'DAC 0': 0, 'DAC 1': 1, 'DAC 2': 2, 'DAC 3': 3}
        self.bottomelectrodes = {'DAC 4': 4,  'DAC 5': 5,  'DAC 6': 6, 'DAC 7': 7}
        self.xminuselectrodes = {'DAC 2': 2, 'DAC 6': 6}
        self.xpluselectrodes = {'DAC 0': 0, 'DAC 4': 4}
        self.yminuselectrodes = {'DAC 1': 1, 'DAC 5': 5}
        self.ypluselectrodes = {'DAC 3': 3, 'DAC 7': 7}
        self.electrodes = Electrodes()
        self.connect()

    @inlineCallbacks
    def connect(self):
        """Creates an Asynchronous connectiontry:
    from config.arduino_dac_config import arduino_dac_config
except:
    from common.lib.config.arduino_dac_config import arduino_dac_config
        """
        from labrad.wrappers import connectAsync
        from labrad.units import WithUnit as U

        self.U = U
        self.cxn = yield connectAsync(name="dac8718 client")
        self.server = yield self.cxn.dac8718_server
        self.reg = yield self.cxn.registry

        try:
            yield self.reg.cd('settings')
            self.settings = yield self.reg.dir()
            self.settings = self.settings[1]
        except:
            self.settings = []

        self.config = dac_8718_config
        self.initializeGUI()

    @inlineCallbacks
    def initializeGUI(self):

        layout = QtGui.QGridLayout()

        qBox = QtGui.QGroupBox('DAC Channels')
        subLayout = QtGui.QGridLayout()
        qBox.setLayout(subLayout)
        layout.addWidget(qBox, 0, 0)
        self.multipole_step = 10
        self.currentvalues = {}

        self.Ex_label = QtGui.QLabel('E_x')
        self.Ey_label = QtGui.QLabel('E_y')
        self.Ez_label = QtGui.QLabel('E_z')
        self.Ex_squeeze_label = QtGui.QLabel('E_x squeeze')
        self.Ey_squeeze_label = QtGui.QLabel('E_y squeeze')
        self.Ez_squeeze_label = QtGui.QLabel('E_z squeeze')

        for channel_key in self.config.channels:
            name = self.config.channels[channel_key].name
            chan_number = self.config.channels[channel_key].number

            widget = QCustomSpinBox(name, (0, 2**16 - 1))
            widget.title.setFixedWidth(120)
            label = QtGui.QLabel('0 V')
            if name in self.settings:
                value = yield self.reg.get(name)
                widget.spinLevel.setValue(value)
                self.currentvalues.update({name: value})
                self.set_value_no_widgets(value, [name, chan_number])
            else:
                widget.spinLevel.setValue(0.0)
            widget.setStepSize(1)
            widget.spinLevel.setDecimals(0)
            widget.spinLevel.valueChanged.connect(lambda value=widget.spinLevel.value(),
                                                  ident=[name, chan_number]:
                                                  self.set_value_no_widgets(value, ident))

            self.d[chan_number] = widget
            self.e[chan_number] = label
            subLayout.addWidget(self.d[chan_number],  chan_number, 1)
            subLayout.addWidget(self.e[chan_number], chan_number, 2)

        self.exsqueezeupwidget = QPushButton('X Squeeze increase')
        self.exsqueezedownwidget = QPushButton('X Squeeze decrease')
        self.eysqueezeupwidget = QPushButton('Y Squeeze increase')
        self.eysqueezedownwidget = QPushButton('Y Squeeze decrease')

        self.ezupwidget = QPushButton('Ez increase')
        self.ezdownwidget = QPushButton('Ez decrease')
        self.exupwidget = QPushButton('Ex increase')
        self.exdownwidget = QPushButton('Ex decrease')
        self.eyupwidget = QPushButton('Ey increase')
        self.eydownwidget = QPushButton('Ey decrease')
        self.save_widget = QPushButton('Save current values to Registry')

        self.dipole_res = QCustomSpinBox('Dipole Res', (0, 1000))
        self.dipole_res.spinLevel.setValue(10)
        self.dipole_res.setStepSize(1)
        self.dipole_res.spinLevel.setDecimals(0)

        self.exsqueezeupwidget.clicked.connect(self.ex_squeeze_up)
        self.eysqueezeupwidget.clicked.connect(self.ey_squeeze_up)

        self.exsqueezedownwidget.clicked.connect(self.ex_squeeze_down)
        self.eysqueezedownwidget.clicked.connect(self.ey_squeeze_down)

        self.ezupwidget.clicked.connect(self.ezup)
        self.ezdownwidget.clicked.connect(self.ezdown)
        self.exupwidget.clicked.connect(self.exup)
        self.exdownwidget.clicked.connect(self.exdown)
        self.eyupwidget.clicked.connect(self.eyup)
        self.eydownwidget.clicked.connect(self.eydown)
        self.dipole_res.spinLevel.valueChanged.connect(self.update_dipole_res)
        self.save_widget.clicked.connect(self.save_to_registry)

        subLayout.addWidget(self.ezupwidget,   0, 5)
        subLayout.addWidget(self.ezdownwidget, 1, 5)
        subLayout.addWidget(self.exupwidget,   3, 6)
        subLayout.addWidget(self.exdownwidget, 3, 3)
        subLayout.addWidget(self.eyupwidget,   2, 5)
        subLayout.addWidget(self.eydownwidget, 4, 5)
        subLayout.addWidget(self.dipole_res,   3, 5)
        subLayout.addWidget(self.save_widget,  5, 5)
        subLayout.addWidget(self.Ex_label,     6, 5)
        subLayout.addWidget(self.Ey_label,     7, 5)
        subLayout.addWidget(self.Ez_label,     8, 5)
        subLayout.addWidget(self.Ex_squeeze_label, 9, 5)
        subLayout.addWidget(self.Ey_squeeze_label, 10, 5)
        subLayout.addWidget(self.Ez_squeeze_label, 11, 5)

        subLayout.addWidget(self.exsqueezeupwidget,   6, 6)
        subLayout.addWidget(self.exsqueezedownwidget, 6, 7)
        subLayout.addWidget(self.eysqueezeupwidget,   7, 6)
        subLayout.addWidget(self.eysqueezedownwidget, 7, 7)

        self.setLayout(layout)

    @inlineCallbacks
    def ezup(self, isheld):
        for name, dacchan in self.topelectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.bottomelectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def ezdown(self, isheld):
        for name, dacchan in self.bottomelectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.topelectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def exup(self, isheld):
        for name, dacchan in self.xpluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.xminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def exdown(self, isheld):
        for name, dacchan in self.xminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.xpluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def eyup(self, isheld):
        for name, dacchan in self.ypluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.yminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def eydown(self, isheld):
        for name, dacchan in self.yminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.ypluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def ey_squeeze_up(self, isheld):
        for name, dacchan in self.ypluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.yminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def ey_squeeze_down(self, isheld):
        for name, dacchan in self.ypluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.yminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def ex_squeeze_up(self, isheld):
        for name, dacchan in self.xpluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.xminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            new_value = currentvalue + self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def ex_squeeze_down(self, isheld):
        for name, dacchan in self.xpluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

        for name, dacchan in self.xminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            new_value = currentvalue - self.multipole_step
            yield self.setvalue(new_value, [name, dacchan])

    @inlineCallbacks
    def setvalue(self, value, ident):
        """
        Parameters
        ----------
        value: float?  - converted to an int
        ident: tuple, (name, chan) where name is a str and chan is an int
        """
        yield self.set_value_no_widgets(value=value, ident=ident)
        channel_number = ident[1]
        # change the GUI display value
        self.d[channel_number].spinLevel.setValue(value)

    @inlineCallbacks
    def set_value_no_widgets(self, value, ident):
        """
        Parameters
        ----------
        value: float?  - converted to an int
        ident: tuple, (name, chan) where name is a str and chan is an int
        """
        name = ident[0]
        channel_number = ident[1]
        value = int(value)
        self._set_electrode_current_value(name, value)
        yield self.server.dacoutput(channel_number, value)
        voltage = self.bit_to_volt(bit=value)
        self.e[channel_number].setText(str(voltage))
        self.currentvalues[name] = value
        self.set_dipole_labels()

    def bit_to_volt(self, bit):
        voltage = (2.2888e-4*bit - 7.5)
        return voltage

    def _set_electrode_current_value(self, name=None, value=None):
        """
        Set electrode value in the Electrodes class.
        """
        self.electrodes.set_electrode_value(name=name, value=value)

    def set_dipole_labels(self):
        xdipole = self.electrodes.x_dipole_moment
        ydipole = self.electrodes.y_dipole_moment
        zdipole = self.electrodes.z_dipole_moment

        self.Ex_label.setText('Ex = ' + str(xdipole))
        self.Ey_label.setText('Ey = ' + str(ydipole))
        self.Ez_label.setText('Ez = ' + str(zdipole))

    def set_squeeze_labels(self):
        pass


    def update_dipole_res(self, value):
        self.multipole_step = value

    def save_to_registry(self):
        for chan in self.currentvalues:
            self.reg.set(chan, self.currentvalues[chan])

    def closeEvent(self, x):
        print 'Saving DAC values to regisry...'
        self.save_to_registry()
        print 'Saved.'
        self.reactor.stop()


if __name__ == "__main__":
    a = QtGui.QApplication([])
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    dacWidget = dacclient(reactor)
    dacWidget.show()
    reactor.run()  # @UndefinedVariable
