import random
import sqlite3
import datetime
'''
This file contain all the required functions to work with the sql database
'''
def getDt():
    '''
    Function that grab the current date and time and put the date and time into seperate
    bucket in the dictionary
    '''
    now = datetime.datetime.now()
    date = now.strftime("%y-%m-%d")
    ntime = now.strftime("%H:%M:%S")
    return dict((("Date", date), ("Time", ntime)))

def normalTransform(d):
    '''
    Tranform a dictionary into a string with just the keys and comma between them
    '''
    new = ''
    for key in d.keys():
        new += key + ', '
    return new.strip(', ')

def weirdTranform(d):
    '''
    Transform a dictionary into a string with just the keys with leading colons and follow by commas
    '''
    new = ''
    for key in d.keys():
        new += (':' + key + ', ')
    return new.strip(', ')

def insertSQL(db, tName, dataDict):
    '''
    Write a dictionary of data (dataDict) into a database (db), into a specified table (tName)
    '''
    conn = sqlite3.connect(db)
    with conn:
        cursor = conn.cursor()
        cursor.execute(f'CREATE TABLE IF NOT EXISTS {tName} ({normalTransform(dataDict)})')
        print(f'INSERT INTO {tName} VALUES ({weirdTranform(dataDict)})')
        cursor.execute(f'INSERT INTO {tName} VALUES ({weirdTranform(dataDict)})', dataDict)
    conn.commit()




        


