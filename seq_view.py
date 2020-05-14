import sys
from PyQt5 import QtWidgets
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication, QDialog, QTableWidgetItem, QMessageBox
import sqlite3


class cSeq(QDialog):
    def __init__(self):
        '''
        This class load up the sequence view window 
        The window load up the stored sequence name and the sequence description
        User can choose to delete a particular sequence from the database
        '''
        super(cSeq, self).__init__()
        loadUi('seq_view.ui', self)
        self.load()
        self.removeButton.clicked.connect(self.delete)

    def load(self):
        '''
        Load up the data in the sequence Database (sData.db) into a table 
        If there is no table in the database then it will load up a blank 
        table in the ui
        '''
        try:
            self.conn = sqlite3.connect("sData.db")
            with self.conn:
                self.cursor = self.conn.cursor()
                data = self.cursor.execute("SELECT * FROM sequences")
                self.tableWidget.setRowCount(0)
                for rowNum, rowData in enumerate(data):
                    self.tableWidget.insertRow(rowNum)
                    for colNum, value in enumerate(rowData):
                        self.tableWidget.setItem(rowNum, colNum, QTableWidgetItem(value))
        except sqlite3.OperationalError:
            pass
    
    def delete(self):
        '''
        Remove the selected row data from the data base then 
        remove the same row from the ui 
        '''
        self.deleteRow = self.tableWidget.currentRow()
        self.deleteName = self.tableWidget.item(self.deleteRow, 0).text()
        self.deleteSeq = self.tableWidget.item(self.deleteRow, 1).text()

        self.conn = sqlite3.connect("sData.db")
        with self.conn:
            self.cursor = self.conn.cursor()
            self.cursor.execute(f"DELETE FROM sequences WHERE Name = '{self.deleteName}' and Sequence = '{self.deleteSeq}'")
            self.conn.commit()

        self.tableWidget.removeRow(self.deleteRow)



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = cSeq()
    window.show()
    sys.exit(app.exec_())
