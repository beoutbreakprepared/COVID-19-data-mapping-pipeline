import configparser
import itertools
import json
import multiprocessing
import os.path
import pandas as pd
import pickle
import re

from datetime import datetime, timedelta
from shutil import copyfile

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

CHUNK_SIZE = 1000
def chunks(all_features):
    '''
    Yields successive equal-sized chunks from the input list.
    '''
    for i in range(0, len(all_features), CHUNK_SIZE):
        yield all_features[i:i + CHUNK_SIZE]

def animation_formating_geo(infile: str, outfile: str, groupby: str = 'week') -> None:
    '''
    Read from full data file, and reformat for animation. 
    Currently grouping on a weekly basis, but subject to change as 
    new cases come in (produces large files). 
    '''
    print("Reading file...")
    with open(infile, 'r') as F:
        in_data = json.load(F)

    n_cpus = multiprocessing.cpu_count()
    all_features = in_data["data"]
    print("Processing " + str(len(all_features)) + " "
          "features in chunks of " + str(int(len(all_features) / CHUNK_SIZE)) + " "
          "with " + str(n_cpus) + " threads...")
    pool = multiprocessing.Pool(n_cpus)
    out_slices = pool.map(animation_formatting_geo_in_memory, chunks(all_features))
    # Concatenate everybody.
    out_data = list(itertools.chain.from_iterable(out_slices))

    # Wrap in feature collection and write to disk
    print("Writing result...")
    with open(outfile, 'w') as F:
        json.dump({"type": "FeatureCollection", "features": out_data}, F)


def animation_formatting_geo_in_memory(in_data: str, groupby: str = 'week') -> None:
    # Give the caller an idea of the process we're making.
    print(".", end="", flush=True)
    full = pd.DataFrame(in_data)

    full.fillna('', inplace=True)
    full['geoid']  = full.apply(lambda s: s['latitude'] + '|' + s['longitude'], axis=1) # To reference locations by a key
    full['date_confirmation'] = full.date_confirmation.apply(lambda x: x.split('-')[0].strip())    

    full['date']   = pd.to_datetime(full['date_confirmation'], format="%d.%m.%Y")  # to ensure sorting is done by date value (not str)
    
    if groupby == 'week':
        full['date'] = full.date.apply(lambda x : x - timedelta(days=x.weekday()))
        freq = 'W-MON'
    else:
        freq = 'D'

    dmin   = full.date.min()
    dmax   = full.date.max()
    drange = pd.date_range(dmin, dmax, freq=freq)

    geoids  = full.geoid.unique()
    counts  = full.groupby(['date', 'geoid']).count()[['ID']]

    # Build reference table (to plug back in city/province/country later)
    reference = pd.DataFrame(columns = ['geoid', 'city', 'province', 'country', 'geo_resolution'])
    for i in full.geoid.unique():
        arow = full[full.geoid==i].iloc[0]
        reference = reference.append({'geoid': i, 'city': arow['city'], 'province': arow['province'],
                                      'country': arow['country'], 'geo_resolution': arow['geo_resolution']}, ignore_index=True)
    reference.set_index('geoid', inplace=True)

    timeline      = []
    has_entry     = []
    latest_counts = {geoid: 0 for geoid in geoids}

    # Loop over dates to get counts
    for d in drange:
        if d in counts.index:
            new_cases  = counts.loc[d]

        else:
            continue

        for geoid in geoids:
            if geoid in new_cases.index:
                N_new = int(new_cases.loc[geoid]['ID']) # json.dump doesn't support numpy.int64?
                total = latest_counts[geoid] + N_new
                latest_counts[geoid] += N_new

            elif geoid in has_entry:
                # repeat location so it doesn't disappear in animation
                N_new = 0
                total = latest_counts[geoid]
            else:
                continue

            if N_new == total == 0:
                raise Exception('This shouldn\'t be possible')

            lat, lon = geoid.split('|')
            ref = reference.loc[geoid]
            entry = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            float(lon),
                            float(lat)
                        ]
                    },
                    "properties": {
                        "date": d.strftime('%Y-%m-%d'),
                        "new": N_new,
                        "total": total,
                        "city": ref['city'],
                        "province": ref['province'],
                        "country": ref['country'],
                        "geo_resolution" : ref['geo_resolution']
                    }
            }

            timeline.append(entry)
            if geoid not in has_entry:
                has_entry.append(geoid)
            
    assert len(geoids) == len(has_entry), "Grouping failed"

    return timeline


def convert_to_geojson(infile, outfile):
    '''
    Convert aggregated file to geojson.
    '''
    geojson_format = {'type': 'Feature', 'geometry': 
            {"type": "Point", 
                "coordinates": None}, 
            'properties': {'age': 'age', 'city': 'city',
                'province': 'province', 
                'country': 'country', 
                'date': 'date_confirmation', 'sex': 'sex', 'source': 'source', 'symptoms': 'symptoms'}}
    geojson_data = []   


    with open(infile, 'r') as F:
        data = json.load(F)
    df = pd.DataFrame(data['data'])

    for i, row in df.iterrows():
        d = geojson_format.copy()
        entry = {
                'type' : 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(row['longitude']), float(row['latitude'])]
                    },
                'properties': {
                    'age': row['age'],
                    'sex': row['sex'],
                    'city': row['city'],
                    'province': row['province'],
                    'country': row['country'],
                    'date': row['date_confirmation'],
                    'source': row['source'],
                    'symptoms': row['symptoms'],
                    'cases': row['cases'],
                    'geo_resolution': row['geo_resolution']
                }
                }
        geojson_data.append(entry)
    final = {'type': 'FeatureCollection', 
            'features': geojson_data}

    with open(outfile, 'w') as F:
        json.dump(final, F)

