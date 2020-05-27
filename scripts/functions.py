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

import data_util

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


def round_lat_long(lat_or_lng):
    return str(round(float(lat_or_lng), LAT_LNG_DECIMAL_PLACES))


def compile_location_info(in_data, out_file,
                          keys=["country", "province", "city"], quiet=False):

    if not quiet:
        print("Exporting location info...")
    location_info = {}
    for item in in_data:
        geo_id = item['geoid']
        if geo_id not in location_info:
            name = str(item[keys[0]])
            # 2-letter ISO code for the country
            if name == "nan":
                code = ""
            else:
                code = data_util.country_code_from_name(name)
            location_info[geo_id] = [(str(item[key]) if str(item[key]) != "nan"
                                      else "") for key in
                                     [keys[2], keys[1]]] + [code]

    output = []
    for geoid in location_info:
        output.append(geoid + ":" + ",".join(location_info[geoid]))
    with open(out_file, "w") as f:
        f.write("\n".join(output))
        f.close()
