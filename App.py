import sys
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QMainWindow, QApplication, QAction, QMessageBox
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
import time
import sqlite3
import pandas as pd
import os
import glob

from dbWork import *
from GCSampler import autoClicker, dataAnalysis

#WHEN MAKING CHANGES TO CONTROLDATA.CSV SUCH AS ADDING A NEW COLLUMN OF DATA, 
#PLEASE UPDATE THE INSERT_NA CLASS IN THE AREA TABLE SECTION NEAR THE END OF THE DOCUMENT TO INCLUDE THAT DATA
#PLEASE KEEP TRACK OF THE ORDER OF THE DATA AS WELL AND UPDATE THE ORDER IN REVERTORDER METHOD ACCORDINGLY (NEW COLUMNS GOES AFTER TEMP AND BEFORE CATHODE)
#FINALLY TO ADD FUNCTIONALITY WITH THE NEW DATA UPDATE GCSAMPLER AND THE ANALYZEDATA THREAD CLASS
class App(QMainWindow):
    def __init__(self):
        super(App, self).__init__()
        loadUi('main_win.ui', self) 

        #Start Button
        self.pushButton.clicked.connect(self.autoStatus) 
        self.pushButton.clicked.connect(self.run_Na)
        self.pushButton.clicked.connect(self.controlTimer)

        #Stop Button
        self.pushButton_2.clicked.connect(self.autoStatus)
        self.pushButton_2.setDisabled(True) 
        self.pushButton_2.clicked.connect(self.killAllThreads)

        self.refreshButton.clicked.connect(self.loadBox)

        #Spinbox to set Injection Interval
        self.doubleSpinBox.setRange(17, 60) 
        self.doubleSpinBox.setDecimals(1)
        self.doubleSpinBox.setSingleStep(0.5)

        #Checkbox to enable Anode injection 
        self.checkBox.toggled.connect(self.anodeToggled)

        #Menu Bar
        self.menuDisplays.triggered[QAction].connect(self.viewFE)
        self.menuEdit.triggered[QAction].connect(self.viewSeq)

        #Putting the cycle names into the drop down menu
        self.loadBox()
    
    def run_Na(self):
        '''
        Run the thread that create None values at the start when the start button 
        is pressed for all the cathode gas tables. This is such that when graphing, 
        the end of one cycle is not connected to the start of the next cycle
        '''
        self.naThread = insert_Na()
        self.naThread.start()

    def controlTimer(self):
        '''
        Grabs the run sequence selected and store it to define which stream is being 
        processed. Then number in the doubleSpinBox is set as the interval value for
        the main timer 

        Start the main timer that control the auto-clicker and analysis loop that is 
        started when the start button is pressed.
        '''
        self.getSequence()
        self.interval = int(self.doubleSpinBox.value() * 1000 * 60) # unit in seconds
        
        self.readPrevState()
        self.timer = QTimer()
        self.timer.setInterval(self.interval)
        self.timer.timeout.connect(self.readPrevState) 
        self.timer.start()
    
    def getSequence(self):
        '''
        Getting the stored sequence based on the selected name of the sequence from the database
        and store it in a local attribute
        '''
        self.conn = sqlite3.connect("sData.db")
        with self.conn:
            self.cursor = self.conn.cursor()
            rawSeq = list(self.cursor.execute("SELECT sequence FROM sequences WHERE name = ?", (self.comboBox.currentText(),)))
        self.runSequence = iSequence(*rawSeq[0])
    
    def readPrevState(self):
        '''
        Start a thread to read the info for the previous injection from injectionInfo.csv
        Connect the done signal to the prevStateStore method 
        At the same time, the clickWarning method is run
        '''
        #print('reading prev state..')
        self.readThread = injectionInfoRead()
        self.readThread.done.connect(self.prevStateStore)
        self.readThread.start()

        self.clickWarning()
    
    def prevStateStore(self, d):
        '''
        Receive the data signal of the previous state and store it as a local attribute
        The data received is mixed up during the transmission and needed to be passed
        through the revertOrder function to return to it's original order
        '''
        
        if d != []:
            self.prevState = d[-1]
            print(self.prevState)
            self.prevState = self.revertOrder(self.prevState)
        else:
            self.prevState = d
        
        #print('prev')
        print(self.prevState)
    
    def revertOrder(self, d):
        '''
        Change the prevstate data back into the desired form 
        '''
        orderArr = ['Date', 'Time', 'Stream', 'Current', 'MassFlow', 'Temp', 'Cathode']
        new = {}
        for keys in orderArr:
            new[keys] = d[keys]
        return new

    def clickWarning(self):
        '''
        Create a warning window to let the user know to take their hands of the mouse and keyboard
        the window is automatically destroyed after 4 seconds and on destuction, start the auto-clicker
        thread
        '''
        import autoWarn
        self.warnWindow =  autoWarn.warnWin()
        self.warnWindow.show()
        self.warnWindow.finished.connect(self.autoThread)

        self.warnTime = QTimer()
        self.warnTime.singleShot(4000, lambda: self.warnWindow.close())

        self.warnWindow.exec_()

    def autoThread(self): 
        '''
        Starting a thread that run the auto-clicker to do the injection in the background
        Also enables the stop button
        It is connected to the writeState method on finish
        '''
        self.pushButton.setDisabled(True) 
        self.pushButton_2.setEnabled(True)

        if self.checkBox.isChecked():
            self.statusbar.showMessage(f'Starting Anode injection for {self.comboBox_2.currentText().lower()} stream...')
        else:
            self.statusbar.showMessage(f'Starting Cathode injection for {self.runSequence.seqList[0].lower()} stream...')
        
        self.injectionThread = injection()
        self.injectionThread.injected.connect(self.writeState)
        self.injectionThread.start()

    def writeState(self):
        '''
        Write down all the info neccessary to do analysis on the next round of injection
        [Date, Time, Stream, Current, MassFlow, Temp, Cathode]

        If the anode checkBox is check, the program go immediately to run the openChrom autoclicker
        If it is unchecked, the program go to shuffle the running sequence to get the next stream
        '''
        #print('writing current state')
        self.statusbar.showMessage('Writing current state...')
        if self.checkBox.isChecked():
            self.anodeStream = self.comboBox_2.currentText()
            self.writeThread = injectionInfoWrite(cathode = False, stream = self.anodeStream)
            self.writeThread.finished.connect(self.ocRun)
            self.writeThread.start()
        else:
            self.currentStream = self.runSequence.seqList[0]
            self.writeThread = injectionInfoWrite(stream = self.currentStream)
            self.writeThread.finished.connect(self.streamShuffle)
            self.writeThread.start()


    def ocRun(self):
        '''
        Start a thread that run the autoclicker to do the openChrom analysis
        It is connected the runAnalysis method upon finish
        '''
        if self.prevState != []:
            self.statusbar.showMessage('Running openchrom analysis...')
            self.ocThread = OC()
            self.ocThread.OCed.connect(self.runAnalysis)
            self.ocThread.start()
        else:
            self.statusbar.showMessage('Waiting for the next injection to start')
    
    def streamShuffle(self):
        '''
        At the end of every cathode run, the sequence gets shuffled 
        the next stream is selected
        '''
        self.runSequence.shuffle()
        self.ocRun()

    def runAnalysis(self):
        '''
        Start a thread that does all the analysis requires based on the previous 
        info data and store them in their respective database 
        '''
        self.statusbar.showMessage('Analyzing data...')
        self.analysisThread = analyzeData(prevState = self.prevState)
        self.analysisThread.done.connect(self.waitMessage)
        self.analysisThread.noNew.connect(self.noNewCSV)
        self.analysisThread.start()
    
    def waitMessage(self):
        self.statusbar.showMessage('Waiting for the next injection to start')

    def noNewCSV(self):
        QMessageBox.warning(self, 'Warning!', 'No new csv file found, check to make sure openchrom is open and operating correctly',
            QMessageBox.Close, QMessageBox.Close)

    def anodeToggled(self): 
        '''
        Setting the anode injection stream comboBox based on the check state
        '''
        if self.checkBox.isChecked():
            streams = ['Combined', 'Bay 1', 'Bay 2', 'Bay 3', 'Bay 4', 'Bay 5']
            self.comboBox_2.insertItems(len(streams) - 1, streams)
        else:
            self.comboBox_2.clear()


    def killAllThreads(self):
        '''
        Cut all the timer, and all running threads
        '''
        self.pushButton_2.setDisabled(True)
        self.pushButton.setEnabled(True)
        
        self.timer.stop()
        
        if self.injectionThread.isRunning():
            self.injectionThread.terminate()
            self.injectionThread.wait()
        else: 
            self.statusbar.showMessage('Finishing up with data analysis')
            try:
                self.writeThread.wait()
                self.ocThread.wait()
                self.analysisThread.wait()
            except:
                pass
        self.statusbar.showMessage('Standby')

    
    def autoStatus(self): 
        '''
        Changing the status display at the bottom of the window based on which button (start/stop) was pressed 
        '''
        sender = self.sender()
        if sender.text() == "Start":
            self.statusbar.showMessage("Automation in Progress")    
        else:
            self.statusbar.showMessage("Standby")
    
    def viewSeq(self,p):
        '''
        Show the sequence editor or viewer
        when the viewer closed, the selection box automatically refresh so that 
        you can't select a deleted cycle definition
        '''
        sender = p.text()
        if sender == "Add Cycle":
            from seq_edit import eSeq
            win4 = eSeq()
            win4.show()
            win4.exec_()

        elif sender == "View Cycles":
            from seq_view import cSeq
            win5 = cSeq()
            win5.show()
            win5.finished.connect(self.loadBox)
            win5.exec_()
    
    def viewFE(self, p):
        '''
        Display the FE view or graph or export the latest data
        '''
        sender = p.text()
        if sender == "Show Current FE":
            import feView
            self.win2 = feView.cFE()
            self.win2.show()
            self.win2.finished.connect(lambda: self.win2.timer.stop())
            self.win2.exec_()

        elif sender == "Graph Data":
            from feGraph import gFE
            win3 = gFE()
            win3.show()
        
        elif sender == "Export Data":
            import export

    def loadBox(self):
        '''
        Load all the defined sequence name we have in the database into the 
        selection box
        '''
        self.conn = sqlite3.connect("sData.db")
        with self.conn:
            self.cursor = self.conn.cursor()
            name_data = pd.read_sql("SELECT name FROM sequences", self.conn)
            self.comboBox.clear()
            self.comboBox.insertItems(len(name_data) - 1, name_data.name.values)

class injection(autoClicker):
    '''
    An inherited thread class from GCSampler that loads the injection auto-clicker file and run it
    Once the autoclicker is finished, it emits the injected signal 
    '''
    injected = pyqtSignal()

    def __init__(self, parent=None):
        super(injection, self).__init__(parent)
    
    def run(self):
        #import test
        #test.move(5) # Delete the 2 test lines and uncomment runGC for real scenario
        self.runGC()
        self.injected.emit()

class OC(autoClicker):
    '''
    An inherited thread class from GCSampler that loads the openChrom auto-clicker file and run it
    Once the autoclicker is finished, it emits the OCed signal 
    '''
    OCed = pyqtSignal()
    def __init__(self, parent=None):
        super(OC, self).__init__(parent)
    
    def run(self):
        self.runOC()
        self.OCed.emit()

class injectionInfoRead(QThread):
    '''
    A qthread class that open the injectionInfo.csv file to read its content and emit the 
    content in the form of a list of one dictionary [{...}], if the file is empty then 
    the emitted data is just an empty list 
    '''
    done = pyqtSignal(list)
    def __init__(self, parent=None):
        super(injectionInfoRead, self).__init__(parent)
    
    def run(self):
        import csv
        with open('injectionInfo.csv', 'r') as f:
            try:
                self.data = list(csv.DictReader(f))
            except IndexError:
                self.data = []
            #print(self.data)
            self.done.emit(self.data)


class injectionInfoWrite(QThread):
    '''
    A qthread class that write to the injectionInfo.csv file the following information:
    Current date and time - using a function defined in testdb.py
    Current stream - defined as the init input
    Current data from the control from reading the controlData.csv file
    Current side of injection in the form of a boolean, True means it is a cathode injection, False means it is an anode injection 
    '''
    done = pyqtSignal()
    def __init__(self, cathode = True, stream = None, parent=None):
        super(injectionInfoWrite, self).__init__(parent)
        self.cathode = cathode
        self.stream = stream

    def run(self):
        '''
        When triggered, the thread uses the other methods in the class to construct
        a dictionary with all the required info about the current injection
        It then write the dictionary into a csv file with the keys as the header
        and items as the corresponding data
        '''
        import csv
        self.combine()
        with open('injectionInfo.csv', 'a+') as f:   
            fieldnames = list(self.info.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            #print(f.tell())
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(self.info)
        self.done.emit()

    def grabDT(self):
        '''
        Get the current date time into a dictionary in the form of
        {'Date': Date, 'Time': Time}
        '''
        self.ctime = getDt()

    def grabControl(self):
        '''
        Get the current control data into a dictionary in the form of
        {'Current': Current, 'Mass Flow': Mass Flow, 'Temp': Temp}
        '''
        import csv
        with open('controlData.csv', 'r') as f:
            self.rawData = list(csv.DictReader(f))
            self.controlData = self.rawData[-1]

    def combine(self):
        '''
        Combine the data from stream info, grabDT and grabControl into a single dictionary
        '''
        self.grabDT()
        self.grabControl()
        self.info = dict(**self.ctime,**{'Stream': self.stream}, **self.controlData, **{'Cathode': self.cathode})
        print(self.info)

class analyzeData(dataAnalysis):
    '''
    An inherited thread class from GCSampler that takes the previous state dictionary as input
    Based on the data from the prevState dictionary, the thread decide which data to extract
    to which database
    '''
    noNew = pyqtSignal()
    done = pyqtSignal()
    def __init__(self, prevState, parent=None):
        super(analyzeData, self).__init__(parent)
        #TEMPERATURE IN CELCIUS
        self.prevState = prevState
        self.cathode = self.prevState.pop('Cathode')
        self.temp = float(self.prevState['Temp'])
        self.n_water_vap(temp = self.temp)
        self.stream = self.prevState['Stream']
        self.massFlow = float(self.prevState['MassFlow'])
        self.current = float(self.prevState['Current'])
        self.date = self.prevState['Date']
        self.time = self.prevState['Time']

        self.setDatabase()

    def run(self):
        if self.checkNew():
            self.read(filename = self.filename)
            print(self.cathode)
            if self.cathode:
                self.integrate(self.cathodeGas)
            else:
                self.integrate(self.anodeGas)
            
            self.areaData = dict(**self.prevState, **self.gasArea)
            insertSQL(self.database, 'Area', self.areaData)

            self.findNx_GC()
            if self.stream != 'Combined':
                self.findMolFrac()
                
                self.molFracData = dict(**self.dt)
                self.molFracData['Stream'] = self.stream
                self.molFracData.update(self.molFrac)
                insertSQL(self.database, 'molFrac', self.molFracData)
                self.done.emit()
            else:
                self.findMx_GC()
                self.findMx_flow(massFlow = self.massFlow)
                self.findVFlow()

                self.molFlowData = dict(**self.dt, **self.molFlow)
                insertSQL(self.database, 'molFlow', self.molFlowData)
                
                self.findFE(current = self.current)
                self.feData = dict(**self.dt, **self.FE)
                insertSQL(self.database, 'FE', self.feData)
                self.done.emit()
        else:
            self.noNew.emit()
    
    def setDatabase(self):
        if self.cathode == 'True':
            self.cathode = True
            self.database = 'cathodeGasData.db'
        else: 
            self.cathode = False
            self.database = 'anodeGasData.db'

        self.dt = dict([('Date', self.date),('Time', self.time)])
            
    
    def checkNew(self):
        '''
        Check for if the OC autoclicker did it thing and output a new csv file
        If there is a new file then the file directory is written into the txt file and return True
        If not then return false
        '''
        oldfile = self.readFile()
        
        folderlist = glob.glob(os.path.join(os.getcwd(), 'DataCSV','*'))
        newfile = max(folderlist, key=os.path.getctime)
        if oldfile == newfile:
            return False
        else:
            self.filename = newfile
            self.writeFile(newfile)
            return True

    def writeFile(self, fname):
        '''
        Use to write the input fname (a file directory) into oldfile.txt
        '''
        with open('oldfile.txt', 'w') as f:
            f.write(fname)

    def readFile(self):
        '''
        Use to read what is in oldfile.txt
        '''
        with open('oldfile.txt', 'r') as f:
            oldfile = f.readline()
            return oldfile


    
class iSequence:
    '''
    This is an object specifically made to handle the stream sequence from 
    the sequence editor. It take the raw string generated from editor and 
    convert it into a list accessed by calling seqList. 
    '''
    def __init__(self, seq):
        self.seq = seq
        self.seqList = self.seq[2:len(self.seq)-1].split('>_<')
    
    def shuffle(self):
        '''
        This method shuffle the sequence by appending the first item in
        the list to the end then deleting that first item 
        '''
        self.seqList.append(self.seqList[0])
        self.seqList.remove(self.seqList[0])

class insert_Na(QThread):
    '''
    An inherited thread class that insert all Null values into the database
    '''
    def __init__(self, parent=None):
        super(insert_Na, self).__init__(parent)

    def run(self):
        ctime = getDt()
        conn = sqlite3.connect("cathodeGasData.db")
        with conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS Area ( Date, Time, Stream, Current, MassFlow, Temp, H2, CO, CH4, C2H4 )")
            new = dict(**ctime, **{"Stream": None, "Current": None, "MassFlow": None,
                                    "Temp": None, "H2": None, "CO": None, "CH4": None, "C2H4": None})
            cursor.execute("INSERT INTO Area VALUES (:Date, :Time, :Stream, :Current, :MassFlow, :Temp, :H2, :CO, :CH4, :C2H4)", new)
            
            cursor.execute("CREATE TABLE IF NOT EXISTS molFlow (Date, Time, H2, CO, CH4, C2H4, H2O, CO2)")
            new2 = dict(**ctime, **{"H2": None, "CO": None, "CH4": None, "C2H4": None,"H2O": None, "CO2": None})
            cursor.execute("INSERT INTO molFlow VALUES (:Date, :Time, :H2, :CO, :CH4, :C2H4, :H2O, :CO2)", new2)

            cursor.execute("CREATE TABLE IF NOT EXISTS FE (Date, Time, Vtot, H2, CO, CH4, C2H4)")
            new3 = dict(**ctime, **{"Vtot": None, "H2": None, "CO": None, "CH4": None, "C2H4": None})
            cursor.execute("INSERT INTO FE VALUES (:Date, :Time, :Vtot, :H2, :CO, :CH4, :C2H4)", new3)

            cursor.execute("CREATE TABLE IF NOT EXISTS molFrac (Date, Time, Stream, H2, CO, CH4, C2H4, H2O, CO2)")
            new4 = dict(**ctime, **{"Stream": None, "H2": None, "CO": None, "CH4": None, "C2H4": None, 'H2O': None, 'CO2': None})
            cursor.execute("INSERT INTO molFrac VALUES (:Date, :Time, :Stream, :H2, :CO, :CH4, :C2H4, :H2O, :CO2)", new4)

            conn.commit()

if __name__ == "__main__":
    app = QApplication(sys.argv) 
    window = App()
    window.show()

    sys._excepthook = sys.excepthook 
    def exception_hook(exctype, value, traceback):
        print(exctype, value, traceback)
        sys._excepthook(exctype, value, traceback) 
        sys.exit(1) 
    sys.excepthook = exception_hook 

    sys.exit(app.exec_())