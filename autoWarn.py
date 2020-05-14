import sys
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication, QDialog
import time

class warnWin(QDialog):
    def __init__(self):
        super(warnWin, self).__init__()
        loadUi('autoWarn.ui', self)
        self.setModal(True)

if __name__ == "__main__":
    app = QApplication(sys.argv) 
    window = warnWin()
    window.show()
    sys.exit(app.exec_())
