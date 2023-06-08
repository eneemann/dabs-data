# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 16:15:29 2022

@author: eneemann

Script to assign attributes to points from point in polygon spatial query
- Tailored to use SGID polygon layers for assignment
- User must update:
    points path
    points field
    polygon path
    polygon field
- function accepts path to points layer and dictionary with field/polygon info
"""

import os
import time
import arcpy

# Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
print('The script start time is {}'.format(readable_start))

# Update variables below
database = r'C:\DABC\DABC.gdb'
points = os.path.join(database, "DABS_All_Licenses_20220907_new_schema")



zone_path = os.path.join(database, 'All_Zones_update_20220908_new_schema')
zone_field = 'Zone_ID'
group_field = 'Group_Name'

# create dictionary where key is name of field that needs updated in points layer
# format is
        # 'pt_field_name': {'poly_path': path, 'poly_field': field}
poly_dict = {
        'Comp_Zone': {'poly_path': zone_path, 'poly_field': zone_field},
        'Comp_Group': {'poly_path': zone_path, 'poly_field': group_field}
        }

###############
#  Functions  #
###############


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
    
        # Delete in memory near table
        arcpy.management.Delete(neartable)
    
##########################
#  Call Functions Below  #
##########################

# Call function if script run as main program
if __name__ == '__main__':
    assign_poly_attr(points, poly_dict)


print('Script shutting down ...')
# Stop timer and print end time in UTC
readable_end = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
print('The script end time is {}'.format(readable_end))
print('Time elapsed: {:.2f}s'.format(time.time() - start_time))