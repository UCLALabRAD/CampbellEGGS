from common.lib.clients.qtui.QCustomSpinBox import QCustomSpinBox
from Qsim.clients.qtui.electrodewidget import ElectrodeIndicator
from twisted.internet.defer import inlineCallbacks
from PyQt4 import QtGui
from PyQt4.Qt import QPushButton
from config.dac_8718_config import dac_8718_config
from electrodes import Electrodes


class ElectrodeWedgeGUI():

    def __init__(self, electrode):
        """
        Parameters
        ----------
        electrode: Electrode instance.
        """
        self.electrode = electrode
        self.name = electrode.name
        self.dac_channel = electrode.number
        self.octant = electrode.number
        self.minval = 0
        self.maxval = int(2**16) - 1

        if self.octant == 0:
            self.is_plus_x = True
            self.is_plus_x = False
            self.is_minus_x = True
            self.is_minus_x = False
            self.is_minus_y = True
            self.is_minus_y = False
            self.is_plus_y = True
            self.is_plus_y = False
            self.is_plus_z = True
            self.is_minus_z = False
            self.is_plus_z = False
            self.is_minus_z = True

        self.setup_widget()

    def setup_widget(self):
        self.spinBox = QCustomSpinBox(self.name, (self.minval, self.maxval))

        try:
            self.initial_bit_value = self.electrode.bit_value
        except:
            self.initial_bit_value = int(2**15)
        self.spinBox.spinLevel.setValue(self.initial_bit_value)

        self.spinBox.setStepSize(1)
        self.spinBox.spinLevel.setDecimals(1)


class DAC8718Client(QtGui.QWidget):

    def __init__(self, reactor, parent=None):

        super(DAC8718Client, self).__init__()
        self.electrodes = Electrodes()
        self.max_bit_value = 2**16 - 1
        self.min_bit_value = 0
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.reactor = reactor
        self.config = dac_8718_config()
        self.minval = self.config.minval
        self.maxval = self.config.maxval
        self.step_size = 0.01
        self.connect()

    @inlineCallbacks
    def connect(self):

        from labrad.wrappers import connectAsync
        from labrad.units import WithUnit as U

        self.U = U
        self.cxn = yield connectAsync(name="dac8718 client")
        self.server = self.cxn.dac8718_server
        self.reg = self.cxn.registry
        yield self.get_settings()
        yield self.initialize_GUI()

    @inlineCallbacks
    def get_settings(self):

        self.settings = {}
        yield self.reg.cd('settings', True)
        self.keys = yield self.reg.dir()
        self.keys = self.keys[1]
        for key in self.keys:
            value = yield self.reg.get(key)
            self.settings[key] = value

    def initialize_GUI(self):

        self.layout = QtGui.QGridLayout()
        qBox = QtGui.QGroupBox('DAC Channels')

        self.subLayout = QtGui.QGridLayout()
        qBox.setLayout(self.subLayout)
        self.layout.addWidget(qBox, 0, 0)

        self.electrode_indicator = ElectrodeIndicator(self.minval, self.maxval)

        self._add_electrode_guis()
        self._add_quadrupole_widgets()
        #self._add_dipole_widgets()

        step_size_box = QCustomSpinBox('Step Size', (0.0001, 3))
        step_size_box.setStepSize(1e-6)
        step_size_box.spinLevel.setDecimals(6)
        self.update_step_size(step_size=1e-6)
        step_size_box.spinLevel.setValue(self.step_size)
        step_size_box.spinLevel.valueChanged.connect(self.update_step_size)

        save_widget = QPushButton('Save values')
        save_widget.clicked.connect(self.save_to_registry)

        self.layout.addWidget(self.electrode_indicator, 0, 1, 1, 3)

        self.layout.addWidget(step_size_box, 9, 0)
        self.layout.addWidget(save_widget, 10, 0)

        self.electrodes.initialize_multipole_values()
        self.update_all_dac_channels()
        self.update_all_gui_indicators()

        self.setLayout(self.layout)

    def _add_electrode_guis(self):
        self.electrode_guis = {}
        for channel_config in self.config.channels:
            channel_name = channel_config.name
            initial_bit_value = self.settings[channel_name]
            self.electrodes.set_electrode_bit_value(name=channel_name,
                                                    value=initial_bit_value)

            electrode = self.electrodes.get_electrode(name=channel_name)
            electrode_gui = ElectrodeWedgeGUI(electrode=electrode)
            self.electrode_guis[channel_name] = electrode_gui
            self.subLayout.addWidget(electrode_gui.spinBox)

    def _add_dipole_widgets(self):
        print "_add_dipole_widgets"
        dipoles_names = ['Ex', 'Ey', 'Ez']
        self.dipole_indicators = []
        for kk, dipole_name in enumerate(dipoles_names):
            print "dipole_name:", dipole_name
            # Value indicator.
            lcd = QtGui.QLCDNumber()
            # Prevents "light" outline coloring from obscuring the numbers.
            lcd.setSegmentStyle(QtGui.QLCDNumber.Flat)
            lcd.setMinimumSize(50, 50)
            self.layout.addWidget(lcd, 3, kk, 1, 1)
            self.dipole_indicators.append(lcd)
            # Up and down value control buttons
            up_name = dipole_name + ' up'
            up_button = QtGui.QPushButton(up_name)
            down_name = dipole_name + ' down'
            down_button = QtGui.QPushButton(down_name)
            multipole_change = self.change_multipole_moment
            up_function = lambda up: multipole_change(up_button.text())
            up_button.clicked.connect(up_function)
            down_text = down_button.text()
            down_function = lambda text = down_text : multipole_change(button_name=text)
            down_button.clicked.connect(down_function)
            self.layout.addWidget(up_button, 4, kk)
            self.layout.addWidget(down_button, 5, kk)

    def _add_quadrupole_widgets(self):
        quadrupole_names = ['Exx_yy', 'Ezz_xx_yy', 'Exy', 'Eyz', 'Ezx']
        self.quadrupole_indicators = []
        for kk, quadrupole_name in enumerate(quadrupole_names):
            # Value indicator.
            lcd = QtGui.QLCDNumber()
            # Prevents "light" outline coloring from obscuring the numbers.
            lcd.setSegmentStyle(QtGui.QLCDNumber.Flat)
            lcd.setMinimumSize(50, 50)
            self.layout.addWidget(lcd, 8, kk, 1, 1)
            self.quadrupole_indicators.append(lcd)
            # Up and down value control buttons
            up_name = quadrupole_name + ' up'
            up_button = QtGui.QPushButton(up_name)
            down_name = quadrupole_name + ' down'
            down_button = QtGui.QPushButton(down_name)
            multipole_change = self.change_multipole_moment
            up_function = lambda: self.change_multipole_moment(up_name)
            up_button.clicked.connect(up_function)
            down_text = down_button.text()
            print "down_text:", down_text
            #down_function = lambda: self.change_multipole_moment(down_name)
            down_button.clicked.connect(self.change_multipole_moment(down_name))
            #down_button.clicked.connect(lambda: multipole_change(down_button))
            self.layout.addWidget(up_button, 6, kk)
            self.layout.addWidget(down_button, 7, kk)

    def change_multipole_moment(self, button):
        button_name = button#.text()
        print "button_name:", button_name
        self._update_multipoles_from_button_name(button_name=button_name)
        self.electrodes.update_voltages_from_multipole_moments()
        self.update_all_dac_channels()
        self.update_all_gui_indicators()

    def _update_multipoles_from_button_name(self, button_name):
        print "_update_multipoles_from_button_name"
        if 'up' in button_name:
            sign = 1
        else:
            sign = -1
        delta_value = sign * self.step_size

        multipole_name = self._multipole_name_from_button(button_name)

        multipole_moments = self.electrodes.multipole_moments
        current_value = multipole_moments.get_value(multipole_name)
        print "\t current_value:", current_value
        new_value = current_value + delta_value
        self.electrodes.multipole_moments.set_value(name=multipole_name,
                                                    value=new_value)

    def update_all_dac_channels(self):
        #print "\n update_all_dac_channels"
        electrode_list = self.electrodes.get_electrode_list()
        #print "electrode_list =", electrode_list
        for kk in xrange(len(electrode_list)):
            electrode = electrode_list[kk]
            print electrode.name
            self.update_dac(electrode)
            electrode_gui = self.electrode_guis[electrode.name]
            #print "\t electrode.bit_value =", electrode.bit_value
            electrode_gui.spinBox.setValues(electrode.bit_value)
            #print "\t electrode.voltage =", electrode.voltage

    def update_all_gui_indicators(self):
        print "\n"
        print "update_all_gui_indicators"
#        M_1 = self.electrodes.multipole_moments.get_value(name='M_1')
#        self.dipole_indicators[0].display(str(M_1))
#
#        M_2 = self.electrodes.multipole_moments.get_value(name='M_2')
#        self.dipole_indicators[1].display(str(M_2))
#
#        M_3 = self.electrodes.multipole_moments.get_value(name='M_3')
#        self.dipole_indicators[2].display(str(M_3))

        M_4 = self.electrodes.multipole_moments.get_value(name='M_4')
        self.quadrupole_indicators[0].display(str(M_4))

        M_5 = self.electrodes.multipole_moments.get_value(name='M_5')
        self.quadrupole_indicators[1].display(str(M_5))

        M_6 = self.electrodes.multipole_moments.get_value(name='M_6')
        self.quadrupole_indicators[2].display(str(M_6))

        M_7 = self.electrodes.multipole_moments.get_value(name='M_7')
        self.quadrupole_indicators[3].display(str(M_7))

        M_8 = self.electrodes.multipole_moments.get_value(name='M_8')
        self.quadrupole_indicators[4].display(str(M_8))

#        print "M_1=", M_1
#        print "M_2=", M_2
#        print "M_3=", M_3
        print "M_4=", M_4
        print "M_5=", M_5
        print "M_6=", M_6
        print "M_7=", M_7
        print "M_8=", M_8

    def _multipole_name_from_button(self, button_name=None):
        """
        button_name: str
        """
        if button_name in ('Ex up', 'Ex down'):
            multipole_name = 'M_1'
        elif button_name in ('Ey up', 'Ey down'):
            multipole_name = 'M_2'
        elif button_name in ('Ez up', 'Ez down'):
            multipole_name = 'M_3'
        elif button_name in ('Exx_yy up', 'Exx_yy down'):
            multipole_name = 'M_4'
        elif button_name in ('Ezz_xx_yy up', 'Ezz_xx_yy down'):
            multipole_name = 'M_5'
        elif button_name in ('Exy up', 'Exy down'):
            multipole_name = 'M_6'
        elif button_name in ('Eyz up', 'Eyz down'):
            multipole_name = 'M_7'
        elif button_name in ('Ezx up', 'Ezx down'):
            multipole_name = 'M_8'
        return multipole_name

    @inlineCallbacks
    def update_dac(self, electrode):
        """
        Parameters
        ----------
        electrode: Electrode class instance.
        """
        yield self.server.dacoutput(electrode.number, electrode.bit_value)
        self.electrode_indicator.update_octant(electrode)

    def update_step_size(self, step_size):
        """
        Changes the bit resolution.
        """
        self.step_size = step_size

    @inlineCallbacks
    def save_to_registry(self, pressed):
        for electrode_gui in self.electrode_guis:
            value = electrode_gui.spinBox.spinLevel.value()
            yield self.reg.set(electrode_gui.name, value)


if __name__ == "__main__":
    a = QtGui.QApplication([])
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    dac_widget = DAC8718Client(reactor)
    dac_widget.show()
    reactor.run()  # @UndefinedVariable
