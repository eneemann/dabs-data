# -*- coding: utf-8 -*-
"""
Created on Tue Dec 20 16:33:11 2022

@author: eneemann

Script to compare addresses in new DABS licenses to addresses in the Master Address Table (MAT) for DABS OpenGov database

20 December 2022: first version of code (EMN)
"""

import os
import time
import pandas as pd
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

#: Get addresses from proposed Google Sheet
sheet_title = time.strftime("%m/%Y")
sheet_title = '05/2023'
sheet = gsheets_client.open_by_key(credentials.SHEET_ID)
proposed_df = sheet.worksheet_by_title(sheet_title).get_as_df()

#: Remove NULLs and blanks, strip whitespace
proposed_df.drop(proposed_df[proposed_df['Address'].isin([None, 'None', '', ' '])].index, inplace=True)
proposed_df = proposed_df.applymap(lambda x: x.strip().upper() if isinstance(x, str) else x)
print(proposed_df.head())


#: Get list of addresses from dabs licenses
proposed_addrs = list(proposed_df['Address'])
proposed_sys = proposed_df.progress_apply(lambda r: f'''{r['Address']} {r['City']}'''.strip('''(,)"''').replace('  ', ' ').replace('  ', ' '), axis = 1)

                
                                                                                       
#: Get list of addresses from MAT
mat_dir = r'C:\DABC\MAT\DABS_20230602'
mat_csv = os.path.join(mat_dir, 'DABS_mat.csv')
mat_df = pd.read_csv(mat_csv)
mat_addrs = list(mat_df['FullAdd'])
mat_df['LongAdd'] = mat_df.progress_apply(lambda r: f'''{r['FullAdd']} {r['City']}'''.strip('''(,)"''').replace('  ', ' ').replace('  ', ' '), axis = 1)
mat_sys = list(mat_df['LongAdd'])

not_matched = list(set(proposed_addrs) - set(mat_addrs))
not_matched_sys = list(set(proposed_sys) - set(mat_sys))

print(f"   Number of unmatched addresses: {len(not_matched)}")
print(f"   Number of unmatched addresses using address system: {len(not_matched_sys)}")

if len(not_matched) > 0:
    print('Unmatched addresses:')
    for address in not_matched:
        print(f'    {address}')
else:
    print('\n All licenses matched, all is right in the world! \n')
    
if len(not_matched_sys) > 0:
    print('Unmatched addresses and systems:')
    for address_sys in not_matched_sys:
        print(f'    {address_sys}')
else:
    print('\n All licenses matched, all is right in the world! \n')
            

#: Stop timer and print end time in UTC
print("Script shutting down ...")
readable_end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("The script end time is {}".format(readable_end))
print("Time elapsed: {:.2f}s".format(time.time() - start_time))