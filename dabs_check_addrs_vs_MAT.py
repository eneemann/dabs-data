# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 19:51:54 2022

@author: eneemann

Script to compare addresses in DABS licenses to addresses in the Master Address Table (MAT) for DABS OpenGov database

15 December 2022: first version of code (EMN)
"""

import os
import time
import arcpy
import pandas as pd
from arcgis import GeoAccessor, GeoSeriesAccessor
import numpy as np
import h3
from tqdm import tqdm

# Initialize the tqdm progress bar tool
tqdm.pandas()

#: Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

#: Create variables
dabs_db = r"C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\DABS_latest_data.gdb"
# dabs_licenses = os.path.join(dabs_db, "DABS_All_Licenses")
# dabs_licenses = os.path.join(r'C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\OpenGov\address_fixes_20221206\DABS.gdb', "DABS_All_Licenses_20221215_addsys")
# dabs_licenses = os.path.join(r'C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\OpenGov\address_fixes_20221206\DABS.gdb', "DABS_All_Licenses_20221219_noGUID")
dabs_licenses = 'https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/DABS_GIS/FeatureServer/0'
mat_dir = r'C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\MAT\DABS_20221209'
mat_csv = os.path.join(mat_dir, 'DABS_mat.csv')
# mat_csv = os.path.join(mat_dir, 'DABS_mat_ALL_ADDRESSES.csv')
# mat_csv = os.path.join(mat_dir, 'DABS_mat_no_dups.csv')
#: Get list of addresses from dabs licenses
dabs_addrs = [str(row).strip('''(',)"''').replace("'", "") for row in arcpy.da.SearchCursor(dabs_licenses, 'Address')]
# dabs_sys = [f"""{str(row[0]).strip('''(',)"''').replace("'", "")} {str(row[1]).strip("(',)").replace("'", "")}""" for row in arcpy.da.SearchCursor(dabs_licenses, ['Address', 'City'])]
dabs_sys = [f"""{str(row[0]).strip('''(,)"''').replace("'", "")} {str(row[1]).strip("(,)").replace("'", "")}""" for row in arcpy.da.SearchCursor(dabs_licenses, ['Address', 'City'])]

                                                                                       
#: Get list of addresses from MAT
mat_df = pd.read_csv(mat_csv)
mat_addrs = list(mat_df['FullAdd'])
# mat_df['LongAdd'] = mat_df.progress_apply(lambda r: f'''{r['FullAdd']} {r['City']}'''.strip('''(',)"''').replace('  ', ' ').replace('  ', ' '), axis = 1)
mat_df['LongAdd'] = mat_df.progress_apply(lambda r: f'''{r['FullAdd']} {r['City']}'''.strip('''(,)"''').replace('  ', ' ').replace('  ', ' '), axis = 1)
mat_sys = list(mat_df['LongAdd'])

not_matched = list(set(dabs_addrs) - set(mat_addrs))
not_matched_sys = list(set(dabs_sys) - set(mat_sys))

print(f"   Number of unmatched addresses: {len(not_matched)}")
print(f"   Number of unmatched addresses using address system: {len(not_matched_sys)}")



#: Stop timer and print end time in UTC
print("Script shutting down ...")
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))


# sql = f'''add_and_sys IN ({", ".join(["'" + add + "'" for add in not_matched_sys])})'''
# print(sql)
