# -*- coding: utf-8 -*-
"""
Created on Wed Aug 31 16:05:31 2022

@author: eneemann
"""

import arcpy
import os
import time

dabs_db = r"C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\DABC.gdb"
dabs_licenses = os.path.join(dabs_db, "DABS_All_Licenses_20220923_calcs")


dabs_descr = {
    'AL': 'AIRPORT LOUNGE',
    'AR': 'ARENA LICENSE',
    'BC': 'BANQUET CATERING',
    'BE': 'ON PREMISE BEER',
    'BR': 'BREWER LOCATED OUTSIDE UTAH',
    'BW': 'BEER WHOLESALER',
    'CL': 'BAR ESTABLISHMENT',
    'HA': 'HOSPITALITY AMENITY',
    'HC': 'HEALTH CARE FACILITY',
    'HL': 'HOTEL',
    'IN': 'INDUSTRIAL / MANUFACTURING',
    'LB': 'BAR ESTABLISHMENT',
    'LR': 'RESTAURANT FULL SERVICE',
    'LT': 'LIQUOR TRANSPORT LICENSE',
    'LW': 'LIQUOR WAREHOUSE',
    'MB': 'MANUFACTURING - BREWERY',
    'MD': 'MANUFACTURING - DISTILLERY',
    'MO': 'MASTER OFF PREMISE BEER RETAILER',
    'MP': 'MINOR PERMIT / CONCERT-DANCE HALL',
    'MR': 'MANUFACTURER REPRESENTATIVE',
    'MW': 'MANUFACTURING - WINERY',
    'OP': 'OFF PREMISE BEER RETAILER',
    'PA': 'PACKAGE AGENCY',
    'PS': 'PUBLIC SERVICE',
    'RB': 'RESTAURANT / BEER ONLY',
    'RC': 'RECEPTION CENTER',
    'RE': 'RESTAURANT',
    'RL': 'RESTAURANT LIMITED',
    'RS': 'RESORT',
    'SA': 'RELIGIOUS',
    'SC': 'SCIENTIFIC / EDUCATIONAL',
    'SE': 'SINGLE EVENT',
    'ST': 'STATE STORES',
    'TB': 'TEMPORARY BEER',
    'TV': 'TAVERN - ON PREMISE BEER'
}

dabs_renew = {
    'AL': '10/31',
    'AR': '10/31',
    'BC': '10/31',
    'BE': '2/28',
    'BR': '12/31',
    'BW': '12/31',
    'CL': '6/30',
    'HA': '10/31',
    'HC': None,
    'HL': '10/31',
    'IN': None,
    'LB': '6/30',
    'LR': '10/31',
    'LT': '5/31',
    'LW': '12/31',
    'MB': '12/31',
    'MD': '12/31',
    'MO': None,
    'MP': None,
    'MR': '12/31',
    'MW': '12/31',
    'OP': '2/28',
    'PA': None,
    'PS': '12/31',
    'RB': '2/28',
    'RC': '10/31',
    'RE': '10/31',
    'RL': '10/31',
    'RS': '10/31',
    'SA': None,
    'SC': None,
    'SE': None,
    'ST': None,
    'TB': None,
    'TV': '2/28'
}

dabs_group = {
    'AL': 'Bar',
    'AR': None,
    'BC': 'Hotel',
    'BE': 'Restaurant',
    'BR': None,
    'BW': 'Industry',
    'CL': 'Bar',
    'HA': 'Hotel',
    'HC': None,
    'HL': 'Hotel',
    'IN': 'Special Use',
    'LB': 'Bar',
    'LR': 'Restaurant',
    'LT': 'Industry',
    'LW': 'Industry',
    'MB': 'Manufacturer',
    'MD': 'Manufacturer',
    'MO': None,
    'MP': 'Bar',
    'MR': 'Industry',
    'MW': 'Manufacturer',
    'OP': 'Off-Premise',
    'PA': 'Package Agency',
    'PS': 'Special Use',
    'RB': 'Restaurant',
    'RC': 'Hotel',
    'RE': 'Restaurant',
    'RL': 'Restaurant',
    'RS': 'Hotel',
    'SA': 'Special Use',
    'SC': 'Special Use',
    'SE': None,
    'ST': 'State Liquor Store',
    'TB': None,
    'TV': 'Bar'
}


dabs_comp_needed = {
    'AL': 'yes',
    'AR': 'no',
    'BC': 'yes',
    'BE': 'yes',
    'BR': 'no',
    'BW': 'yes',
    'CL': 'yes',
    'HA': 'yes',
    'HC': 'no',
    'HL': 'yes',
    'IN': 'no',
    'LB': 'yes',
    'LR': 'yes',
    'LT': 'yes',
    'LW': 'yes',
    'MB': 'yes',
    'MD': 'yes',
    'MO': 'no',
    'MP': 'yes',
    'MR': 'no',
    'MW': 'yes',
    'OP': 'no',
    'PA': 'no',
    'PS': 'no',
    'RB': 'yes',
    'RC': 'yes',
    'RE': 'yes',
    'RL': 'yes',
    'RS': 'yes',
    'SA': 'no',
    'SC': 'no',
    'SE': 'no',
    'ST': 'no',
    'TB': 'no',
    'TV': 'yes'
}

# Calculate DABS fields from License Number
update_count = 0
#               0          1             2            3            4              5
fields = ['Lic_Number', 'Lic_Type', 'Lic_Descr', 'Lic_Group', 'Renew_Date', 'Comp_Needed']
with arcpy.da.UpdateCursor(dabs_licenses, fields) as cursor:
    print("Looping through rows to calculate DABS fields ...")
    for row in cursor:
        lic_type = row[0][:2]
        row[1] = lic_type
        row[2] = dabs_descr[f'{lic_type}']
        row[3] = dabs_group[f'{lic_type}']
        row[4] = dabs_renew[f'{lic_type}']
        row[5] = dabs_comp_needed[f'{lic_type}']
        update_count += 1
        cursor.updateRow(row)
print(f"Total count of updates is {update_count}")