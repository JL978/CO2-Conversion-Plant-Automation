import sys
import sqlite3
import pandas as pd
import datetime
from datetime import timedelta
import numpy as np

from PyQt5.uic import loadUi
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QApplication, QMenu, QMessageBox
from PyQt5.QtCore import pyqtSignal, QTimer, QThread

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates



class gFE(QMainWindow):
    def __init__(self):
        '''
        This method create a graphing window that display the collected data over time
        '''
        super(gFE, self).__init__()
        loadUi('FE_G.ui', self)

        self.addToolBar(0x8, NavigationToolbar(self.graphWidget.canvas, self))
        
        self.comboBox.textActivated.connect(self.streamState)
        
        self.timer = QTimer()
        #Interval time in miliseconds
        self.timer.setInterval(5000) #We probably don't need the graph to update this often
        self.timer.timeout.connect(self.run_update)
        self.timer.start()

        #This attribute is used for testing - it maps the hours values into minutes
        #Todo - change this into the right timedelta coresponding with hours (hours=x)
        self.td = {'6 Hours': timedelta(minutes=3), '12 Hours': timedelta(minutes=12), '24 Hours': timedelta(minutes=24), 
        '36 Hours': timedelta(minutes=36), '48 Hours': timedelta(minutes=48)}

    def run_update(self):
        '''
        Connected to the update timer (self.timer)
        Grab the current dataType text(FE or molFlow) and current stream text
        Start a getData thread with the chosen texts and connect emited data 
        from the getData thread to updating the graph
        '''
        self.dataType = self.comboBox.currentText()
        self.selectedStream = self.comboBox_2.currentText()

        self.data = getData(mode = self.dataType, stream = self.selectedStream)
        self.data.got.connect(self.update)
        self.data.noData.connect(self.noDataThread)
        self.data.start()

    def update(self, dtf):
        '''
        Update the display on the graph with the latest data
        The dtf parameter is the collected pd dataframe data pulled from the emitted signal of the
        getData thread 
        '''
        #The final parameter - how far back to display the data
        #This grab what is chosen in the time dropdown menu and set a max time and min time to 
        #display on the graph
        self.tback = self.comboBox_3.currentText()
        #The max time is not based on current time but based on the latest data time plus 3 min
        currentMax = max(dtf.dt.values)
        self.x_max = currentMax + np.timedelta64(3, 'm') 
        self.x_min = currentMax - np.timedelta64(self.td[self.tback])

        #Assigning the individual values to it own attribute to make it easier put in the plot command later
        self.dt = dtf.dt.values
        self.hydrogen = dtf.H2.values
        self.cmono = dtf.CO.values
        self.meth = dtf.CH4.values
        self.eth = dtf.C2H4.values

        self.graphWidget.canvas.axes.cla()
        
        #This block format the x-axis to split up the ticks into just the time of day
        #and offset the date into the bottom right corner of the graph
        #It does this by some 'magic' so don't change anything in here 
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        formatter = mdates.ConciseDateFormatter(locator)
        formatter.offset_formats[3] = '%b %d'
        formatter.offset_formats[4] = '%b %d'
        self.graphWidget.canvas.axes.xaxis.set_major_locator(locator)
        self.graphWidget.canvas.axes.xaxis.set_major_formatter(formatter)

        #Plotting the data onto the graph
        self.graphWidget.canvas.axes.plot(self.dt, self.hydrogen, linestyle='-', marker='o', markersize=1, label = 'H2')
        self.graphWidget.canvas.axes.plot(self.dt, self.cmono, linestyle='-', marker='o', markersize=1, label = 'CO')
        self.graphWidget.canvas.axes.plot(self.dt, self.meth, linestyle='-', marker='o', markersize=1, label = 'CH4')
        self.graphWidget.canvas.axes.plot(self.dt, self.eth, linestyle='-', marker='o', markersize=1, label = 'C2H4')

        #Setting axes name and diplay the lengend 
        self.graphWidget.canvas.axes.set_xlabel('Time', fontweight='bold')
        self.graphWidget.canvas.axes.set_ylabel(f'{self.dataType}', fontweight='bold')
        self.graphWidget.canvas.axes.legend()
        
        #Use the max and min time found earlier to set the range of the x-axis diplay
        self.graphWidget.canvas.axes.set_xlim(self.x_min, self.x_max)
        
        self.graphWidget.canvas.draw()

    def streamState(self, text):
        '''
        Control what is shown the streamText dropdown menu based on what was chosen in comboBox (Data Type)
        If it's FE was chosen, only the combined stream is shown
        If MolFlow was chosen, all the different streams are shown
        '''
        if text == 'FE' or text == 'molFlow':
            self.comboBox_2.clear()
            self.comboBox_2.insertItem(0, 'Combined')
        else:
            clist = ['Combined', 'Bay 1','Bay 2','Bay 3','Bay 4','Bay 5']
            self.comboBox_2.clear()
            self.comboBox_2.insertItems(len(clist), clist)
    
    def noDataThread(self):
        self.timer.stop()
        QMessageBox.critical(self, 'Warning!', 'No data to graph',
            QMessageBox.Close, QMessageBox.Close)
        self.close()
    
    def closeEvent(self,event):
        self.timer.stop()
        event.accept()

class getData(QThread):
    got = pyqtSignal(pd.DataFrame)
    noData = pyqtSignal()
    def __init__(self, mode=None, stream=None, parent=None):
        '''
        An inherited QThread class that goes to grab data based on what data type and 
        stream you selected in the ui
        It emits a got signal as a pandas dataframe data type 
        '''
        super(getData, self).__init__(parent)
        self.mode = mode
        self.stream = stream

    def run(self):
        self.conn = sqlite3.connect("cathodeGasData.db")
        with self.conn:
            try: 
                if self.mode == "FE" or self.mode == "molFlow":
                    # If the chosen mode is FE or molflow, the only stream available is combined
                    # so you don't need to pick the stream, just read directly from the FE table
                    self.df = pd.read_sql(f"SELECT * FROM {self.mode}", self.conn)
                else:
                    # If the chosen mode is molFrac, you need to pick a specific stream and also any Nan
                    # values such that the disconnected data don't connect
                    self.df = pd.read_sql(f"SELECT * FROM {self.mode} WHERE Stream='{self.stream}' OR Stream IS NULL", self.conn)
                
                # Creating a new data collumn that combines both the date and the time into one to make graphing easier 
                self.dt = []
                print(self.df)
                for date, vtime in zip(self.df.Date.values, self.df.Time.values):
                    self.dt.append(datetime.datetime.fromisoformat('20' + date + ' ' + vtime))
                self.df["dt"] = self.dt
                self.got.emit(self.df)

            except pd.io.sql.DatabaseError:
                self.noData.emit()
                
            
            

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = gFE()
    window.show()
    sys.exit(app.exec_())
