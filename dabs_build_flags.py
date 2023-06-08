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
import requests
import pandas as pd
import numpy as np
import geopandas as gpd
from arcgis.features import GeoAccessor, GeoSeriesAccessor



#: Start timer and print start time in UTC
start_time = time.time()
readable_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script start time is {}".format(readable_start))
today = time.strftime("%Y%m%d")

#: Set up directories
base_dir = r'C:\DABC\Flags'
work_dir = os.path.join(base_dir, f'Flags_{today}')
latest_db = r'C:\DABC\DABS_latest_data.gdb'

if os.path.isdir(work_dir) == False:
    os.mkdir(work_dir)
    
today_db_name = "DABS_Flags_" + today
today_db = os.path.join(work_dir, today_db_name + ".gdb")
    

# Set up SGID paths and variables
SGID = r"C:\Users\eneemann\AppData\Roaming\ESRI\ArcGISPro\Favorites\internal@SGID@internal.agrc.utah.gov.sde"

park_path = os.path.join(SGID, 'SGID.RECREATION.ParksLocal')
school_path = os.path.join(SGID, 'SGID.SOCIETY.Schools_PreKto12')
library_path = os.path.join(SGID, 'SGID.SOCIETY.PublicLibraries')
osm_path = os.path.join(SGID, 'SGID.SOCIETY.OpenSourcePlaces')
statewide_parcels = r'https://services1.arcgis.com/99lidPhWCzftIe9K/ArcGIS/rest/services/UtahStatewideParcels/FeatureServer/0'
# statewide_parcels = r'C:\Users\eneemann\Documents\ArcGIS\Projects\DABC\DABC.gdb\Utah_StateWideParcel'

# #: Make layer from statewide parcels
# parcel_time = time.time()
# arcpy.management.MakeFeatureLayer(statewide_parcels, "statewide_parcels")
# print("Time elapsed exporting statewide parcels from AGOL: {:.2f}s".format(time.time() - parcel_time))

#: Get SGID layers names from paths
park = park_path.split('.')[-1]
school = school_path.split('.')[-1]
library = library_path.split('.')[-1]
osm = osm_path.split('.')[-1]

#: SGID fields to use for given layers
park_field = 'NAME'
school_field = 'SchoolName'
library_field = 'LIBRARY'
osm_field = 'name'

SGID_files = [park, school, library, osm]
SGID_layers = [park_path, school_path, library_path, osm_path]

#: Set up names and paths for feature classes
parcels_name = 'Utah_Parcels'
parks_name = park
osm_name = osm
library_name = library
school_name = school
combined_points_name = 'Combined_Points'
combined_polygons_name = 'Combined_Polygons'

parcels_fc = os.path.join(today_db, parcels_name)
parks_fc = os.path.join(today_db, parks_name)
osm_fc = os.path.join(today_db, osm)
library_fc = os.path.join(today_db, library)
playground_fc = os.path.join(today_db, 'playgrounds')
library_parcel_fc = os.path.join(today_db, 'library_parcels')
school_parcel_fc = os.path.join(today_db, 'school_parcels')
church_parcel_fc = os.path.join(today_db, 'church_parcels')
playground_parcel_fc = os.path.join(today_db, 'playground_parcels')
school_fc = os.path.join(today_db, school)
combined_points = os.path.join(today_db, combined_points_name)
combined_polygons = os.path.join(today_db, combined_polygons_name)
combined_buffers = os.path.join(today_db, 'DABS_Flag_Areas')


# temp_files = ['Building_centroids_original', pois_FC, poi_areas_FC, poi_areas_centroid,
#               pofw_FC, pofw_areas_FC, pofw_areas_centroid, transport_FC, transport_centroid,
#               buildings_FC, buildings_centroid]


#: Create working geodatabase with today's date
def create_gdb():
    print("Creating file geodatabase ...")
    if arcpy.Exists(today_db) == False:
        arcpy.CreateFileGDB_management(work_dir, today_db_name)
    
    arcpy.env.workspace = today_db
    arcpy.env.qualifiedFieldNames = False


#: Copy SGID data layers to local for faster processing
def export_data():
    export_time = time.time()
    for item in SGID_layers:
        exported = item.rsplit('.', 1)[-1]
        if arcpy.Exists(os.path.join(today_db, exported)):
            arcpy.management.Delete(os.path.join(today_db, exported))
        print(f"Exporting SGID {item} to: {exported}")
        arcpy.FeatureClassToFeatureClass_conversion (item, today_db, exported)     
    
    print("Time elapsed exporting SGID data: {:.2f}s".format(time.time() - export_time))
    
    #: Copy statewide parcels from AGOL to local
    parcel_time = time.time()
    arcpy.conversion.FeatureClassToFeatureClass(statewide_parcels, today_db, parcels_name)
    print("Time elapsed exporting statewide parcels from AGOL: {:.2f}s".format(time.time() - parcel_time))


def create_initial_layers():   
    #: Create initial polygon layer from parks
    arcpy.conversion.FeatureClassToFeatureClass(parks_fc, today_db, combined_polygons_name)
    print(f"Polygon layer is starting with {arcpy.management.GetCount(combined_polygons)[0]} features from SGID parks")
    
    arcpy.management.AddField(combined_polygons, "category", "TEXT", "", "", 40)
    arcpy.management.AlterField(combined_polygons, "NAME", "name")
    arcpy.management.AlterField(combined_polygons, "COUNTY", "County")
    
    # Calc category field = 'park'
    fields = ['category']
    with arcpy.da.UpdateCursor(combined_polygons, fields) as cursor:
        for row in cursor:
            row[0] = 'park'
            cursor.updateRow(row)
    print(f"Updated category field to 'park' on {arcpy.management.GetCount(combined_polygons)[0]} features")
    
    #: Create initial points layer from OSM places (churches)
    church_query = """category LIKE '%christian%' OR category IN ('jewish', 'muslim', 'buddhist', 'hindu')"""
    arcpy.conversion.FeatureClassToFeatureClass(osm_fc, today_db, combined_points_name, church_query)
    print(f"Point layer is starting with {arcpy.management.GetCount(combined_points)[0]} features from OSM churches")
    
    # Calc category field = 'church'
    fields = ['category']
    with arcpy.da.UpdateCursor(combined_points, fields) as cursor:
        for row in cursor:
            row[0] = 'church'
            cursor.updateRow(row)
    print(f"Updated category field to 'church' on {arcpy.management.GetCount(combined_points)[0]} features")
        
    #: Select containing parcels and move them into a polygon fc
    fms = arcpy.FieldMappings()
    # Add all fields from inputs.
    fms.addTable(parcels_fc)
    fms.addTable(combined_points)
    
    #: Name fields you want
    keepers = ['name', 'category', 'PARCEL_ID', 'PARCEL_ADD', 'PARCEL_CITY', 'PARCEL_ZIP', 'County'] # etc.
    
    #: Remove all unwanted output fields.
    for field in fms.fields:
        if field.name not in keepers:
            fms.removeFieldMap(fms.findFieldMapIndex(field.name))
    
    #: Execute spatial join
    arcpy.analysis.SpatialJoin(parcels_fc, combined_points, church_parcel_fc, 'JOIN_ONE_TO_MANY', 'KEEP_COMMON', fms, 'INTERSECT', '10 Meters')
    
    #: Append churches into combined polygons
    print(f"Adding {arcpy.management.GetCount(church_parcel_fc)[0]} church parcels to combined_polygons")
    arcpy.management.Append(church_parcel_fc, combined_polygons, "NO_TEST")
    
    #: Append parks into combined points layer
    temp = 'in_memory\\park_points'
    if arcpy.Exists(temp):
        print(f"Deleting {temp} ...")
        arcpy.management.Delete(temp)
    arcpy.management.FeatureToPoint(parks_fc, temp, "INSIDE")
    print(f"Adding {arcpy.management.GetCount(temp)[0]} POFW area features to combined_places")
    arcpy.management.Append('in_memory\\park_points', combined_points, "NO_TEST")
    
    # Calc category field = 'church'
    park_count = 0
    fields = ['category']
    query = "category IS NULL"
    with arcpy.da.UpdateCursor(combined_points, fields, query) as cursor:
        for row in cursor:
            row[0] = 'park'
            park_count += 1
            cursor.updateRow(row)
    print(f"Updated category field to 'park' on {park_count} point features")
    


def add_libraries():
    # #: Add libraries to combined points
    # fms = arcpy.FieldMappings()
    
    # fm_dict = {library_field: osm_field}
    
    # for key in fm_dict:
    #     fm = arcpy.FieldMap()
    #     fm.addInputField(library_fc, key)
    #     output_addpt = fm.outputField
    #     output_addpt.name = fm_dict[key]
    #     fm.outputField = output_addpt
    #     fms.addFieldMap(fm)
    
    #: Add fields and calculate
    arcpy.management.AddField(library_fc, "category", "TEXT", "", "", 40)
    arcpy.management.AddField(library_fc, "name", "TEXT", "", "", 180)
    
    # Calc category field = 'library'
    count = 0
    fields = [library_field, 'name', 'category']
    with arcpy.da.UpdateCursor(library_fc, fields) as cursor:
        for row in cursor:
            row[1] = row[0]
            row[2] = 'library'
            count += 1
            cursor.updateRow(row)
    print(f"Updated fields on {count} library features")
    
    #: Append libraries into combined points
    print(f"Adding {arcpy.management.GetCount(library_fc)[0]} library features to combined_points")
    arcpy.management.Append(library_fc, combined_points, "NO_TEST")
      
    #: Select containing parcels and move them into a polygon fc
    fms = arcpy.FieldMappings()
    # Add all fields from inputs.
    fms.addTable(parcels_fc)
    fms.addTable(library_fc)
    
    #: Name fields you want
    keepers = ['name', 'category', 'PARCEL_ID', 'PARCEL_ADD', 'PARCEL_CITY', 'PARCEL_ZIP', 'County'] # etc.
    
    #: Remove all unwanted output fields.
    for field in fms.fields:
        if field.name not in keepers:
            fms.removeFieldMap(fms.findFieldMapIndex(field.name))
    
    #: Execute spatial join
    arcpy.analysis.SpatialJoin(parcels_fc, library_fc, library_parcel_fc, 'JOIN_ONE_TO_MANY', 'KEEP_COMMON', fms, 'INTERSECT', '10 Meters')
    
    #: Append libraries into combined polygons
    print(f"Adding {arcpy.management.GetCount(library_parcel_fc)[0]} library parcels to combined_polygons")
    arcpy.management.Append(library_parcel_fc, combined_polygons, "NO_TEST")
   
    
def add_schools():
    # #: Add schools to combined points
    # fms = arcpy.FieldMappings()
    
    # fm_dict = {school_field: osm_field}
    
    # for key in fm_dict:
    #     fm = arcpy.FieldMap()
    #     fm.addInputField(school_fc, key)
    #     output_addpt = fm.outputField
    #     output_addpt.name = fm_dict[key]
    #     fm.outputField = output_addpt
    #     fms.addFieldMap(fm)
    
    #: Add fields and calculate
    arcpy.management.AddField(school_fc, "category", "TEXT", "", "", 40)
    arcpy.management.AddField(school_fc, "name", "TEXT", "", "", 180)
    
    # Calc category field = 'school'
    count = 0
    fields = [school_field, 'name', 'category']
    with arcpy.da.UpdateCursor(school_fc, fields) as cursor:
        for row in cursor:
            row[1] = row[0]
            row[2] = 'school'
            count += 1
            cursor.updateRow(row)
    print(f"Updated fields on {count} school features")
    
    #: Append schools into combined points
    print(f"Adding {arcpy.management.GetCount(school_fc)[0]} school features to combined_points")
    arcpy.management.Append(school_fc, combined_points, "NO_TEST")
      
    #: Select containing parcels and move them into a polygon fc
    fms = arcpy.FieldMappings()
    # Add all fields from inputs.
    fms.addTable(parcels_fc)
    fms.addTable(school_fc)
    
    #: Name fields you want
    keepers = ['name', 'category', 'PARCEL_ID', 'PARCEL_ADD', 'PARCEL_CITY', 'PARCEL_ZIP', 'County'] # etc.
    
    #: Remove all unwanted output fields.
    for field in fms.fields:
        if field.name not in keepers:
            fms.removeFieldMap(fms.findFieldMapIndex(field.name))
    
    #: Execute spatial join
    arcpy.analysis.SpatialJoin(parcels_fc, school_fc, school_parcel_fc, 'JOIN_ONE_TO_MANY', 'KEEP_COMMON', fms, 'INTERSECT', '10 Meters')
    
    #: Append schools into combined polygons
    print(f"Adding {arcpy.management.GetCount(school_parcel_fc)[0]} school parcels to combined_polygons")
    arcpy.management.Append(school_parcel_fc, combined_polygons, "NO_TEST")
       

#: Retrieve Overpass API data with requests, convert to dataframe
def get_overpass_df(query_string):
    r = requests.get(query_string)
    df = pd.DataFrame(r.json()['elements'])

    return df


def add_osm_plagrounds():
    #: Add data from Overpass API using spatial dataframes
    overpass_start_time = time.time()
    #: Get data from Overpass query
    print("Pulling additional data from Overpass API ...")
    query_string = 'http://overpass-api.de/api/interpreter?data=[out:json];area[name="Utah"]->.utah;nwr[leisure=playground](area.utah);out center;'
    overpass = get_overpass_df(query_string)
    
    #: Separate into nodes and ways, get coordinates, build geodataframe, concatenate into one geodataframe
    overpass_nodes = overpass[overpass['type']=='node']
    node_gdf = gpd.GeoDataFrame(overpass_nodes, geometry=gpd.points_from_xy(overpass_nodes['lon'], overpass_nodes['lat']))
    overpass_ways = overpass[overpass['type']=='way']
    overpass_ways.drop(['lat', 'lon'], axis=1, inplace=True)
    overpass_ways['lon'] = overpass_ways.apply(lambda r: r['center']['lon'], axis=1)
    overpass_ways['lat'] = overpass_ways.apply(lambda r: r['center']['lat'], axis=1)
    way_gdf = gpd.GeoDataFrame(overpass_ways, geometry=gpd.points_from_xy(overpass_ways['lon'], overpass_ways['lat']))
    
    playgrounds_df = pd.concat([overpass_nodes, overpass_ways])
    playgrounds_small = playgrounds_df[['id', 'type', 'tags', 'geometry', 'lat', 'lon']]
    
    #: Normalize the tags field (dictionary) into separate columns
    print("Normalizing Overpass dataframe ...")
    temp = pd.json_normalize(playgrounds_small['tags'])
    playgrounds_normal = pd.concat([playgrounds_small.drop('tags', axis=1), temp], axis=1)
    
    #: Filter data down to columns that will be kept and only non-private playgrounds
    public_playgrounds = playgrounds_normal[~playgrounds_normal['access'].isin(['residents', 'private', 'permit', 'customers'])]
    keep_cols = ['id', 'geometry', 'name', 'leisure', 'lat', 'lon']
    public_playgrounds = public_playgrounds[keep_cols]
    
    #: Calculate category field and rename geometry to SHAPE
    public_playgrounds['category'] = 'playground'
    public_playgrounds.rename(columns={'geometry': 'SHAPE'}, inplace=True)
    
    #: Convert to ESRI sedf, then to feature class
    sr = arcpy.SpatialReference(4326)
    playground_sedf = pd.DataFrame.spatial.from_xy(df=public_playgrounds, x_column='lon', y_column='lat', sr=4326)
    playground_sedf.spatial.to_featureclass(location=playground_fc)
    
    #: Append playgrounds into combined points
    print(f"Adding {arcpy.management.GetCount(playground_fc)[0]} playground features to combined_points")
    arcpy.management.Append(playground_fc, combined_points, "NO_TEST")
      
    #: Select containing parcels and move them into a polygon fc
    fms = arcpy.FieldMappings()
    # Add all fields from inputs.
    fms.addTable(parcels_fc)
    fms.addTable(playground_fc)
    
    #: Name fields you want
    keepers = ['name', 'category', 'PARCEL_ID', 'PARCEL_ADD', 'PARCEL_CITY', 'PARCEL_ZIP', 'County'] # etc.
    
    #: Remove all unwanted output fields.
    for field in fms.fields:
        if field.name not in keepers:
            fms.removeFieldMap(fms.findFieldMapIndex(field.name))
    
    #: Execute spatial join
    arcpy.analysis.SpatialJoin(parcels_fc, playground_fc, playground_parcel_fc, 'JOIN_ONE_TO_MANY', 'KEEP_COMMON', fms, 'INTERSECT', '10 Meters')
    
    #: Append playgrounds into combined polygons
    print(f"Adding {arcpy.management.GetCount(playground_parcel_fc)[0]} playground parcels to combined_polygons")
    arcpy.management.Append(playground_parcel_fc, combined_polygons, "NO_TEST")
    
    print("Time elapsed on OSM playgrounds: {:.2f}s".format(time.time() - overpass_start_time))
    
    #: Simplify schema on the combined points
    arcpy.management.DeleteField(combined_points, ['addr_dist', 'osm_id', 'city', 'zip', 'county', 'block_id', 'ugrc_addr', 'disclaimer', 'lat', 'lon',
                                                   'amenity', 'cuisine', 'tourism', 'shop', 'website', 'phone', 'open_hours', 'osm_addr'])


def build_buffer():
    #: Generate 200ft buffers around the combined polygon/parcel layer
    arcpy.analysis.Buffer(combined_polygons, combined_buffers, "200 Feet", "FULL", "ROUND", "NONE")
    
    #: Simplify schema on the bufferes
    arcpy.management.DeleteField(combined_buffers, ['CITY', 'ACRES', 'TYPE', 'STATUS', 'BUFF_DIST', 'ORIG_FID' ])


def copy_to_latest_db():
    #: Copy final files to latest database
    arcpy.env.workspace = latest_db
    print("Deleting old files ...")
    deletes = ['Utah_Parcels', 'DABS_Flag_Areas', 'DABS_Flag_Locations']
    
    for file in deletes:
        if arcpy.Exists(file):
            print(f"Deleting {file} ...")
            arcpy.management.Delete(file)
    
    print("Copying files to latest_db ...")
    arcpy.FeatureClassToFeatureClass_conversion (parcels_fc, latest_db, 'Utah_Parcels')
    arcpy.FeatureClassToFeatureClass_conversion (combined_points, latest_db, 'DABS_Flag_Locations')
    arcpy.FeatureClassToFeatureClass_conversion (combined_buffers, latest_db, 'DABS_Flag_Areas')


def delete_files():
    #: Delete temporary and intermediate files
    print("Deleting copied SGID files ...")
    for file in SGID_files:
        if arcpy.Exists(file):
            print(f"Deleting {file} ...")
            arcpy.management.Delete(file)
    
    # print("Deleting temporary files ...")
    # for file in temp_files:
    #     if arcpy.Exists(file):
    #         print(f"Deleting {file} ...")
    #         arcpy.management.Delete(file) 



#: Call functions 
create_gdb()
export_data()
create_initial_layers()
add_libraries()
add_schools()
add_osm_plagrounds()
build_buffer()
copy_to_latest_db()
# delete_files()


#: Stop timer and print end time in UTC
print("Script shutting down ...")
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))
