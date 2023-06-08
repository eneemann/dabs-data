# -*- coding: utf-8 -*-
"""
Created on Thu Feb 9 08:13:11 2023

@author: eneemann

Script to compare active DABS licenses against those in the map application

09 February 2023: first version of code (EMN)
"""

import os
from pathlib import Path
import time
import arcpy
import pandas as pd
from arcgis import GeoAccessor, GeoSeriesAccessor
import numpy as np
import h3
from tqdm import tqdm
import pygsheets

try:
    from . import credentials
except ImportError:
    import credentials

# Initialize the tqdm progress bar tool
tqdm.pandas()
gsheets_client = pygsheets.authorize(service_file=credentials.SERVICE_ACCOUNT_JSON)

#: Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

#: Set up variables
dabs_licenses = 'https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/DABS_GIS/FeatureServer/0'


#: Get addresses from proposed Google Sheet
sheet_title = time.strftime("%m/%Y")
sheet_title = 'Current Licenses 2.8.23'
sheet = gsheets_client.open_by_key(credentials.SHEET_ID)
active_df = sheet.worksheet_by_title(sheet_title).get_as_df()

#: Remove NULLs and blanks, strip whitespace
active_df = active_df.applymap(lambda x: x.strip().upper() if isinstance(x, str) else x)
# active_df.sort_values(['DABS', 'matID'], axis=0, ascending=[False, True], inplace=True)
print(active_df.head())

#: Get list of active licenses
actives = list(active_df['LICENSE_NO'])
actives.sort()
print(f'Active license count:   {len(actives)}')
# actives = list(set(actives))
# print(f'Active license count:   {len(actives)}')  
           
#: Get list of licenses from AGOL
dabs_licenses = [str(row).strip('''(',)"''').replace("'", "") for row in arcpy.da.SearchCursor(dabs_licenses, 'Lic_Number')]
dabs_licenses.sort()
print(f'AGOL license count:     {len(dabs_licenses)}')
# dabs_licenses = list(set(dabs_licenses))
# print(f'AGOL license count:     {len(dabs_licenses)}')

AGOL_to_remove = list(set(dabs_licenses) - set(actives))
AGOL_to_remove.sort()
print(f'\nLicenses to remove from AGOL {len(AGOL_to_remove)}:')
print(AGOL_to_remove)

AGOL_to_add = list(set(actives) - set(dabs_licenses))
AGOL_to_add.sort()
print(f'\nLicenses to add to AGOL {len(AGOL_to_add)}:')
print(AGOL_to_add)

#: Export removals to CSV
removes_df = pd.DataFrame.from_dict({'Lic_Number': AGOL_to_remove})
print(removes_df.head())
out_dir = Path(r'C:\DABC\Active_License_Review')
remove_name = out_dir / f'licenses_to_remove_{today}.csv'
removes_df.to_csv(remove_name)     

#: Export needed additions to CSV
adds_df = active_df[active_df['LICENSE_NO'].isin(AGOL_to_add)]
add_name = out_dir / f'licenses_to_add_{today}.csv'
adds_df.to_csv(add_name)

   
#: Stop timer and print end time in UTC
print("Script shutting down ...")
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
