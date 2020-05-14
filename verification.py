from GCSampler import dataAnalysis
import os
import csv
'''
To use this script:
- Collect the raw files that you want to analyze
- Use TCNav graphic editor to get the areas of the different gases and input the following information into verification.csv
   - File name without the extension
   - Area of H2, CO, Ch4, C2H4 in that particular order
   - Save the file, check to make sure there are no spaces in each headers between the commas
- Use OpenChrom to export data to DataCSV 
- Run this script and a report of the difference in area will be generated with the name defined by the variable export_file
- To make adjustments to the integration, go to GCSampler and change the execution steps there. Afte adjustment, run this script again to check if results are better
'''
export_file = 'verlog.csv' #Change this name is you want seperate reports
with open('verification.csv', 'r') as f:
    data = list(csv.DictReader(f, delimiter = ','))
    for row in data:
        filename = row.pop('FileName')
        analyze = dataAnalysis()
        analyze.read(os.path.join(os.getcwd(), 'DataCSV', (filename+'.csv')))
        analyze.integrate(analyze.cathodeGas)
        
        error = {}
        for gas, area in analyze.gasArea.items():
            error[gas] = abs(area - float(row[gas])) / float(row[gas])

        with open(export_file, 'a+', newline='') as log:
            write = csv.writer(log)
            write.writerow([f'File: {filename}'] + analyze.cathodeGas)
            write.writerow(['Manual Output'] + list(row.values()))
            write.writerow(['Python Output'] + list(analyze.gasArea.values()))
            write.writerow(['Error'] + list(error.values()))
            write.writerow('')
