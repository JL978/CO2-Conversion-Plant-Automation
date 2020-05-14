from PyQt5.QtWidgets import*

from matplotlib.backends.backend_qt5agg import FigureCanvas

from matplotlib.figure import Figure

from matplotlib import style
#https://www.youtube.com/watch?v=2C5VnE9wPhk&t=355s
    
class MplWidget(QWidget):
    def __init__(self, parent = None):
        '''
        Set up the graphing area 
        This class is used to define the class of the plot area in feGraph.py
        In the FE_G.ui file, there is an attribute called graphWidget that has been
        promoted to this class
        '''
        #style.use('seaborn-deep') #seaborn-deep
        QWidget.__init__(self, parent)
        self.fig = Figure()
        

        self.canvas = FigureCanvas(self.fig)
        
        vertical_layout = QVBoxLayout()
        vertical_layout.addWidget(self.canvas)
        
        self.canvas.axes = self.canvas.figure.add_subplot(111)
        self.setLayout(vertical_layout)

