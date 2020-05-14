# -*- coding: utf-8 -*-
from scipy.integrate import simps
import pandas as pd
import numpy as np
import time 
import os
import pyautogui
import csv
import sys 
from PyQt5.QtCore import pyqtSignal, QThread

class autoClicker(QThread):
    imageErrors = {"OCicon.png": "OpenChrom Icon", "OCmethod.png": "method button to manage the chromatogram in OpenChrom",
          "OCrunmethod.png":"run method button to manage the chromatogram in OpenChrom",
          "OCclosetab.png": "X to close the chromatogram tab in OpenChrom",
          "OCcheck.png": "method button to manage the chromatogram in OpenChrom",
          "OCok.png": "OK to cofirm not saving the chromatogram in OpenChrom",
          "OCdownar.png": "file managment list to scroll to the most recent .RAW file in OpenChrom",
          "OCfile.png": ".RAW file to open in OpenChrom",
          "start run.png": "start run button in TC Nav",
          "run.png": "run button in TC Nav",
          "tc icon.png": "TC Nav icon on screen"
          }
    imgError = pyqtSignal(str)
    def __init__(self, parent=None):
        '''
        QThread class that does all the required autoclicking - for both the injection and the 
        openChrom data conversion
        '''
        super(autoClicker, self).__init__(parent)

    def lcs(self, screenshot, click = True, sleep = 0, con = 0.8):
        '''
        (L)ocate the screenshot, (C)lick on it (or not), then (S)leep
        '''
        imgDir = os.path.join(os.getcwd(),'Screenshots', screenshot)
        if click == False:
            try:
                pyautogui.moveTo((pyautogui.locateCenterOnScreen(imgDir, confidence = con)))
            except pyautogui.ImageNotFoundException:
                self.imgError.emit('Could not find the ' + self.imageErrors[screenshot])
        else:
            try:
                pyautogui.click((pyautogui.locateCenterOnScreen(imgDir, confidence = con)))
            except pyautogui.ImageNotFoundException:
                self.imgError.emit('Could not find the ' + self.imageErrors[screenshot])
        time.sleep(sleep)
    
    def start_GC(self):
        '''
        The sequence that start the GC injection given the TCNav window is displayed on screen
        '''
        self.lcs("run.png", sleep = 1, con = 0.9)
        self.lcs("start run.png")

    def runGC(self):
        '''
        Check to see if the TCNav window is displayed on screen before executing the run sequence
        '''
        try: 
            window = pyautogui.locateCenterOnScreen(os.path.join(os.getcwd(),'Screenshots',"window.png"), confidence=0.9)
        except pyautogui.ImageNotFoundException:
            self.imgError.emit('Could not find the ' + self.imageErrors['window.png'])
            self.terminate()

        if window != None:
            self.start_GC()
        else:
            self.lcs("tc icon.png", sleep = 1)    
            self.start_GC()
    
    def runOC(self):
        '''
        Excecuting the sequence to export the previous GC .RAW to CSV via OpenChrom
        '''
        # clicking open chrom logo
        self.lcs("OCicon.png", sleep = 2)

        # moving mouse to the top left of the screen
        self.lcs("OCfile.png", click = False)

                        
        #moving mouse down to hover over the files
        pyautogui.move(pyautogui.position()[0], 400)
        time.sleep(1)

        #scrolling to the bottom file
        self.lcs("OCdownar.png", con = 0.7, click = False)
        pyautogui.click(pyautogui.position()[0], pyautogui.position()[1], 500, 0.01)


        #locating file tab
        self.lcs("OCfile.png", sleep = 2, click = False)
        #moving to the last file
        pyautogui.move(-50, 225)
        pyautogui.click(pyautogui.position()[0], pyautogui.position()[1], 2)
        time.sleep(5)

        #locating the method, running the method, closing the tab
        self.lcs("OCmethod.png", sleep = 2)
        self.lcs("OCrunmethod.png", sleep = 2)
        self.lcs("OCclosetab.png", sleep = 2)
        self.lcs("OCcheck.png", sleep = 2)
        self.lcs("OCok.png", sleep = 2)
        
        self.lcs("OCupar.png", con=0.7, click = False)
        pyautogui.click(pyautogui.position()[0], pyautogui.position()[1], 500, 0.01)
        self.lcs("OCfile.png", sleep = 2, click = False)
        pyautogui.move(-150, 240)
        pyautogui.click(pyautogui.position()[0], pyautogui.position()[1], 1)
        # except Exception as e:
        #     self.someError.emit('The following error occure when working with OpenChrom:\n' + str(e))
        #     self.terminate()


class dataAnalysis(QThread):
    #Data for area analysis
    areaTime = {'H2': (1.328, 1.616), 'CO2': (2, 3.2), 
                'C2H4': (3.2, 3.824), 'CH4': (10, 12),
                'CO': (12.56, 13.6), 'O2': (5.008, 7.008)}
    cathodeGas = ['H2', 'CO', 'CH4', 'C2H4']
    anodeGas = ['H2', 'CO', 'CH4', 'C2H4', 'O2']
    
    #Data for GC Analysis
    pressure = 101325
    volume = 1E-6
    #UPDATE THIS BEFORE RUNNING 
    mol_per_area = {"H2":2.57e-13, "CO":4.97e-14, "CH4":5.13e-14, "C2H4":2.67e-14, "O2":1e-14} # current value for O2 is a placeholder, replace with calibrated data
    #			
    #Data for Gas stream Analysis
    gasMass = {"H2": 2.02, "CO": 28.01, "CH4": 16.04, "C2H4":28.05, "CO2":44.01, "H2O":18.02, 'O2': 32.0}
    #UPDATE THIS BEFORE RUNNING 
    c_gas = {"H2":1.23e4, "CO":1.54e+4, "CH4":6.36e+4, "C2H4":1.98e+4, "O2": 500} # current value for O2 is a placeholder, replace with calibrated data
    #			     
    def __init__(self, parent=None):
        '''
        The inherited class that does all of the data analysis
        '''
        super(dataAnalysis, self).__init__(parent)
    
    #Area Analysis Methods
    def read(self, filename):
        '''
        Read the csv file that was just converted from raw with OC and store both the
        x and the y value into local attributes
        '''
        self.results = pd.read_csv(filename, sep=',',header=None)
        self.x = list(self.results.loc[1:len(self.results.loc[:,3]),1].astype(float))
        self.y = list(self.results.loc[1:len(self.results.loc[:,3]),3].astype(float))
    
    def findIndex(self, num, arr):
        '''
        A function used to return the index of a number in a sorted array
        If there are no exact match, it return the index of the largest number that is 
        smaller than the input number
        '''
        i = 0
        while arr[i] <= num:
            i += 1
        return i 

    def integrate(self, gasArr):
        '''
        Integrate all the gases in gasArr based on each gas start and end time  
        '''
        self.gasArea = {}
        for gas in gasArr:
            startindex = self.findIndex(self.areaTime[gas][0], self.x)
            endindex = self.findIndex(self.areaTime[gas][1], self.x)

            xinterval = np.asarray(self.x[startindex:endindex])
            yinterval = np.asarray(self.y[startindex:endindex])
    
            df = xinterval[2] - xinterval[1]
            area = simps(yinterval, dx = df)
            #CHECK TO SEE IF 1000 IS THE NUMBER THAT WE WANT 
            #This is the signal to noise adjustment factor
            if area < 1000:
                area = 0
            self.gasArea[gas] = area
        #print('Area\n' + str(self.gasArea))

    #GC Analysis Methods
    def n_water_vap(self, temp):
        '''
        Find the amount of water in the injected volume based on partial pressure
        Also find the total number of moles of the injected volume based on temperature
        '''
        #TEMPERATURE IN CELCIUS
        p = 0.0002*temp**3 - 0.0078*temp**2 + 0.2392*temp - 0.0747 #[kPa]
        self.nH2O = ((p*1000)*self.volume) / (8.314*(temp+273)) #[mol]
        self.n_ideal = (self.pressure*self.volume/(8.314*temp))

    def findNx_GC(self):
        '''
        Find the mol number of each of the component in the GC injected volume
        '''
        self.nx_GC = {}
        n_combine = 0
        for gas, area in self.gasArea.items():
            self.nx_GC[gas] = area * self.mol_per_area[gas]
            n_combine += self.nx_GC[gas]

        self.nx_GC["H2O"] = self.nH2O
        n_combine += self.nx_GC["H2O"]

        self.nx_GC["CO2"] = self.n_ideal - n_combine
    
    def findMolFrac(self):
        '''
        Find the mol fraction of each of the component 
        '''
        self.molFrac = {}
        for key, value in self.nx_GC.items():
             self.molFrac[key] = value/self.n_ideal
        #print('molFrac\n' + str(self.molFrac))
    
    #Flow Anlysis Methods
    def findMx_GC(self):
        '''
        Find the mass of each of the component in the GC injected volume
        '''
        self.mx_GC =  {}
        self.mtot_GC = 0
        for gas, mol in self.nx_GC.items():
            self.mx_GC[gas] = mol * self.gasMass[gas]
            self.mtot_GC += self.mx_GC[gas]
        #print('mxGC\n' + str(self.mx_GC))

    def findMx_flow(self, massFlow):
        '''
        Find the mass flow of the main flow of each component
        '''
        self.massFlow = massFlow
        self.massFlowx = {}
        for gas in self.mx_GC.keys():
            self.massFlowx[gas] = (self.massFlow * (self.mx_GC[gas]/self.mtot_GC)) * (1000/3600) #[g/s]
        #print('mxFlow\n' + str(self.massFlowx))

    def findVFlow(self):
        '''
        Convert the massFlow into volumetric flow
        '''
        self.molFlow = {}
        n_flow_tot = 0
        for gas, mass in self.massFlowx.items():
            self.molFlow[gas] = (mass/self.gasMass[gas])
            n_flow_tot += self.molFlow[gas]

        self.V_flow_tot = n_flow_tot *8.314 * self.temp/self.pressure* 1e6 * 60 #[mL/min]
        #print('molFlow\n' + str(self.molFlow))

    def findFE(self, current):
        '''
        Use everything we have found upto this point to find the FE of each component
        '''
        self.FE = {}
        self.FE['Vtot'] = self.V_flow_tot
        for gas in self.gasArea.keys():
            self.FE[gas] = self.gasArea[gas] * self.V_flow_tot / (current * self.c_gas[gas] * 100)
        #print('FE\n' + str(self.FE))


    

