from clients.qtui.multiplexerchannel import QCustomWavemeterChannel
from twisted.internet.defer import inlineCallbacks, returnValue
from clients.connection import connection
from PyQt4 import QtGui
from wlm_client_config import multiplexer_config

    
SIGNALID1 = 445566
#this is the signal for the updated frequencys
    
class wavemeterchannel(QtGui.QWidget):

    def __init__(self, reactor, parent = None):
        """initializes the GUI creates the reactor 
            and empty dictionary for channel widgets to 
            be stored for iteration. also grabs chan info
            from wlm_client_config file 
        """ 
        super(wavemeterchannel, self).__init__()
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.reactor = reactor     
        self.d = {} 
        self.chaninfo = multiplexer_config.info     
        self.connect()
        
    @inlineCallbacks
    def connect(self):
        """Creates an Asynchronous connection to the wavemeter computer and
        connects incoming signals to relavent functions
        
        """
        from labrad.wrappers import connectAsync
        self.cxn = yield connectAsync('169.232.156.230')
        self.server = yield self.cxn.multiplexerserver
        yield self.server.signal__frequency_changed(SIGNALID1)
        yield self.server.addListener(listener = self.updateFrequency, source = None, ID = SIGNALID1) 
        self.initializeGUI()
        
    @inlineCallbacks
    def initializeGUI(self):  
        
        layout = QtGui.QGridLayout()
        for chan in self.chaninfo:
            port = self.chaninfo[chan][0]
            hint = self.chaninfo[chan][1]
            
            widget = QCustomWavemeterChannel(chan, hint) 

            import RGBconverter as RGB  
            RGB = RGB.RGBconverter()
            color = int(2.998e8/(float(hint)*1e3))
            color = RGB.wav2RGB(color)
            color = tuple(color)

            widget.spinFreq.setValue(float(hint))

            widget.currentfrequency.setStyleSheet('color: rgb' + str(color))
            
            widget.spinExp.valueChanged.connect(lambda exp = widget.spinExp.value(), port = port : self.expChanged(exp, port))
            initvalue = yield self.server.get_exposure(port)
            widget.spinExp.setValue(initvalue)
            

            initmeas = yield self.server.get_switcher_signal_state(port)
            initmeas = initmeas
            widget.measSwitch.setChecked(bool(initmeas))
            widget.measSwitch.toggled.connect(lambda state = widget.measSwitch.isDown(), port = port  : self.changeState(state, port))
            
            widget.spinFreq.valueChanged.connect(self.freqChanged)

            self.d[port] = widget
            layout.addWidget(self.d[port])
        self.setLayout(layout)
        yield None

    
    @inlineCallbacks
    def expChanged(self, exp, chan):
        #these are switched, dont know why
        exp = int(exp)
        yield self.server.set_exposure_time(chan,exp)
        
    
    def updateFrequency(self , c , signal):     
        chan = signal[0]
        if chan in self.d : 
            freq = signal[1]
            
            if self.d[chan].measSwitch.isDown():
                self.d[chan].currentfrequency.setText('Not Measured')                       
            elif freq == -3.0:
                self.d[chan].currentfrequency.setText('Under Exposed')
            elif freq == -4.0:
                self.d[chan].currentfrequency.setText('Over Exposed')
            else:
                self.d[chan].currentfrequency.setText(str(freq)[0:10])
                
    @inlineCallbacks
    def changeState(self, state, chan):
        yield self.server.set_switcher_signal_state(chan, state)
        if state == False:  self.d[chan].currentfrequency.setText('Not Measured') 
        
    def freqChanged(self,value):
        print value

    def closeEvent(self, x):
        self.reactor.stop()
        
        
        
if __name__=="__main__":
    a = QtGui.QApplication( [] )
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    wavemeterWidget = wavemeterchannel(reactor)
    wavemeterWidget.show()
    reactor.run()
    