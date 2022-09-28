# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 11:27:54 2022

@author: eneemann

Script to export Master Address Table (MAT) for DABS OpenGov database

16 September 2022: first version of code (EMN)
"""

import os
import time
import zipfile
import wget
import arcpy
import requests
import pandas as pd
import numpy as np
from arcgis.features import GeoAccessor, GeoSeriesAccessor
import h3
from tqdm import tqdm

# Initialize the tqdm progress bar tool
tqdm.pandas()

#: Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

#: Set up directories
base_dir = r'C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\MAT'
work_dir = os.path.join(base_dir, f'DABS_{today}')

if os.path.isdir(work_dir) == False:
    os.mkdir(work_dir)
    
today_db_name = "DABS_MAT_" + today
today_db = os.path.join(work_dir, today_db_name + ".gdb")
addpts_wgs84 = os.path.join(today_db, 'AddressPoints_WGS84')

# dabc_db = r'C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\DABC.gdb'
# addpts = os.path.join(dabc_db, r'TEST_Millard_SGID_Addpts')


# Set up SGID paths and variables
SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
addr_path = os.path.join(SGID, 'SGID.LOCATION.AddressPoints')

#: Get SGID layers names from paths
addr = addr_path.split('.')[-1]

SGID_files = [addr]
SGID_layers = [addr_path]

addpts = os.path.join(today_db, addr)

#: Create working geodatabase with today's date
def create_gdb():
    print("Creating file geodatabase ...")
    if arcpy.Exists(today_db) == False:
        arcpy.CreateFileGDB_management(work_dir, today_db_name)
    
    arcpy.env.workspace = today_db
    arcpy.env.qualifiedFieldNames = False


#: Copy SGID data layers to local for faster processing
#: This seems to be a little faster than hitting the internal SGID and we must project locally
def export_sgid():
    export_time = time.time()
    for item in SGID_layers:
        exported = item.rsplit('.', 1)[-1]
        if arcpy.Exists(os.path.join(today_db, exported)):
            arcpy.management.Delete(os.path.join(today_db, exported))
        print(f"Exporting SGID {item} to: {exported}")
        arcpy.FeatureClassToFeatureClass_conversion(item, today_db, exported)     
    
    print("Time elapsed exporting SGID data: {:.2f}s".format(time.time() - export_time))
    fc = os.path.join(today_db, exported)
    
    return fc


def project_fc():
    print("Projecting to WGS84 ...")
    sr = arcpy.SpatialReference("WGS 1984")
    arcpy.Project_management(addpts, addpts_wgs84, sr, "WGS_1984_(ITRF00)_To_NAD_1983")

     
        

#: Call functions 
create_gdb()
addpts = export_sgid()
project_fc()



#: Convert working feature class to spatial data frame
print("Converting working data to spatial dataframe ...")
addpts_sdf = pd.DataFrame.spatial.from_featureclass(addpts_wgs84)

#: Updating UTAddPtID in a lamdba function
print("Updating UTAddPtID as a lambda function ...")
update_time = time.time()
addpts_sdf['UTAddPtID'] = addpts_sdf.progress_apply(lambda r: f'''{r['UTAddPtID']}'''.replace(' | ', '_').replace(' ', '_').strip(), axis=1)
print("\n    Time elapsed updating UTAddPtID as a lambda function: {:.2f}s".format(time.time() - update_time))

#: Calc UNIT as new variable
print("Calculating UNIT as a new column ...")
unit_time = time.time()
mask = addpts_sdf['UnitType'].isin([None, 'None', '', ' '])
addpts_sdf.loc[mask, 'UnitType'] = ''
mask = addpts_sdf['UnitID'].isin([None, 'None', '', ' '])
addpts_sdf.loc[mask, 'UnitID'] = ''
addpts_sdf['UNIT'] = addpts_sdf.progress_apply(lambda r: f'''{r['UnitType']} {r['UnitID']}'''.strip().replace('  ', ' ').replace('  ', ' '), axis = 1)
print("\n    Time elapsed for UNIT calculation: {:.2f}s".format(time.time() - unit_time))

#: Calc STREET as new variable
print("Calculating STREET as a new column ...")
street_time = time.time()
addpts_sdf['STREET'] = addpts_sdf.progress_apply(lambda r: f'''{r['FullAdd']}'''.split(' ', 1)[1].strip(), axis = 1)
# If UnitType is not blank
mask = ~addpts_sdf['UnitType'].isin([None, 'None', '', ' '])
addpts_sdf.loc[mask, 'STREET'] = addpts_sdf[mask].progress_apply(lambda r: r['STREET'].split(r['UnitType'])[0].strip(), axis = 1)
# If # in STREET
mask = addpts_sdf['STREET'].str.contains('#')
addpts_sdf.loc[mask, 'STREET'] = addpts_sdf[mask].progress_apply(lambda r: r['STREET'].split('#')[0].strip(), axis = 1)
print("\n    Time elapsed for STREET calculation: {:.2f}s".format(time.time() - street_time))

#: Calc lat/lon as new variable
print("Calculating lat/lon as a new column ...")
latlon_time = time.time()
addpts_sdf['longitude'] = addpts_sdf.SHAPE.apply(lambda p: p.x)
addpts_sdf['latitude'] = addpts_sdf.SHAPE.apply(lambda p: p.y)
print("\n    Time elapsed for lat/lon as new variable: {:.2f}s".format(time.time() - latlon_time))

#: Use basic h3 to test timing in a lamdba function
print("Calculating basic h3 index as a lambda function ...")
h3_lambda = time.time()
addpts_sdf['h3_index_13'] = addpts_sdf.progress_apply(lambda p: h3.geo_to_h3(p['latitude'], p['longitude'], 13), axis = 1)
print("\n    Time elapsed in h3 as a lambda function: {:.2f}s".format(time.time() - h3_lambda))

#: Calculate matID in a lamdba function
print("Calculating matID as a lambda function ...")
mat_lambda = time.time()
#: Change matID calculation to follow 'h3index_UNIT' pattern
# addpts_sdf['matID'] = addpts_sdf.progress_apply(lambda r: f'''{r['UTAddPtID']}_{r['h3_index_13']}''', axis = 1)
addpts_sdf['matID'] = addpts_sdf.progress_apply(lambda r: f'''{r['h3_index_13']}_{r['UNIT']}'''.rstrip('_').replace(' ', '_').strip(), axis = 1)
print("\n    Time elapsed in matID as a lambda function: {:.2f}s".format(time.time() - mat_lambda))

#: Slim down the dataframe to a specified set of columns
columns = ['FullAdd', 'AddNum', 'PrefixDir', 'StreetName', 'SuffixDir', 'StreetType', 'UNIT', 'STREET', 'City', 'ZipCode', 'State',
           'ParcelID', 'longitude', 'latitude', 'matID']
addpts_slim = addpts_sdf[columns]

#: Compare size of dataframe before/after removing duplicates
orig_length = len(addpts_slim.index)
print(f'Number of points before de-duplicating:  {orig_length}')

addpts_slim.drop_duplicates('matID', inplace=True)

final_length = len(addpts_slim.index)
diff = orig_length - final_length
print(f'Number of points after removing duplicates:  {final_length}')
print(f'Removed {diff} duplicates!')

addpts_slim.nunique()


#: Export dataframe to CSV
mat_csv = os.path.join(work_dir, f'DABS_{today}_mat.csv')
addpts_slim.to_csv(mat_csv)


#: Delete extra files from geodatabase
def delete_files():
    #: Delete temporary and intermediate files
    arcpy.env.workspace = today_db
    print("Deleting copied SGID files ...")
    for file in SGID_files:
        if arcpy.Exists(file):
            print(f"Deleting {file} ...")
            arcpy.management.Delete(file)
    
delete_files()



#: Stop timer and print end time in UTC
print("Script shutting down ...")
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
