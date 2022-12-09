# -*- coding: utf-8 -*-
"""
Created on Wed Aug 31 16:05:31 2022

@author: eneemann
"""

import arcpy
import os
import time
try:
    from . import credentials
except ImportError:
    import credentials

#: Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

# Set variables, get AGOL username and password
portal_url = arcpy.GetActivePortalURL()
print(portal_url)

user = credentials.AGOL_USER
pw = credentials.AGOL_PASSWORD
arcpy.SignInToPortal(portal_url, user, pw)
del pw


#: Create variables (pointing to AGOL data)
dabs_licenses = credentials.AGOL_LAYER
zone_path = r'https://services1.arcgis.com/99lidPhWCzftIe9K/ArcGIS/rest/services/DABS_OpenGov_GIS/FeatureServer/1'
county_path = r'https://services1.arcgis.com/99lidPhWCzftIe9K/ArcGIS/rest/services/UtahCountyBoundaries/FeatureServer/0'

#: Set up polygon assignment fields
zone_field = 'Zone_ID'
group_field = 'Group_Name'
county_field = 'NAME'

#: Create polygon assignment dictionary where key is name of field that needs updated in points layer
#: format is:
        #: 'pt_field_name': {'poly_path': path, 'poly_field': field}
poly_dict = {
        'Comp_Zone': {'poly_path': zone_path, 'poly_field': zone_field},
        'Comp_Group': {'poly_path': zone_path, 'poly_field': group_field},
        'County': {'poly_path': county_path, 'poly_field': county_field}
        }

#: Create dictionaries for attribute look-ups based on two-letter license type code
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
    
        # Delete in memory near table
        arcpy.management.Delete(neartable)

#: Create layer for field calculations and polygon assignments
#: Delete temporary layer
if arcpy.Exists("dabs_lyr"):
    arcpy.Delete_management("dabs_lyr")
query = """County IS NULL or County IN ('', ' ')"""
arcpy.management.MakeFeatureLayer(dabs_licenses, "dabs_lyr", query)

#: Calculate lon/lat values for all points (in WGS84 coords)
print("Calculating lat/lon values ...")
lat_calc = 'arcpy.PointGeometry(!Shape!.centroid, !Shape!.spatialReference).projectAs(arcpy.SpatialReference(4326)).centroid.Y'
lon_calc = 'arcpy.PointGeometry(!Shape!.centroid, !Shape!.spatialReference).projectAs(arcpy.SpatialReference(4326)).centroid.X'

arcpy.management.CalculateField("dabs_lyr", 'Point_Y', lat_calc, "PYTHON3")
arcpy.management.CalculateField("dabs_lyr", 'Point_X', lon_calc, "PYTHON3")

#: Calculate DABS fields from License Number
update_count = 0
#:               0          1             2            3            4              5            6
fields = ['Lic_Number', 'Lic_Type', 'Lic_Descr', 'Lic_Group', 'Renew_Date', 'Comp_Needed', 'Suite_Unit']
with arcpy.da.UpdateCursor("dabs_lyr", fields) as cursor:
    print("Looping through rows to calculate DABS fields ...")
    for row in cursor:
        lic_type = row[0][:2].upper()
        row[1] = lic_type
        row[2] = dabs_descr[f'{lic_type}']
        row[3] = dabs_group[f'{lic_type}']
        row[4] = dabs_renew[f'{lic_type}']
        row[5] = dabs_comp_needed[f'{lic_type}']
        # row[6] = None
        update_count += 1
        cursor.updateRow(row)
print(f"Total count of updates is {update_count}")

#: Call polygon assignment function
print("Assigning polygon attributes ...")
assign_poly_attr("dabs_lyr", poly_dict)

#: Delete temporary layer
if arcpy.Exists("dabs_lyr"):
    arcpy.Delete_management("dabs_lyr")

#: Stop timer and print end time in UTC
print("Script shutting down ...")
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))