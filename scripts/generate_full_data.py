#!/usr/bin/env python3

'''
Pull data from latestdata.csv, and JHU repo for US
split into daily slices.
'''

import pandas as pd
import requests
import argparse
import sys
from io import StringIO
import re
import json
import os
import split
import multiprocessing


jhu_url= 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'

latestdata_url = 'https://raw.githubusercontent.com/beoutbreakprepared/nCoV2019/master/latest_data/latestdata.csv'




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


def prepare_latest_data(infile, **kwargs):
    if infile :
        readfrom = infile
    else:
        req = requests.get(latestdata_url)
        if req.status_code != 200:
            print('could not get latestdata.csv, aborting')
            sys.exit(1)
        readfrom = StringIO(req.text)

    df = pd.read_csv(readfrom,
            usecols=['country', 'date_confirmation', 'latitude', 'longitude'])

    roundto = kwargs.get('roundto', 4)
    df['latitude'] = df.latitude.round(roundto).astype(str)
    df['longitude'] = df.longitude.round(roundto).astype(str)

    # filters
    df = df[~df.country.isin(['United States', 'Virgin Islands, U.S.', 'Puerto Rico'])]
    df = df[~df.latitude.isnull() | df.longitude.isnull()]
    df = df[~df.latitude.str.contains('[aA-zZ]', regex=True)]
    df = df[~df.longitude.str.contains('[aA-zZ]', regex=True)]
    df['date_confirmation'] = df.date_confirmation.str.extract('(\d{2}\.\d{2}\.\d{4})')
    df = df[pd.to_datetime(df.date_confirmation,
        format="%d.%m.%Y", errors='coerce') < pd.datetime.now()]


    # geoids
    df['geoid'] = df['latitude'] + '|' + df['longitude']
    df = df.drop(['country', 'latitude', 'longitude'], axis=1)

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

def prepare_jhu_data(outfile, read_from_file, **kwargs):
    '''
    Get JHU data from URL and format to
    to be compatible with full-data.json
    (used for US data)
    '''

    if read_from_file:
        read_from = read_from_file
    else:
        # Get JHU data
        req = requests.get(jhu_url)
        if req.status_code != 200:
            print('Could not get JHU data, aborting')
            sys.exit(1)
        read_from = StringIO(req.text)

    df = pd.read_csv(read_from)

    if outfile:
        df.to_csv(outfile, index=False)

    roundto = kwargs.get('roundto', 4)
    df['Lat'] = df.Lat.round(roundto)
    df['Long_'] = df.Long_.round(roundto)

    # do some filtering
    df = df.dropna()
    df = df[df.Admin2 != 'Unassigned']
    df = df[~((df.Lat == 0) & (df.Long_ == 0))]

    df['geoid'] = df.Lat.astype(str) + '|' + df['Long_'].astype(str)
    df.drop(['Lat', 'Long_'], axis=1, inplace=True)

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

    date = new_cases.name
    features = []
    daily_dict = {"date": date.replace('.', '-'),
                "features": []}

    for id in new_cases.index:
        if new == total == 0:
            continue
        properties = {"geoid": id, "total": int(total_cases[id])}
        if new_cases[id] != 0:
          properties['new'] = int(new_cases[id])

        features.append({"properties": properties})

    return {"date": new_cases.name.replace(".", "-"), "features": features}

def chunks(new_cases, total_cases):
    '''
    Yields successive equal-sized chunks from the input list.
    '''
    for i in range(len(new_cases)):
        yield (new_cases.iloc[i], total_cases.iloc[i])

def main():
  args = parser.parse_args()

  if args.timeit:
      import time
      t0 = time.time()

  latest = prepare_latest_data(args.latest)
  jhu = prepare_jhu_data(args.jhu, args.input_jhu)
  full = latest.merge(jhu, on='date', how='outer')
  full.fillna(0, inplace=True)
  full = full.set_index('date')
  for c in full.columns:
      if c == 'date':
          continue
      else :
          full[c] = full[c].astype(int)

  # drop columns with negative values (errors in JHU data)
  # Hopefully they will be fixed at some point.
  if args.full:
      full.to_csv(args.full)

  latest_date = split.normalize_date(full.index[-1]).replace('.', '-')

  full.index = [split.normalize_date(x) for x in full.index]
  full.index.name = 'date'
  full = full.sort_index(by='date')

  new_cases = full
  total_cases = new_cases.cumsum()

  n_cpus = multiprocessing.cpu_count()
  print("Processing " + str(len(full)) + " features "
          "with " + str(n_cpus) + " threads...")

  pool = multiprocessing.Pool(n_cpus)
  out_slices = pool.starmap(daily_slice, chunks(new_cases, total_cases), chunksize=10)

  for s in out_slices:
    out_name = ("latest" if s['date'] == latest_date else s['date'].replace('-','.')) + '.json'
    daily_slice_file_path = os.path.join(args.out_dir, out_name)

    if os.path.exists(daily_slice_file_path):
        print("I will not clobber '" + daily_slice_file_path + "', " "please delete it first")
        continue

    with open(daily_slice_file_path, "w") as f:
        f.write(json.dumps(s))

  if args.timeit:
      print(round(time.time() - t0, 2), "seconds")

if __name__ == '__main__':
    main()
