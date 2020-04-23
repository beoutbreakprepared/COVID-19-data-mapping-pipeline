#!/usr/bin/env python3 

'''
- Generate full-data.json from latestdata.csv and JHU data
- Split data into daily slices
'''

import pandas as pd
import requests 
import argparse
import sys
from io import StringIO
import re
import json

jhu_url= 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'


# Columns we're keeping. 
COLNAMES = ['ID', 'latitude', 'longitude',
            'city', 'province', 'country',
            'age', 'sex', 'symptoms', 
            'source', 'date_confirmation', 
            'geo_resolution']


parser = argparse.ArgumentParser(description='Generate full-data.json file')
parser.add_argument('-l', '--latest', type=str, required=True, 
        help='path to latestdata.csv')
parser.add_argument('-o', '--outfile', required=True, type=str,
        help='path to output file')
parser.add_argument('-j', '--jhu', type=str, help='Option to save jhu data (before formating)',
        default=False)

def jhu(url, jhu_file):
    '''
    Get JHU data from URL and format to 
    to be compatible with full-data.json
    (used for US data)
    '''

    # Get JHU data
    req = requests.get(jhu_url)
    if req.status_code != 200:
        print('Could not get JHU data, aborting')
        sys.exit(1)
    
    print(req.text[:100])
    us_data = pd.read_csv(StringIO(req.text))
    print(us_data) 
    if jhu_file:
        with open(jhu_file, 'w') as F:
            F.write(req.text)

    # rename date columns to match sheet format (%d.%m.%d)
    rx = '\d{1,2}/\d{1,2}/\d'
    date_columns = []

    for c in us_data.columns:
        print(c)
        if re.match(rx, c):
            month, day, year = c.split('/')
            month = str(month).zfill(2)
            day   = str(day).zfill(2)
            year = '20' + str(year) if len(year) == 2 else year
            date = '{}.{}.{}'.format(day, month, year)
            date_columns.append(date)
            us_data.rename({c : date}, axis=1, inplace=True)
            print(date)
    date_columns = sorted(date_columns, key=lambda x: pd.to_datetime(x, format='%d.%m.%Y'))


    # reformat JHU to have same structure as sheet
    # This may seem silly because we unpack and then reduce to Unique again,
    # we do it because the "full_data" file is sent to FM-Global

    # only defining columns where values will change for now.
    # Loop is done in this order so that IDs persist.
    print(len(us_data[us_data.Lat.astype(float) == 0]))
    us_reformed = pd.DataFrame(columns=['latitude', 'longitude', 'city', 'province', 'date_confirmation'])
    for i, date in enumerate(date_columns):
        print(date)
        for j, row in us_data.iterrows():
            if float(row['Lat']) == 0 or float(row['Long_']) == 0:
                continue

            if pd.isnull(row['Lat']) or pd.isnull(row['Long_']):
                continue

            if i == 0:
                N = int(row[date])
            else:
                N = int(row[date]) - int(row[date_columns[i-1]])

                entry = {
                    'latitude': row['Lat'],
                    'longitude': row['Long_'],
                    'city': row['Admin2'],
                    'province': row['Province_State'],
                    'date_confirmation': date
                }
                us_reformed = us_reformed.append([entry]*N, ignore_index=True)

    us_reformed.insert(0, 'ID', range(1, len(us_reformed) + 1))
    us_reformed['ID'] = us_reformed['ID'].apply(lambda x : 'JHU' + str(x))
    us_reformed.insert(5, 'country', 'United States')
    us_reformed.insert(6, 'age', '')
    us_reformed.insert(7, 'sex', '')
    us_reformed.insert(8, 'symptoms', '')
    us_reformed.insert(9, 'source', 'JHU')
    us_reformed.insert(11, 'geo_resolution', 'admin2')


    return us_reformed 

def latestdata(path): 
    '''
    Read latestdata.csv and filter out US/Virgin Isllands/ Puerto Rico
    These are in JHU data. 
    '''    
    df = pd.read_csv(path, dtype=str)
    filter_ = ~df.country.isin(['United States', 'Virgin Islands, U.S.', 'Puerto Rico'])
    return df[filter_]


def clean_data(data: pd.DataFrame, colnames: list) -> pd.DataFrame:
    '''
    Basic cleaning and filtering:
    - valid lat/longs
    - valid dates (using %d.%m.%Y format)
    - manage white space
    - Keeps only columns that are going to be in final version.

    Args:
    :data: pd.DataFrame, data from sheet
    :colnames: list, list of columns we are keeping for final version
    '''
    df = data.copy()
    df.rename({x: x.strip() for x in df.columns}, inplace=True, axis=1)

    # drop invalid lat/longs
    lat,lon     = df.latitude, df.longitude
    invalid_lat = lat.str.contains('#REF') | lat.str.contains('N/A') | lat.isnull() | (lat == '')
    invalid_lon = lon.str.contains('#REF') | lon.str.contains('N/A') | lon.isnull() | (lon == '')
    invalid     = invalid_lat | invalid_lon
    df = df[~invalid] # NOT invalid

    # Only keep those that have a date_confirmation
    df['date_confirmation'] = df['date_confirmation'].str.strip() # some have empty spaces
    dc = df.date_confirmation
    valid_date = (dc != '') & ~(dc.isnull())
    df = df[valid_date]

    # Basic cleaning for strings
    for c in ['city', 'province', 'country']:
        df[c] = df[c].str.strip()
        df[c] = df[c].str.title()
        df[c] = df[c].str.replace('\xa0', ' ') # encoding for a space that was found in some entries.

    # Only keep the columns we want
    df = df[colnames]

    return df


def main():
    args = parser.parse_args()
    jhu_data = jhu(jhu_url, jhu_file=args.jhu)
    latest   = latestdata(args.latest)
    data = latest.append(jhu_data, ignore_index=True)
    data = clean_data(data, COLNAMES)
    data = {'data': data.to_dict(orient='records')}
    with open(args.outfile, 'w') as F:
        json.dump(data, F)

if __name__ == '__main__':
    main()
