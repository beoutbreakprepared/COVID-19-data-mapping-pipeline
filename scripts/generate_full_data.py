#!/usr/bin/env python3

'''
Pull data from latestdata.csv, and JHU repo for US
split into daily slices.
'''

import argparse
import json
import functions
import os
import multiprocessing
import pandas as pd
import re
import requests
import split
import sys

from io import StringIO

JHU_URL= 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'

LATEST_DATA_URL = 'https://raw.githubusercontent.com/beoutbreakprepared/nCoV2019/master/latest_data/latestdata.csv'


parser = argparse.ArgumentParser(description='Generate full-data.json file')

parser.add_argument('out_dir', type=str, default = '.',
        help='path to dailies directory')

parser.add_argument('-l', '--latest', type=str, default=False,
        help='path to read latestdata.csv locally, fetch from github otherwise')

parser.add_argument('-f', '--full', type=str, default=False,
        help="option to save full-data")

parser.add_argument('-j', '--jhu', type=str,
        help='Option to save jhu data (before formating)',
        default=False)


parser.add_argument('-t', '--timeit', action='store_const', const=True,
        help='option to print execution time')

parser.add_argument('--input_jhu', default='', type=str,
        help='read from local jhu file')


def prepare_latest_data(infile, quiet=False):
    if infile :
        readfrom = infile
    else:
        if not quiet:
            print("Downloading latest data...")
        req = requests.get(LATEST_DATA_URL)
        if req.status_code != 200:
            print('could not get latestdata.csv, aborting')
            sys.exit(1)
        readfrom = StringIO(req.text)


    df = pd.read_csv(readfrom, usecols=['city', 'province', 'country',
        'date_confirmation', 'latitude', 'longitude'])

    df['latitude'] = df.latitude.astype(str)
    df['longitude'] = df.longitude.astype(str)

    # filters
    df = df[~df.country.isin(['United States', 'Virgin Islands, U.S.', 'Puerto Rico'])]
    df = df[~df.latitude.isnull() | df.longitude.isnull()]
    df = df[~df.latitude.str.contains('[aA-zZ]', regex=True)]
    df = df[~df.longitude.str.contains('[aA-zZ]', regex=True)]
    df['date_confirmation'] = df.date_confirmation.str.extract('(\d{2}\.\d{2}\.\d{4})')
    df = df[pd.to_datetime(df.date_confirmation,
        format="%d.%m.%Y", errors='coerce') < pd.datetime.now()]

    df["geoid"] = df.apply(lambda row: functions.latlong_to_geo_id(
        row.latitude, row.longitude), axis=1)

    # Extract mappings between lat|long and geographical names, then only keep
    # the geo_id.
    functions.compile_location_info(df.to_dict("records"),
        "app/location_info_world.data", quiet=quiet)
    df = df.drop(['city', 'province', 'country', 'latitude', 'longitude'], axis=1)

    dates  = df.date_confirmation.unique()
    geoids = df.geoid.unique()
    geoids.sort()

    new = pd.DataFrame(columns=geoids, index=dates)
    new.index.name = 'date'
    for i in new.index:
        counts = df[df.date_confirmation == i].geoid.value_counts()
        new.loc[i] = counts
    new = new.fillna(0)
    new.reset_index(drop=False)
    return new

def prepare_jhu_data(outfile, read_from_file, quiet=False):
    '''
    Get JHU data from URL and format to
    to be compatible with full-data.json
    (used for US data)
    '''

    if read_from_file:
        read_from = read_from_file
    else:
        # Get JHU data
        if not quiet:
            print("Downloading data from JHU...")
        req = requests.get(JHU_URL)
        if req.status_code != 200:
            print('Could not get JHU data, aborting')
            sys.exit(1)
        read_from = StringIO(req.text)

    df = pd.read_csv(read_from)

    if outfile:
        df.to_csv(outfile, index=False)

    roundto = functions.LAT_LNG_DECIMAL_PLACES
    df['Lat'] = df.Lat.round(roundto)
    df['Long_'] = df.Long_.round(roundto)

    # do some filtering
    df = df.dropna()
    df = df[df.Admin2 != 'Unassigned']
    df = df[~((df.Lat == 0) & (df.Long_ == 0))]

    df["geoid"] = df.apply(lambda row: functions.latlong_to_geo_id(
        row['Lat'], row['Long_']), axis=1)
    functions.compile_location_info(df.to_dict("records"),
        out_file="app/location_info_us.data",
        keys=["Country_Region", "Province_State", "Admin2"],
        quiet=quiet)

    rx = '\d{1,2}/\d{1,2}/\d'
    date_columns = [c for c in df.columns if re.match(rx, c)]
    keep = ['geoid'] + date_columns
    df = df[keep]

    # rename to match latestdata format
    new_dates = []
    for c in date_columns:
        month, day, year = c.split('/')
        month = month.zfill(2)
        day = day.zfill(2)
        year = '20' + year if len(year) == 2 else year
        new = f'{day}.{month}.{year}'
        new_dates.append(new)
    df.rename(dict(zip(date_columns, new_dates)), axis=1, inplace=True)

    df = df.set_index('geoid')
    df = df - df.shift(1, axis=1).fillna(0).astype(int)

    # some entries are inconsistent, i.e. not really cumulative for those
    # we assign a value of zero (for new cases).  Induces a bit of error, but
    # preferable than ignoring entirely.
    df[df < 0] = 0

    df = df.T
    df.index.name = 'date'
    df.reset_index(inplace=True)
    return df

def daily_slice(new_cases, total_cases):
    # full starts from new cases by location/date
    # structure for daily slice YYYY.MM.DD.json
    #{"date": "YYYY-MM-DD", "features": [{"properties": {"geoid": "lat|long",
    # "new": int, "total": int}}, ... ]

    assert new_cases.name == total_cases.name, "mismatched dates"

    features = []

    for id in new_cases.index:
        new = int(new_cases[id])
        total = int(total_cases[id])
        if new == total == 0:
            continue
        properties = {"geoid": id, "total": total}
        if new != 0:
          properties['new'] = new

        features.append({"properties": properties})

    return {"date": new_cases.name.replace(".", "-"), "features": features}

def chunks(new_cases, total_cases):
    '''
    Yields successive equal-sized chunks from the input list.
    '''
    for i in range(len(new_cases)):
        yield (new_cases.iloc[i], total_cases.iloc[i])

def generate_data(out_dir, latest=False, jhu=False, input_jhu='',
    export_full_data=False, overwrite=False, quiet=False):

  latest = prepare_latest_data(latest, quiet=quiet)
  jhu = prepare_jhu_data(jhu, input_jhu, quiet=quiet)
  full = latest.merge(jhu, on='date', how='outer')
  full.fillna(0, inplace=True)
  full = full.set_index('date')
  for c in full.columns:
      if c == 'date':
          continue

      full[c] = full[c].astype(int)

  # drop columns with negative values (errors in JHU data)
  # Hopefully they will be fixed at some point.
  if export_full_data:
      full.to_csv(export_full_data)

  latest_date = split.normalize_date(full.index[-1]).replace('.', '-')

  full.index = [split.normalize_date(x) for x in full.index]
  full.index.name = 'date'
  full = full.sort_values(by='date')

  new_cases = full
  total_cases = new_cases.cumsum()

  n_cpus = multiprocessing.cpu_count()
  if not quiet:
      print("Processing " + str(len(full)) + " features "
            "with " + str(n_cpus) + " threads...")

  pool = multiprocessing.Pool(n_cpus)
  out_slices = pool.starmap(daily_slice, chunks(new_cases, total_cases), chunksize=10)

  for s in out_slices:
    out_name = ("latest" if s['date'] == latest_date else s['date'].replace('-','.')) + '.json'
    daily_slice_file_path = os.path.join(out_dir, out_name)

    if not overwrite and os.path.exists(daily_slice_file_path):
        print("I will not clobber '" + daily_slice_file_path + "', " "please delete it first")
        continue

    with open(daily_slice_file_path, "w") as f:
        f.write(json.dumps(s))

  # Concatenate location info for the US and elsewhere
  os.system("rm -f app/location_info.data")
  os.system("cat app/location_info_world.data app/location_info_us.data > "
            "app/location_info.data")
  os.remove("app/location_info_world.data")
  os.remove("app/location_info_us.data")

if __name__ == '__main__':
    args = parser.parse_args()

    if args.timeit:
        import time
        t0 = time.time()

    generate_data(args.out_dir, args.latest, args.jhu, args.input_jhu, args.full)

    if args.timeit:
        print(round(time.time() - t0, 2), "seconds")
