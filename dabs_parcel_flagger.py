# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 11:26:04 2022

@author: eneemann

Script to combine OSM and SGID data to build DABS buffers for alcohol license flags

21 Sep 2022: first version of code (EMN)
"""

import os
import time
import arcpy


#: Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

#: Set up variables
latest_db = r'C:\DABC\DABS_latest_data.gdb'
flag_areas = os.path.join(latest_db, 'DABS_Flag_Areas')
parcels = os.path.join(latest_db, 'Utah_Parcels')

#: Add field to the parcels layer
# print(f"Adding 'DABS_Flag' field to parcels ...")
# arcpy.management.AddField(parcels, "DABS_Flag", "TEXT", "", "", 5)

#: Calculate the field to 'False' for rows
print("Calculating all rows to 'False' ...")
fields = ['DABS_Flag']
with arcpy.da.UpdateCursor(parcels, fields) as cursor:
    for row in cursor:
        row[0] = 'False'
        cursor.updateRow(row)

#: Create selection on parcels that intersect flag areas
selection = arcpy.management.SelectLayerByLocation(parcels, "INTERSECT", flag_areas)
select_count = int(arcpy.management.GetCount(selection)[0])
print(f"Selected {select_count} parcels that intersect flag areas ...")

#: Calculate the field to 'True' for intersected rows
print("Calculating selected rows to 'True' ...")
fields = ['DABS_Flag']
with arcpy.da.UpdateCursor(selection, fields) as cursor:
    for row in cursor:
        row[0] = 'True'
        cursor.updateRow(row)


#: Stop timer and print end time in UTC
print("Script shutting down ...")
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
