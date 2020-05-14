import sys
from PyQt5 import QtWidgets
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QMainWindow, QApplication, QDialog, QMessageBox
from PyQt5.QtCore import QTimer
import sqlite3

class eSeq(QDialog):
    def __init__(self):
        '''
        This class create a window for the user to add a sequence name and
        create a sequence associated with that name

        '''
        super(eSeq, self).__init__()
        loadUi('seq_edit.ui', self)

        self.sequenceText.setReadOnly(True)
        
        self.conn = sqlite3.connect("sData.db")

        self.initTable()

        self.addButtons(self.combinedButton)
        self.addButtons(self.bay1Button)
        self.addButtons(self.bay2Button)
        self.addButtons(self.bay3Button)
        self.addButtons(self.bay4Button)
        self.addButtons(self.bay5Button)
        
        self.clearButton.clicked.connect(self.clearSeq)
        
        self.saveButton.setDisabled(True)
        self.saveButton.clicked.connect(self.checkName)
        
        self.cancelButton.clicked.connect(self.quit)

        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.checkEmpty)
        self.timer.start()

    def checkEmpty(self):
        '''
        This method check for if both the user-defined fields are empty
        If the either one of the field are empty, the save button is set to be disabled
        This method is connected to a timer that goes of every 500ms (self.timer)
        '''
        if self.sequenceText.text() == '' or self.nameText.text() == '':
            self.saveButton.setDisabled(True)
        else:
            self.saveButton.setDisabled(False)
    
    def addButtons(self, button):
        '''
        Connect a button to the addSeq method
        '''
        button.clicked.connect(self.addSeq)

    def addSeq(self):
        '''
        Transform the text from a button into a sequence text where the added text is in the format _<buttonName>
        and append it to the end of the existing sequenceText
        '''
        a = ''
        a += ('_<' + self.sender().text() + '>').rstrip()
        self.sequenceText.insert(a)

    def clearSeq(self):
        '''
        Empty the entire sequenceText text box
        '''
        self.sequenceText.clear()

    def quit(self):
        '''
        Close the entire window
        '''
        self.close()

    def initTable(self):
        '''
        Set up a table called sequences in the database (sData.db) if not already exist with 2 collumns - name and sequence
        '''
        with self.conn:
            self.cursor = self.conn.cursor()
            self.cursor.execute("CREATE TABLE IF NOT EXISTS sequences( name text, sequence text )")
            self.conn.commit()
    
    def checkName(self):
        '''
        Check for if the user-defined sequence name is already in the database, and give a pop up window
        to warn the user that the name already exist in the database
        '''
        with self.conn:
            self.cursor = self.conn.cursor()
            self.checker = self.cursor.execute('SELECT * FROM sequences WHERE name = ?', (self.nameText.text(),))
        if self.checker.fetchone()!= None:
            QMessageBox.warning(self, 'Warning!', f'The name "{self.nameText.text()}" already exist, please choose a different name',
            QMessageBox.Cancel, QMessageBox.Cancel)
        else:
            self.Save()


    def Save(self):
        '''
        Save the user-defined sequence name and definition into the database
        '''
        with self.conn:
            self.cursor = self.conn.cursor()
            self.cursor.execute("INSERT INTO sequences VALUES (?, ?)", (self.nameText.text(), self.sequenceText.text()))
            self.conn.commit()
        self.quit()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = eSeq()
    window.show()
    sys.exit(app.exec_())