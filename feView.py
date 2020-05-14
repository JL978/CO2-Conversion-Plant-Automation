import sys
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import sqlite3
from dbWork import insertSQL, getDt
import random

class cFE(QDialog):
    def __init__(self):
        '''
        This method create a window that automatically update to show the lastest
        FE data collected. The update rate is set up in self.timer.setInterval in ms
        '''
        super(cFE, self).__init__()
        loadUi('FE_D.ui', self)
        self.run_update()
        
        self.timer = QTimer()
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.run_update)
        self.timer.start()


    def run_update(self):
        '''
        Connecting the FE signal from the getData thread to the update method then run the thread
        '''
        self.data = getData()
        self.data.FE.connect(self.update)
        self.data.start()

    def update(self, arr):
        '''
        Grab the FE signal from the getData thread (arr) and update the lcd displays
        '''
        self.lcdH2.display(arr[0])
        self.lcdCO.display(arr[1])
        self.lcdCH4.display(arr[2])
        self.lcdC2H4.display(arr[3])

class getData(QThread):
    FE = pyqtSignal(list)
    def __init__(self, parent=None):
        '''
        An inherited qthread class that goes into the FE database and and grab the last data point and emit
        the FE data in list form 
        '''
        super(getData, self).__init__(parent)
        
    def run(self):
        dt = getDt()
        l = {'flowRate': None, 'H2':None, 'CO':None,'CH4':None,'C2H4':None}
        for gas in l.keys():
            l[gas] = random.randint(0,40)
        data = dict(**dt, **l)
        insertSQL("cathodeGasData.db", 'FE', data)
        self.conn = sqlite3.connect("cathodeGasData.db")
        with self.conn:
            self.cursor = self.conn.cursor()
            self.data = list(self.cursor.execute("SELECT * FROM FE ORDER BY Date DESC, Time DESC LIMIT 1"))
            print(self.data)
            (Date, Time, VFlow, *vFE) = self.data[0]
            self.FE.emit(vFE)


if __name__ == "__main__":
    app = QApplication(sys.argv) 
    window = cFE()
    window.show()
    sys.exit(app.exec_())

