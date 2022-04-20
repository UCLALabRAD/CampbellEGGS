from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QFrame, QWidget, QLabel, QGridLayout

from EGGS_labrad.clients.Widgets import TextChangingButton


class stability_gui(QFrame):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setFrameStyle(0x0001 | 0x0030)
        self.makeWidgets()
        self.makeLayout()
        self.setWindowTitle("Stability Client")

    def makeWidgets(self):
        shell_font = 'MS Shell Dlg 2'
        self.setFixedSize(190, 150)
        # title
        self.all_label = QLabel('Stability Client')
        self.all_label.setFont(QFont(shell_font, pointSize=18))
        self.all_label.setAlignment(Qt.AlignCenter)
            # readout
        self.voltage_display_label = QLabel('VPP (V)')
        self.voltage_display = QLabel('000.00')
        self.voltage_display.setFont(QFont(shell_font, pointSize=25))
        self.voltage_display.setAlignment(Qt.AlignCenter)
        self.voltage_display.setStyleSheet('color: blue')
            # record button
        self.record_button = TextChangingButton(('Stop Recording', 'Start Recording'))
        self.record_button.setMaximumHeight(25)

    def makeLayout(self):
        layout = QGridLayout(self)
        col1 = 0
        layout.addWidget(self.all_label, 0, col1)
        layout.addWidget(self.voltage_display_label, 1, col1)
        layout.addWidget(self.voltage_display, 2, col1)
        layout.addWidget(self.record_button, 3, col1)


if __name__ == "__main__":
    from EGGS_labrad.clients import runGUI
    runGUI(stability_gui)
