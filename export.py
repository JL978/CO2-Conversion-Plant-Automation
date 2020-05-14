import pandas as pd
import sqlite3
import os
'''
A simple script that pull all the data out of the sqlite databases and convert them into csv files
The csv files are named after the available tables: [Area, molFlow, FE, molFrac]
All the exported files are goes to their respected folder in a folder called Exported Data
This folder should be found in the same folder as this script, if it is not already present
then the folder is created 
'''
databases = {'Cathode': 'cathodeGasData.db','Anode': 'anodeGasData.db'}
dataDir = os.path.join(os.getcwd(), 'Exported Data')

def export():
    for side, db in databases.items():
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        tables = cursor.execute('Select name from sqlite_master where type = "table"')
        for table in tables:
            data = pd.read_sql(f'Select * From {table[0]}', conn)
            #data.dropna() #uncomment if the inserted null values are not needed
            fileName = f'{table[0]}.csv'
            fileDir = os.path.join(dataDir, side, fileName)
            data.to_csv(fileDir, index = False)
try: 
    export()
except FileNotFoundError:
    os.mkdir(dataDir)
    os.mkdir(os.path.join(dataDir, 'Cathode'))
    os.mkdir(os.path.join(dataDir, 'Anode'))
finally:
    export()
