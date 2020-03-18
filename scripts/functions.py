import json
import pickle
import os.path
import configparser
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from shutil import copyfile

def log_message(message, config):
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
        json.dump(data, F, indent=4)



def load_sheet(data_range: str, config: configparser.ConfigParser) -> pd.DataFrame:
    scopes      = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds       = None
    token       = config['SHEETS'].get('TOKEN', './token.pickle')
    credentials = config['SHEETS'].get('CREDENTIALS', './credentials.json')
    spreadsheetid = config['SHEETS'].get('SPREADSHEETID')

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
        log_message('ERROR: data not found')
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
                    message = f'ERROR :  {repr(Err)}'
                    log_message(message)
                    raise Err
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

    # constants
    name_cols = ['city', 'province', 'country']

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
    for c in name_cols:
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
                    'city': '',
                    'province': '',
                    'country': '',
                    'age': '',
                    'sex': '',
                    'symptoms': '',
                    'source': '',
                    'date_confirmation' : '',
                    'cases': count,
                    'geo_resolution': ''
                }
            results.append(d)

    return results

def animation_formating(infile: str, outfile: str, groupby: str = 'week') -> None:
    '''
    Read from full data file, and reformat for animation. 
    Currently grouping on a weekly basis, but subject to change as 
    new cases come in (produces large files). 
    '''
    with open(infile, 'r') as F:
        data = json.load(F)

    df1  = pd.DataFrame(data['outside_Hubei'], dtype=str)
    df2  = pd.DataFrame(data['Hubei'], dtype=str)
    full = pd.concat([df1, df2], ignore_index=True)
    full.fillna('', inplace=True)
    full['geoid']  = full.apply(lambda s: s['latitude'] + '|' + s['longitude'], axis=1) # To reference locations by a key
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

    # Put in feature collection and save
    animation = {"type": "FeatureCollection", "features": timeline}
    with open(outfile, 'w') as F:
        json.dump(animation, F)


