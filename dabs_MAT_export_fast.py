# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 11:27:54 2022

@author: eneemann

Script to export Master Address Table (MAT) for DABS OpenGov database

16 September 2022: first version of code (EMN)
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
# today = '20230201'

# previous_mat_path = r"C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\MAT\DABS_20221209\DABS_mat.csv"

#: Set up directories
base_dir = r'C:\DABC\MAT'
work_dir = os.path.join(base_dir, f'DABS_{today}')

if os.path.isdir(work_dir) == False:
    os.mkdir(work_dir)
    
today_db_name = "DABS_MAT_" + today
today_db = os.path.join(work_dir, today_db_name + ".gdb")
addpts_wgs84 = os.path.join(today_db, 'AddressPoints_WGS84')

# dabc_db = r'C:\DABC\DABC.gdb'
# addpts = os.path.join(dabc_db, r'TEST_Millard_SGID_Addpts')


# Set up SGID paths and variables
SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"
addr_path = os.path.join(SGID, 'SGID.LOCATION.AddressPoints')

#: Get SGID layers names from paths
addr = addr_path.split('.')[-1]
SGID_files = [addr]
SGID_layers = [addr_path]
addpts = os.path.join(today_db, addr)

#: Set up polygon layer paths
dabs_db = r"C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\DABS_latest_data.gdb"
zone_path = os.path.join(dabs_db, 'DABS_Compliance_Zones')
flag_path = os.path.join(dabs_db, 'DABS_Flag_Areas')

#: Set up polygon assignment fields
group_field = 'Group_Name'
flag_field = 'category'

#: Create polygon assignment dictionary where key is name of field that needs updated in points layer
#: format is:
        #: 'pt_field_name': {'poly_path': path, 'poly_field': field}
poly_dict = {
        'Comp_Group': {'poly_path': zone_path, 'poly_field': group_field},
        'Flag': {'poly_path': flag_path, 'poly_field': flag_field}
        }

#: Get existing DABS licenses and put in a list to check against later
# dabs_db = r"C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\DABS_latest_data.gdb"
dabs_db = r"C:\DABC\DABS_latest_data.gdb"
dabs_licenses = os.path.join(dabs_db, "DABS_All_Licenses")
# dabs_licenses = os.path.join(r'C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\OpenGov\address_fixes_20221206\DABS.gdb', "DABS_All_Licenses_20221216_addsys_fixed")
dabs_addrs = [str(row).strip('''(',)"''').replace("'", "") for row in arcpy.da.SearchCursor(dabs_licenses, 'Address')]

              
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
    
    
#: Create function for compliance zone assignments
def assign_poly_attr(pts, polygonDict):
    
    arcpy.env.workspace = os.path.dirname(pts)
    arcpy.env.overwriteOutput = True
    
    for lyr in polygonDict:
        # set path to polygon layer
        polyFC = polygonDict[lyr]['poly_path']
        print (f'working on {polyFC} ... ')
        
        # generate near table for each polygon layer
        neartable = 'in_memory\\near_table'
        arcpy.analysis.GenerateNearTable(pts, polyFC, neartable, '1 Meters', 'NO_LOCATION', 'NO_ANGLE', 'CLOSEST')
        
        # create dictionaries to store data
        pt_poly_link = {}       # dictionary to link points and polygons by OIDs 
        poly_OID_field = {}     # dictionary to store polygon NEAR_FID as key, polygon field as value
    
        # loop through near table, store point IN_FID (key) and polygon NEAR_FID (value) in dictionary (links two features)
        with arcpy.da.SearchCursor(neartable, ['IN_FID', 'NEAR_FID', 'NEAR_DIST']) as nearCur:
            for row in nearCur:
                pt_poly_link[row[0]] = row[1]       # IN_FID will return NEAR_FID
                # add all polygon OIDs as key in dictionary
                poly_OID_field.setdefault(row[1])
        
        # loop through polygon layer, if NEAR_FID key in poly_OID_field, set value to poly field name
        with arcpy.da.SearchCursor(polyFC, ['OID@', polygonDict[lyr]['poly_field']]) as polyCur:
            for row in polyCur:
                if row[0] in poly_OID_field:
                    poly_OID_field[row[0]] = row[1]
        
        # loop through points layer, using only OID and field to be updated
        with arcpy.da.UpdateCursor(pts, ['OID@', lyr]) as uCur:
            for urow in uCur:
                try:
                    # search for corresponding polygon OID in polygon dictionay (polyDict)
                    if pt_poly_link[urow[0]] in poly_OID_field:
                        # if found, set point field equal to polygon field
                        # IN_FID in pt_poly_link returns NEAR_FID, which is key in poly_OID_field that returns value of polygon field
                        urow[1] =  poly_OID_field[pt_poly_link[urow[0]]]
                except:         # if error raised, just put a blank in the field
                    urow[1] = ''
                uCur.updateRow(urow)
    
        # Delete in-memory near table
        arcpy.management.Delete(neartable)

     
########################    
#: Call functions 
create_gdb()
addpts = export_sgid()
project_fc()

arcpy.management.AddField(addpts_wgs84, "Flag", "TEXT", "", "", 10)
arcpy.management.AddField(addpts_wgs84, "Comp_Group", "TEXT", "", "", 10)


#: Call polygon assignment function
print("Assigning polygon attributes ...")
polygon_time = time.time()
assign_poly_attr(addpts_wgs84, poly_dict)
print("\n    Time elapsed assigning polygon attributes: {:.2f}s".format(time.time() - polygon_time))
#########################


#: Convert working feature class to spatial data frame
print("Converting working data to spatial dataframe ...")
addpts_sdf = pd.DataFrame.spatial.from_featureclass(addpts_wgs84)

#: Replace 'City' values with 'AddSystem' values
print("Populating 'City' field with 'AddSystem' values...")
addpts_sdf['City'] = addpts_sdf['AddSystem']

#: If AddSystem contains a parenthesis, split on first and remove
mask = addpts_sdf['City'].str.contains('(', regex=False)
addpts_sdf.loc[mask, 'City'] = addpts_sdf[mask].progress_apply(lambda r: r['City'].rsplit('(', 1)[0].strip(), axis = 1)

#: Clean up 'FullAdd' values (remove apostrophes)
print("Cleaning up 'FullAdd' values...")
#: If AddSystem contains apostrophes, remove them
mask = addpts_sdf['FullAdd'].str.contains("'")
addpts_sdf.loc[mask, 'FullAdd'] = addpts_sdf[mask].progress_apply(lambda r: r['FullAdd'].replace("'", ""), axis = 1)

#: Turn flag field into yes/no
print("Changing 'Flag' into a yes/no field...")
mask = addpts_sdf['Flag'].isin([None, '', ' '])
addpts_sdf.loc[mask, 'Flag'] = 'no'
addpts_sdf.loc[~mask, 'Flag'] = 'yes'

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
# If apostrophe in STREET
mask = addpts_sdf['STREET'].str.contains("'")
addpts_sdf.loc[mask, 'STREET'] = addpts_sdf[mask].progress_apply(lambda r: r['STREET'].replace("'", ""), axis = 1)
print("\n    Time elapsed for STREET calculation: {:.2f}s".format(time.time() - street_time))

#: Calc DABS as new variable
print("Calculating DABS as a new column ...")
dabs_time = time.time()
mask = addpts_sdf['FullAdd'].isin(dabs_addrs)
addpts_sdf.loc[mask, 'DABS'] = 'yes'
addpts_sdf.loc[~mask, 'DABS'] = 'no'
print("\n    Time elapsed for STREET calculation: {:.2f}s".format(time.time() - dabs_time))

#: Calc lat/lon as new variable
print("Calculating lat/lon as a new column ...")
latlon_time = time.time()
addpts_sdf['longitude'] = addpts_sdf.SHAPE.progress_apply(lambda p: p.x)
addpts_sdf['latitude'] = addpts_sdf.SHAPE.progress_apply(lambda p: p.y)
print("\n    Time elapsed for lat/lon as new variable: {:.2f}s".format(time.time() - latlon_time))

#: Use basic h3 to test timing in a lamdba function
print("Calculating basic h3 index as a lambda function ...")
h3_lambda = time.time()
addpts_sdf['h3_index_13'] = addpts_sdf.progress_apply(lambda p: h3.geo_to_h3(p['latitude'], p['longitude'], 13), axis = 1)
print("\n    Time elapsed in h3 as a lambda function: {:.2f}s".format(time.time() - h3_lambda))

#: Calculate matID in a lamdba function
print("Calculating matID as a lambda function ...")
mat_lambda = time.time()
#: Change matID calculation to follow 'h3index_AddNum_UNIT' pattern
addpts_sdf['matID'] = addpts_sdf.progress_apply(lambda r: f'''{r['h3_index_13']}_{r['AddNum']}_{r['UNIT']}'''.rstrip('_').replace(' ', '_').strip(), axis = 1)
print("\n    Time elapsed in matID as a lambda function: {:.2f}s".format(time.time() - mat_lambda))

#: Slim down the dataframe to a specified set of columns
columns_dabs = ['FullAdd', 'AddNum', 'PrefixDir', 'StreetName', 'SuffixDir', 'StreetType', 'UNIT', 'STREET', 'City', 'ZipCode', 'State',
           'ParcelID', 'longitude', 'latitude', 'matID', 'Comp_Group', 'Flag', 'DABS']
addpts_slim = addpts_sdf[columns_dabs]

#: Strip all strings of whitespace
strip_time = time.time()
addpts_slim = addpts_slim.applymap(lambda x: x.strip() if isinstance(x, str) else x)
print("\n    Time elapsed stripping all whitespace: {:.2f}s".format(time.time() - strip_time))

#: Compare size of dataframe before/after removing matID duplicates
orig_length = len(addpts_slim.index)
print(f'Number of points before de-duplicating:  {orig_length}')

#: Remove duplicates on matID
addpts_slim.sort_values(['DABS', 'matID'], axis=0, ascending=[False, True], inplace=True)
addpts_slim.drop_duplicates('matID', inplace=True, keep='first')

#: remove 'DABS' column
columns = ['FullAdd', 'AddNum', 'PrefixDir', 'StreetName', 'SuffixDir', 'StreetType', 'UNIT', 'STREET', 'City', 'ZipCode', 'State',
           'ParcelID', 'longitude', 'latitude', 'matID', 'Comp_Group', 'Flag']
addpts_slim = addpts_slim[columns]

final_length = len(addpts_slim.index)
diff = orig_length - final_length
print(f'Number of points after removing duplicates on matID:  {final_length}')
print(f'Removed {diff} duplicates!')

addpts_slim.nunique()


#: Export dataframe to CSV
mat_csv = os.path.join(work_dir, 'DABS_mat.csv')
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


#: Stop timer and print end time
print("Script shutting down ...")
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
