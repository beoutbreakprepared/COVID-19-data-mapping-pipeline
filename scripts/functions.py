import configparser
import itertools
import json
import multiprocessing
import os.path
import pandas as pd
import pickle
import re
import sys

from datetime import datetime, timedelta
from shutil import copyfile

LAT_LNG_DECIMAL_PLACES = 4

class GoogleSheet(object):
    '''
    Simple object to help organizing.
    Attributes:
    :spreadsheetid:-> str, Google Spreadsheet ID (from link).
    :name: -> list or str, sheet name (list when multiple sheets in 1 spreadsheet).
    :ID: -> str, code for ID column in sheets (specific to region).
    '''

    def __init__(self, *args):
        self.spreadsheetid = args[0]
        self.name = args[1]
        self.ID = args[2]

def get_GoogleSheets(config: configparser.ConfigParser) -> GoogleSheet:
    '''
    Fetch info for the different sheets.
    '''

    # fetch for original sheet (temporary as things will get migrated)
    sheet0 = config['ORIGINAL_SHEET']
    name1 = sheet0.get('NAME1')
    name2 = sheet0.get('NAME2')
    sid = sheet0.get('SID')
    ID  = sheet0.get('ID')
    s1 = GoogleSheet(sid, name1, ID)
    s2 = GoogleSheet(sid, name2, ID)


    sheets = [s1, s2] # change to blank when no longer using original.

    # Fetch for Regional Sheets.
    pattern = '^SHEET\d*$'
    sections = config.sections()
    for s in sections:
        if re.match(pattern, s):
            id_ = config[s]['ID']
            sid = config[s]['SID']
            name = config[s]['NAME']
            googlesheet = GoogleSheet(sid, name, id_)
            sheets.append(googlesheet)

    return sheets


def log_message(message: str, config: configparser.ConfigParser) -> None:
    logfile = config['FILES'].get('LOG', './logfile')
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = '{} {}'.format(date, message)
    with open(logfile, 'a') as F:
        F.write(message)
        F.write('\n')

def savedata(data: list, outfile: str) -> None:
    '''
    dave data to file.
    '''
    with open(outfile, 'w') as F:
        json.dump(data, F)



def load_sheet(Sheet: GoogleSheet, config: configparser.ConfigParser) -> pd.DataFrame:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    # Sheet Import Script adapted from : https://developers.google.com/sheets/api/quickstart/python
    scopes      = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds       = None
    token       = config['SHEETS'].get('TOKEN', './token.pickle')
    credentials = config['SHEETS'].get('CREDENTIALS', './credentials.json')
    spreadsheetid = Sheet.spreadsheetid
    data_range    = f'{Sheet.name}!A:V'

    if os.path.exists(token):
        with open(token, 'rb') as t:
            creds = pickle.load(t)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials, scopes)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token, 'wb') as t:
            pickle.dump(creds, t)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet   = service.spreadsheets()
    values  = sheet.values().get(spreadsheetId=spreadsheetid, range=data_range).execute().get('values', [])

    if not values:
        raise ValueError('Sheet data not found')

    else:
        # Have to loop through values because they don't necessarily match the the column number.
        columns = values[0]
        data    = values[1:]

        n    = len(columns)
        ilat = columns.index('latitude')
        ilon = columns.index('longitude')
        idate = columns.index('date_confirmation')


        keep = []
        for _ in data:
            d = _.copy() # might change the value.

            # Flags to write to log accurately.
            length_error = False
            lat_error    = False
            date_error   = False
            try:

                # Length Errors
                # Trailing empty cells return a different length than otherwise
                length_error = True
                if len(d) < n :
                    # extend with empty strings
                    nstrings = n - len(d)
                    d.extend(['']*nstrings)
                assert len(d) == n
                length_error = False

                # Lat/Long errors
                lat_error = True
                _ = float(d[ilat])
                _ = float(d[ilon])
                lat_error = False

                # Dates
                date_error = True
                date = d[idate]
                if date == '':
                    continue
                elif '-' in d[idate]:
                    date = d[idate].split('-')[-1]
                else:
                    date = d[idate]
                _ = pd.to_datetime(date, format='%d.%m.%Y', exact=True)
                date_error = False

                keep.append(d)

            except Exception as Err:
                if True in [length_error, lat_error, date_error]:
                    continue
                else:
                    raise Err
        for x, y in enumerate(columns):
            if y.strip() == '' and columns[x-1] == 'province':
                columns[x] = 'country'
        return pd.DataFrame(data=keep, columns=columns)

def clean_data(data: pd.DataFrame, colnames: list) -> pd.DataFrame:
    '''
    Basic cleaning and filtering on dataframe.
    Most of this gets done either by curators or pipeline now, this filters out for :
    - valid lat/longs
    - valid dates (using %d.%m.%Y format)
    - manage white space
    - Keeps only columns that are going to be in final version.

    Args
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
    dc = dc.fillna('')
    dc = dc.apply(lambda x: x.split('-')[1].strip() if '-'  in x else x.strip())
    valid_date = (dc != '') & ~(dc.isnull()) & dc.str.match('.*\d{2}\.\d{2}\.\d{4}.*')
    df = df[valid_date]
    df['date_confirmation'] = df['date_confirmation'].str.strip()

    # Basic cleaning for strings
    for c in ['city', 'province', 'country']:
        df[c] = df[c].str.strip()
        df[c] = df[c].str.title()
        df[c] = df[c].str.replace('\xa0', ' ') # encoding for a space that was found in some entries.


    # Only keep the columns we want
    df = df[colnames]

    return df


def reduceToUnique(data: pd.DataFrame) -> list:
    '''
    Get counts for unique locations (by lat/long combination).
    Output is a records style list [{d1}, {d2}, ... {}].

    Does some situatinal name changing for consistency, but this should be done on Curator's side.
    '''
    df = data.copy()
    groups = df.groupby(['latitude', 'longitude'])


    results = []
    for g in groups:
        lat, lon = g[0]
        cut      = g[1]
        count    = len(cut)
        try:
            # Uniques to flag inconsistencies.
            cities = cut.city.unique()
            provinces = cut.province.unique()
            countries = cut.country.unique()

            # Subject to change.
            city     = cities[0]
            province = provinces[0]
            country  = countries[0]

            if 'Singapore' in countries:
                city = ''
                province = ''
                country = 'Singapore'

            elif 'Macau' in provinces:
                city = ''
                province = 'Macau'
                country = 'China'

            else:
                # get city that occurs the most.
                if len(cities) > 1:
                    vcounts = cut.city.value_counts()
                    city = vcounts[vcounts == vcounts.max()].index[0]

            # Only display this info on map if N cases == 1
            age = cut.age.values[0] if count == 1 else ''
            sex = cut.sex.values[0] if count == 1 else ''
            symptoms = cut.symptoms.values[0] if count == 1 else ''
            source = cut.source.values[0] if count == 1 else ''
            geo_resolution = cut.geo_resolution.values[0]

            d = {
                    'latitude': lat,
                    'longitude': lon,
                    'city': city,
                    'province': province,
                    'country': country,
                    'age': age,
                    'sex': sex,
                    'symptoms': symptoms,
                    'source': source,
                    'date_confirmation': date_confirmation,
                    'cases': count,
                    'geo_resolution' : geo_resolution
                }
            results.append(d)

        except:
            d = {
                    'latitude': lat,
                    'longitude': lon,
                    'city': city,
                    'province': province,
                    'country': country,
                    'age': '',
                    'sex': '',
                    'symptoms': '',
                    'source': '',
                    'date_confirmation' : '',
                    'cases': count,
                    'geo_resolution': geo_resolution
                }
            results.append(d)

    return results

def animation_formating(infile):
    '''
    Read from "full-data" and convert to something usable for the animation.
    '''

    with open(infile, 'r') as F:
        data = json.load(F)

    data = data['data']
    data = pd.DataFrame(data)
    data = data[['latitude', 'longitude', 'date_confirmation']]

    # drop #REF! in case they are propagated here :
    data = data[data.latitude != '#REF!']
    data = data[data.longitude != '#REF!']
    data = data[data.date_confirmation != '#REF!']

    data['date']  = pd.to_datetime(data.date_confirmation, errors='coerce', format='%d.%m.%Y')
    data['coord'] = data.apply(lambda s: str('{}|{}'.format(s['latitude'], s['longitude'])), axis=1)
#    data.drop(['date_confirmation', 'latitude', 'longitude'], inplace=True, axis=1)
    data.dropna(inplace=True)

    # Sort so that results are in order (might be important for animation)
    data.sort_values(by='date', inplace=True)

    sums    = {} # To store cumulative sums at each location
    results = {}

    # Loop through dates and coordinates and count
    for date in data.date.unique():
        datestr = pd.to_datetime(date).strftime('%Y-%m-%d') # unique coverts to np.datetime64, which doesn't have strftime.

        if datestr not in results.keys():
            results[datestr] = []

        subset = data[data.date == date]
        for coord in subset.coord.unique():
            N_cases = len(subset[subset.coord == coord])

            if coord not in sums.keys():
                sums[coord] = N_cases
            else:
                sums[coord] += N_cases


            lat, long = coord.split('|')
            results[datestr].append({'caseCount': sums[coord],
                                     'latitude': lat,
                                     'longitude': long})

            if sums[coord] < 10:
                pin = 'pin4.svg'
            elif sums[coord] >= 10 and sums[coord] < 25:
                pin = 'pin3.svg'
            elif sums[coord] >= 25 and sums[coord] < 50:
                pin = 'pin2.svg'
            else:
                pin = 'pin1.svg'

            results[datestr][-1]['pin'] = pin

    # Reformatting data to fit with animation script :
    dates = results.keys()
    array = [{d: results[d]} for d in dates]

    return array


def round_lat_long(lat_or_lng):
    return str(round(float(lat_or_lng), LAT_LNG_DECIMAL_PLACES))

def latlong_to_geo_id(lat, lng):
  '''
  Returns a string key from a latitude and longitude.
  '''
  return "|".join([str(round(float(a), LAT_LNG_DECIMAL_PLACES)) for a in [lat, lng]])

def find_country_iso_code_from_name(name, dict):
  if name == "nan":
    return ""
  # If this is already a 2-letter ISO code, return it as-is
  if len(name) == 2 and name == name.upper():
    return name
  if name in dict:
    return dict[name]
  for key in dict:
    if key.lower() == name.lower():
      return dict[key]

  print("Sorry, I don't know about '" + name + "', you might want "
        "to update the country data file.")
  sys.exit(1)

def compile_location_info(in_data, out_file,
    keys=["country", "province", "city"], country_file="app/countries.data",
    quiet=False):

    if not quiet:
        print("Reading country data...")
    countries = {}
    with open(country_file) as f:
        country_data = f.read().strip()
        for country in country_data.split("|"):
            (name, iso) = country.split(":")
            countries[name] = iso
        f.close()

    location_info = {}
    for item in in_data:
        geo_id = item['geoid']
        if geo_id not in location_info:
            # 2-letter ISO code for the country
            country_iso = find_country_iso_code_from_name(
                          str(item[keys[0]]), countries)
            location_info[geo_id] = [(str(item[key]) if str(item[key]) != "nan" else "") for key in [keys[2], keys[1]]] + [country_iso]

    output = []
    for geoid in location_info:
        output.append(geoid + ":" + ",".join(location_info[geoid]))
    with open(out_file, "w") as f:
        f.write("\n".join(output))
        f.close()
