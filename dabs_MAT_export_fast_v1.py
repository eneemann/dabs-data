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
# import h3 as h3_basic
import h3.api.numpy_int as h3
from tqdm import tqdm
# import credentials

# Initialize the tqdm progress bar tool
tqdm.pandas()

#: Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

#: Set up directories
base_dir = r'C:\Users\eneemann\Documents\ArcGIS\Projects\DABC'
work_dir = os.path.join(base_dir, f'DABS_{today}')

if os.path.isdir(work_dir) == False:
    os.mkdir(work_dir)
    
today_db_name = "DABS_MAT_" + today
today_db = os.path.join(work_dir, today_db_name + ".gdb")
addpts_wgs84 = os.path.join(today_db, 'AddressPoints_WGS84')

dabc_db = r'C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\DABC.gdb'
# addpts = os.path.join(dabc_db, r'TEST_Millard_SGID_Addpts')


# Set up SGID paths and variables
# SGID = credentials.SGID
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
#: This seems to be a little faster than hitting the internal SGID for point-in-polygon analyses
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


def calc_fields():
    #: Add new fields
    arcpy.management.AddField(addpts, "STREET", "TEXT", "", "", 50)
    arcpy.management.AddField(addpts, 'longitude', 'FLOAT', field_scale="6", field_alias="Longitude")
    arcpy.management.AddField(addpts, 'latitude', 'FLOAT', field_scale="6", field_alias="Latitude")
    arcpy.management.AddField(addpts, "UNIT", "TEXT", "", "", 20)

    #: Calculate fields (disclaimer, replace blanks with NULLs)
    calc_time = time.time()
    #                   0            1          2         3           4       5        6
    calc_fields = ['UTAddPtID', 'FullAdd', 'AddNum', 'UnitType', 'UnitID', 'UNIT', 'STREET']
    with arcpy.da.UpdateCursor(addpts, calc_fields) as update_cursor:
        print("Looping through rows in FC to calculate fields ...")
        for row in update_cursor:
            #: recalc addptid with underscores
            temp = row[0].replace(' | ', '_')
            temp = temp.replace(' ', '_').strip()
            row[0] = temp
            
            #: calc combined unit field
            if row[3] is None:
                unittype = ''
            else:
                unittype = row[3]
            if row[4] is None:
                unitid = ''
            else:
                unitid = row[4]
            row[5] = f'{unittype} {unitid}'.strip().replace('  ', ' ').replace('  ', ' ')
            
            #: calc STREET field by chopping off addnum and unit info
            street = row[1].split(' ', 1)[1]
            
            if row[3] is not None and row[3] not in ('', ' '):
                final = street.split(row[3])[0].strip()
            elif '#' in street:
                final = street.split('#')[0].strip()
            else:
                final = street
                
            row[6] = final
                
            update_cursor.updateRow(row)
    

    #: Calculate lon/lat values for all points (in WGS84 coords)
    lat_calc = 'arcpy.PointGeometry(!Shape!.centroid, !Shape!.spatialReference).projectAs(arcpy.SpatialReference(4326)).centroid.Y'
    lon_calc = 'arcpy.PointGeometry(!Shape!.centroid, !Shape!.spatialReference).projectAs(arcpy.SpatialReference(4326)).centroid.X'

    arcpy.management.CalculateField(addpts, 'latitude', lat_calc, "PYTHON3")
    arcpy.management.CalculateField(addpts, 'longitude', lon_calc, "PYTHON3")

    print("Time elapsed calculating fields: {:.2f}s".format(time.time() - calc_time))




def assign_h3(row):
    """
    Function to calculate h3 grid index from lat/lon values
    """
    # row['h3_index_13'] = h3.latlng_to_cell(row['latitude'], row['longitude'], 13)
    row['h3_int_13'] = h3.geo_to_h3(row['latitude'], row['longitude'], 13)
    row['h3_index_13'] = h3.h3_to_string(row['h3_int_13'])
    row['matID'] = f'''{row['UTAddPtID']}_{row['h3_index_13']}'''

    return row


def field_calc(row):
    """
    Function to calculate the combined unit field
    """
    #: recalc addptid with underscores
    row['UTAddPtID'] = row['UTAddPtID'].replace(' | ', '_')
    row['UTAddPtID'] = row['UTAddPtID'].replace(' ', '_').strip()
    
    
    #: calc combined unit field
    if row['UnitType'] is None:
        unittype = ''
    else:
        unittype = row['UnitType']
    if row['UnitID'] is None:
        unitid = ''
    else:
        unitid = row['UnitID']
    row['UNIT'] = f'{unittype} {unitid}'.strip().replace('  ', ' ').replace('  ', ' ')


    #: calc STREET field by chopping off addnum and unit info
    street = row['FullAdd'].split(' ', 1)[1]
    
    if row['UnitType'] is not None and row['UnitType'] not in ('', ' '):
        final = street.split(row['UnitType'])[0].strip()
    elif '#' in street:
        final = street.split('#')[0].strip()
    else:
        final = street
        
    row['STREET'] = final

    # #: calc lat/lon fields
    # row['longitude'] = row.SHAPE.x
    # row['latitude'] = row.SHAPE.y


    return row



# #: Final cleanup of columns and names, replace blanks in OSM_addr with NaNs/nulls, 
# addpts_sdf.drop(['code', 'id'], axis=1, inplace=True)
# addpts_sdf['OSM_addr'].replace(r'^\s*$', np.nan, regex=True, inplace=True)
# addpts_sdf.rename(columns={'fclass': 'category', 'opening_hours': 'open_hours'}, inplace=True)




def get_h3():
    #: calculate h3 index
    pass
        
        

#: Call functions 
# create_gdb()
# addpts = export_sgid()
# project_fc()
# calc_fields()



#: Convert working feature class to spatial data frame
print("Converting working data to spatial dataframe ...")
addpts_sdf = pd.DataFrame.spatial.from_featureclass(addpts_wgs84)



#: recalc addptid with underscores
# addpts_sdf['UTAddPtID'] = addpts_sdf['UTAddPtID'].str.replace('|', '')
# addpts_sdf['UTAddPtID'] = addpts_sdf['UTAddPtID'].str.replace(' ', '_').str.strip()

print("Calculating other fields (UNIT, STREET, lat, lon)...")
#: calc combined unit field
addpts_sdf = addpts_sdf.progress_apply(field_calc, axis=1)


#: Calc lat/lon as new variable
print("Calculating lat/lon as a new column ...")
column_time = time.time()
addpts_sdf['longitude'] = addpts_sdf.SHAPE.apply(lambda p: p.x)
addpts_sdf['latitude'] = addpts_sdf.SHAPE.apply(lambda p: p.y)
# df['lat'] = df['SHAPE'].y
print("\n    Time elapsed for lat/lon as new variable: {:.2f}s".format(time.time() - column_time))


# print("Calculating lat/lon values ...")
# df['longitude'] = df['SHAPE'].x
# df['latitude'] = df['SHAPE'].y

# head2['latitude_new'] = head2['SHAPE'].y

# head2[['latitude_new', 'longitude_new']] = head2.apply(lambda p: (p.SHAPE.y, p.SHAPE.x), axis=1, result_type='expand')


# print("Calculating h3 index and unique ID ...")
# h3_start_time = time.time()
# addpts_sdf = addpts_sdf.progress_apply(assign_h3, axis=1)
# print("Time elapsed in h3 function: {:.2f}s".format(time.time() - h3_start_time))


#: Use basic h3 to test timing in a lamdba function
print("Calculating basic h3 index as a lambda function ...")
h3_basic_lambda = time.time()
addpts_sdf['h3_index_13'] = addpts_sdf.progress_apply(lambda p: h3_basic.geo_to_h3(p['latitude'], p['longitude'], 13), axis = 1)
print("\n    Time elapsed in basic h3 as a lambda function: {:.2f}s".format(time.time() - h3_basic_lambda))

#: Calculate matID in a lamdba function
print("Calculating matID as a lambda function ...")
h3_basic_lambda = time.time()
addpts_sdf['matID'] = addpts_sdf.progress_apply(lambda r: f'''{r['UTAddPtID']}_{r['h3_index_13']}''' axis = 1)
print("\n    Time elapsed in matID as a lambda function: {:.2f}s".format(time.time() - h3_basic_lambda))


columns = ['FullAdd', 'AddNum', 'PrefixDir', 'StreetName', 'SuffixDir', 'StreetType', 'STREET', 'City', 'ZipCode',
           'longitude', 'latitude', 'UNIT', 'matID']
addpts_slim = addpts_sdf[columns]

orig_length = len(addpts_slim.index)
print(f'Number of points before deduplicating:  {orig_length}')

addpts_slim.drop_duplicates('matID', inplace=True)

final_length = len(addpts_slim.index)
diff = orig_length - final_length
print(f'Number of points after removing duplicates:  {final_length}')
print(f'Removed {diff} duplicates!')

addpts_slim.nunique()

# df = addpts_slim.groupby(['matID']).size()


mat_csv = os.path.join(work_dir, f'DABS_{today}_mat.csv')
addpts_slim.to_csv(mat_csv)


# def lat_lon(row):
#     #: calc lat/lon fields
#     row['longitude_test'] = row.SHAPE.x
#     row['latitude_test'] = row.SHAPE.y

#     return row

# test = head2.progress_apply(lat_lon, axis=1)


# get_h3()


#: Stop timer and print end time in UTC
print("Script shutting down ...")
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
